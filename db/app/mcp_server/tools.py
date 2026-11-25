"""MCP araçlarının asıl mantığı (MCP'den bağımsız düz Python fonksiyonları -> kolay test).

Her araç:
  * yalnızca tanımlı görevini yapar ve gereğinden fazla veri açığa çıkarmaz,
  * ai_readonly bağlantısını kullanır (asla veri sahibi bağlantısını değil),
  * süre ve sonucu denetim kaydına yazar (SQL metni yazılmaz),
  * hata durumunda kullanıcıya şema/kimlik bilgisi içermeyen güvenli mesaj döner.
"""
import time
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy.exc import DBAPIError, OperationalError

from app.config import get_settings
from app.db.ai_views import view_names
from app.db.schema_discovery import describe_table, discover_ai_schema
from app.db.session import get_ai_engine
from app.security.sql_validator import validate_select_sql
from app.services.audit import log_event, sql_fingerprint

SAFE_DB_ERROR = "Sorgu çalıştırılırken bir hata oluştu. Lütfen sorguyu değiştirip tekrar deneyin."
SAFE_TIMEOUT = "Sorgu izin verilen süreyi aştı. Lütfen daha dar bir tarih aralığı veya filtre deneyin."
SAFE_UNAVAILABLE = "Veritabanına şu anda ulaşılamıyor. Lütfen daha sonra tekrar deneyin."


def _json_safe(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def get_database_schema(user_id: int | None = None) -> dict:
    start = time.perf_counter()
    try:
        result = discover_ai_schema(get_ai_engine())
        status = "ok"
    except Exception:  # noqa: BLE001
        log_event("mcp_get_database_schema_error", "hata", user_id)
        return {"status": "error", "message": SAFE_UNAVAILABLE}
    ms = int((time.perf_counter() - start) * 1000)
    log_event("mcp_get_database_schema", f"durum={status} sure_ms={ms}", user_id)
    return {"status": "ok", **result}


def get_table_info(table_name: str, user_id: int | None = None) -> dict:
    start = time.perf_counter()
    try:
        info = describe_table(get_ai_engine(), table_name)
    except Exception:  # noqa: BLE001
        log_event("mcp_get_table_info_error", "hata", user_id)
        return {"status": "error", "message": SAFE_UNAVAILABLE}
    ms = int((time.perf_counter() - start) * 1000)
    if info is None:
        log_event("mcp_get_table_info_blocked", f"tablo_izinli_degil sure_ms={ms}", user_id)
        return {"status": "rejected", "message": "Bu tablo bulunamadı veya erişime izin verilmiyor."}
    log_event("mcp_get_table_info", f"tablo={info['name']} sure_ms={ms}", user_id)
    return {"status": "ok", "table": info}


def execute_readonly_sql(sql: str, user_id: int | None = None) -> dict:
    settings = get_settings()
    fp = sql_fingerprint(sql)
    start = time.perf_counter()

    verdict = validate_select_sql(sql, max_rows=settings.ai_max_rows)
    if not verdict.ok:
        log_event("mcp_query_blocked", f"kod={verdict.code} sql={fp}", user_id)
        return {"status": "rejected", "code": verdict.code, "message": verdict.message}

    try:
        with get_ai_engine().connect() as conn:
            # '%' karakteri psycopg'de parametre işaretidir; LIKE '%x%' için kaçırılmalıdır.
            result = conn.exec_driver_sql(verdict.sql.replace("%", "%%"))
            columns = list(result.keys())
            fetched = result.fetchmany(settings.ai_max_rows + 1)  # bir fazlası: kırpıldı mı anlamak için
    except OperationalError as exc:
        ms = int((time.perf_counter() - start) * 1000)
        is_timeout = "statement timeout" in str(getattr(exc, "orig", exc)).lower()
        log_event("mcp_query_timeout" if is_timeout else "mcp_query_error",
                  f"sql={fp} sure_ms={ms} hata={'timeout' if is_timeout else 'baglanti'}", user_id)
        return {"status": "error", "message": SAFE_TIMEOUT if is_timeout else SAFE_UNAVAILABLE}
    except DBAPIError:
        ms = int((time.perf_counter() - start) * 1000)
        log_event("mcp_query_error", f"sql={fp} sure_ms={ms} hata=veritabani", user_id)
        return {"status": "error", "message": SAFE_DB_ERROR}
    except Exception:  # noqa: BLE001
        log_event("mcp_query_error", f"sql={fp} hata=beklenmeyen", user_id)
        return {"status": "error", "message": SAFE_DB_ERROR}

    truncated = len(fetched) > settings.ai_max_rows
    rows = [[_json_safe(v) for v in row] for row in fetched[: settings.ai_max_rows]]
    ms = int((time.perf_counter() - start) * 1000)
    log_event("mcp_query_ok", f"sql={fp} satir={len(rows)} kirpildi={truncated} sure_ms={ms}", user_id)
    return {
        "status": "ok",
        "columns": columns,
        "rows": rows,
        "row_count": len(rows),
        "truncated": truncated,
        "executed_sql": verdict.sql,  # FR-03.7: yetkili kullanıcıya gösterilebilir
        "duration_ms": ms,
    }


def get_database_statistics(user_id: int | None = None) -> dict:
    """Yalnızca izin verilen görünümlerden genel sayılar; kişisel veri içermez."""
    start = time.perf_counter()
    try:
        with get_ai_engine().connect() as conn:
            counts = {v: conn.exec_driver_sql(f'SELECT count(*) FROM "{v}"').scalar_one() for v in view_names()}
            lo, hi = conn.exec_driver_sql("SELECT min(sale_date), max(sale_date) FROM sales").one()
            critical = conn.exec_driver_sql("SELECT count(*) FROM products WHERE stock_quantity < min_stock_level").scalar_one()
    except Exception:  # noqa: BLE001
        log_event("mcp_get_database_statistics_error", "hata", user_id)
        return {"status": "error", "message": SAFE_UNAVAILABLE}
    ms = int((time.perf_counter() - start) * 1000)
    log_event("mcp_get_database_statistics", f"sure_ms={ms}", user_id)
    return {
        "status": "ok",
        "row_counts": counts,
        "sales_date_range": {"first": _json_safe(lo), "last": _json_safe(hi)},
        "critical_stock_product_count": critical,
    }
