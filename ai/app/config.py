"""Ayarlar. Değerler .env dosyasından (veya ortam değişkenlerinden) okunur."""
import os
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:  # python-dotenv yoksa sadece ortam değişkenleri kullanılır
    pass

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

# --- Gemini ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
# Model adını AI Studio'daki "limitler" sayfasından kontrol edin; ücretsiz katmanda
# hangi modelin açık olduğu hesaba göre değişebilir. Hata alırsanız .env'de değiştirin.
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
# İki LLM çağrısı arasındaki asgari bekleme (sn). Ücretsiz katmanın dakikalık sınırı için.
LLM_MIN_INTERVAL = float(os.getenv("LLM_MIN_INTERVAL", "4"))

# --- Veritabanı (Gün 1: yerel PostgreSQL; sonra MCP'ye geçilecek) ---
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://localhost/eczane_ai_test")
