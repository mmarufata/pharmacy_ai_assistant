# ai/ — Text-to-SQL asistanı (Merve'nin bölümü) · Gün 1

Kullanıcının Türkçe sorusunu Gemini ile SQL'e çevirir, sonucu çalıştırır, kısa özet yazar.
Bu sürümde veritabanı çağrısı bir **stub**'tır (`app/sql_tools.py`); MCP'ye geçişte yalnızca
`execute_readonly_sql` fonksiyonunun içi değişecek.

## Kurulum (bir kez)

```bash
cd ai
python -m venv venv
venv\Scripts\activate          # Mac/Linux: source venv/bin/activate
pip install -r requirements.txt
copy .env.example .env         # Mac/Linux: cp .env.example .env
```

1. https://aistudio.google.com adresinden **API anahtarı** alın, `.env` içindeki `GEMINI_API_KEY`'e yazın.
2. PostgreSQL'i kurun, sonra örnek veriyi yükleyin (şifre sorarsa kurulumda verdiğiniz şifre):

```bash
createdb -U postgres eczane_ai_test
psql -U postgres -d eczane_ai_test -f sample_db_postgres.sql
psql -U postgres -d eczane_ai_test -c "SELECT COUNT(*) FROM sales;"    # 508 olmalı
```

Kullanıcı/şifre gerekiyorsa `.env` içinde:
`DATABASE_URL=postgresql://postgres:SIFRENIZ@localhost:5432/eczane_ai_test`

## Çalıştırma

```bash
python -m app.cli "Bu ay en çok satılan 5 ürün hangileri?"   # tek soru (ekran görüntüsü için)
python -m app.cli                                            # sohbet modu
python -m eval.run_day1                                      # 13 soruluk ölçüm -> eval/results_day1.csv
python -m pytest -q                                          # birim testler (DB ve API gerekmez)
```

## Dosyalar

| Dosya | Görevi |
|---|---|
| `app/llm.py` | Gemini çağrısı (tek yerde), kota hatasında bekleyip tekrar dener |
| `app/prompts.py` | Sistem prompt'u: kurallar + şema + 5 few-shot örnek |
| `app/sql_tools.py` | SQL temizleme, ön kontrol, `execute_readonly_sql` stub'ı (MCP sözleşmesi) |
| `app/assistant.py` | `answer_question(soru)`: soru → SQL → sonuç → özet. Flask bunu çağıracak |
| `eval/run_day1.py`, `eval/compare.py` | 13 soruyu sonuç tabanlı ölçer |
| `data/` | `schema_for_prompt.txt`, `verified_examples.json` (Meral/arkadaşınızın paketi) |

## Ölçümü doğru yorumlama

- **5 soru few-shot** olarak prompt'tadır (`prompts.FEWSHOT_IDX`). Asıl doğruluk rakamı **8 held-out sorudur**; 13'ün tamamı daha iyimserdir. Raporda ikisini de yazın.
- **`BOS_ESLESME`**: iki sonuç da boş demektir (örn. "son 7 gün", çünkü veri 17 Kasım'da bitiyor). Bu doğruluk kanıtı sayılmaz, doğruya eklemeyin.
- Doğruluk SQL metniyle değil **sonuç değerleriyle** ölçülür (sıra ve kolon adı önemsiz).

## Sorun giderme

- `GEMINI_API_KEY bulunamadı` → `.env` dosyası `ai/` klasöründe mi, anahtar yazılı mı?
- `HTTP 404 ... model` → `.env`'de `GEMINI_MODEL`'i AI Studio'da görünen bir model adıyla değiştirin.
- `HTTP 429` → kota doldu; `LLM_MIN_INTERVAL=8` yapın veya yarın tekrar deneyin (günlük kota gece yarısı Pasifik saatinde sıfırlanır).
- `password authentication failed` → `.env`'deki `DATABASE_URL`'e kullanıcı ve şifre ekleyin.
- Sonuç `error` ise `python -m app.cli` çıktısındaki `debug:` satırına bakın.

## Henüz yok (sonraki günler)

Hata düzeltme/yeniden deneme döngüsü, sohbet hafızası, gerçek MCP çağrısı, Flask entegrasyonu, 40+ soruluk değerlendirme seti.
