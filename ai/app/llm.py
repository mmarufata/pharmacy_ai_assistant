"""LLM çağrısı: TEK yerde. Sağlayıcıyı değiştirmek isterseniz yalnızca bu dosyayı değiştirin.

Gemini'yi resmi SDK yerine doğrudan REST ile çağırıyoruz (yalnızca `requests` gerekir).
"""
import time

import requests

from . import config

_API = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
_last_call = 0.0


class LLMError(Exception):
    """LLM çağrısı başarısız oldu (anahtar yok, kota, ağ, boş yanıt...)."""


def _throttle():
    """Ücretsiz katmanın dakikalık sınırına takılmamak için çağrılar arasında bekle."""
    global _last_call
    wait = config.LLM_MIN_INTERVAL - (time.time() - _last_call)
    if wait > 0:
        time.sleep(wait)
    _last_call = time.time()


def generate(system, messages, json_mode=False, temperature=0.0, max_retries=4):
    """Gemini'den metin üretir.

    system   : sistem prompt'u (str)
    messages : [{"role": "user" | "model", "text": "..."}]
    json_mode: True ise yanıtın JSON olması istenir
    """
    if not config.GEMINI_API_KEY:
        raise LLMError("GEMINI_API_KEY bulunamadı. .env dosyasına ekleyin.")

    body = {
        "system_instruction": {"parts": [{"text": system}]},
        "contents": [{"role": m["role"], "parts": [{"text": m["text"]}]} for m in messages],
        "generationConfig": {"temperature": temperature, "maxOutputTokens": 4096},
    }
    if json_mode:
        body["generationConfig"]["responseMimeType"] = "application/json"

    url = _API.format(model=config.GEMINI_MODEL)
    headers = {"x-goog-api-key": config.GEMINI_API_KEY, "Content-Type": "application/json"}

    last_err = "bilinmeyen hata"
    for attempt in range(max_retries + 1):
        _throttle()
        try:
            r = requests.post(url, headers=headers, json=body, timeout=60)
        except requests.RequestException as e:
            last_err = f"ağ hatası: {e}"
            time.sleep(2 ** attempt)
            continue

        if r.status_code in (429, 500, 503):  # kota veya geçici sunucu hatası: bekleyip tekrar dene
            last_err = f"HTTP {r.status_code}: {r.text[:200]}"
            time.sleep(5 * 2 ** attempt)
            continue
        if r.status_code != 200:
            raise LLMError(f"Gemini HTTP {r.status_code}: {r.text[:300]}")

        data = r.json()
        try:
            parts = data["candidates"][0]["content"]["parts"]
        except (KeyError, IndexError):
            reason = data.get("promptFeedback") or data.get("candidates", [{}])[0].get("finishReason")
            raise LLMError(f"Gemini boş yanıt döndürdü: {reason}")
        text = "".join(p.get("text", "") for p in parts if not p.get("thought"))
        if not text.strip():
            raise LLMError("Gemini boş metin döndürdü.")
        return text

    raise LLMError(f"Gemini {max_retries + 1} denemede yanıt vermedi ({last_err}).")
