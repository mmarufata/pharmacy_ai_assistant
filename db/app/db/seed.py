"""Tamamen SENTETİK eczane verisi üretir. Gerçek müşteri/reçete/sağlık verisi içermez.

Özellikler:
  * Deterministik: sabit rastgele tohum (seed) -> her çalıştırmada aynı yapı (tarihler bugüne göre kayar).
  * Tekrar çalıştırılabilir: veri zaten varsa HİÇBİR ŞEY eklemez (çoğaltmaz).
  * Tutarlı: products.stock_quantity = stock_movements toplamı; satış toplamları kalem toplamlarıyla eşit.
  * Silme yalnızca açıkça istenirse (reset=True) yapılır.
"""
import os
import random
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from sqlalchemy import Engine, func, select, text
from sqlalchemy.orm import Session
from werkzeug.security import generate_password_hash

from app.db.models import (
    AuditLog, Base, Customer, Payment, Prescription, PrescriptionItem, Product, QueryHistory,
    ReportHistory, Sale, SaleItem, StockMovement, Supplier, User,
)

SEED = 42
DAYS_OF_HISTORY = 120

SUPPLIERS = [
    ("Anadolu İlaç Deposu", "0332 555 01 01"),
    ("Selçuklu Ecza Deposu", "0332 555 02 02"),
    ("Mevlana Medikal", "0332 555 03 03"),
    ("Konya Kozmetik Dağıtım", "0332 555 04 04"),
    ("Bozkır Sağlık Ürünleri", "0332 555 05 05"),
]

# (ad, kategori, fiyat, tedarikçi_idx, rx: reçeteli mi)
PRODUCTS = [
    ("Parasetamol 500 mg 20 Tablet", "Ağrı Kesici", "42.50", 0, False),
    ("İbuprofen 400 mg 20 Tablet", "Ağrı Kesici", "58.90", 0, False),
    ("Aspirin 100 mg 30 Tablet", "Ağrı Kesici", "49.90", 0, False),
    ("Kas Ağrısı Jeli 50 g", "Ağrı Kesici", "74.00", 1, False),
    ("C Vitamini 1000 mg 20 Efervesan", "Vitamin ve Takviye", "95.00", 1, False),
    ("D3 Vitamini Damla 20 ml", "Vitamin ve Takviye", "129.90", 1, False),
    ("Multivitamin 30 Tablet", "Vitamin ve Takviye", "189.00", 1, False),
    ("Magnezyum 400 mg 60 Kapsül", "Vitamin ve Takviye", "219.50", 4, False),
    ("Omega 3 Balık Yağı 60 Kapsül", "Vitamin ve Takviye", "249.00", 4, False),
    ("Demir Takviyesi 30 Kapsül", "Vitamin ve Takviye", "135.00", 4, False),
    ("Boğaz Pastili 24'lü", "Soğuk Algınlığı", "64.00", 0, False),
    ("Burun Spreyi 15 ml", "Soğuk Algınlığı", "52.00", 0, False),
    ("Öksürük Şurubu 120 ml", "Soğuk Algınlığı", "78.50", 0, False),
    ("Sıcak Limonlu Toz 10'lu", "Soğuk Algınlığı", "88.00", 1, False),
    ("Nemlendirici Krem 100 ml", "Cilt Bakımı", "165.00", 3, False),
    ("Güneş Kremi SPF50 50 ml", "Cilt Bakımı", "310.00", 3, False),
    ("Yüz Temizleme Jeli 200 ml", "Cilt Bakımı", "185.00", 3, False),
    ("El Kremi 75 ml", "Cilt Bakımı", "79.90", 3, False),
    ("Dudak Koruyucu 4.5 g", "Cilt Bakımı", "49.00", 3, False),
    ("Bebek Bezi Hasarı Kremi 100 g", "Anne ve Bebek", "112.00", 3, False),
    ("Bebek Şampuanı 300 ml", "Anne ve Bebek", "134.00", 3, False),
    ("Emzik Silikon 2'li", "Anne ve Bebek", "98.00", 2, False),
    ("Islak Mendil 72'li", "Anne ve Bebek", "59.90", 2, False),
    ("Diş Macunu 75 ml", "Ağız Bakımı", "69.00", 3, False),
    ("Diş Fırçası Orta", "Ağız Bakımı", "45.00", 3, False),
    ("Ağız Gargarası 250 ml", "Ağız Bakımı", "115.00", 3, False),
    ("Dijital Ateş Ölçer", "Medikal Malzeme", "180.00", 2, False),
    ("Tansiyon Aleti Koldan", "Medikal Malzeme", "1150.00", 2, False),
    ("Yara Bandı 20'li", "Medikal Malzeme", "34.00", 2, False),
    ("Steril Gazlı Bez 10'lu", "Medikal Malzeme", "28.00", 2, False),
    ("Medikal Maske 50'li", "Medikal Malzeme", "89.00", 2, False),
    ("Antibiyotik A 500 mg 16 Tablet", "Reçeteli İlaç", "145.00", 0, True),
    ("Tansiyon İlacı B 5 mg 30 Tablet", "Reçeteli İlaç", "86.00", 0, True),
    ("Diyabet İlacı C 850 mg 60 Tablet", "Reçeteli İlaç", "112.50", 1, True),
    ("Kolesterol İlacı D 20 mg 30 Tablet", "Reçeteli İlaç", "174.00", 0, True),
    ("Mide İlacı E 20 mg 14 Kapsül", "Reçeteli İlaç", "96.00", 1, True),
    ("Alerji İlacı F 10 mg 20 Tablet", "Reçeteli İlaç", "73.00", 0, True),
    ("Tiroid İlacı G 100 mcg 100 Tablet", "Reçeteli İlaç", "64.00", 1, True),
    ("Ağrı Kesici H 50 mg 20 Tablet", "Reçeteli İlaç", "101.00", 0, True),
]

FIRST_NAMES = ["Ayşe", "Mehmet", "Fatma", "Ali", "Zeynep", "Mustafa", "Elif", "Hasan", "Emine", "İbrahim",
               "Hatice", "Yusuf", "Merve", "Ahmet", "Büşra", "Emre"]
LAST_NAMES = ["Yılmaz", "Kaya", "Demir", "Şahin", "Çelik", "Yıldız", "Aydın", "Öztürk", "Arslan", "Doğan"]


def _money(x) -> Decimal:
    return Decimal(str(x)).quantize(Decimal("0.01"))


def is_seeded(session: Session) -> bool:
    return (session.scalar(select(func.count()).select_from(User)) or 0) > 0


def reset_all_tables(engine: Engine) -> None:
    """TÜM VERİYİ SİLER. Yalnızca açıkça çağrılırsa çalışır."""
    names = ", ".join(t.name for t in Base.metadata.sorted_tables)
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE {names} RESTART IDENTITY CASCADE"))


def seed_database(engine: Engine, today: date | None = None, reset: bool = False) -> bool:
    """Veriyi üretir. Döndürür: True = veri eklendi, False = zaten vardı (hiçbir şey yapılmadı)."""
    password = os.environ.get("SEED_DEFAULT_PASSWORD")
    if not password:
        raise RuntimeError("SEED_DEFAULT_PASSWORD ortam değişkeni gerekli (.env.example'a bakın).")
    if reset:
        reset_all_tables(engine)

    rnd = random.Random(SEED)
    today = today or date.today()
    start = today - timedelta(days=DAYS_OF_HISTORY)

    with Session(engine) as s, s.begin():
        if is_seeded(s):
            return False

        pw_hash = generate_password_hash(password)
        users = [
            User(first_name="Demo", last_name="Yönetici", email="admin@example.com", password_hash=pw_hash, role="admin"),
            User(first_name="Demo", last_name="Eczacı", email="eczaci@example.com", password_hash=pw_hash, role="pharmacist"),
            User(first_name="Demo", last_name="Kalfa", email="kalfa@example.com", password_hash=pw_hash, role="staff"),
            User(first_name="Demo", last_name="Çalışan", email="calisan@example.com", password_hash=pw_hash, role="staff"),
        ]
        suppliers = [Supplier(name=n, phone=p) for n, p in SUPPLIERS]
        customers = [
            Customer(first_name=rnd.choice(FIRST_NAMES), last_name=rnd.choice(LAST_NAMES),
                     insurance_status=rnd.choices(["sgk", "private", "none"], [75, 10, 15])[0])
            for _ in range(30)
        ]
        s.add_all(users + suppliers + customers)
        s.flush()

        # --- Ürünler: barkodlar metin ve başında 0 olabilir ---
        products: list[Product] = []
        rx_flags: dict[int, bool] = {}
        for i, (name, cat, price, sup_idx, rx) in enumerate(PRODUCTS):
            expiry = None
            if cat != "Medikal Malzeme" or rnd.random() < 0.4:
                expiry = today + timedelta(days=rnd.randint(120, 900))
            p = Product(name=name, barcode=f"0869{i:04d}{rnd.randint(1000, 9999)}", category=cat,
                        stock_quantity=0, min_stock_level=rnd.choice([5, 10, 15, 20]),
                        price=_money(price), expiry_date=expiry, supplier_id=suppliers[sup_idx].supplier_id)
            products.append(p)
        # Rapor senaryoları için bilinçli örnekler: yakın SKT ve geçmiş SKT
        for p in rnd.sample(products, 5):
            p.expiry_date = today + timedelta(days=rnd.randint(10, 55))
        products[10].expiry_date = today - timedelta(days=5)
        s.add_all(products)
        s.flush()
        for p, (_, _, _, _, rx) in zip(products, PRODUCTS):
            rx_flags[p.product_id] = rx
        otc = [p for p in products if not rx_flags[p.product_id]]
        rx_products = [p for p in products if rx_flags[p.product_id]]
        # Popülerlik ağırlıkları: bazı ürünler çok satsın
        weights = [rnd.choice([1, 1, 2, 3, 5, 8]) for _ in otc]

        sellers = [users[1], users[2], users[3]]
        sold: dict[int, int] = {p.product_id: 0 for p in products}
        returned: dict[int, int] = {p.product_id: 0 for p in products}
        movements: list[StockMovement] = []

        # --- Satışlar ---
        d = start
        while d <= today:
            n_sales = rnd.randint(2, 7) if d.weekday() < 6 else rnd.randint(0, 2)
            for _ in range(n_sales):
                ts = datetime.combine(d, time(rnd.randint(9, 19), rnd.randint(0, 59), rnd.randint(0, 59)))
                if ts > datetime.now() and d == today:
                    continue
                status = rnd.choices(["completed", "refunded", "cancelled"], [94, 3, 3])[0]
                sale = Sale(sale_date=ts, total_amount=_money(0), status=status,
                            user_id=rnd.choice(sellers).user_id,
                            customer_id=rnd.choice(customers).customer_id if rnd.random() < 0.3 else None)
                chosen = {rnd.choices(otc, weights)[0] for _ in range(rnd.randint(1, 4))}
                total = Decimal("0.00")
                for p in chosen:
                    qty = rnd.choice([1, 1, 1, 2, 2, 3])
                    line = _money(p.price * qty)
                    total += line
                    sale.items.append(SaleItem(product_id=p.product_id, quantity=qty, unit_price=p.price, line_total=line))
                    if status != "cancelled":  # iptal edilen satış stoktan düşmez
                        sold[p.product_id] += qty
                        movements.append(StockMovement(product_id=p.product_id, movement_type="sale", quantity=-qty,
                                                       movement_date=ts, user_id=sale.user_id,
                                                       description="Satış çıkışı"))
                        if status == "refunded":
                            returned[p.product_id] += qty
                            movements.append(StockMovement(product_id=p.product_id, movement_type="return", quantity=qty,
                                                           movement_date=ts + timedelta(hours=2), user_id=sale.user_id,
                                                           description="Satış iadesi"))
                sale.total_amount = total
                sale.payment = Payment(payment_method=rnd.choices(["cash", "credit_card", "other"], [40, 55, 5])[0])
                s.add(sale)
            d += timedelta(days=1)

        # --- Stok hareketleri: başlangıç girişi + bazı ek girişler + fire ---
        critical_ids = {p.product_id for p in rnd.sample(otc, 6)}  # bilinçli olarak kritik stoktaki ürünler
        first_day = datetime.combine(start - timedelta(days=1), time(8, 0))
        for p in products:
            net_out = sold[p.product_id] - returned[p.product_id]
            waste = rnd.randint(1, 3) if rnd.random() < 0.15 else 0
            if p.product_id in critical_ids:
                remaining, restock = rnd.randint(0, max(p.min_stock_level - 1, 0)), 0
            else:
                remaining, restock = rnd.randint(p.min_stock_level + 5, p.min_stock_level + 80), rnd.choice([0, 0, 20, 40])
            initial = net_out + waste + remaining
            if initial > 0:
                movements.append(StockMovement(product_id=p.product_id, movement_type="stock_in", quantity=initial,
                                               movement_date=first_day, user_id=users[1].user_id,
                                               description="Başlangıç stok girişi"))
            if restock:
                movements.append(StockMovement(product_id=p.product_id, movement_type="stock_in", quantity=restock,
                                               movement_date=datetime.combine(today - timedelta(days=rnd.randint(5, 40)), time(10, 0)),
                                               user_id=users[1].user_id, description="Tedarikçi mal kabul"))
            if waste:
                movements.append(StockMovement(product_id=p.product_id, movement_type="waste", quantity=-waste,
                                               movement_date=datetime.combine(today - timedelta(days=rnd.randint(1, 60)), time(17, 0)),
                                               user_id=users[1].user_id, description="Hasarlı/fire"))
            p.stock_quantity = remaining + restock
        s.add_all(movements)

        # --- Reçeteler (sentetik SGK senaryoları; gerçek SGK kuralı DEĞİLDİR) ---
        sgk_customers = [c for c in customers if c.insurance_status == "sgk"]
        for _ in range(60):
            cust = rnd.choice(customers)
            covered = cust.insurance_status == "sgk" and rnd.random() < 0.9
            presc = Prescription(prescription_status=rnd.choices(["completed", "pending", "cancelled"], [85, 10, 5])[0],
                                 customer_id=cust.customer_id, user_id=users[1].user_id,
                                 sgk_status="sgk_covered" if covered else "private",
                                 prescription_date=today - timedelta(days=rnd.randint(0, DAYS_OF_HISTORY)))
            for p in rnd.sample(rx_products, rnd.randint(1, 3)):
                qty = rnd.choice([1, 1, 2])
                total = _money(p.price * qty)
                if covered:
                    diff = _money(rnd.choice([0, 0, 0, 5, 10]))  # fiyat farkı ayrı kalemdir
                    sgk = _money(total * Decimal("0.80"))          # sentetik oran
                    copay = _money(total - sgk)
                else:
                    sgk, diff, copay = _money(0), _money(0), total
                presc.items.append(PrescriptionItem(product_id=p.product_id, quantity=qty, unit_price=p.price,
                                                    sgk_covered_amount=sgk, patient_copay=copay, price_difference=diff))
            s.add(presc)

        # --- Örnek denetim / geçmiş kayıtları ---
        for u in users:
            s.add(AuditLog(user_id=u.user_id, action_type="login", action_description="Başarılı giriş (sentetik örnek)",
                           created_at=datetime.combine(today - timedelta(days=1), time(9, 0))))
        s.add(AuditLog(user_id=None, action_type="unauthorized_access", action_description="Yetkisiz erişim denemesi (sentetik örnek)",
                       created_at=datetime.combine(today - timedelta(days=2), time(23, 40))))
        for q, st, ms, err in [("Bu ay en çok satılan 5 ürün hangileri?", "success", 120, None),
                               ("Kritik stoktaki ürünler neler?", "success", 85, None),
                               ("Ürünleri sil", "blocked", 3, "Yalnızca okuma sorgularına izin verilir.")]:
            s.add(QueryHistory(user_id=users[1].user_id, question=q, query_status=st, execution_time_ms=ms, error_message=err))
        s.add(ReportHistory(user_id=users[0].user_id, name="Aylık satış özeti", report_type="sales_summary",
                            report_status="completed", description="Sentetik örnek rapor kaydı"))
        return True
