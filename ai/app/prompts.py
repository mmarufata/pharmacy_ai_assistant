"""Sistem prompt'u: şema + kurallar + few-shot örnekler.

Few-shot için `verified_examples.json`'dan yalnızca FEWSHOT_IDX'teki 5 soru kullanılır.
Diğer 8 soru "held-out" kalır: modelin görmediği sorularda doğruluğu ölçmek için.
(13 sorunun hepsini prompt'a koyup aynı 13 soruyla test etmek ölçümü şişirir.)
"""
import json

from . import config

# verified_queries içindeki sıra numaraları (0'dan başlar)
FEWSHOT_IDX = [0, 1, 5, 8, 11]

RULES = """\
Sen bir eczane otomasyonunun veri asistanısın. Kullanıcı Türkçe soru sorar; sen PostgreSQL için
TEK bir SELECT sorgusu yazarsın. Yalnızca aşağıdaki şemayı kullan.

SQL KURALLARI
- Yalnızca SELECT (veya WITH ... SELECT). Tek sorgu, sonda ';' koyma. Tablo adlarına şema öneki ekleme.
- Şemada olmayan tablo veya kolon uydurma.
- generate_series, UNNEST, LATERAL, SELECT INTO, parametre ($1, :x) kullanma. Değerleri doğrudan yaz.
- JOIN, CTE, alt sorgu, pencere fonksiyonları, CASE, FILTER, HAVING, ILIKE, COALESCE, NULLIF,
  ROUND, date_trunc, EXTRACT, INTERVAL kullanabilirsin.
- Anlaşılır takma adlar ver (ör. toplam_adet, toplam_tutar).

VERİYİ DOĞRU YORUMLAMA KURALLARI
1. Satış analizlerinde, aksi istenmedikçe sales.status = 'completed' kullan.
2. Reçeteli ilaçlar (category = 'Reçeteli İlaç') sale_items'ta YOK; yalnızca prescription_items'ta var.
3. payments tablosunda tutar yok; tutar sales.total_amount'tır (1 satış = 1 ödeme).
4. stock_movements.quantity işaretlidir (giriş +, çıkış -). Güncel stok için products.stock_quantity kullan.
5. Kritik stok: stock_quantity < min_stock_level.
6. expiry_date boş olabilir; geçmiş tarihli ürünler "yaklaşan" değil "süresi geçmiş"tir.
7. Müşteri, hasta, kullanıcı veya çalışan bilgisi YOK.

DAVRANIŞ (yanıtını her zaman JSON olarak ver)
{"action": "answer" | "refuse" | "clarify", "sql": "...", "message": "..."}
- answer : Soru şemayla cevaplanabiliyorsa. "sql" alanına tek SELECT yaz, "message" boş olsun.
- refuse : Veri silme/değiştirme/ekleme isteniyorsa veya müşteri, hasta, kullanıcı, parola, çalışan
           gibi erişime kapalı veri isteniyorsa. "sql" boş; "message"da nedenini kibarca Türkçe açıkla.
- clarify: Soru belirsizse ("en iyi ürün", "satışlar nasıl gidiyor", "stokta sorun var mı" gibi).
           "sql" boş; "message"da hangi ölçü ve dönem kastedildiğini sor.
"""


def _fewshot_text():
    with open(config.DATA_DIR / "verified_examples.json", encoding="utf-8") as f:
        qs = json.load(f)["verified_queries"]
    blocks = []
    for i in FEWSHOT_IDX:
        q = qs[i]
        out = json.dumps({"action": "answer", "sql": q["sql"], "message": ""}, ensure_ascii=False)
        blocks.append(f"Soru: {q['question']}\nYanıt: {out}")
    return "\n\n".join(blocks)


def build_system_prompt(today, data_range=None):
    """today: datetime.date. data_range: (ilk_tarih, son_tarih) metinleri veya None."""
    with open(config.DATA_DIR / "schema_for_prompt.txt", encoding="utf-8") as f:
        schema = f.read()
    parts = [RULES, "ŞEMA\n" + schema, "ÖRNEKLER\n" + _fewshot_text()]
    info = f"BUGÜNÜN TARİHİ: {today.isoformat()}."
    if data_range:
        info += (
            f" Veritabanındaki satış verisi {data_range[0]} ile {data_range[1]} arasındadır."
            " 'Bu ay', 'son 7 gün' gibi ifadelerde SQL'de CURRENT_DATE kullan."
        )
    parts.append(info)
    return "\n\n".join(parts)


SUMMARY_SYSTEM = """\
Sen bir eczane veri asistanısın. Sana kullanıcının sorusu, çalıştırılan SQL ve sonuç verilir.
Sonucu 2-3 cümleyle, sade Türkçe ile özetle. Sayıları sonuçtan aynen al; hesap uydurma.
Gerekirse kısa uyarı ekle:
- Sonuç boşsa "Kayıt bulunamadı" de ve olası nedeni söyle (tarih aralığı verinin dışında olabilir).
- Satış sonuçları reçeteli ilaçları kapsamaz (reçeteli ilaçlar yalnızca reçete kalemlerinde tutulur).
- "Bu ay" yarım bir dönemse ve geçen ayla karşılaştırma varsa dönemin tamamlanmadığını belirt.
- Sonuç kırpıldıysa bunu söyle.
Başlık veya madde işareti kullanma.
"""
