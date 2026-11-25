from app import sql_tools as t
from app.assistant import parse_llm_json
from eval.compare import compare_results


def test_clean_sql_fences_and_semicolon():
    assert t.clean_sql("```sql\nSELECT 1;\n```") == "SELECT 1"
    assert t.clean_sql("```SQL\nSELECT 1\n```\nAçıklama") == "SELECT 1"
    assert t.clean_sql("  SELECT 1 ;; ") == "SELECT 1"
    assert t.clean_sql("SELECT 1") == "SELECT 1"


def test_precheck_accepts_valid():
    assert t.precheck("SELECT name FROM products ORDER BY price DESC LIMIT 5") is None
    assert t.precheck("WITH a AS (SELECT 1 AS x) SELECT * FROM a") is None
    assert t.precheck("SELECT name FROM products WHERE name ILIKE '%update%'") is None  # metin içinde


def test_precheck_rejects():
    cases = {
        "DROP TABLE products": "NOT_SELECT",
        "SELECT 1; DROP TABLE products": "MULTIPLE_STATEMENTS",
        "SELECT * FROM users": "TABLE_NOT_ALLOWED",
        "SELECT * FROM public.products": "TABLE_NOT_ALLOWED",
        "SELECT pg_sleep(10)": "FORBIDDEN_FUNCTION",
        "WITH x AS (DELETE FROM sales RETURNING *) SELECT * FROM x": "FORBIDDEN_STATEMENT",
        "": "EMPTY",
    }
    for sql, code in cases.items():
        r = t.precheck(sql)
        assert r and r["status"] == "rejected" and r["code"] == code, (sql, r)


def test_extract_from_not_treated_as_table():
    assert t.precheck("SELECT EXTRACT(MONTH FROM sale_date) FROM sales") is None


def test_parse_llm_json():
    assert parse_llm_json('{"action":"answer","sql":"SELECT 1","message":""}')["sql"] == "SELECT 1"
    assert parse_llm_json('```json\n{"action":"refuse","sql":"","message":"yapılamaz"}\n```')["action"] == "refuse"
    assert parse_llm_json("```sql\nSELECT 1\n```")["action"] == "answer"
    assert parse_llm_json("anlamadım")["action"] == "clarify"


def test_compare_results():
    assert compare_results([["a", 1.0]], [["a", 1]])[0] == "OK"
    assert compare_results([["a", 1], ["b", 2]], [["b", 2], ["a", 1]])[0] == "OK"
    assert compare_results([["a", 1]], [["a", 1, 99]])[0] == "OK_EK_KOLON"
    assert compare_results([["a", 1]], [["a", 2]])[0] == "FAIL"
    assert compare_results([], [])[0] == "BOS_ESLESME"


def test_parse_llm_json_fence_inside_sql_field():
    raw = '{"action": "answer", "sql": "```sql\\nSELECT 1;\\n```", "message": ""}'
    plan = parse_llm_json(raw)
    assert plan["action"] == "answer"
    assert t.clean_sql(plan["sql"]) == "SELECT 1"
