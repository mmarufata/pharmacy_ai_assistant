"""Model kısıtları ve sentetik veri testleri (gerçek PostgreSQL test veritabanı)."""
from datetime import date, datetime
from decimal import Decimal

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import Base, Payment, Product, Sale, SaleItem, StockMovement, User

pytestmark = pytest.mark.db


def q(engine, sql):
    with engine.connect() as c:
        return c.exec_driver_sql(sql).scalar_one()


def test_all_13_tables_exist(db):
    assert len(Base.metadata.tables) == 13
    names = {r[0] for r in db.connect().exec_driver_sql(
        "select tablename from pg_tables where schemaname='public'").fetchall()}
    assert set(Base.metadata.tables) <= names


def test_seed_is_idempotent(db):
    from app.db.seed import seed_database
    before = q(db, "select (select count(*) from products)+(select count(*) from sales)+(select count(*) from users)")
    assert seed_database(db) is False  # ikinci çalıştırma hiçbir şey eklemez
    after = q(db, "select (select count(*) from products)+(select count(*) from sales)+(select count(*) from users)")
    assert before == after


def test_seed_requires_password_env(db, monkeypatch):
    from app.db.seed import seed_database
    monkeypatch.delenv("SEED_DEFAULT_PASSWORD")
    with pytest.raises(RuntimeError):
        seed_database(db)


def test_passwords_are_hashed_not_plain(db):
    import os
    with Session(db) as s:
        for u in s.scalars(select(User)):
            assert u.password_hash != os.environ["SEED_DEFAULT_PASSWORD"]
            assert u.password_hash.startswith(("scrypt:", "pbkdf2:"))


def test_barcodes_are_text_and_keep_leading_zero(db):
    with Session(db) as s:
        barcodes = [p.barcode for p in s.scalars(select(Product))]
    assert barcodes and all(isinstance(b, str) and b.startswith("0") for b in barcodes)
    assert len(set(barcodes)) == len(barcodes)


def test_every_sale_has_exactly_one_payment(db):
    assert q(db, "select count(*) from sales s where (select count(*) from payments p where p.sale_id=s.sale_id) <> 1") == 0


def test_sale_totals_equal_item_sums(db):
    assert q(db, """select count(*) from sales s where s.total_amount <>
                    (select sum(line_total) from sale_items i where i.sale_id=s.sale_id)""") == 0


def test_stock_equals_sum_of_movements_and_never_negative(db):
    assert q(db, """select count(*) from products p where p.stock_quantity <>
                    coalesce((select sum(quantity) from stock_movements m where m.product_id=p.product_id),0)""") == 0
    assert q(db, """select count(*) from (select sum(quantity) over (partition by product_id
                    order by movement_date, movement_id) r from stock_movements) x where r < 0""") == 0


def test_seed_supports_report_scenarios(db):
    assert q(db, "select count(*) from products where stock_quantity < min_stock_level") > 0       # kritik stok
    assert q(db, "select count(*) from products where expiry_date between current_date and current_date + 60") > 0
    assert q(db, "select count(distinct payment_method) from payments") >= 2
    assert q(db, "select count(*) from sales where customer_id is null") > 0                        # müşterisiz satış
    assert q(db, "select count(*) from prescription_items where sgk_covered_amount > 0") > 0


def test_second_payment_for_same_sale_is_rejected(db):
    sale_id = q(db, "select sale_id from sales limit 1")
    with pytest.raises(IntegrityError):
        with Session(db) as s, s.begin():
            s.add(Payment(sale_id=sale_id, payment_method="cash"))


@pytest.mark.parametrize("bad", [
    dict(stock_quantity=-1),
    dict(price=Decimal("-1.00")),
])
def test_product_check_constraints(db, bad):
    base = dict(name="X", barcode="0000000000001", category="Test", stock_quantity=1, min_stock_level=1, price=Decimal("1.00"))
    base.update(bad)
    with pytest.raises(IntegrityError):
        with Session(db) as s, s.begin():
            s.add(Product(**base))


def test_line_total_must_equal_quantity_times_price(db):
    sid = q(db, "select sale_id from sales limit 1")
    pid = q(db, "select product_id from products limit 1")
    with pytest.raises(IntegrityError):
        with Session(db) as s, s.begin():
            s.add(SaleItem(sale_id=sid, product_id=pid, quantity=2, unit_price=Decimal("10.00"), line_total=Decimal("99.00")))


def test_invalid_enum_values_rejected(db):
    uid = q(db, "select user_id from users limit 1")
    with pytest.raises(IntegrityError):
        with Session(db) as s, s.begin():
            s.add(Sale(total_amount=Decimal("1.00"), status="weird", user_id=uid))
    pid = q(db, "select product_id from products limit 1")
    with pytest.raises(IntegrityError):  # satış hareketi pozitif olamaz
        with Session(db) as s, s.begin():
            s.add(StockMovement(product_id=pid, movement_type="sale", quantity=5))


def test_foreign_keys_enforced(db):
    with pytest.raises(IntegrityError):
        with Session(db) as s, s.begin():
            s.add(SaleItem(sale_id=-1, product_id=-1, quantity=1, unit_price=Decimal("1"), line_total=Decimal("1")))
