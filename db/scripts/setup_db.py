"""Veritabanı kurulumu: tablolar + 'ai' görünümleri + salt okunur rol ve izinler.

Güvenli ve tekrar çalıştırılabilirdir: tabloları SİLMEZ (create_all yalnızca eksikleri oluşturur),
görünümleri CREATE OR REPLACE ile günceller, rol varsa yalnızca parolasını/ayarlarını günceller.

Kullanım:  python -m scripts.setup_db
Gereksinim: DATABASE_URL kullanıcısının rol oluşturma yetkisi (CREATEROLE) olmalıdır.
"""
import sys

from sqlalchemy import Engine, make_url, text

from app.config import get_settings
from app.db.ai_views import AI_ROLE_NAME, AI_SCHEMA_NAME, create_view_sql, view_names
from app.db.models import Base
from app.db.session import get_app_engine


def setup_database(engine: Engine, ai_password: str, statement_timeout_ms: int = 5000) -> None:
    Base.metadata.create_all(engine)

    with engine.begin() as conn:
        db_name = conn.execute(text("SELECT current_database()")).scalar_one()
        role = AI_ROLE_NAME

        # 1) Rol: yoksa oluştur, varsa parolasını güncelle. DDL parametre almadığından format(%I/%L) ile güvenli alıntılanır.
        exists = conn.execute(text("SELECT 1 FROM pg_roles WHERE rolname = :r"), {"r": role}).scalar()
        # CREATE'te yetkisiz özellikler açıkça kapatılır; ALTER'da yalnızca parola güncellenir
        # (süper kullanıcı olmayan sahip, NOSUPERUSER gibi özellikleri ALTER ile yazamaz).
        attrs = "LOGIN PASSWORD %L" if exists else "LOGIN PASSWORD %L NOSUPERUSER NOCREATEDB NOCREATEROLE"
        verb = "ALTER" if exists else "CREATE"
        stmt = conn.execute(
            text(f"SELECT format('{verb} ROLE %I {attrs}', "
                 "CAST(:r AS text), CAST(:p AS text))"),
            {"r": role, "p": ai_password},
        ).scalar_one()
        conn.exec_driver_sql(stmt)

        # 2) Rol düzeyinde güvenlik ayarları
        conn.exec_driver_sql(f"ALTER ROLE {role} SET search_path = {AI_SCHEMA_NAME}")
        conn.exec_driver_sql(f"ALTER ROLE {role} SET statement_timeout = {int(statement_timeout_ms)}")
        conn.exec_driver_sql(f"ALTER ROLE {role} SET default_transaction_read_only = on")
        conn.exec_driver_sql(f"ALTER ROLE {role} SET idle_in_transaction_session_timeout = 10000")

        # 3) Şema ve görünümler
        conn.exec_driver_sql(f"CREATE SCHEMA IF NOT EXISTS {AI_SCHEMA_NAME}")
        for v in view_names():
            conn.exec_driver_sql(create_view_sql(v))

        # 4) İzinler: önce her şeyi geri al, sonra yalnızca onaylı görünümlere SELECT ver
        conn.exec_driver_sql(f'GRANT CONNECT ON DATABASE "{db_name}" TO {role}')
        conn.exec_driver_sql(f"REVOKE ALL ON SCHEMA public FROM {role}")
        conn.exec_driver_sql(f"REVOKE ALL ON ALL TABLES IN SCHEMA public FROM {role}")
        conn.exec_driver_sql(f"REVOKE ALL ON ALL TABLES IN SCHEMA {AI_SCHEMA_NAME} FROM {role}")
        conn.exec_driver_sql(f"GRANT USAGE ON SCHEMA {AI_SCHEMA_NAME} TO {role}")
        for v in view_names():
            conn.exec_driver_sql(f'GRANT SELECT ON {AI_SCHEMA_NAME}."{v}" TO {role}')


def main() -> int:
    s = get_settings()
    ai_password = make_url(s.ai_readonly_database_url).password
    if not ai_password:
        print("HATA: AI_READONLY_DATABASE_URL içinde parola yok.", file=sys.stderr)
        return 1
    setup_database(get_app_engine(), ai_password, s.ai_statement_timeout_ms)
    print(f"Tamam: tablolar, '{AI_SCHEMA_NAME}' görünümleri ve '{AI_ROLE_NAME}' rolü hazır.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
