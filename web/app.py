
from flask import Flask, render_template, request, jsonify
from db.database import get_connection

app = Flask(__name__)

import re

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/api/query", methods=["POST"])
def query():
    data = request.get_json(silent=True) or {}
    question = data.get("question", "").strip()

    if not question:
        return jsonify({
            "success": False,
            "message": "Lütfen bir soru yaz."
        }), 400

    # Şimdilik yalnızca bağlantıyı test ediyoruz.
    # Sonraki aşamada AI, SQL ve MCP akışı eklenecek.
    return jsonify({
        "success": True,
        "question": question,
        "stage": "received",
        "message": (
            "Sorun Flask backend'e ulaştı. "
            "AI, MCP ve veritabanı bağlantısı henüz eklenmedi."
        )
    })

# ==========================================
# MÜŞTERİ YÖNETİMİ - LİSTELEME
# ==========================================

@app.route("/api/customers", methods=["GET"])
def get_customers():
    try:
        with get_connection() as connection:
            customers = connection.execute("""
                SELECT
                    id,
                    name,
                    phone,
                    email,
                    notes,
                    created_at
                FROM customers
                ORDER BY id DESC
            """).fetchall()

        return jsonify({
            "success": True,
            "customers": [dict(customer) for customer in customers]
        })

    except Exception:
        app.logger.exception("Müşteriler listelenemedi")

        return jsonify({
            "success": False,
            "message": "Müşteriler listelenirken hata oluştu."
        }), 500


# ==========================================
# MÜŞTERİ YÖNETİMİ - EKLEME
# ==========================================

@app.route("/api/customers", methods=["POST"])
def add_customer():
    try:
        data = request.get_json(silent=True) or {}

        if not isinstance(data, dict):
            return jsonify({
                "success": False,
                "message": "Geçersiz veri formatı."
            }), 400

        name = str(data.get("name") or "").strip()
        phone = str(data.get("phone") or "").strip()
        email = str(data.get("email") or "").strip()
        notes = str(data.get("notes") or "").strip()

        if not name or not phone:
            return jsonify({
                "success": False,
                "message": "Ad soyad ve telefon zorunludur."
            }), 400

        
        if len(name) < 2 or len(name) > 120:
            return jsonify({
                "success": False,
                "message": "Ad soyad 2-120 karakter olmalıdır."
            }), 400

        if not re.fullmatch(r"05[0-9]{9}", phone):
            return jsonify({
                "success": False,
                "message": "Telefon 05 ile başlamalı ve 11 rakam olmalıdır."
            }), 400

        if len(notes) > 500:
            return jsonify({
                "success": False,
                "message": "Notlar en fazla 500 karakter olabilir."
            }), 400


        with get_connection() as connection:
            cursor = connection.execute("""
                INSERT INTO customers (name, phone, email, notes)
                VALUES (?, ?, ?, ?)
            """, (name, phone, email, notes))

            customer_id = cursor.lastrowid

        return jsonify({
            "success": True,
            "message": "Müşteri başarıyla eklendi.",
            "customer_id": customer_id
        }), 201

    except Exception:
        app.logger.exception("Müşteri eklenemedi")

        return jsonify({
            "success": False,
            "message": "Müşteri eklenirken hata oluştu."
        }), 500

# ==========================================
# MÜŞTERİ YÖNETİMİ - SİLME API
# ==========================================

@app.route("/api/customers/<int:customer_id>", methods=["DELETE"])
def delete_customer(customer_id):
    try:
        with get_connection() as connection:

            # Önce müşteri mevcut mu kontrol et
            customer = connection.execute("""
                SELECT id, name
                FROM customers
                WHERE id = ?
            """, (customer_id,)).fetchone()

            if customer is None:
                return jsonify({
                    "success": False,
                    "message": "Müşteri bulunamadı."
                }), 404

            # Müşterinin satış geçmişi var mı?
            sale = connection.execute("""
                SELECT id
                FROM sales
                WHERE customer_id = ?
                LIMIT 1
            """, (customer_id,)).fetchone()

            if sale is not None:
                return jsonify({
                    "success": False,
                    "message": (
                        "Bu müşterinin satış geçmişi bulunduğu için "
                        "silme işlemi yapılamaz."
                    )
                }), 409

            # Satış geçmişi yoksa müşteriyi sil
            connection.execute("""
                DELETE FROM customers
                WHERE id = ?
            """, (customer_id,))

        return jsonify({
            "success": True,
            "message": "Müşteri başarıyla silindi."
        }), 200

    except Exception:
        app.logger.exception("Müşteri silinemedi")

        return jsonify({
            "success": False,
            "message": "Müşteri silinirken hata oluştu."
        }), 500

# ==========================================
# MÜŞTERİ YÖNETİMİ - GÜNCELLEME API
# ==========================================

@app.route("/api/customers/<int:customer_id>", methods=["PUT"])
def update_customer(customer_id):
    try:
        data = request.get_json(silent=True)

        if not isinstance(data, dict):
            return jsonify({
                "success": False,
                "message": "Geçerli JSON verisi gönderilmelidir."
            }), 400

        name = data.get("name")
        phone = data.get("phone")
        email = data.get("email", "")
        notes = data.get("notes", "")

        # Önce veri tiplerini kontrol et
        if not isinstance(name, str) or not name.strip():
            return jsonify({
                "success": False,
                "message": "Ad soyad zorunludur."
            }), 400

        if not isinstance(phone, str) or not phone.strip():
            return jsonify({
                "success": False,
                "message": "Telefon numarası zorunludur."
            }), 400

        if not isinstance(email, str) or not isinstance(notes, str):
            return jsonify({
                "success": False,
                "message": "E-posta ve notlar metin olmalıdır."
            }), 400

        name = name.strip()
        phone = phone.strip()
        email = email.strip()
        notes = notes.strip()

        # Ad soyad uzunluk kontrolü
        if len(name) < 2 or len(name) > 120:
            return jsonify({
                "success": False,
                "message": "Ad soyad 2-120 karakter olmalıdır."
            }), 400

        # Telefon numarası kontrolü
        if not re.fullmatch(r"05[0-9]{9}", phone):
            return jsonify({
                "success": False,
                "message": "Telefon 05 ile başlamalı ve 11 rakam olmalıdır."
            }), 400

        # Not uzunluğu kontrolü
        if len(notes) > 500:
            return jsonify({
                "success": False,
                "message": "Notlar en fazla 500 karakter olabilir."
            }), 400

        # Müşteri bilgilerini güncelle
        with get_connection() as connection:
            cursor = connection.execute("""
                UPDATE customers
                SET name = ?,
                    phone = ?,
                    email = ?,
                    notes = ?
                WHERE id = ?
            """, (name, phone, email, notes, customer_id))

            if cursor.rowcount == 0:
                return jsonify({
                    "success": False,
                    "message": "Müşteri bulunamadı."
                }), 404

        return jsonify({
            "success": True,
            "message": "Müşteri bilgileri başarıyla güncellendi."
        }), 200

    except Exception:
        app.logger.exception("Müşteri güncellenemedi")

        return jsonify({
            "success": False,
            "message": "Müşteri güncellenirken hata oluştu."
        }), 500

# ==========================================
# ÜRÜN YÖNETİMİ - LİSTELEME API
# ==========================================

@app.route("/api/products", methods=["GET"])
def get_products():
    try:
        from datetime import date

        today = date.today()

        with get_connection() as connection:
            products = connection.execute("""
                SELECT
                    id,
                    barcode,
                    name,
                    stock,
                    price,
                    expiry_date
                FROM products
                ORDER BY id DESC
            """).fetchall()

        product_list = []

        for product in products:
            item = dict(product)

            try:
                expiry = date.fromisoformat(item["expiry_date"])
                days_left = (expiry - today).days

                if days_left < 0:
                    expiry_status = "expired"
                    expiry_label = "SKT Geçmiş"

                elif days_left <= 30:
                    expiry_status = "warning"
                    expiry_label = "SKT Yaklaşıyor"

                else:
                    expiry_status = "safe"
                    expiry_label = "SKT Uygun"

            except (ValueError, TypeError):
                days_left = None
                expiry_status = "unknown"
                expiry_label = "Tarih Geçersiz"

            item["days_left"] = days_left
            item["expiry_status"] = expiry_status
            item["expiry_label"] = expiry_label

            product_list.append(item)

        return jsonify({
            "success": True,
            "products": product_list
        })

    except Exception:
        app.logger.exception("Ürünler listelenemedi")

        return jsonify({
            "success": False,
            "message": "Ürünler listelenirken bir hata oluştu."
        }), 500

# ==========================================
# AI - AKILLI STOK ANALİZİ API
# ==========================================

@app.route("/api/ai/stock-analysis", methods=["GET"])
def stock_analysis():
    from datetime import date

    try:
        with get_connection() as connection:

            # ECZANE AYARLARINI VERITABANINDAN OKU
            settings = connection.execute("""
                SELECT critical_stock_limit, expiry_warning_days
                FROM settings
                WHERE id = 1
            """).fetchone()

            critical_limit = (
                int(settings["critical_stock_limit"])
                if settings else 8
            )

            expiry_warning_days = (
                int(settings["expiry_warning_days"])
                if settings else 30
            )

            # URUNLER VE SON 30 GUNLUK SATISLAR
            rows = connection.execute("""
                SELECT
                    p.id,
                    p.name,
                    p.stock,
                    p.expiry_date,
                    COALESCE(SUM(
                        CASE
                            WHEN s.status = 'completed'
                             AND s.sale_date >= datetime(
                                 'now', 'localtime', '-30 days'
                             )
                            THEN s.quantity
                            ELSE 0
                        END
                    ), 0) AS sold_last_30_days
                FROM products p
                LEFT JOIN sales s ON s.product_id = p.id
                GROUP BY p.id, p.name, p.stock, p.expiry_date
                ORDER BY p.name
            """).fetchall()

        analyses = []

        for row in rows:
            product = dict(row)

            stock = int(product["stock"] or 0)
            sold = int(product["sold_last_30_days"] or 0)
            daily_average = sold / 30

            # SKT KONTROLU
            expiry_date = product["expiry_date"]
            today = date.today()

            if expiry_date:
                expiry = date.fromisoformat(expiry_date)
                days_until_expiry = (expiry - today).days
            else:
                days_until_expiry = None

            is_expired = (
                days_until_expiry is not None
                and days_until_expiry < 0
            )

            # RISK HESAPLAMASI
            if is_expired:
                estimated_days = 0
                risk = "SKT Geçmiş"

            elif (
                days_until_expiry is not None
                and days_until_expiry <= expiry_warning_days
            ):
                risk = "SKT Yaklaşıyor"
                estimated_days = (
                    round(stock / daily_average, 1)
                    if daily_average > 0 else None
                )

            elif stock <= 0:
                estimated_days = 0
                risk = "Kritik"

            elif stock <= critical_limit:
                estimated_days = (
                    round(stock / daily_average, 1)
                    if daily_average > 0 else None
                )
                risk = "Kritik"

            elif daily_average == 0:
                estimated_days = None
                risk = "Veri Yetersiz"

            else:
                estimated_days = round(
                    stock / daily_average, 1
                )

                if estimated_days <= 3:
                    risk = "Kritik"
                elif estimated_days <= 7:
                    risk = "Yüksek"
                elif estimated_days <= 14:
                    risk = "Orta"
                else:
                    risk = "Düşük"

            # SIPARIS ONERISI
            if is_expired:
                recommendation = (
                    "Ürünün son kullanma tarihi geçmiş. "
                    "Satışa sunmayın, stoktan ayırın."
                )
                suggested_order = 0

            elif (
                days_until_expiry is not None
                and days_until_expiry <= expiry_warning_days
            ):
                recommendation = (
                    "Son kullanma tarihi yaklaşıyor. "
                    "Öncelikle mevcut stoğu değerlendirin."
                )
                suggested_order = 0

            elif stock <= 0:
                recommendation = (
                    "Stok tükendi. Acil sipariş oluşturun."
                )
                suggested_order = max(
                    0, round(daily_average * 30 - stock + 0.5)
                )

            
            elif daily_average == 0 and stock <= critical_limit:
                recommendation = (
                    "Kritik stok seviyesi. "
                    "Satış geçmişi yetersiz; manuel sipariş kontrolü yapın."
                )
                suggested_order = 0

            elif daily_average == 0:
                recommendation = (
                    "Satış verisi yetersiz. "
                    "Stok durumunu manuel kontrol edin."
                )
                suggested_order = 0

            elif (
                stock <= critical_limit
                or estimated_days <= 7
            ):
                suggested_order = max(
                    0, round(daily_average * 30 - stock + 0.5)
                )

                if suggested_order > 0:
                    recommendation = (
                        "Stok seviyesi kritik. Yeni sipariş planlayın."
                    )
                else:
                    recommendation = (
                        "Stok seviyesi kritik ancak mevcut stok "
                        "tahmini 30 günlük talebi karşılıyor. "
                        "Stok durumunu takip edin."
                    )

            elif estimated_days <= 14:
                recommendation = (
                    "Stok seviyesini takip edin. "
                    "Sipariş hazırlığı yapın."
                )
                suggested_order = max(
                    0, round(daily_average * 30 - stock + 0.5)
                )

            else:
                recommendation = "Stok seviyesi yeterli."
                suggested_order = 0

            analyses.append({
                "product_id": product["id"],
                "product_name": product["name"],
                "current_stock": stock,
                "sold_last_30_days": sold,
                "daily_average_sales": round(daily_average, 2),
                "estimated_days_remaining": estimated_days,
                "days_until_expiry": days_until_expiry,
                "risk_level": risk,
                "recommendation": recommendation,
                "suggested_order_quantity": suggested_order
            })

        return jsonify({
            "success": True,
            "critical_stock_limit": critical_limit,
            "expiry_warning_days": expiry_warning_days,
            "analysis": analyses
        }), 200

    except Exception:
        app.logger.exception("Stok analizi yapılamadı")

        return jsonify({
            "success": False,
            "message": "Stok analizi sırasında hata oluştu."
        }), 500
# ==========================================
# ÜRÜN YÖNETİMİ - EKLEME API
# ==========================================

@app.route("/api/products", methods=["POST"])
def add_product():
    data = request.get_json(silent=True) or {}

    barcode = str(data.get("barcode") or "").strip()
    name = str(data.get("name") or "").strip()
    expiry_date = str(data.get("expiry_date") or "").strip()

    try:
        stock = int(data.get("stock"))
        price = float(data.get("price"))
    except (TypeError, ValueError, OverflowError):
        return jsonify({
            "success": False,
            "message": "Stok ve fiyat geçerli sayılar olmalıdır."
        }), 400

    if not barcode or not name or not expiry_date:
        return jsonify({
            "success": False,
            "message": "Barkod, ürün adı ve SKT zorunludur."
        }), 400

    if stock < 0 or price < 0:
        return jsonify({
            "success": False,
            "message": "Stok ve fiyat negatif olamaz."
        }), 400

    try:
        from datetime import date
        
        parsed_date = date.fromisoformat(expiry_date)

        if (
            len(expiry_date) != 10
            or parsed_date.isoformat() != expiry_date
            or not (2000 <= parsed_date.year <= 2100)
        ):
            raise ValueError("Geçersiz SKT yılı")

    except ValueError:
        return jsonify({
            "success": False,
            "message": "SKT YYYY-MM-DD formatında olmalıdır."
        }), 400

    try:
        with get_connection() as connection:
            cursor = connection.execute("""
                INSERT INTO products
                    (barcode, name, stock, price, expiry_date)
                VALUES (?, ?, ?, ?, ?)
            """, (barcode, name, stock, price, expiry_date))

            product_id = cursor.lastrowid

        return jsonify({
            "success": True,
            "message": "Ürün başarıyla kaydedildi.",
            "product_id": product_id
        }), 201

    except Exception as error:
        import sqlite3

        if isinstance(error, sqlite3.IntegrityError):
            return jsonify({
                "success": False,
                "message": "Bu barkod zaten kayıtlı veya ürün bilgileri geçersiz."
            }), 409

        app.logger.exception("Ürün kaydedilemedi")

        return jsonify({
            "success": False,
            "message": "Ürün kaydedilirken bir hata oluştu."
        }), 500

    # ==========================================
# URUN GUNCELLEME API
# ==========================================

@app.route("/api/products/<int:product_id>", methods=["PUT"])
def update_product(product_id):
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "success": False,
            "message": "Geçerli JSON verisi gönderilmelidir."
        }), 400

    allowed_fields = {
        "barcode", "name", "stock", "price", "expiry_date"
    }

    fields = []
    values = []

    for field in allowed_fields:
        if field not in data:
            continue

        value = data[field]

        if field in ("barcode", "name"):
            if not isinstance(value, str) or not value.strip():
                return jsonify({
                    "success": False,
                    "message": f"{field} boş olamaz."
                }), 400
            value = value.strip()

        elif field == "stock":
            if type(value) is not int or value < 0:
                return jsonify({
                    "success": False,
                    "message": "Stok negatif olmayan tam sayı olmalıdır."
                }), 400

        elif field == "price":
            if type(value) not in (int, float) or not 0 <= value < float("inf"):
                return jsonify({
                    "success": False,
                    "message": "Fiyat geçerli ve negatif olmayan sayı olmalıdır."
                }), 400

        
        elif field == "expiry_date":
            from datetime import date
            try:
                if not isinstance(value, str):
                    raise ValueError("SKT metin olmalıdır")

                parsed_date = date.fromisoformat(value)

                if (
                    len(value) != 10
                    or parsed_date.isoformat() != value
                    or not (2000 <= parsed_date.year <= 2100)
                ):
                    raise ValueError("Geçersiz SKT yılı")

            except (TypeError, ValueError):
                return jsonify({
                    "success": False,
                    "message": "SKT YYYY-MM-DD formatında olmalıdır."
                }), 400


        fields.append(f"{field} = ?")
        values.append(value)

    if not fields:
        return jsonify({
            "success": False,
            "message": "Güncellenecek alan bulunamadı."
        }), 400

    try:
        with get_connection() as connection:
            cursor = connection.execute(
                f"UPDATE products SET {', '.join(fields)} WHERE id = ?",
                values + [product_id]
            )

            if cursor.rowcount == 0:
                return jsonify({
                    "success": False,
                    "message": "Ürün bulunamadı."
                }), 404

        return jsonify({
            "success": True,
            "message": "Ürün başarıyla güncellendi."
        })

    except Exception as error:
        import sqlite3

        if isinstance(error, sqlite3.IntegrityError):
            return jsonify({
                "success": False,
                "message": "Barkod zaten kayıtlı veya bilgiler geçersiz."
            }), 409

        app.logger.exception("Ürün güncellenemedi")

        return jsonify({
            "success": False,
            "message": "Ürün güncellenirken hata oluştu."
        }), 500

    # ==========================================
# URUN SILME API
# ==========================================

@app.route("/api/products/<int:product_id>", methods=["DELETE"])

def delete_product(product_id):
    try:
        with get_connection() as connection:
            sales_count = connection.execute(
                "SELECT COUNT(*) FROM sales WHERE product_id = ?",
                (product_id,)
            ).fetchone()[0]

            if sales_count > 0:
                return jsonify({
                    "success": False,
                    "message": (
                        f"Bu ürüne ait {sales_count} satış kaydı bulunduğu "
                        "için ürün silinemez. Satış geçmişi korunmalıdır."
                    )
                }), 409

            cursor = connection.execute(
                "DELETE FROM products WHERE id = ?",
                (product_id,)
            )

            if cursor.rowcount == 0:
                return jsonify({
                    "success": False,
                    "message": "Ürün bulunamadı."
                }), 404

        return jsonify({
            "success": True,
            "message": "Ürün başarıyla silindi."
        })

    except Exception:
        app.logger.exception("Ürün silinemedi")

        return jsonify({
            "success": False,
            "message": "Ürün silinirken bir hata oluştu."
        }), 500


# ==========================================
# SATIŞ İADE API
# ==========================================

@app.route("/api/sales/<int:sale_id>/refund", methods=["POST"])
def refund_sale(sale_id):
    try:
        with get_connection() as connection:
            # Es zamanli iadelerde stok tekrarini onle
            connection.execute("BEGIN IMMEDIATE")

            sale = connection.execute("""
                SELECT id, product_id, quantity, status
                FROM sales
                WHERE id = ?
            """, (sale_id,)).fetchone()

            if sale is None:
                return jsonify({
                    "success": False,
                    "message": "Satış bulunamadı."
                }), 404

            if sale["status"] == "refunded":
                return jsonify({
                    "success": False,
                    "message": "Bu satış daha önce iade edilmiş."
                }), 409

            connection.execute("""
                UPDATE sales
                SET status = 'refunded'
                WHERE id = ?
            """, (sale_id,))

            cursor=connection.execute("""
                UPDATE products
                SET stock = stock + ?
                WHERE id = ?
            """, (sale["quantity"], sale["product_id"]))

            if cursor.rowcount != 1:
                raise ValueError("İade edilecek ürün bulunamadı.")
            
        return jsonify({
            "success": True,
            "message": "Satış başarıyla iade edildi. Ürün stoğa eklendi."
        })

    except Exception:
        app.logger.exception("Satış iade işlemi başarısız")

        return jsonify({
            "success": False,
            "message": "İade işlemi sırasında bir hata oluştu."
        }), 500

    # ==========================================
# SATIS OLUSTURMA API
# ==========================================

@app.route("/api/sales", methods=["POST"])
def create_sale():
    try:
        data = request.get_json(silent=True)

        if not isinstance(data, dict):
            return jsonify({
                "success": False,
                "message": "Geçerli JSON verisi gönderilmedi."
            }), 400

        product_id = data.get("product_id")
        quantity = data.get("quantity")
        customer_id = data.get("customer_id")

        if (
            type(product_id) is not int
            or product_id <= 0
            or type(quantity) is not int
            or quantity <= 0
        ):
            return jsonify({
                "success": False,
                "message": "Geçerli ürün ID ve miktar girin."
            }), 400
        
                
           
        if customer_id is not None and (
            type(customer_id) is not int or customer_id <= 0
        ):
            return jsonify({
                "success": False,
                "message": "Geçerli bir müşteri ID girin."
            }), 400


        with get_connection() as connection:
            # Yazma işlemini baştan kilitleyerek stok yarışını önle
            connection.execute("BEGIN IMMEDIATE")

            if customer_id is not None:
                customer = connection.execute(
                    "SELECT id FROM customers WHERE id = ?",
                    (customer_id,)
                ).fetchone()

                if customer is None:
                    return jsonify({
                        "success": False,
                        "message": "Seçilen müşteri bulunamadı."
                    }), 404

            product = connection.execute(
                "SELECT id, stock, price, expiry_date FROM products WHERE id = ?",
                (product_id,)
            ).fetchone()

            if product is None:
                return jsonify({
                    "success": False,
                    "message": "Ürün bulunamadı."
                }), 404

            
            # Son kullanma tarihi kontrolü
            from datetime import date

            try:
                expiry_date = date.fromisoformat(product["expiry_date"])
            except (TypeError, ValueError):
                return jsonify({
                    "success": False,
                    "message": "Ürünün son kullanma tarihi geçersiz."
                }), 400

            if expiry_date < date.today():
                return jsonify({
                    "success": False,
                    "message": "Son kullanma tarihi geçmiş ürün satılamaz."
                }), 400


            if product["stock"] < quantity:
                return jsonify({
                    "success": False,
                    "message": "Yetersiz stok."
                }), 400

            unit_price = product["price"]
            total_price = round(unit_price * quantity, 2)

            connection.execute(
                "UPDATE products SET stock = stock - ? WHERE id = ?",
                (quantity, product_id)
            )

         
            cursor = connection.execute("""
                INSERT INTO sales (
                    product_id,
                    quantity,
                    unit_price,
                    total_price,
                    customer_id,
                    sale_date
                    )
                    VALUES (?, ?, ?, ?, ?, datetime('now', 'localtime'))

            """, (
                product_id,
                quantity,
                unit_price,
                total_price,
                customer_id
            ))


            sale_id = cursor.lastrowid
            remaining_stock = product["stock"] - quantity

        return jsonify({
            "success": True,
            "message": "Satış başarıyla kaydedildi.",
            "sale_id": sale_id,
            "customer_id": customer_id,
            "remaining_stock": remaining_stock,
            "total_price": total_price
        }), 201

    except Exception:
        app.logger.exception("Satış oluşturulamadı")

        return jsonify({
            "success": False,
            "message": "Satış sırasında bir hata oluştu."
        }), 500

    
# ==========================================
# SATIŞ GEÇMİŞİ API
# ==========================================

@app.route("/api/sales", methods=["GET"])
def get_sales():
    try:
        with get_connection() as connection:

            rows = connection.execute("""
                SELECT
                    s.id,
                    p.name AS product_name,
                    p.barcode AS barcode,
                    s.quantity,
                    s.unit_price,
                    s.total_price,
                    s.sale_date,
                    s.status,
                    s.customer_id,
                    c.name AS customer_name
                FROM sales s
                JOIN products p ON s.product_id = p.id
                LEFT JOIN customers c ON s.customer_id = c.id
                ORDER BY s.id DESC
            """).fetchall()

        return jsonify({
            "success": True,
            "sales": [dict(row) for row in rows]
        }), 200

    except Exception:
        app.logger.exception("Satış geçmişi alınamadı")

        return jsonify({
            "success": False,
            "message": "Satış geçmişi alınamadı."
        }), 500

# ==========================================
# GÜNLÜK SATIŞ RAPORU API
# ==========================================

@app.route("/api/reports/daily", methods=["GET"])
def get_daily_report():
    try:
        with get_connection() as connection:

            # Günlük satış istatistikleri
            summary = connection.execute("""
                SELECT
                    COUNT(*) AS total_sales,
                    COALESCE(SUM(quantity), 0) AS total_quantity,
                    COALESCE(SUM(total_price), 0) AS total_revenue
                FROM sales
                WHERE DATE(sale_date) = DATE('now', 'localtime')
                 AND status = 'completed'
            """).fetchone()

            # Günün en çok satılan ürünü
            top_product = connection.execute("""
                SELECT
                    p.name AS product_name,
                    SUM(s.quantity) AS quantity
                FROM sales s
                JOIN products p ON s.product_id = p.id
                WHERE DATE(s.sale_date) = DATE('now', 'localtime')
                 AND s.status = 'completed'
                GROUP BY s.product_id, p.name
                ORDER BY quantity DESC, p.name ASC
                LIMIT 1
            """).fetchone()

        return jsonify({
            "success": True,
            "date": __import__("datetime").date.today().isoformat(),
            "total_sales": summary["total_sales"],
            "total_quantity": summary["total_quantity"],
            "total_revenue": round(summary["total_revenue"], 2),
            "top_product": dict(top_product) if top_product else None
        }), 200

    except Exception:
        app.logger.exception("Günlük satış raporu oluşturulamadı")
        return jsonify({
            "success": False,
            "message": "Günlük satış raporu alınamadı."
        }), 500

    
# ==========================================
# TARIH ARALIKLI SATIS RAPORU API
# ==========================================

@app.route("/api/reports/range", methods=["GET"])
def get_range_report():
    from datetime import date

    start_date = request.args.get("start_date", "")
    end_date = request.args.get("end_date", "")

    try:
        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)
    except ValueError:
        return jsonify({
            "success": False,
            "message": "Tarih formatı YYYY-MM-DD olmalıdır."
        }), 400

    if start > end:
        return jsonify({
            "success": False,
            "message": "Başlangıç tarihi bitiş tarihinden sonra olamaz."
        }), 400

    try:
        with get_connection() as connection:
            summary = connection.execute("""
                SELECT
                    COUNT(*) AS total_sales,
                    COALESCE(SUM(quantity), 0) AS total_quantity,
                    COALESCE(SUM(total_price), 0) AS total_revenue
                FROM sales
                WHERE DATE(sale_date) BETWEEN ? AND ?
                  AND status = 'completed'
            """, (start.isoformat(), end.isoformat())).fetchone()

        return jsonify({
            "success": True,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "total_sales": summary["total_sales"],
            "total_quantity": summary["total_quantity"],
            "total_revenue": round(summary["total_revenue"], 2)
        }), 200

    except Exception:
        app.logger.exception("Tarih aralıklı satış raporu hatası")
        return jsonify({
            "success": False,
            "message": "Satış raporu oluşturulamadı."
        }), 500

    
# ==========================================
# ECZANE AYARLARI API
# ==========================================

@app.route("/api/settings", methods=["GET"])
def get_settings():
    try:
        with get_connection() as connection:
            row = connection.execute(
                "SELECT * FROM settings WHERE id = 1"
            ).fetchone()

        if row is None:
            return jsonify({
                "success": False,
                "message": "Ayar kaydı bulunamadı."
            }), 404

        return jsonify({
            "success": True,
            "settings": {
                "pharmacyName": row["pharmacy_name"],
                "pharmacyPhone": row["pharmacy_phone"],
                "pharmacyEmail": row["pharmacy_email"],
                "criticalStockLimit": row["critical_stock_limit"],
                "expiryWarningDays": row["expiry_warning_days"]
            }
        }), 200

    except Exception:
        app.logger.exception("Ayarlar alınamadı")
        return jsonify({
            "success": False,
            "message": "Ayarlar alınamadı."
        }), 500


@app.route("/api/settings", methods=["POST"])
def save_settings():
    try:
        data = request.get_json(silent=True) or {}

        pharmacy_name = str(data.get("pharmacyName", "")).strip()
        pharmacy_phone = str(data.get("pharmacyPhone", "")).strip()
        pharmacy_email = str(data.get("pharmacyEmail", "")).strip()

        critical_limit = data.get("criticalStockLimit", 3)
        expiry_days = data.get("expiryWarningDays", 30)

        if (
            isinstance(critical_limit, bool)
            or not isinstance(critical_limit, int)
            or critical_limit < 0
        ):
            return jsonify({
                "success": False,
                "message": "Kritik stok sınırı geçersiz."
            }), 400

        if (
            isinstance(expiry_days, bool)
            or expiry_days not in (7, 15, 30, 60)
        ):
            return jsonify({
                "success": False,
                "message": "SKT uyarı süresi geçersiz."
            }), 400

        with get_connection() as connection:
            connection.execute("""
                UPDATE settings
                SET pharmacy_name = ?,
                    pharmacy_phone = ?,
                    pharmacy_email = ?,
                    critical_stock_limit = ?,
                    expiry_warning_days = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = 1
            """, (
                pharmacy_name,
                pharmacy_phone,
                pharmacy_email,
                critical_limit,
                expiry_days
            ))

        return jsonify({
            "success": True,
            "message": "Ayarlar başarıyla kaydedildi."
        }), 200

    except Exception:
        app.logger.exception("Ayarlar kaydedilemedi")
        return jsonify({
            "success": False,
            "message": "Ayarlar kaydedilemedi."
        }), 500

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5001, debug=True)

