"""Denetim kaydı (audit_logs) yazıcısı.

İlkeler:
  * Kayıt, veri sahibi bağlantısıyla yazılır (ai_readonly yazamaz).
  * Sorgu METNİ veya sonuç verisi yazılmaz; yalnızca olay türü, süre, satır sayısı, hata KODU ve SQL'in kısa özet değeri (hash).
  * Loglama hatası asıl işlemi bozmaz (yalnızca stderr'e uyarı).
"""
import hashlib
import logging

from sqlalchemy.orm import Session

from app.db.models import AuditLog
from app.db.session import get_app_engine

logger = logging.getLogger(__name__)


def sql_fingerprint(sql: str | None) -> str:
    """Aynı sorguyu ilişkilendirmek için kısa özet; içerik geri elde edilemez."""
    return hashlib.sha256((sql or "").encode("utf-8")).hexdigest()[:12]


def log_event(action_type: str, description: str, user_id: int | None = None) -> None:
    try:
        with Session(get_app_engine()) as s, s.begin():
            s.add(AuditLog(user_id=user_id, action_type=action_type, action_description=description[:1000]))
    except Exception:  # noqa: BLE001 - loglama asıl işlemi asla düşürmemeli
        logger.warning("audit log yazılamadı (action_type=%s)", action_type)
