"""Test altyapısı.

Veritabanı testleri AYRI bir test veritabanı ister (TEST_DATABASE_URL, TEST_AI_READONLY_DATABASE_URL).
Bu veritabanı her oturumda SIFIRLANIR; bu yüzden adında 'test' geçmiyorsa testler çalışmayı reddeder.
SQL doğrulayıcı testleri veritabanı gerektirmez.
"""
import os

import pytest
from sqlalchemy import make_url, text

TEST_URL = os.environ.get("TEST_DATABASE_URL")
TEST_AI_URL = os.environ.get("TEST_AI_READONLY_DATABASE_URL")

if TEST_URL and TEST_AI_URL:
    # Uygulama modülleri import edilmeden ÖNCE ayarlanmalı (dev veritabanına yanlışlıkla bağlanmayı önler)
    os.environ["DATABASE_URL"] = TEST_URL
    os.environ["AI_READONLY_DATABASE_URL"] = TEST_AI_URL
    os.environ["AI_STATEMENT_TIMEOUT_MS"] = "1500"
    os.environ["AI_MAX_ROWS"] = "500"
    os.environ.setdefault("SEED_DEFAULT_PASSWORD", "test-only-password")


def pytest_collection_modifyitems(config, items):
    if TEST_URL and TEST_AI_URL:
        return
    skip = pytest.mark.skip(reason="TEST_DATABASE_URL / TEST_AI_READONLY_DATABASE_URL tanımlı değil")
    for item in items:
        if "db" in item.keywords:
            item.add_marker(skip)


@pytest.fixture(scope="session")
def db():
    """Temiz, kurulu ve sentetik veriyle doldurulmuş test veritabanı (owner engine döner)."""
    from app.db.models import Base
    from app.db.seed import seed_database
    from app.db.session import get_app_engine, reset_caches
    from scripts.setup_db import setup_database

    name = make_url(TEST_URL).database or ""
    assert "test" in name, f"Güvenlik: '{name}' bir test veritabanı gibi görünmüyor; testler durduruldu."

    reset_caches()
    engine = get_app_engine()
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA IF EXISTS ai CASCADE"))
    Base.metadata.drop_all(engine)
    setup_database(engine, make_url(TEST_AI_URL).password, statement_timeout_ms=1500)
    seed_database(engine)
    yield engine
    reset_caches()
