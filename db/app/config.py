"""Ortam değişkenlerinden (.env) yapılandırma okur.

Parolalar ve bağlantı bilgileri asla kaynak koda yazılmaz; yalnızca .env / ortam değişkenlerinden gelir.
"""
import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()  # .env varsa yükler; yoksa mevcut ortam değişkenleri kullanılır


class ConfigError(RuntimeError):
    """Eksik veya hatalı yapılandırma."""


@dataclass(frozen=True)
class Settings:
    database_url: str
    ai_readonly_database_url: str
    ai_max_rows: int
    ai_statement_timeout_ms: int


def _require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise ConfigError(f"Ortam değişkeni eksik: {name} (.env.example dosyasına bakın)")
    return value


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(
        database_url=_require("DATABASE_URL"),
        ai_readonly_database_url=_require("AI_READONLY_DATABASE_URL"),
        ai_max_rows=int(os.environ.get("AI_MAX_ROWS", "500")),
        ai_statement_timeout_ms=int(os.environ.get("AI_STATEMENT_TIMEOUT_MS", "5000")),
    )
