"""SQL doğrulayıcı testleri (veritabanı gerektirmez)."""
import pytest

from app.security.sql_validator import validate_select_sql as validate

ALLOWED = [
    "SELECT name, price FROM products ORDER BY price DESC LIMIT 5",
    "SELECT * FROM ai.products",
    "SELECT * FROM PRODUCTS",
    "SELECT * FROM products;",
    """SELECT p.name, SUM(si.quantity) AS total_qty
       FROM sale_items si JOIN products p ON p.product_id = si.product_id
       JOIN sales s ON s.sale_id = si.sale_id
       WHERE s.status = 'completed' AND s.sale_date >= date_trunc('month', current_date)
       GROUP BY p.name ORDER BY total_qty DESC LIMIT 5""",
    "WITH t AS (SELECT sale_id, total_amount FROM sales) SELECT SUM(total_amount) FROM t",
    "SELECT to_char(sale_date, 'YYYY-MM') AS month, SUM(total_amount) FROM sales GROUP BY 1",
    "SELECT name FROM products WHERE name LIKE '%aspirin%'",
    "SELECT COUNT(*) FROM products WHERE stock_quantity < min_stock_level",
    "SELECT name FROM products WHERE expiry_date <= current_date + INTERVAL '60 days'",
    "SELECT payment_method, COUNT(*) FROM payments GROUP BY payment_method",
    "SELECT SUM(sgk_covered_amount), SUM(patient_copay) FROM prescription_items",
    "SELECT product_id FROM products UNION SELECT product_id FROM sale_items",
]

# (sql, beklenen hata kodu)
BLOCKED = [
    ("", "EMPTY"),
    ("   ", "EMPTY"),
    ("DROP TABLE products", "FORBIDDEN_STATEMENT"),
    ("DELETE FROM products", "FORBIDDEN_STATEMENT"),
    ("UPDATE products SET price = 0", "FORBIDDEN_STATEMENT"),
    ("INSERT INTO products(name) VALUES ('x')", "FORBIDDEN_STATEMENT"),
    ("TRUNCATE products", "FORBIDDEN_STATEMENT"),
    ("SET ROLE postgres", "FORBIDDEN_STATEMENT"),
    ("COPY products TO '/tmp/x'", "FORBIDDEN_STATEMENT"),
    ("EXPLAIN ANALYZE SELECT 1", "FORBIDDEN_STATEMENT"),
    ("SELECT 1; DROP TABLE products", "MULTIPLE_STATEMENTS"),
    ("SELECT * FROM products; SELECT * FROM sales", "MULTIPLE_STATEMENTS"),
    ("SELECT * FROM users", "TABLE_NOT_ALLOWED"),
    ("SELECT * FROM public.users", "TABLE_NOT_ALLOWED"),
    ("SELECT * FROM public.products", "TABLE_NOT_ALLOWED"),
    ("SELECT * FROM audit_logs", "TABLE_NOT_ALLOWED"),
    ("SELECT * FROM customers", "TABLE_NOT_ALLOWED"),
    ("SELECT * FROM pg_catalog.pg_tables", "TABLE_NOT_ALLOWED"),
    ("SELECT * FROM information_schema.tables", "TABLE_NOT_ALLOWED"),
    ("SELECT * FROM otherdb.ai.products", "TABLE_NOT_ALLOWED"),
    ("SELECT password_hash FROM products", "COLUMN_NOT_ALLOWED"),
    ("SELECT customer_id FROM sales", "COLUMN_NOT_ALLOWED"),
    ("SELECT user_id FROM sales", "COLUMN_NOT_ALLOWED"),
    ("SELECT pg_sleep(10)", "FORBIDDEN_FUNCTION"),
    ("SELECT current_setting('search_path')", "FORBIDDEN_FUNCTION"),
    ("SELECT query_to_xml('select 1', true, true, '')", "FORBIDDEN_FUNCTION"),
    ("SELECT lo_import('/etc/passwd')", "FORBIDDEN_FUNCTION"),
    ("SELECT version()", "FORBIDDEN_FUNCTION"),
    ("SELECT current_user", "FORBIDDEN_FUNCTION"),
    ("SELECT current_database()", "FORBIDDEN_FUNCTION"),
    ("SELECT * FROM generate_series(1, 100)", "FORBIDDEN_CONSTRUCT"),
    ("SELECT * FROM unnest(ARRAY[1, 2])", "FORBIDDEN_CONSTRUCT"),
    ("SELECT * FROM products, LATERAL (SELECT 1) x", "FORBIDDEN_CONSTRUCT"),
    ("SELECT * INTO leaked FROM products", "FORBIDDEN_CONSTRUCT"),
    ("SELECT * FROM products FOR UPDATE", "FORBIDDEN_CONSTRUCT"),
    ("WITH d AS (DELETE FROM products RETURNING *) SELECT * FROM d", "FORBIDDEN_CONSTRUCT"),
    ("WITH u AS (UPDATE products SET price = 0 RETURNING *) SELECT * FROM u", "FORBIDDEN_CONSTRUCT"),
    ("SELECT * FROM products WHERE product_id = $1", "FORBIDDEN_CONSTRUCT"),
    ("SELECT * FROM products WHERE product_id = :id", "FORBIDDEN_CONSTRUCT"),
    ("VALUES (1)", "NOT_SELECT"),
]


@pytest.mark.parametrize("sql", ALLOWED)
def test_allowed_queries_pass(sql):
    result = validate(sql)
    assert result.ok, f"reddedilmemeliydi: {result.code}"
    assert result.sql and result.sql.upper().startswith(("SELECT", "WITH"))


@pytest.mark.parametrize("sql,code", BLOCKED)
def test_dangerous_queries_are_blocked(sql, code):
    result = validate(sql)
    assert not result.ok
    assert result.code == code
    assert result.sql is None


def test_blocked_messages_do_not_leak_schema_or_internals():
    for sql, _ in BLOCKED:
        r = validate(sql)
        msg = (r.message or "").lower()
        for secret in ("password", "users", "public", "pg_", "ai_readonly", "postgres"):
            assert secret not in msg, (sql, msg)


def test_limit_added_when_missing():
    assert validate("SELECT name FROM products", max_rows=500).sql.endswith("LIMIT 501")


def test_limit_capped_when_too_large():
    assert validate("SELECT name FROM products LIMIT 100000", max_rows=500).sql.endswith("LIMIT 501")


def test_small_user_limit_is_kept():
    assert validate("SELECT name FROM products LIMIT 3", max_rows=500).sql.endswith("LIMIT 3")


def test_limit_added_to_union():
    r = validate("SELECT product_id FROM products UNION SELECT product_id FROM sale_items", max_rows=100)
    assert r.ok and r.sql.endswith("LIMIT 101")


def test_schema_prefix_is_normalized():
    assert " ai." not in validate("SELECT name FROM ai.products").sql


def test_comments_are_stripped_from_executed_sql():
    r = validate("SELECT name FROM products -- ; DROP TABLE products")
    assert r.ok
    assert "DROP" not in r.sql.upper()
    r = validate("SELECT name /* DELETE FROM products */ FROM products")
    assert r.ok and "DELETE" not in r.sql.upper()


def test_too_long_query_rejected():
    assert validate("SELECT " + "1," * 3000 + "1").code == "TOO_LONG"


def test_garbage_rejected_without_exception():
    for junk in ["SELEC * FROM", "((((", "SELECT * FROM products WHERE", "'; DROP TABLE x; --"]:
        assert not validate(junk).ok


def test_cte_name_cannot_unlock_real_tables():
    # CTE adı 'users' olsa bile içindeki gerçek 'users' tablosuna erişim yine reddedilir
    r = validate("WITH users AS (SELECT * FROM users) SELECT * FROM users")
    assert not r.ok and r.code == "TABLE_NOT_ALLOWED"


def test_quoted_uppercase_identifier_does_not_bypass_allowlist():
    assert not validate('SELECT * FROM "Products"').ok


def test_non_string_input_is_rejected_safely():
    assert not validate(None).ok


@pytest.mark.parametrize("sql", [
    "WITH pg_tables AS (SELECT * FROM pg_tables) SELECT * FROM pg_tables",
    "WITH pg_roles AS (SELECT * FROM pg_roles) SELECT * FROM pg_roles",
    "WITH a AS (SELECT * FROM b), b AS (SELECT * FROM products) SELECT * FROM a",   # ileri referans geçersiz
    "SELECT * FROM (WITH x AS (SELECT 1) SELECT 1) s, x",                            # x kapsam dışı
])
def test_cte_scoping_attacks_are_blocked(sql):
    r = validate(sql)
    assert not r.ok and r.code == "TABLE_NOT_ALLOWED"


@pytest.mark.parametrize("sql", [
    "WITH a AS (SELECT product_id FROM products), b AS (SELECT product_id FROM a) SELECT * FROM b",
    "SELECT * FROM (WITH x AS (SELECT product_id FROM products) SELECT * FROM x) s",
    "WITH RECURSIVE n AS (SELECT 1 AS i UNION ALL SELECT i + 1 FROM n WHERE i < 5) SELECT * FROM n",
    "WITH monthly AS (SELECT date_trunc('month', sale_date) m, SUM(total_amount) t FROM sales GROUP BY 1) "
    "SELECT m, t FROM monthly ORDER BY m",
])
def test_legitimate_cte_usage_still_works(sql):
    assert validate(sql).ok
