
import sqlite3
from pathlib import Path
from contextlib import contextmanager

DB_PATH = Path(__file__).resolve().parent / "eczane.db"


@contextmanager
def get_connection():
    connection = sqlite3.connect(DB_PATH)

    try:
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")

        with connection:
            yield connection

    finally:
        connection.close()

def init_db():
    with get_connection() as connection:

        # ==========================================
        # 1. ÜRÜNLER TABLOSU
        # ==========================================
        connection.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                barcode TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                stock INTEGER NOT NULL DEFAULT 0
                    CHECK (stock >= 0),
                price REAL NOT NULL DEFAULT 0
                    CHECK (price >= 0),
                expiry_date TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # ==========================================
        # 2. MÜŞTERİLER TABLOSU
        # ==========================================
        connection.execute("""
            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                phone TEXT NOT NULL,
                email TEXT,
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # ==========================================
        # 3. SATIŞLAR TABLOSU
        # ==========================================
        connection.execute("""
            CREATE TABLE IF NOT EXISTS sales (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                customer_id INTEGER,
                quantity INTEGER NOT NULL CHECK (quantity > 0),
                unit_price REAL NOT NULL CHECK (unit_price >= 0),
                total_price REAL NOT NULL CHECK (total_price >= 0),
                sale_date TEXT DEFAULT (datetime('now', 'localtime')),
                status TEXT NOT NULL DEFAULT 'completed'
                    CHECK (status IN ('completed', 'refunded')),
                FOREIGN KEY (product_id) REFERENCES products(id),
                FOREIGN KEY (customer_id) REFERENCES customers(id)
            )
        """)

        # ==========================================
        # 4. ESKİ VERİTABANI SÜTUN KONTROLÜ
        # ==========================================
        columns = {
            row["name"]
            for row in connection.execute(
                "PRAGMA table_info(sales)"
            ).fetchall()
        }

        # Status sütunu yoksa ekle
        if "status" not in columns:
            connection.execute("""
                ALTER TABLE sales
                ADD COLUMN status TEXT NOT NULL DEFAULT 'completed'
                    CHECK (status IN ('completed', 'refunded'))
            """)
            print("Status sütunu eklendi.")

        # Customer_id sütunu yoksa ekle
        if "customer_id" not in columns:
            connection.execute("""
                ALTER TABLE sales
                ADD COLUMN customer_id INTEGER
                    REFERENCES customers(id)
            """)
            print("Customer_id sütunu eklendi.")


        # ==========================================
        # 4. ECZANE AYARLARI TABLOSU
        # ==========================================
        connection.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                pharmacy_name TEXT NOT NULL DEFAULT '',
                pharmacy_phone TEXT NOT NULL DEFAULT '',
                pharmacy_email TEXT NOT NULL DEFAULT '',
                critical_stock_limit INTEGER NOT NULL DEFAULT 3,
                expiry_warning_days INTEGER NOT NULL DEFAULT 30,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Varsayılan ayar kaydı
        connection.execute("""
            INSERT OR IGNORE INTO settings (
                id,
                pharmacy_name,
                pharmacy_phone,
                pharmacy_email,
                critical_stock_limit,
                expiry_warning_days
            )
            VALUES (1, '', '', '', 3, 30)
        """)


    print("EczaneAI veritabanı hazır!")


if __name__ == "__main__":
    init_db()
