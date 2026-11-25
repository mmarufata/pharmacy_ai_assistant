"""Yapay zekânın görebileceği 'ai' şemasındaki görünümlerin TEK TANIM KAYNAĞI.

Bu sözlük üç yerde kullanılır:
  1. scripts/setup_db.py  -> CREATE VIEW ve GRANT SELECT komutlarını üretir
  2. sql_validator.py     -> izin verilen tablo/kolon listesi (sqlglot şeması)
  3. schema_discovery.py  -> LLM'e verilecek Türkçe açıklamalı şema

Hassas alanlar (password_hash, e-posta, müşteri adı/kimliği, log ve geçmiş tabloları) BİLEREK dışarıda bırakılmıştır.
Görünümler 'ai' şemasında, ana tablolarla AYNI adı taşır; ai_readonly rolünün search_path'i 'ai' olduğundan
LLM 'FROM products' yazdığında görünüme erişir, 'public.products' tablosuna erişemez.
"""

# (kolon, sqlglot tipi, Türkçe açıklama)
AI_VIEWS: dict[str, dict] = {
    "products": {
        "source": "products",
        "description": "Eczanedeki ürünler ve güncel stok bilgisi.",
        "columns": [
            ("product_id", "INT", "Ürün kimliği"),
            ("name", "TEXT", "Ürün adı"),
            ("barcode", "TEXT", "Barkod (metin)"),
            ("category", "TEXT", "Ürün kategorisi"),
            ("stock_quantity", "INT", "Mevcut stok adedi"),
            ("min_stock_level", "INT", "Kritik stok eşiği; stok bunun altındaysa ürün kritiktir"),
            ("price", "DECIMAL", "Güncel satış fiyatı (TL)"),
            ("expiry_date", "DATE", "Son kullanma tarihi (boş olabilir)"),
            ("supplier_id", "INT", "Tedarikçi kimliği -> suppliers.supplier_id"),
        ],
    },
    "suppliers": {
        "source": "suppliers",
        "description": "Ürün tedarikçileri ve iletişim telefonu.",
        "columns": [
            ("supplier_id", "INT", "Tedarikçi kimliği"),
            ("name", "TEXT", "Tedarikçi adı"),
            ("phone", "TEXT", "Telefon numarası"),
        ],
    },
    "sales": {
        "source": "sales",
        "description": "Satış işlemleri (fiş başlığı). Müşteri bilgisi bilinçli olarak yoktur.",
        "columns": [
            ("sale_id", "INT", "Satış kimliği"),
            ("sale_date", "TIMESTAMP", "Satış tarihi ve saati"),
            ("total_amount", "DECIMAL", "Satışın toplam tutarı (TL)"),
            ("status", "TEXT", "Durum: completed (tamamlandı), cancelled (iptal), refunded (iade)"),
        ],
    },
    "sale_items": {
        "source": "sale_items",
        "description": "Her satıştaki ürün kalemleri.",
        "columns": [
            ("sale_item_id", "INT", "Kalem kimliği"),
            ("sale_id", "INT", "Satış kimliği -> sales.sale_id"),
            ("product_id", "INT", "Ürün kimliği -> products.product_id"),
            ("quantity", "INT", "Satılan adet"),
            ("unit_price", "DECIMAL", "Satış anındaki birim fiyat (TL)"),
            ("line_total", "DECIMAL", "Kalem toplamı = quantity * unit_price (TL)"),
        ],
    },
    "payments": {
        "source": "payments",
        "description": "Satışın ödeme yöntemi. Her satışın tam olarak bir ödemesi vardır; ödeme tutarı sales.total_amount'tır.",
        "columns": [
            ("payment_id", "INT", "Ödeme kimliği"),
            ("payment_method", "TEXT", "Ödeme yöntemi: cash (nakit), credit_card (kredi kartı), other (diğer)"),
            ("sale_id", "INT", "Satış kimliği -> sales.sale_id (benzersiz)"),
        ],
    },
    "stock_movements": {
        "source": "stock_movements",
        "description": "Stok giriş/çıkış hareketleri. quantity işaretlidir: giriş +, çıkış -.",
        "columns": [
            ("movement_id", "INT", "Hareket kimliği"),
            ("product_id", "INT", "Ürün kimliği -> products.product_id"),
            ("movement_type", "TEXT", "Tür: stock_in (giriş), sale (satış), return (iade), waste (fire), count_adjustment (sayım düzeltmesi)"),
            ("quantity", "INT", "Adet (giriş +, çıkış -)"),
            ("movement_date", "TIMESTAMP", "Hareket tarihi ve saati"),
        ],
    },
    "prescriptions": {
        "source": "prescriptions",
        "description": "Reçete başlıkları. Hasta ve kullanıcı bilgisi bilinçli olarak yoktur.",
        "columns": [
            ("prescription_id", "INT", "Reçete kimliği"),
            ("prescription_status", "TEXT", "Durum: pending, completed, cancelled"),
            ("sgk_status", "TEXT", "sgk_covered (SGK kapsamında) veya private (özel)"),
            ("prescription_date", "DATE", "Reçete tarihi"),
        ],
    },
    "prescription_items": {
        "source": "prescription_items",
        "description": "Reçete kalemleri ve SGK / hasta katkı payı tutarları (sentetik prototip verisi).",
        "columns": [
            ("prescription_item_id", "INT", "Kalem kimliği"),
            ("prescription_id", "INT", "Reçete kimliği -> prescriptions.prescription_id"),
            ("product_id", "INT", "Ürün kimliği -> products.product_id"),
            ("quantity", "INT", "Adet"),
            ("unit_price", "DECIMAL", "Birim fiyat (TL)"),
            ("sgk_covered_amount", "DECIMAL", "SGK'nın karşıladığı tutar (TL)"),
            ("patient_copay", "DECIMAL", "Hasta katkı payı (TL)"),
            ("price_difference", "DECIMAL", "Fiyat farkı (TL)"),
        ],
    },
}

AI_SCHEMA_NAME = "ai"
AI_ROLE_NAME = "ai_readonly"


def view_names() -> list[str]:
    return list(AI_VIEWS)


def columns_of(view: str) -> list[str]:
    return [c[0] for c in AI_VIEWS[view]["columns"]]


def sqlglot_schema() -> dict[str, dict[str, str]]:
    """sqlglot.optimizer.qualify için {tablo: {kolon: tip}} sözlüğü."""
    return {v: {c[0]: c[1] for c in meta["columns"]} for v, meta in AI_VIEWS.items()}


def create_view_sql(view: str) -> str:
    meta = AI_VIEWS[view]
    cols = ", ".join(columns_of(view))
    return f'CREATE OR REPLACE VIEW {AI_SCHEMA_NAME}."{view}" AS SELECT {cols} FROM public."{meta["source"]}"'
