"""SQLAlchemy modelleri (ER diyagramı Sayfa-3 ile uyumlu, İngilizce adlarla).

ER diyagramındaki Türkçe -> İngilizce eşleme:
  Kullanıcı->users, Ürün->products, Tedarikçi->suppliers, Satış->sales, Satış_Kalemleri->sale_items,
  Ödeme->payments, Müşteri->customers, Reçete->prescriptions, Reçete_Kalemi->prescription_items,
  Stok_Hareketleri->stock_movements, Log_Kayıtları->audit_logs, Sorgu_Geçmişi->query_history,
  Rapor_Geçmişi->report_history

ER'ye göre EKLENEN alanlar (onay gerekir, gerekçeleri README'de):
  products.min_stock_level, sales.status
ER'den bilinçli sadeleştirmeler:
  payments.amount YOK (1:1 ilişki, tutar sales.total_amount'tan gelir)
"""
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, Numeric, String, Text,
    UniqueConstraint, func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

Money = Numeric(12, 2)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("role IN ('admin', 'pharmacist', 'staff')", name="ck_users_role"),
    )

    user_id: Mapped[int] = mapped_column(primary_key=True)
    first_name: Mapped[str] = mapped_column(String(80))
    last_name: Mapped[str] = mapped_column(String(80))
    email: Mapped[str] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))  # düz metin parola ASLA tutulmaz
    role: Mapped[str] = mapped_column(String(20))


class Supplier(Base):
    __tablename__ = "suppliers"

    supplier_id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150))
    phone: Mapped[str | None] = mapped_column(String(30))

    products: Mapped[list["Product"]] = relationship(back_populates="supplier")


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint("stock_quantity >= 0", name="ck_products_stock_nonneg"),
        CheckConstraint("price >= 0", name="ck_products_price_nonneg"),
        CheckConstraint("min_stock_level >= 0", name="ck_products_min_stock_nonneg"),
    )

    product_id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    barcode: Mapped[str] = mapped_column(String(32), unique=True)  # başında sıfır olabilir -> metin
    category: Mapped[str] = mapped_column(String(80))
    stock_quantity: Mapped[int] = mapped_column(Integer, default=0)
    min_stock_level: Mapped[int] = mapped_column(Integer, default=10)  # ER'ye EKLENDİ (kritik stok için)
    price: Mapped[Decimal] = mapped_column(Money)
    expiry_date: Mapped[date | None] = mapped_column(Date)
    supplier_id: Mapped[int | None] = mapped_column(ForeignKey("suppliers.supplier_id"))

    supplier: Mapped[Supplier | None] = relationship(back_populates="products")


class Customer(Base):
    __tablename__ = "customers"
    __table_args__ = (
        CheckConstraint("insurance_status IN ('sgk', 'private', 'none')", name="ck_customers_insurance"),
    )

    customer_id: Mapped[int] = mapped_column(primary_key=True)
    first_name: Mapped[str] = mapped_column(String(80))
    last_name: Mapped[str] = mapped_column(String(80))
    insurance_status: Mapped[str] = mapped_column(String(20), default="none")


class Sale(Base):
    __tablename__ = "sales"
    __table_args__ = (
        CheckConstraint("total_amount >= 0", name="ck_sales_total_nonneg"),
        CheckConstraint("status IN ('completed', 'cancelled', 'refunded')", name="ck_sales_status"),
        Index("ix_sales_sale_date", "sale_date"),
    )

    sale_id: Mapped[int] = mapped_column(primary_key=True)
    sale_date: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    total_amount: Mapped[Decimal] = mapped_column(Money)
    status: Mapped[str] = mapped_column(String(20), default="completed")  # ER'ye EKLENDİ (iptal/iade için)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"))
    customer_id: Mapped[int | None] = mapped_column(ForeignKey("customers.customer_id"))  # müşterisiz satış serbest

    items: Mapped[list["SaleItem"]] = relationship(back_populates="sale", cascade="all, delete-orphan")
    payment: Mapped["Payment | None"] = relationship(back_populates="sale", uselist=False)


class SaleItem(Base):
    __tablename__ = "sale_items"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_sale_items_qty_pos"),
        CheckConstraint("line_total = quantity * unit_price", name="ck_sale_items_line_total"),
        Index("ix_sale_items_sale_id", "sale_id"),
        Index("ix_sale_items_product_id", "product_id"),
    )

    sale_item_id: Mapped[int] = mapped_column(primary_key=True)
    sale_id: Mapped[int] = mapped_column(ForeignKey("sales.sale_id", ondelete="CASCADE"))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.product_id"))
    quantity: Mapped[int] = mapped_column(Integer)
    unit_price: Mapped[Decimal] = mapped_column(Money)
    line_total: Mapped[Decimal] = mapped_column(Money)

    sale: Mapped[Sale] = relationship(back_populates="items")
    product: Mapped[Product] = relationship()


class Payment(Base):
    """Satış ile 1:1. Tutar ayrıca saklanmaz; sales.total_amount kullanılır (ekip kararı)."""
    __tablename__ = "payments"
    __table_args__ = (
        CheckConstraint("payment_method IN ('cash', 'credit_card', 'other')", name="ck_payments_method"),
        UniqueConstraint("sale_id", name="uq_payments_sale_id"),  # 1:1'i veritabanı garanti eder
    )

    payment_id: Mapped[int] = mapped_column(primary_key=True)
    payment_method: Mapped[str] = mapped_column(String(20))
    sale_id: Mapped[int] = mapped_column(ForeignKey("sales.sale_id", ondelete="CASCADE"))

    sale: Mapped[Sale] = relationship(back_populates="payment")


class Prescription(Base):
    __tablename__ = "prescriptions"
    __table_args__ = (
        CheckConstraint("prescription_status IN ('pending', 'completed', 'cancelled')", name="ck_presc_status"),
        CheckConstraint("sgk_status IN ('sgk_covered', 'private')", name="ck_presc_sgk_status"),
    )

    prescription_id: Mapped[int] = mapped_column(primary_key=True)
    prescription_status: Mapped[str] = mapped_column(String(20))
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.customer_id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"))
    sgk_status: Mapped[str] = mapped_column(String(20))
    prescription_date: Mapped[date] = mapped_column(Date)

    items: Mapped[list["PrescriptionItem"]] = relationship(back_populates="prescription", cascade="all, delete-orphan")


class PrescriptionItem(Base):
    __tablename__ = "prescription_items"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_presc_items_qty_pos"),
        CheckConstraint(
            "sgk_covered_amount >= 0 AND patient_copay >= 0 AND price_difference >= 0",
            name="ck_presc_items_amounts_nonneg",
        ),
    )

    prescription_item_id: Mapped[int] = mapped_column(primary_key=True)
    prescription_id: Mapped[int] = mapped_column(ForeignKey("prescriptions.prescription_id", ondelete="CASCADE"))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.product_id"))
    quantity: Mapped[int] = mapped_column(Integer)
    unit_price: Mapped[Decimal] = mapped_column(Money)
    sgk_covered_amount: Mapped[Decimal] = mapped_column(Money, default=0)
    patient_copay: Mapped[Decimal] = mapped_column(Money, default=0)
    price_difference: Mapped[Decimal] = mapped_column(Money, default=0)

    prescription: Mapped[Prescription] = relationship(back_populates="items")
    product: Mapped[Product] = relationship()


class StockMovement(Base):
    """quantity İŞARETLİDİR: girişler (+), çıkışlar (-). Stok = SUM(quantity)."""
    __tablename__ = "stock_movements"
    __table_args__ = (
        CheckConstraint(
            "movement_type IN ('stock_in', 'sale', 'return', 'waste', 'count_adjustment')",
            name="ck_stock_movement_type",
        ),
        CheckConstraint("quantity <> 0", name="ck_stock_movement_qty_nonzero"),
        CheckConstraint(
            "(movement_type IN ('stock_in', 'return') AND quantity > 0) OR "
            "(movement_type IN ('sale', 'waste') AND quantity < 0) OR "
            "movement_type = 'count_adjustment'",
            name="ck_stock_movement_sign",
        ),
        Index("ix_stock_movements_product_id", "product_id"),
    )

    movement_id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.product_id"))
    movement_type: Mapped[str] = mapped_column(String(20))
    quantity: Mapped[int] = mapped_column(Integer)
    movement_date: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.user_id"))
    description: Mapped[str | None] = mapped_column(String(255))


class AuditLog(Base):
    """Önemli olay kayıtları. Yapay zekâ erişimine KAPALI. Sorgu metni/hassas değer yazılmaz."""
    __tablename__ = "audit_logs"

    log_id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.user_id"))  # boş olabilir
    action_type: Mapped[str] = mapped_column(String(50))
    action_description: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class QueryHistory(Base):
    __tablename__ = "query_history"

    query_id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"))
    question: Mapped[str] = mapped_column(Text)
    query_status: Mapped[str] = mapped_column(String(20))  # success / failed / blocked
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    execution_time_ms: Mapped[int | None] = mapped_column(Integer)
    error_message: Mapped[str | None] = mapped_column(Text)


class ReportHistory(Base):
    __tablename__ = "report_history"

    report_id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"))
    name: Mapped[str] = mapped_column(String(200))
    report_type: Mapped[str] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    report_status: Mapped[str] = mapped_column(String(20))
    description: Mapped[str | None] = mapped_column(Text)
