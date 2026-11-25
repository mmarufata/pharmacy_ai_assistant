"""MCP araç mantığı testleri (doğrulayıcı + salt okunur bağlantı + denetim kaydı birlikte)."""
import pytest
from sqlalchemy import text

from app.mcp_server import tools

pytestmark = pytest.mark.db


def audit_rows(db, action_prefix):
    with db.connect() as c:
        return c.execute(text("select action_type, action_description from audit_logs where action_type like :p order by log_id"),
                         {"p": action_prefix + "%"}).fetchall()


def test_valid_query_returns_rows_and_columns(db):
    r = tools.execute_readonly_sql("SELECT name, stock_quantity FROM products ORDER BY name LIMIT 3")
    assert r["status"] == "ok" and r["columns"] == ["name", "stock_quantity"]
    assert r["row_count"] == 3 and len(r["rows"]) == 3 and r["truncated"] is False
    assert "executed_sql" in r and r["duration_ms"] >= 0


def test_top_selling_products_query(db):
    r = tools.execute_readonly_sql("""
        SELECT p.name, SUM(si.quantity) AS total_qty, SUM(si.line_total) AS revenue
        FROM sale_items si JOIN products p ON p.product_id = si.product_id
        JOIN sales s ON s.sale_id = si.sale_id
        WHERE s.status = 'completed' GROUP BY p.name ORDER BY total_qty DESC LIMIT 5""")
    assert r["status"] == "ok" and r["row_count"] == 5
    qtys = [row[1] for row in r["rows"]]
    assert qtys == sorted(qtys, reverse=True)
    assert all(isinstance(row[2], float) for row in r["rows"])  # Decimal -> JSON uyumlu


def test_like_with_percent_works(db):
    r = tools.execute_readonly_sql("SELECT name FROM products WHERE name LIKE '%Vitamin%'")
    assert r["status"] == "ok" and r["row_count"] >= 1


def test_results_are_json_serializable(db):
    import json
    r = tools.execute_readonly_sql("SELECT sale_date, total_amount FROM sales LIMIT 2")
    json.dumps(r)


def test_empty_result_is_ok_not_error(db):
    r = tools.execute_readonly_sql("SELECT name FROM products WHERE name = 'yok-boyle-urun'")
    assert r["status"] == "ok" and r["row_count"] == 0 and r["rows"] == []


def test_row_limit_and_truncation_flag(db):
    r = tools.execute_readonly_sql("SELECT sale_item_id FROM sale_items")  # 1000+ satır var
    assert r["row_count"] == 500 and r["truncated"] is True
    r = tools.execute_readonly_sql("SELECT sale_item_id FROM sale_items LIMIT 500")
    assert r["row_count"] == 500 and r["truncated"] is False


@pytest.mark.parametrize("sql", [
    "DELETE FROM products", "DROP TABLE products", "SELECT * FROM users", "SELECT * FROM public.products",
    "SELECT password_hash FROM products", "SELECT pg_sleep(5)", "SELECT 1; SELECT 2",
    "WITH pg_tables AS (SELECT * FROM pg_tables) SELECT * FROM pg_tables",
])
def test_dangerous_queries_rejected_with_safe_message(db, sql):
    r = tools.execute_readonly_sql(sql)
    assert r["status"] == "rejected"
    for secret in ("password", "relation", "permission denied", "postgres", "psycopg", "ai_readonly"):
        assert secret not in r["message"].lower()


def test_database_error_is_sanitized(db):
    r = tools.execute_readonly_sql("SELECT 1 / 0")
    assert r["status"] == "error" and r["message"] == tools.SAFE_DB_ERROR
    assert "division" not in r["message"].lower()


def test_timeout_returns_friendly_message(db):
    # Kartezyen çarpım: doğrulayıcı izin verir, veritabanı zaman aşımıyla keser (test ortamında 1.5 sn)
    r = tools.execute_readonly_sql("SELECT COUNT(*) FROM sale_items a CROSS JOIN sale_items b CROSS JOIN sale_items c")
    assert r["status"] == "error" and r["message"] == tools.SAFE_TIMEOUT
    assert audit_rows(db, "mcp_query_timeout")


def test_audit_log_written_without_sql_text_or_data(db):
    secret_literal = "gizli-arama-metni-12345"
    tools.execute_readonly_sql(f"SELECT name FROM products WHERE name = '{secret_literal}'", user_id=None)
    tools.execute_readonly_sql("DROP TABLE products")
    rows = audit_rows(db, "mcp_query")
    assert any(a == "mcp_query_ok" for a, _ in rows)
    assert any(a == "mcp_query_blocked" for a, _ in rows)
    for _, desc in rows:
        assert secret_literal not in desc and "SELECT" not in desc.upper().replace("SELECT_", "") and "DROP" not in desc.upper()
    assert any("kod=FORBIDDEN_STATEMENT" in d for a, d in rows if a == "mcp_query_blocked")


def test_audit_log_records_user_id(db):
    uid = db.connect().execute(text("select user_id from users limit 1")).scalar_one()
    tools.execute_readonly_sql("SELECT 1", user_id=uid)
    with db.connect() as c:
        assert c.execute(text("select count(*) from audit_logs where user_id=:u and action_type='mcp_query_ok'"), {"u": uid}).scalar_one() >= 1


def test_get_database_schema_lists_only_allowed_views(db):
    r = tools.get_database_schema()
    names = {t["name"] for t in r["tables"]}
    assert r["status"] == "ok" and names == {"products", "suppliers", "sales", "sale_items", "payments",
                                              "stock_movements", "prescriptions", "prescription_items"}
    flat = str(r).lower()
    for secret in ("password_hash", "audit_logs", "query_history", "customers", "email"):
        assert secret not in flat


def test_get_table_info(db):
    r = tools.get_table_info("Products")
    assert r["status"] == "ok" and {c["name"] for c in r["table"]["columns"]} >= {"product_id", "stock_quantity"}
    assert all(c["description"] for c in r["table"]["columns"])


@pytest.mark.parametrize("name", ["users", "audit_logs", "public.users", "pg_tables", "", "products; DROP TABLE x", None, 5])
def test_get_table_info_rejects_unknown_or_forbidden(db, name):
    r = tools.get_table_info(name)
    assert r["status"] == "rejected"
    assert "users" not in r["message"].lower()  # tablonun var olup olmadığı sızdırılmaz


def test_get_database_statistics(db):
    r = tools.get_database_statistics()
    assert r["status"] == "ok" and r["row_counts"]["products"] > 0
    assert r["critical_stock_product_count"] > 0 and r["sales_date_range"]["first"] < r["sales_date_range"]["last"]
    assert "users" not in r["row_counts"]


def test_db_unavailable_gives_safe_message(db, monkeypatch):
    from sqlalchemy import create_engine
    broken = create_engine("postgresql+psycopg://ai_readonly:wrong@127.0.0.1:1/nodb", connect_args={"connect_timeout": 1})
    monkeypatch.setattr(tools, "get_ai_engine", lambda: broken)
    r = tools.execute_readonly_sql("SELECT 1")
    assert r["status"] == "error" and r["message"] == tools.SAFE_UNAVAILABLE
    assert "wrong" not in str(r) and "127.0.0.1" not in str(r)
