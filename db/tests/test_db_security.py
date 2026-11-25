"""Veritabanı düzeyi güvenlik testleri: ai_readonly rolü doğrulayıcı OLMADAN bile kısıtlı olmalı."""
import pytest
from sqlalchemy.exc import DBAPIError

from app.db.ai_views import AI_VIEWS, view_names

pytestmark = pytest.mark.db

SENSITIVE_COLUMNS = {"password_hash", "email", "first_name", "last_name", "customer_id", "user_id",
                     "insurance_status", "question", "error_message", "action_description", "description_text"}


def run(sql):
    from app.db.session import get_ai_engine
    with get_ai_engine().connect() as conn:
        return conn.exec_driver_sql(sql).fetchall()


def test_ai_role_can_read_approved_views(db):
    for v in view_names():
        assert run(f'SELECT count(*) FROM "{v}"')[0][0] >= 0


@pytest.mark.parametrize("sql", [
    "SELECT * FROM public.users",
    "SELECT * FROM public.products",
    "SELECT * FROM public.customers",
    "SELECT * FROM public.audit_logs",
    "SELECT * FROM public.query_history",
    "SELECT * FROM users",                      # search_path 'ai' olduğundan ilişki bulunamaz
])
def test_ai_role_cannot_read_base_tables(db, sql):
    with pytest.raises(DBAPIError):
        run(sql)


@pytest.mark.parametrize("sql", [
    "INSERT INTO products(name) VALUES ('x')",
    "UPDATE products SET price = 0",
    "DELETE FROM sales",
    "TRUNCATE products",
    "DROP VIEW ai.products",
    "CREATE TABLE ai.evil(a int)",
    "CREATE TEMP TABLE evil(a int)",
    "CREATE TABLE public.evil(a int)",
    "ALTER TABLE public.products ADD COLUMN x int",
    "GRANT ALL ON ai.products TO PUBLIC",
])
def test_ai_role_cannot_write_or_change_schema(db, sql):
    with pytest.raises(DBAPIError):
        run(sql)


def test_data_unchanged_after_attack_attempts(db):
    from sqlalchemy import text
    with db.connect() as c:
        assert c.execute(text("select count(*) from products")).scalar_one() > 0
        assert c.execute(text("select count(*) from sales")).scalar_one() > 0


def test_ai_role_is_not_privileged(db):
    row = run("SELECT rolsuper, rolcreaterole, rolcreatedb, rolreplication, rolbypassrls FROM pg_roles WHERE rolname = current_user")[0]
    assert not any(row)


def test_ai_role_settings(db):
    assert run("SHOW search_path")[0][0] == "ai"
    assert run("SHOW default_transaction_read_only")[0][0] == "on"
    assert run("SHOW statement_timeout")[0][0] in ("1500ms", "1.5s")


def test_statement_timeout_enforced_at_database_level(db):
    with pytest.raises(DBAPIError) as exc:
        run("SELECT pg_sleep(30)")
    assert "statement timeout" in str(exc.value).lower()


def test_views_expose_no_sensitive_columns(db):
    cols = run("""SELECT table_name, column_name FROM information_schema.columns WHERE table_schema = 'ai'""")
    exposed = {c for _, c in cols}
    assert not (exposed & SENSITIVE_COLUMNS), exposed & SENSITIVE_COLUMNS
    # veritabanındaki gerçek kolonlar, izin listesiyle birebir aynı olmalı
    for view, col in cols:
        assert col in [c[0] for c in AI_VIEWS[view]["columns"]]


def test_only_allowlisted_views_exist_in_ai_schema(db):
    objs = {r[0] for r in run("SELECT table_name FROM information_schema.tables WHERE table_schema = 'ai'")}
    assert objs == set(view_names())
