"""Veritabanı bağlantıları.

İki ayrı bağlantı vardır ve bilerek ayrı tutulur:
  * app engine : veri sahibi kullanıcı. Tablo oluşturma, seed ve log yazma için.
  * ai engine  : 'ai_readonly' kullanıcısı. Yalnızca 'ai' şemasındaki görünümleri SELECT edebilir.
Yapay zekânın çalıştırdığı sorgular HİÇBİR ZAMAN app engine üzerinden gitmez.
"""
from functools import lru_cache

from sqlalchemy import Engine, create_engine

from app.config import get_settings


@lru_cache(maxsize=1)
def get_app_engine() -> Engine:
    return create_engine(get_settings().database_url, pool_pre_ping=True)


@lru_cache(maxsize=1)
def get_ai_engine() -> Engine:
    s = get_settings()
    # Rol düzeyindeki ayarlara ek olarak bağlantı düzeyinde de kısıtlar uygulanır (çift emniyet).
    options = (
        f"-c statement_timeout={s.ai_statement_timeout_ms} "
        "-c default_transaction_read_only=on "
        "-c search_path=ai"
    )
    return create_engine(
        s.ai_readonly_database_url,
        pool_pre_ping=True,
        connect_args={"options": options},
    )


def reset_caches() -> None:
    """Testlerde farklı ortam değişkenleriyle yeniden başlamak için."""
    get_settings.cache_clear()
    get_app_engine.cache_clear()
    get_ai_engine.cache_clear()
