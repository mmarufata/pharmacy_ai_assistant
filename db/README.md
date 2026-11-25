# MCP Destekli Eczane Asistanı — Veritabanı, MCP ve Güvenlik Katmanı (Kişi 2)

Bu depo, projenin kodlarını içerir.
Flask arayüzü (Arzu) ve LLM/Text-to-SQL (Merve) bu katmanı aşağıdaki "Entegrasyon" bölümüne göre kullanır.

## Mimari (bu katmanın yeri)

```
LLM uygulaması (Merve) ──► MCP araçları ──► SQL doğrulayıcı (SQLGlot AST) ──► ai_readonly bağlantısı ──► 'ai' görünümleri ──► ana tablolar
                              │                                                                                              (PostgreSQL)
                              └──► audit_logs (süre, durum, hata kodu; SQL metni YAZILMAZ)
```

Güvenlik tek bir yere bağlı değildir; her katman diğeri atlatılsa bile korur:

| Katman | Ne yapar | Test |
|---|---|---|
| SQL doğrulayıcı | Tek SELECT, yasak yapı/fonksiyon/tablo/kolon reddi, LIMIT zorlama, doğrulanmış ağaçtan SQL üretimi | `tests/test_sql_validator.py` |
| `ai_readonly` rolü | Süper kullanıcı değil; yalnızca `ai` şemasındaki 8 görünüme SELECT; read-only işlem; `statement_timeout` | `tests/test_db_security.py` |
| `ai` görünümleri | Hassas kolonlar (parola özeti, e-posta, müşteri/kullanıcı kimliği) ve log/geçmiş tabloları hiç görünmez | `test_views_expose_no_sensitive_columns` |
| Çalıştırıcı | Satır sınırı (+`truncated` bayrağı), zaman aşımı, güvenli hata mesajları | `tests/test_mcp_tools.py` |
| Denetim | Her araç çağrısı süre/durum/hata koduyla loglanır, sorgu metni ve veri loglanmaz | `test_audit_log_written_without_sql_text_or_data` |

## Kurulum

Gereksinimler: Python 3.12, PostgreSQL 14+.

```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                   # değerleri doldurun; .env Git'e GİTMEZ
```

PostgreSQL'de bir kez (yönetici hesabıyla) veritabanı ve veri sahibi rolü oluşturun.
Veri sahibi, `ai_readonly` rolünü oluşturabilmek için `CREATEROLE` yetkisi ister:

```sql
CREATE ROLE pharmacy_owner LOGIN PASSWORD '...' CREATEROLE;
CREATE DATABASE pharmacy_db OWNER pharmacy_owner ENCODING 'UTF8' TEMPLATE template0;
```

Ardından:

```bash
python -m scripts.setup_db            # tablolar + 'ai' görünümleri + ai_readonly rolü/izinleri (tekrar çalıştırılabilir, veri SİLMEZ)
python -m scripts.seed_db             # sentetik veri; veri varsa HİÇBİR ŞEY yapmaz
python -m scripts.seed_db --reset --yes   # ⚠ TÜM VERİYİ SİLER (açık onay bayrağı zorunlu)
python -m app.mcp_server.server       # MCP sunucusu (stdio) — normalde bir MCP istemcisi başlatır
```

### Testler

Veritabanı testleri tabloları sıfırladığı için **ayrı** bir veritabanı kullanır (adında `test` geçmelidir):

```sql
CREATE DATABASE pharmacy_test OWNER pharmacy_owner ENCODING 'UTF8' TEMPLATE template0;
```
```bash
export TEST_DATABASE_URL="postgresql+psycopg://pharmacy_owner:...@localhost:5432/pharmacy_test"
export TEST_AI_READONLY_DATABASE_URL="postgresql+psycopg://ai_readonly:...@localhost:5432/pharmacy_test"
python -m pytest -q                   # bu değişkenler yoksa DB testleri atlanır, doğrulayıcı testleri yine çalışır
```
Son çalıştırma: **146 test geçti** (PostgreSQL 16, Python 3.12).

## Klasör yapısı

```
app/
  config.py                 .env okuma (parola kaynak kodda yok)
  db/models.py              13 SQLAlchemy modeli (ER ile uyumlu, İngilizce adlar)
  db/session.py             app engine (sahip) ve ai engine (salt okunur) — ayrı bağlantılar
  db/ai_views.py            YZ'nin görebileceği görünümlerin TEK tanım kaynağı (izin listesi + Türkçe açıklamalar)
  db/schema_discovery.py    ai_readonly'nin gerçekten görebildiği şemayı çıkarır
  db/seed.py                sentetik, deterministik, tekrar çalıştırılabilir veri
  security/sql_validator.py SQLGlot AST doğrulayıcı
  services/audit.py         denetim kaydı yazıcısı
  mcp_server/tools.py       4 aracın mantığı (MCP'den bağımsız, test edilebilir)
  mcp_server/server.py      FastMCP sarmalayıcı (stdio)
scripts/setup_db.py, seed_db.py
tests/                      146 test
```

## ER → kod eşlemesi ve ER'DEN SAPMALAR (ekip onayı gerekir)

İsimler: Kullanıcı→`users`, Ürün→`products`, Tedarikçi→`suppliers`, Satış→`sales`, Satış_Kalemleri→`sale_items`,
Ödeme→`payments`, Müşteri→`customers`, Reçete→`prescriptions`, Reçete_Kalemi→`prescription_items`,
Stok_Hareketleri→`stock_movements`, Log_Kayıtları→`audit_logs`, Sorgu_Geçmişi→`query_history`, Rapor_Geçmişi→`report_history`.
Kolonlar ER'deki adların İngilizcesidir (örn. `stok_miktarı`→`stock_quantity`). **ER diyagramını bu adlarla güncelleyin.**

| Karar | Durum | Gerekçe |
|---|---|---|
| Satış–Ödeme **1:1**, `payments.amount` yok | Ekip kararı uygulandı | `UNIQUE(sale_id)` ile veritabanı garanti eder. Karma ödeme **desteklenmez**. Sonradan 1:N'e geçiş: UNIQUE kaldır + `amount` ekle. |
| `products.min_stock_level` **EKLENDİ** | ⚠ Onay bekliyor | "Kritik stoktaki ürünler" sorusu için eşik gerekir. |
| `sales.status` **EKLENDİ** (completed/cancelled/refunded) | ⚠ Onay bekliyor | İptal/iade raporları (FR-05.6) ve doğru satış toplamları için. |
| Tarih alanları `timestamp` | ⚠ Onay bekliyor | ER'de `date` idi; saatlik analiz ve sıralama için. |
| `stock_movements.quantity` **işaretli** (giriş +, çıkış −) | Varsayım | Stok = `SUM(quantity)`; yön, `movement_type` ile CHECK'le tutarlı tutulur. |
| `products.stock_quantity` + hareket toplamı | Varsayım | Seed'de tutarlıdır (testli). Uygulamada tek doğru kaynağı belirlemek gerekir. |
| Reçete ↔ Satış bağı **yok** | ⚠ Açık soru | Reçeteli satışın kasa/ödeme karşılığı belirsiz. Gerekirse `prescriptions.sale_id` (nullable) eklenir. |
| Maliyet alanı yok | Bilinçli | Kâr hesaplanmayacak (planda "maliyet yoksa kâr gösterme"). |

## YZ'nin görebildiği görünümler (`ai` şeması)

`products`, `suppliers`, `sales`, `sale_items`, `payments`, `stock_movements`, `prescriptions`, `prescription_items`.
**Bilinçli olarak yok:** `users`, `customers`, `audit_logs`, `query_history`, `report_history` ve `sales`/`prescriptions` üzerindeki
`customer_id`/`user_id`. Görünümler ana tablolarla aynı adı taşır; rolün `search_path`'i `ai` olduğundan LLM `FROM products` yazar.

## MCP araçları

| Araç | Girdi | Not |
|---|---|---|
| `get_database_schema` | `user_id?` | İzinli görünümler + Türkçe açıklamalı kolonlar |
| `get_table_info` | `table_name`, `user_id?` | İzinsiz/olmayan tablo aynı mesajı verir (varlık sızdırılmaz) |
| `execute_readonly_sql` | `sql`, `user_id?` | Dönüş: `status` = `ok` / `rejected` / `error`, `rows`, `truncated`, `executed_sql` |
| `get_database_statistics` | `user_id?` | Satır sayıları, satış tarih aralığı, kritik stok sayısı |

## Entegrasyon notları

**Merve (LLM):** Şema bilgisini `get_database_schema` çıktısından alın (Türkçe açıklamalar prompt'a uygundur).
`status == "rejected"` ise `code` alanına göre davranın (örn. `COLUMN_NOT_ALLOWED` → şemayı yeniden verip SQL'i düzelttirin, en fazla N deneme).
`truncated == true` ise yanıtta "sonuç ilk 500 satırla sınırlı" uyarısı verin. Sonuç boşsa uydurmayın.

**Arzu (Flask):** Araçlar MCP olmadan da doğrudan çağrılabilir: `from app.mcp_server import tools; tools.execute_readonly_sql(sql, user_id=...)`.
**Kullanıcı yetkilendirmesi (rol kontrolü) Flask katmanındadır**; MCP yalnızca ilettiğiniz `user_id`'yi denetim kaydına yazar.
Sorgu/rapor geçmişi (`query_history`, `report_history`) yazımı henüz bağlanmadı: `executed_sql` ve `duration_ms` bu kayıtlar için hazırdır.

**Hata mesajları:** `message` alanı kullanıcıya olduğu gibi gösterilebilir (şema/kimlik bilgisi içermez). `code` yalnızca loglama içindir.

## Haftalık plan (Kişi 2) — gerçek durum

| Hafta | Görev | Durum |
|---|---|---|
| 1 | ER, MCP araç listesi, güvenlik gereksinimleri | ✅ (bu README + ER düzeltmeleri) · ⬜ **Botanik EOS veri erişimi araştırması yapılmadı** (üretici/yetkili kaynakla iletişim gerekir) |
| 2 | PostgreSQL, SQLAlchemy, ilişkiler, sentetik veri, şema keşfi | ✅ |
| 3 | MCP sunucusu, 3+ araç, salt okunur kullanıcı, SELECT kontrolü, süre/satır sınırı | ✅ (4 araç) |
| 4 | MCP'nin Flask/AI akışıyla birleşmesi | 🔶 Araç tarafı hazır (zaman aşımı/boş sonuç/DB hatası işlenir); **Flask ve LLM kodu ile entegrasyon diğer üyelerle yapılmalı** |
| 5 | AST doğrulama, yazma/çoklu ifade/izinsiz tablo testleri, denetim logu hassas veri kontrolü | ✅ · 🔶 Rol bazlı (uygulama düzeyi) yetki testleri Flask'a bağlı |
| 6 | Rapor sorgularının JOIN/filtre doğruluğu, performans | 🔶 İlişki ve tutarlılık testleri var; rapor bazlı beklenen-sonuç karşılaştırmaları ve `EXPLAIN` incelemesi yapılmadı |
| 7 | Denetim kayıtları, iptal/iade sorgusu, veri tutarsızlığı kontrolleri | 🔶 MCP olayları loglanıyor; kullanıcı eylemleri (giriş vb.) Flask'tan loglanmalı; **veri kalitesi kontrolleri yapılmadı** |
| 8 | Testlerin tekrarı, mimari/DB dokümantasyonu | 🔶 Testler hazır; diyagramlar ve nihai doküman yazılmadı |

## Bilinen sınırlılıklar (dürüst liste)

- **Kolon doğrulaması görünüm şemasına dayanır.** Doğrulayıcı kolonları `ai` görünümlerine göre çözer; hassas kolon zaten görünümde yoktur (iki katman).
- **Sistem kataloğu salt okunur rolle okunabilir olabilir.** PostgreSQL varsayılanı budur. Doğrulayıcı `pg_catalog`/`information_schema` ve CTE ile gizlemeyi engeller, ama doğrulayıcı atlatılırsa katalog adları okunabilir (veri değil, şema adları). Üretimde ek sertleştirme (ayrı veritabanı/küme) düşünülmelidir.
- **Zaman aşımı yalnızca veritabanı düzeyindedir.** Ağır sorgular (örn. kartezyen çarpım) doğrulayıcıdan geçer, `statement_timeout` ile kesilir.
- **SQLGlot ve MCP sürümleri sabittir** (`sqlglot==30.32.0`, `mcp==1.30.0`). Sürüm yükseltmesi doğrulayıcıyı etkileyebilir (ör. bu sürümde `WITH` anahtarı `with_`); yükseltmeden sonra `pytest` çalıştırın. MCP 2.x'te `FastMCP` yeniden adlandırıldı; 1.x'e bilerek sabitlendi.
- **Doğruluk ≠ başarılı çalışma.** Doğrulayıcı SQL'in *güvenli* olduğunu garanti eder, *doğru soruyu yanıtladığını* değil (bu Merve'nin değerlendirme işidir).
- `setup_db` testi yalnızca `ALTER ROLE` yolunu tekrar çalıştırır; `CREATE ROLE` yolu temiz kurulumda elle doğrulandı.
- Bağlantı havuzu SQLAlchemy varsayılanlarındadır; eşzamanlı kullanıcı yükü (NFR-08) ölçülmedi.
- Veriler tamamen sentetiktir; SGK hesapları gerçek mevzuat değil, prototip varsayımıdır.
