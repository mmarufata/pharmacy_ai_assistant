"""SQL temizleme ve `execute_readonly_sql` STUB'ı.

Stub, MCP sunucusundaki `execute_readonly_sql` aracının DÖNÜŞ SÖZLEŞMESİNİ taklit eder
(README 6.3): {"status": "ok" | "rejected" | "error", ...}. MCP'ye geçince yalnızca
`execute_readonly_sql` fonksiyonunun gövdesi gerçek MCP çağrısıyla değiştirilir.

NOT: Buradaki ön kontroller yalnızca yerel geliştirme içindir. Asıl güvenlik (salt okunur rol,
AST doğrulaması, tablo/kolon izinleri) Meral'in MCP sunucusundadır; bu stub onun yerine geçmez.
"""
import datetime
import decimal
import re
import time

from . import config

MAX_ROWS = 500
TIMEOUT_MS = 5000

# Gerçek sistemde yapay zekâya kapalı olan tablolar (yerel veritabanında zaten yoktur,
# ama MCP'nin vereceği `rejected` cevabını taklit etmek için burada da reddediyoruz).
_BLOCKED_TABLES = {
    "users", "customers", "audit_logs", "roles", "login_history", "password_resets",
}
_FORBIDDEN_WORDS = re.compile(
    r"\b(insert|update|delete|drop|alter|create|truncate|grant|revoke|copy|merge|call|"
    r"execute|vacuum|set|explain)\b",
    re.I,
)


def clean_sql(text):
    """Model çıktısındaki ```sql ... ``` bloğunu ve sondaki ';' işaretini temizler."""
    s = (text or "").strip()
    m = re.search(r"```(?:sql|postgresql|pgsql)?\s*(.*?)```", s, re.S | re.I)
    if m:
        s = m.group(1).strip()
    s = s.strip()
    while s.endswith(";"):
        s = s[:-1].rstrip()
    return s


def _strip_literals_and_comments(sql):
    s = re.sub(r"--[^\n]*", " ", sql)
    s = re.sub(r"/\*.*?\*/", " ", s, flags=re.S)
    s = re.sub(r"'(?:[^']|'')*'", "''", s)
    return s


def precheck(sql):
    """Yerel ön kontrol. Geçerse None, geçmezse MCP biçiminde `rejected` sözlüğü döner."""
    if not sql.strip():
        return _rej("EMPTY", "Sorgu boş.")
    if len(sql) > 4000:
        return _rej("TOO_LONG", "Sorgu çok uzun.")
    s = _strip_literals_and_comments(sql)
    if ";" in s:
        return _rej("MULTIPLE_STATEMENTS", "Yalnızca tek bir sorgu çalıştırılabilir.")
    if not re.match(r"\s*(select|with)\b", s, re.I):
        return _rej("NOT_SELECT", "Yalnızca SELECT sorguları çalıştırılabilir.")
    if _FORBIDDEN_WORDS.search(s):
        return _rej("FORBIDDEN_STATEMENT", "Bu işlem yapılamaz. Yalnızca okuma yapılabilir.")
    if re.search(r"\b(pg_\w+|information_schema|current_setting|version)\b", s, re.I):
        return _rej("FORBIDDEN_FUNCTION", "Sorgu izin verilmeyen bir fonksiyon veya şema kullanıyor.")
    for name in re.findall(r"\b(?:from|join)\s+([a-zA-Z_][\w\.]*)", s, re.I):
        parts = name.lower().split(".")
        if len(parts) > 1 and parts[0] != "ai":
            return _rej("TABLE_NOT_ALLOWED", "Sorgu erişime izin verilmeyen bir tabloya başvuruyor.")
        if parts[-1] in _BLOCKED_TABLES:
            return _rej("TABLE_NOT_ALLOWED", "Sorgu erişime izin verilmeyen bir tabloya başvuruyor.")
    return None


def _rej(code, message):
    return {"status": "rejected", "code": code, "message": message}


def _json_value(v):
    if isinstance(v, decimal.Decimal):
        return float(v)
    if isinstance(v, (datetime.datetime, datetime.date)):
        return v.isoformat()
    return v


def _connect():
    import psycopg2  # geç içe aktarma: testlerde psycopg2 olmadan da çalışsın

    return psycopg2.connect(config.DATABASE_URL)


def execute_readonly_sql(sql, user_id=None):
    """STUB. MCP `execute_readonly_sql` ile aynı dönüş biçimi."""
    t0 = time.time()
    sql = clean_sql(sql)

    rejected = precheck(sql)
    if rejected:
        return rejected

    run_sql = sql if re.search(r"\blimit\s+\d+\s*$", sql, re.I) else f"{sql}\nLIMIT {MAX_ROWS + 1}"

    conn = None
    try:
        conn = _connect()
        conn.set_session(readonly=True, autocommit=False)
        cur = conn.cursor()
        cur.execute(f"SET LOCAL statement_timeout = {TIMEOUT_MS}")
        cur.execute(run_sql)
        columns = [d[0] for d in cur.description]
        rows = cur.fetchall()
        conn.rollback()
    except Exception as e:  # noqa: BLE001
        name = type(e).__name__
        if name == "QueryCanceled":
            msg = "Sorgu izin verilen süreyi aştı. Lütfen daha dar bir tarih aralığı veya filtre deneyin."
        else:
            msg = "Sorgu çalıştırılırken bir hata oluştu."
        # `debug` yalnızca stub'da vardır (geliştirme için). MCP'den gelmez.
        return {"status": "error", "message": msg, "debug": f"{name}: {str(e).strip()[:300]}"}
    finally:
        if conn is not None:
            conn.close()

    truncated = len(rows) > MAX_ROWS
    rows = rows[:MAX_ROWS]
    return {
        "status": "ok",
        "columns": columns,
        "rows": [[_json_value(v) for v in r] for r in rows],
        "row_count": len(rows),
        "truncated": truncated,
        "executed_sql": run_sql,
        "duration_ms": int((time.time() - t0) * 1000),
    }


def get_data_range():
    """Satış verisinin tarih aralığını döndürür (prompt'a 'veri şu tarihte bitiyor' demek için)."""
    r = execute_readonly_sql("SELECT MIN(sale_date)::date, MAX(sale_date)::date FROM sales")
    if r["status"] == "ok" and r["rows"] and r["rows"][0][0]:
        return r["rows"][0][0], r["rows"][0][1]
    return None
