
document.addEventListener("DOMContentLoaded", function () {

    const DEFAULT_SETTINGS = {
        pharmacyName: "",
        pharmacyPhone: "",
        pharmacyEmail: "",
        criticalStockLimit: 3,
        expiryWarningDays: 30
    };

    const menuItems = document.querySelectorAll(".menu-item");
    const pageTitle = document.querySelector(".welcome h2");
    const mainContent = document.querySelector(".main-content");

    if (!mainContent || !pageTitle) {
        console.error("Ana içerik veya başlık bulunamadı.");
        return;
    }

    // Dashboard bölümleri
    const dashboardSections = [
        document.querySelector(".stats-grid"),
        document.querySelector(".content-grid"),
        document.querySelector(".orders-panel")
    ].filter(Boolean);


    // ==========================================
    // AI - AKILLI STOK ANALİZİ SAYFASI
    // ==========================================

    const aiStockHTML = `
        <section class="ai-stock-page">
            <div class="products-header">
                <div>
                    <h2>Yapay Zekâ Destekli Stok Analizi</h2>
                    <p>Satış geçmişine göre stok tükenme tahminleri.</p>
                </div>
            </div>

            <div class="products-table-container">
                <table class="products-table">
                    <thead>
                        <tr>
                            <th>Ürün Adı</th>
                            <th>Mevcut Stok</th>
                            <th>30 Günlük Satış</th>
                            <th>Günlük Ortalama</th>
                            <th>Tahmini Kalan Gün</th>
                            <th>Risk Durumu</th>
                        </tr>
                    </thead>
                    <tbody id="aiStockTableBody">
                        <tr>
                            <td colspan="6">
                                Analiz verileri yükleniyor...
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </section>
    `;

    // ==========================================
    // AI - STOK ANALİZİ VERİLERİNİ YÜKLE
    // ==========================================

    async function loadAIStockAnalysis() {
        const tableBody = document.getElementById("aiStockTableBody");

        if (!tableBody) return;

        tableBody.innerHTML = `
            <tr>
                <td colspan="8">Analiz verileri yükleniyor...</td>
            </tr>
        `;

        try {
            const response = await fetch("/api/ai/stock-analysis");
            const result = await response.json();

            if (!response.ok || !result.success) {
                throw new Error(result.message || "Analiz alınamadı.");
            }

            tableBody.innerHTML = "";


            // ==========================================
            // OTOMATİK STOK RİSK UYARISI
            // ==========================================

            const warningBox = document.getElementById("aiStockWarning");
            const warningText = document.getElementById("aiStockWarningText");


            const criticalProducts = result.analysis.filter(
                product => product.risk_level === "Kritik"
            );

            const highRiskProducts = result.analysis.filter(
                product => product.risk_level === "Yüksek"
            );

            const expiredProducts = result.analysis.filter(
                product => product.risk_level === "SKT Geçmiş"
            );

            const nearExpiryProducts = result.analysis.filter(
                product => product.risk_level === "SKT Yaklaşıyor"
            );

            const totalRisky =
                criticalProducts.length +
                highRiskProducts.length +
                expiredProducts.length +
                nearExpiryProducts.length;

            if (warningBox && warningText) {
                if (totalRisky > 0) {

                    warningText.textContent =
                        `${criticalProducts.length} kritik, ` +
                        `${highRiskProducts.length} yüksek riskli, ` +
                        `${expiredProducts.length} SKT geçmiş ve ` +
                        `${nearExpiryProducts.length} SKT yaklaşan ürün var. ` +
                        `Toplam ${totalRisky} ürün için gerekli kontrolleri yapın.`;

                    warningBox.hidden = false;
                } else {
                    warningText.textContent = "";
                    warningBox.hidden = true;
                }
            }

            if (result.analysis.length === 0) {
                tableBody.innerHTML = `
                    <tr>
                        <td colspan="8">Analiz edilecek ürün bulunamadı.</td>
                    </tr>
                `;
                return;
            }


            const riskPriority = {
                "SKT Geçmiş": 1,
                "Kritik": 2,
                "Yüksek": 3,
                "SKT Yaklaşıyor": 4,
                "Orta": 5,
                "Düşük": 6,
                "Veri Yetersiz": 7
            };


            result.analysis.sort((a, b) => {
                return (riskPriority[a.risk_level] ?? 99)
                    - (riskPriority[b.risk_level] ?? 99);
            });

            result.analysis.forEach(product => {
                const row = document.createElement("tr");


                const values = [
                    product.product_name,
                    product.current_stock,
                    product.sold_last_30_days,
                    product.daily_average_sales,
                    product.estimated_days_remaining === null
                        ? "Hesaplanamıyor"
                        : product.estimated_days_remaining + " gün",
                    product.risk_level,
                    product.recommendation,
                    product.suggested_order_quantity + " adet"
                ];


                values.forEach((value, index) => {
                    const cell = document.createElement("td");

                    if (index === 5) {
                        const badge = document.createElement("span");

                        badge.className = "ai-risk-badge";


                        const riskClasses = {
                            "SKT Geçmiş": "risk-critical",
                            "Kritik": "risk-critical",
                            "Yüksek": "risk-high",
                            "SKT Yaklaşıyor": "risk-high",
                            "Orta": "risk-medium",
                            "Düşük": "risk-low",
                            "Veri Yetersiz": "risk-unknown"
                        };

                        badge.classList.add(
                            riskClasses[value] || "risk-unknown"
                        );

                        badge.textContent = value;
                        cell.appendChild(badge);
                    } else {
                        cell.textContent = value;
                    }

                    row.appendChild(cell);
                });


                tableBody.appendChild(row);
            });

        } catch (error) {
            console.error("AI stok analizi hatası:", error);

            tableBody.innerHTML = `
                <tr>
                    <td colspan="8">
                        Stok analizi yüklenirken hata oluştu.
                    </td>
                </tr>
            `;
        }
    }

    // Ürünler sayfası

    const productsHTML = `
    <section class="products-page">
        <div class="products-header">
            <div>
                <h2>Ürün Yönetimi</h2>
                <p>Eczanedeki ürünleri görüntüleyin ve arayın.</p>
            </div>
            <button type="button" id="addProductBtn" class="add-product-btn">
                + Yeni Ürün Ekle
            </button>
        </div>

        <div class="products-toolbar">
            <div class="product-search">
                <span>⌕</span>
                <input type="search" id="productSearch"
                    placeholder="Ürün adı veya barkod ara...">
            </div>
            <span id="productCount" class="product-count">3 ürün</span>
        </div>

        <div class="products-table-container">
            <table class="products-table">
                <thead>
                    <tr>
                        <th>Barkod</th>
                        <th>Ürün Adı</th>
                        <th>Stok</th>
                        <th>Fiyat</th>
                        <th>Son Kullanma Tarihi</th>
                        <th>Stok Durumu</th>
                        <th>SKT Durumu</th>
                        <th>İşlemler</th>
                    </tr>
                </thead>
                <tbody id="productsTableBody">
                    <tr>
                        <td>8699546090012</td>
                        <td>Parol 500 mg</td>
                        <td>45</td>
                        <td>85,50 TL</td>
                        <td>12.2027</td>
                        <td><span class="stock-status stock-normal">Normal</span></td>
                        <td><span class="expiry-status expiry-normal">Normal</span></td>
                        <td>
                            <button type="button" class="edit-product-btn">Düzenle</button>
                            <button type="button" class="delete-product-btn">Sil</button>
                        </td>
                    </tr>
                    <tr>
                        <td>8699546090029</td>
                        <td>Parol Plus</td>
                        <td>8</td>
                        <td>110,00 TL</td>
                        <td>06.2027</td>
                        <td><span class="stock-status stock-low">Azalan stok</span></td>
                        <td><span class="expiry-status expiry-normal">Normal</span></td>
                        <td>
                            <button type="button" class="edit-product-btn">Düzenle</button>
                            <button type="button" class="delete-product-btn">Sil</button>
                        </td>
                    </tr>
                    <tr>
                        <td>8699546090036</td>
                        <td>Parol Pediatrik</td>
                        <td>3</td>
                        <td>75,00 TL</td>
                        <td>03.2027</td>
                        <td><span class="stock-status stock-critical">Kritik stok</span></td>
                        <td><span class="expiry-status expiry-normal">Normal</span></td>
                        <td>
                            <button type="button" class="edit-product-btn">Düzenle</button>
                            <button type="button" class="delete-product-btn">Sil</button>
                        </td>
                    </tr>
                </tbody>
            </table>

            <p id="noProductsMessage" class="no-products" hidden>
                Aramanızla eşleşen ürün bulunamadı.
            </p>
        </div>

        <p class="demo-note">      
        Ürün bilgileri SQLite veritabanında güvenli şekilde saklanır. Stok ve son kullanma tarihi bilgileri güncel olarak takip edilir.
        </p>
    </section>
`;



    function getExpiryStatus(expiry) {
        if (typeof expiry !== "string") {
            return {
                text: "Tarih Geçersiz",
                className: "expiry-unknown"
            };
        }

        const parts = expiry.split("-").map(Number);

        if (parts.length !== 3 || parts.some(n => !Number.isInteger(n))) {
            return {
                text: "Tarih Geçersiz",
                className: "expiry-unknown"
            };
        }

        const [year, month, day] = parts;
        const expiryDate = new Date(year, month - 1, day);

        if (
            expiryDate.getFullYear() !== year ||
            expiryDate.getMonth() !== month - 1 ||
            expiryDate.getDate() !== day
        ) {
            return {
                text: "Tarih Geçersiz",
                className: "expiry-unknown"
            };
        }

        const today = new Date();
        today.setHours(0, 0, 0, 0);

        const daysLeft = Math.round(
            (Date.UTC(year, month - 1, day) -
                Date.UTC(
                    today.getFullYear(),
                    today.getMonth(),
                    today.getDate()
                )) / 86400000
        );

        if (daysLeft < 0) {
            return {
                text: "SKT Geçmiş",
                className: "expiry-expired"
            };
        }


        const settings = getPharmacySettings();
        const warningDays = Number(settings.expiryWarningDays);

        if (daysLeft <= warningDays) {


            return {
                text: daysLeft === 0
                    ? "Bugün Son Gün"
                    : `${daysLeft} Gün Kaldı`,
                className: "expiry-warning"
            };
        }

        return {
            text: "SKT Uygun",
            className: "expiry-normal"
        };
    }

    function updateExpiryStatuses() {
        const rows = document.querySelectorAll("#productsTableBody tr");

        rows.forEach(function (row) {
            if (row.cells.length < 7) return;

            const expiryText = row.cells[4].textContent.trim();
            const expiryCell = row.cells[6];

            if (!expiryText || !expiryCell) return;

            let day, month, year;
            const parts = expiryText.split(".");

            if (parts.length === 3) {
                // GG.AA.YYYY
                [day, month, year] = parts;
            } else if (parts.length === 2) {
                // AA.YYYY biçimi: ayın son günü kabul edilir
                [month, year] = parts;
                day = new Date(Number(year), Number(month), 0)
                    .getDate()
                    .toString();
            } else {
                return;
            }

            month = month.padStart(2, "0");
            day = day.padStart(2, "0");

            const expiry = `${year}-${month}-${day}`;
            const status = getExpiryStatus(expiry);

            let badge = expiryCell.querySelector(".expiry-status");

            if (!badge) {
                expiryCell.textContent = "";
                badge = document.createElement("span");
                expiryCell.appendChild(badge);
            }

            badge.className = "expiry-status " + status.className;
            badge.textContent = status.text;
        });
    }

    function showSuccessToast(title, message) {
        const toast = document.createElement("div");

        const icon = document.createElement("span");
        icon.textContent = "✓";
        icon.style.fontSize = "22px";

        const content = document.createElement("div");

        const heading = document.createElement("strong");
        heading.textContent = title;

        const description = document.createElement("div");
        description.textContent = message;
        description.style.fontSize = "13px";
        description.style.marginTop = "4px";

        content.append(heading, description);
        toast.append(icon, content);

        Object.assign(toast.style, {
            position: "fixed",
            top: "24px",
            right: "24px",
            background: "#ffffff",
            color: "#166534",
            border: "1px solid #bbf7d0",
            borderLeft: "5px solid #22c55e",
            borderRadius: "12px",
            padding: "16px 20px",
            display: "flex",
            alignItems: "center",
            gap: "12px",
            boxShadow: "0 8px 24px rgba(0,0,0,0.12)",
            zIndex: "99999",
            fontFamily: "inherit"
        });

        document.body.appendChild(toast);

        setTimeout(function () {
            toast.remove();
        }, 3500);
    }


    function showErrorToast(message) {
        const toast = document.createElement("div");

        const icon = document.createElement("span");
        icon.textContent = "!";
        icon.style.fontSize = "24px";
        icon.style.fontWeight = "bold";

        const content = document.createElement("div");

        const heading = document.createElement("strong");
        heading.textContent = "Ürün silinemedi";

        const description = document.createElement("div");
        description.textContent = message;
        description.style.fontSize = "13px";
        description.style.marginTop = "5px";
        description.style.lineHeight = "1.5";

        content.append(heading, description);
        toast.append(icon, content);

        Object.assign(toast.style, {
            position: "fixed",
            top: "24px",
            right: "24px",
            background: "#ffffff",
            color: "#991b1b",
            border: "1px solid #fecaca",
            borderLeft: "5px solid #ef4444",
            borderRadius: "12px",
            padding: "16px 20px",
            display: "flex",
            alignItems: "center",
            gap: "12px",
            boxShadow: "0 8px 24px rgba(0,0,0,0.12)",
            zIndex: "99999",
            fontFamily: "inherit",
            maxWidth: "420px"
        });

        document.body.appendChild(toast);

        setTimeout(function () {
            toast.remove();
        }, 5000);
    }


    function showToast(message, type = "success") {
        const oldToast = document.getElementById("appToast");
        if (oldToast) oldToast.remove();

        const toast = document.createElement("div");
        toast.id = "appToast";

        const isSuccess = type === "success";

        const icon = document.createElement("span");
        icon.textContent = isSuccess ? "✓" : "!";
        icon.style.fontSize = "22px";
        icon.style.fontWeight = "bold";

        const text = document.createElement("span");
        text.textContent = message;

        Object.assign(toast.style, {
            position: "fixed",
            top: "24px",
            right: "24px",
            background: "#ffffff",
            color: isSuccess ? "#166534" : "#991b1b",
            border: `1px solid ${isSuccess ? "#bbf7d0" : "#fecaca"}`,
            borderLeft: `5px solid ${isSuccess ? "#22c55e" : "#ef4444"}`,
            borderRadius: "12px",
            padding: "16px 20px",
            display: "flex",
            alignItems: "center",
            gap: "12px",
            boxShadow: "0 8px 24px rgba(0,0,0,0.12)",
            zIndex: "99999",
            maxWidth: "420px",
            fontFamily: "inherit"
        });

        toast.append(icon, text);
        document.body.appendChild(toast);

        setTimeout(function () {
            toast.remove();
        }, 4000);
    }

    function updateDashboardStats() {
        const rows = document.querySelectorAll("#productsTableBody tr");


        const settings = getPharmacySettings();
        const criticalLimit = Number(settings.criticalStockLimit ?? 8);


        let totalProducts = 0;
        let criticalStock = 0;
        let lowStock = 0;
        let inStock = 0;

        let expiredCount = 0;
        let warningCount = 0;
        let safeCount = 0;


        const expiryWarningText = document.getElementById("dashboardExpiryWarningText");

        if (expiryWarningText) {
            const warningDays = Number(settings.expiryWarningDays ?? 30);

            expiryWarningText.textContent =
                `${warningDays} gün içinde SKT dolacak ürünler`;
        }



        rows.forEach(function (row) {
            if (row.cells.length < 3 || row.hidden) return;

            totalProducts++;

            const stock = Number(row.cells[2].textContent.trim());

            if (stock <= criticalLimit) {
                criticalStock++;
            } else if (stock <= criticalLimit + 5) {
                lowStock++;
            } else {
                inStock++;
            }


            const expiryText = row.cells[4]?.textContent.trim();

            if (expiryText) {
                const parts = expiryText.split(".");

                if (parts.length === 3) {
                    const [day, month, year] = parts;
                    const expiry = `${year}-${month}-${day}`;
                    const status = getExpiryStatus(expiry);

                    if (status.className === "expiry-expired") {
                        expiredCount++;
                    } else if (status.className === "expiry-warning") {
                        warningCount++;
                    } else if (status.className === "expiry-normal") {
                        safeCount++;
                    }
                }
            }

        });
        // Dashboard üzerindeki sayaçları güncelle
        const totalElement = document.getElementById("totalProductsCount");
        const inventoryTotalElement = document.getElementById("inventoryTotalCount");
        const criticalElement = document.getElementById("criticalStockCount");
        const inStockElement = document.getElementById("inStockCount");
        const lowStockElement = document.getElementById("lowStockCount");
        const inventoryCriticalElement =
            document.getElementById("inventoryCriticalCount");



        const expiredElement = document.getElementById("dashboardExpiredCount");
        const warningElement = document.getElementById("dashboardWarningCount");
        const safeElement = document.getElementById("dashboardSafeCount");

        if (expiredElement) expiredElement.textContent = expiredCount;
        if (warningElement) warningElement.textContent = warningCount;
        if (safeElement) safeElement.textContent = safeCount;

        if (totalElement) totalElement.textContent = totalProducts;
        if (inventoryTotalElement) {
            inventoryTotalElement.textContent = totalProducts;
        }
        if (criticalElement) criticalElement.textContent = criticalStock;
        if (inStockElement) inStockElement.textContent = inStock;
        if (lowStockElement) lowStockElement.textContent = lowStock;

        if (inventoryCriticalElement) {
            inventoryCriticalElement.textContent = criticalStock;
        }

        // Stok dağılımı grafiğini güncelle
        const donut = document.querySelector(".donut");

        if (donut) {
            const total = inStock + lowStock + criticalStock;

            const inStockAngle = total ? (inStock / total) * 360 : 0;
            const lowStockAngle =
                total ? ((inStock + lowStock) / total) * 360 : 0;

            donut.style.setProperty("--in-stock-angle", inStockAngle + "deg");
            donut.style.setProperty("--low-stock-angle", lowStockAngle + "deg");
        }
    }


    function checkCriticalStock() {
        const rows = document.querySelectorAll("#productsTableBody tr");

        const criticalProducts = [];
        const outOfStockProducts = [];


        const settings = getPharmacySettings();

        const criticalLimit = Number(settings.criticalStockLimit);

        rows.forEach(function (row) {
            if (row.cells.length < 3) return;

            const productName = row.cells[1].textContent.trim();
            const stock = Number(row.cells[2].textContent.trim());

            if (!productName || !Number.isFinite(stock)) return;

            if (stock === 0) {
                outOfStockProducts.push(productName);
            } else if (stock <= criticalLimit) {
                criticalProducts.push(
                    productName + " (Stok: " + stock + ")"
                );
            }
        });

        const warningElement =
            document.getElementById("criticalStockWarning");

        if (!warningElement) return;

        const warnings = [];

        if (outOfStockProducts.length > 0) {
            warnings.push(
                "Stok tükendi: " + outOfStockProducts.join(", ")
            );
        }

        if (criticalProducts.length > 0) {
            warnings.push(
                "Kritik stok uyarısı: " + criticalProducts.join(", ")
            );
        }

        warningElement.textContent = warnings.length > 0
            ? warnings.join(" | ")
            : "Kritik stokta ürün bulunmuyor.";

        // Önce eski durum sınıflarını temizle
        warningElement.classList.remove("stock-safe", "stock-danger");

        // Stok durumuna göre renk belirle
        if (warnings.length > 0) {
            warningElement.classList.add("stock-danger");
        } else {
            warningElement.classList.add("stock-safe");
        }

        warningElement.style.display = "block";
    }

    // Ürünler sayfasını oluştur
    const productsContainer = document.createElement("div");
    // Yeni ürün ekleme formu
    const addProductFormHTML = `
      <div id="addProductModal" class="product-modal" hidden>
         <div class="product-modal-content">
            <h2>Yeni Ürün Ekle</h2>

            <form id="addProductForm">
                <label for="newBarcode">Barkod</label>
                <input id="newBarcode" name="barcode" required>

                <label for="newProductName">Ürün Adı</label>
                <input id="newProductName" name="name" autocomplete="off" required>
                <label for="newStock">Stok Miktarı</label>
                <input id="newStock" name="stock" type="number" min="0" required>

                <label for="newPrice">Fiyat (TL)</label>
                <input id="newPrice" name="price" type="number" min="0" step="0.01" required>
            
                <label for="newExpiry">Son Kullanma Tarihi</label>
                <input id="newExpiry" name="expiry" type="date" min="2000-01-01" max="2100-12-31" required>

                <div class="product-form-actions">
                    <button type="button" id="cancelProductBtn">İptal</button>
                    <button type="submit">Ürünü Ekle</button>
                </div>

            </form>
        </div>
    </div>
`;
    productsContainer.id = "productsContainer";
    productsContainer.innerHTML = productsHTML;
    productsContainer.insertAdjacentHTML("beforeend", addProductFormHTML);
    productsContainer.hidden = true;
    mainContent.appendChild(productsContainer);

    // Arama elemanları
    const productSearch =
        productsContainer.querySelector("#productSearch");

    const productsTableBody =
        productsContainer.querySelector("#productsTableBody");

    // Flask backend üzerinden ürünleri getir
    async function fetchProductsFromBackend() {
        try {
            const response = await fetch("/api/products");

            if (!response.ok) {
                throw new Error("Ürünler alınamadı.");
            }

            const data = await response.json();


            return data.products;

        } catch (error) {
            console.error("Backend bağlantı hatası:", error);
        }
    }
    async function refreshProductsTable() {
        const products = await fetchProductsFromBackend();

        if (!Array.isArray(products)) {
            throw new Error("Ürün listesi güncellenemedi.");
        }
        productsTableBody.innerHTML = "";

        products.forEach(function (product) {
            const row = document.createElement("tr");

            row.dataset.productId = product.id;

            const [year, month, day] = product.expiry_date.split("-");
            const formattedExpiry = `${day}.${month}.${year}`;


            const settings = getPharmacySettings();

            const criticalLimit = Number(settings.criticalStockLimit);


            const stock = Number(product.stock);

            let stockClass = "stock-normal";
            let stockText = "Normal";

            if (stock === 0) {
                stockClass = "stock-critical";
                stockText = "Stok Tükendi";
            } else if (stock <= criticalLimit) {
                stockClass = "stock-critical";
                stockText = "Kritik stok";
            } else if (stock <= criticalLimit + 5) {
                stockClass = "stock-low";
                stockText = "Azalan stok";
            }


            const values = [
                product.barcode,
                product.name,
                stock,
                Number(product.price).toFixed(2).replace(".", ",") + " TL",
                formattedExpiry
            ];

            values.forEach(function (value) {
                const cell = document.createElement("td");
                cell.textContent = value;
                row.appendChild(cell);
            });

            const stockCell = document.createElement("td");
            const stockBadge = document.createElement("span");

            stockBadge.className = "stock-status " + stockClass;
            stockBadge.textContent = stockText;
            stockCell.appendChild(stockBadge);
            row.appendChild(stockCell);


            // ==========================================
            // SON KULLANMA TARİHİ DURUMU
            // ==========================================
            const expiryCell = document.createElement("td");
            const expiryBadge = document.createElement("span");


            const expiryStatusInfo = getExpiryStatus(product.expiry_date);

            const expiryStatus =
                expiryStatusInfo.className === "expiry-expired" ? "expired" :
                    expiryStatusInfo.className === "expiry-warning" ? "warning" :
                        expiryStatusInfo.className === "expiry-normal" ? "safe" :
                            "unknown";


            if (expiryStatus === "expired") {
                expiryBadge.className = "expiry-status expiry-expired";
                expiryBadge.textContent = "SKT Geçmiş";


            } else if (expiryStatus === "warning") {
                expiryBadge.className = "expiry-status expiry-warning";
                expiryBadge.textContent = expiryStatusInfo.text;


            } else if (expiryStatus === "safe") {
                expiryBadge.className = "expiry-status expiry-normal";
                expiryBadge.textContent = "SKT Uygun";

            } else {
                expiryBadge.className = "expiry-status expiry-unknown";
                expiryBadge.textContent = "Tarih Geçersiz";
            }

            expiryCell.appendChild(expiryBadge);
            row.appendChild(expiryCell);

            const actionsCell = document.createElement("td");

            const editButton = document.createElement("button");
            editButton.type = "button";
            editButton.className = "edit-product-btn";
            editButton.textContent = "✎ Düzenle";

            const deleteButton = document.createElement("button");
            deleteButton.type = "button";
            deleteButton.className = "delete-product-btn";
            deleteButton.textContent = "✕ Sil";

            actionsCell.appendChild(editButton);
            actionsCell.appendChild(deleteButton);
            row.appendChild(actionsCell);

            productsTableBody.appendChild(row);
        });

        updateExpiryStatuses();
        updateDashboardStats();
        checkCriticalStock();
        updateAnalyticsReport();

        productSearch.dispatchEvent(new Event("input"));
    }

    refreshProductsTable().catch(function (error) {
        console.error("İlk ürün yükleme hatası:", error);

        showToast(
            "Ürünler yüklenemedi. Bağlantınızı kontrol edip sayfayı yenileyin.",
            "error"
        );
    });

    const productCount =
        productsContainer.querySelector("#productCount");

    const noProductsMessage =
        productsContainer.querySelector("#noProductsMessage");

    // Ürün ekleme formu elemanları
    const addProductBtn =
        productsContainer.querySelector("#addProductBtn");

    const addProductModal =
        productsContainer.querySelector("#addProductModal");

    addProductModal.hidden = true;

    const addProductForm =
        productsContainer.querySelector("#addProductForm");

    const cancelProductBtn =
        productsContainer.querySelector("#cancelProductBtn");

    // Düzenlenen ürünü takip et
    let editingRow = null;

    const formTitle = addProductModal.querySelector("h2");
    const submitButton = addProductForm.querySelector(
        'button[type="submit"]'
    );

    // Formu aç
    addProductBtn.addEventListener("click", function () {
        addProductModal.hidden = false;
    });

    // Formu kapat
    cancelProductBtn.addEventListener("click", function () {
        addProductModal.hidden = true;
        addProductForm.reset();

        editingRow = null;
        formTitle.textContent = "Yeni Ürün Ekle";
        submitButton.textContent = "Ürünü Ekle";
    });


    addProductForm.addEventListener("submit", async function (event) {
        event.preventDefault();

        const barcode = addProductForm.elements["barcode"].value.trim();
        const name = addProductForm.elements["name"].value.trim();
        const stock = Number(addProductForm.elements["stock"].value);
        const price = Number(addProductForm.elements["price"].value);
        const expiry = addProductForm.elements["expiry"].value;


        // Son kullanma tarihinin yilini kontrol et
        const expiryYear = Number(expiry.split("-")[0]);

        if (
            !/^\d{4}-\d{2}-\d{2}$/.test(expiry) ||
            !Number.isInteger(expiryYear) ||
            expiryYear < 2000 ||
            expiryYear > 2100
        ) {
            showToast("Geçerli bir son kullanma tarihi girin. Yıl 2000 ile 2100 arasında olmalıdır.", "error");
            return;
        }


        if (
            !barcode ||
            !name ||
            !expiry ||
            addProductForm.elements["stock"].value === "" ||
            addProductForm.elements["price"].value === "" ||
            !Number.isInteger(stock) ||
            stock < 0 ||
            !Number.isFinite(price) ||
            price < 0
        ) {
            showToast("Lütfen geçerli ürün bilgileri girin.", "error");
            return;
        }

        // Barkodun başka bir üründe kullanılıp kullanılmadığını kontrol et
        const rows = productsTableBody.querySelectorAll("tr");

        for (const row of rows) {
            if (
                row !== editingRow &&
                row.cells[0].textContent.trim() === barcode
            ) {
                showToast("Bu barkodla kayıtlı başka bir ürün zaten var.", "error");
                return;
            }
        }

        // Ayarlar sayfasındaki kritik stok limitini al
        const settings = getPharmacySettings();
        const criticalLimit = Number(settings.criticalStockLimit ?? 3);


        // Stok durumunu belirle
        let stockClass = "stock-normal";
        let stockText = "Normal";

        if (stock === 0) {
            stockClass = "stock-critical";
            stockText = "Stok Tükendi";
        } else if (stock <= criticalLimit) {
            stockClass = "stock-critical";
            stockText = "Kritik stok";
        } else if (stock <= criticalLimit + 5) {
            stockClass = "stock-low";
            stockText = "Azalan stok";
        }

        // Tarihi ay.yıl biçimine dönüştür
        // Tarihi gün.ay.yıl biçimine dönüştür
        const [year, month, day] = expiry.split("-");
        const formattedExpiry = `${day}.${month}.${year}`;
        const expiryStatus = getExpiryStatus(expiry);

        // Fiyatı biçimlendir
        const formattedPrice =
            price.toLocaleString("tr-TR", {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2
            }) + " TL";

        if (editingRow) {
            // Güncellenecek ürünün SQLite ID'sini al
            const productId = editingRow.dataset.productId;

            if (!productId) {
                alert("Ürün ID'si bulunamadı. Güncelleme yapılamadı.");
                return;
            }

            try {
                const response = await fetch(`/api/products/${productId}`, {
                    method: "PUT",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        barcode: barcode,
                        name: name,
                        stock: stock,
                        price: price,
                        expiry_date: expiry
                    })
                });

                const result = await response.json();

                if (!response.ok || !result.success) {
                    alert(result.message || "Ürün güncellenemedi.");
                    return;
                }

            } catch (error) {
                console.error("Ürün güncelleme hatası:", error);
                showToast("Backend bağlantı hatası. Ürün güncellenemedi.", "error");
                return;
            }

            // Mevcut ürünü güncelle
            editingRow.cells[0].textContent = barcode;
            editingRow.cells[1].textContent = name;
            editingRow.cells[2].textContent = String(stock);
            editingRow.cells[3].textContent = formattedPrice;
            editingRow.cells[4].textContent = formattedExpiry;

            // SKT durumunu güncelle
            const expiryBadge =
                editingRow.cells[6].querySelector(".expiry-status");

            expiryBadge.className =
                "expiry-status " + expiryStatus.className;

            expiryBadge.textContent = expiryStatus.text;

            const statusBadge =
                editingRow.cells[5].querySelector(".stock-status");

            statusBadge.className = "stock-status " + stockClass;
            statusBadge.textContent = stockText;

            updateDashboardStats();
            checkCriticalStock();
            updateExpiryStatuses();
            updateAnalyticsReport();

            showToast("Ürün başarıyla güncellendi!", "success");

        } else {
            // Yeni ürünü önce SQLite veritabanına kaydet
            let savedProduct;

            try {
                const response = await fetch("/api/products", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        barcode: barcode,
                        name: name,
                        stock: stock,
                        price: price,
                        expiry_date: expiry
                    })
                });

                const result = await response.json();


                if (!response.ok || !result.success) {
                    showToast(result.message || "Ürün kaydedilemedi.", "error");
                    return;
                }

                savedProduct = result;

            } catch (error) {
                console.error("Ürün ekleme hatası:", error);
                showToast("Backend bağlantı hatası. Ürün kaydedilemedi.", "error");
                return;
            }// Yeni ürün satırı oluştur
            const row = productsTableBody.insertRow();
            row.dataset.productId = savedProduct.product_id;

            [barcode, name, String(stock), formattedPrice, formattedExpiry]
                .forEach(function (value) {
                    row.insertCell().textContent = value;
                });

            const statusCell = row.insertCell();
            const statusBadge = document.createElement("span");
            statusBadge.className = "stock-status " + stockClass;
            statusBadge.textContent = stockText;
            statusCell.appendChild(statusBadge);

            const expiryCell = row.insertCell();
            const expiryBadge = document.createElement("span");

            expiryBadge.className =
                "expiry-status " + expiryStatus.className;

            expiryBadge.textContent = expiryStatus.text;
            expiryCell.appendChild(expiryBadge);

            const actionsCell = row.insertCell();

            const editButton = document.createElement("button");
            editButton.type = "button";
            editButton.className = "edit-product-btn";
            editButton.textContent = "✎ Düzenle";

            const deleteButton = document.createElement("button");
            deleteButton.type = "button";
            deleteButton.className = "delete-product-btn";
            deleteButton.textContent = "✕ Sil";

            actionsCell.append(editButton, deleteButton);

            updateDashboardStats();
            checkCriticalStock();
            updateExpiryStatuses();
            updateAnalyticsReport();


            showToast("Ürün başarıyla eklendi!", "success");

        }

        // Formu sıfırla ve kapat
        editingRow = null;
        addProductForm.reset();
        addProductModal.hidden = true;

        formTitle.textContent = "Yeni Ürün Ekle";
        submitButton.textContent = "Ürünü Ekle";

        productSearch.dispatchEvent(new Event("input"));
    });

    // Ürün düzenleme işlemi
    productsTableBody.addEventListener("click", async function (event) {
        const editButton = event.target.closest(".edit-product-btn");
        if (!editButton) return;

        editingRow = editButton.closest("tr");

        // Mevcut ürün bilgilerini forma aktar
        addProductForm.elements["barcode"].value =
            editingRow.cells[0].textContent.trim();

        addProductForm.elements["name"].value =
            editingRow.cells[1].textContent.trim();

        addProductForm.elements["stock"].value =
            editingRow.cells[2].textContent.trim();

        addProductForm.elements["price"].value =
            editingRow.cells[3].textContent
                .replace("TL", "")
                .trim()
                .replace(/\./g, "")
                .replace(",", ".");

        const [day, month, year] =
            editingRow.cells[4].textContent.trim().split(".");

        addProductForm.elements["expiry"].value = `${year}-${month}-${day}`;

        formTitle.textContent = "Ürün Bilgilerini Düzenle";
        submitButton.textContent = "Değişiklikleri Kaydet";

        addProductModal.hidden = false;
    });

    // Ürün silme işlemi
    productsTableBody.addEventListener("click", async function (event) {
        const deleteButton = event.target.closest(".delete-product-btn");

        if (!deleteButton) return;

        const row = deleteButton.closest("tr");
        const productName = row.cells[1].textContent.trim();


        const confirmed = await new Promise(function (resolve) {
            const overlay = document.createElement("div");

            Object.assign(overlay.style, {
                position: "fixed",
                inset: "0",
                background: "rgba(15, 23, 42, 0.55)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                zIndex: "99999",
                padding: "20px"
            });

            const modal = document.createElement("div");

            Object.assign(modal.style, {
                background: "#ffffff",
                borderRadius: "18px",
                padding: "28px",
                width: "100%",
                maxWidth: "420px",
                boxShadow: "0 20px 60px rgba(0,0,0,0.18)",
                fontFamily: "inherit"
            });

            modal.innerHTML = `
        <div style="font-size:32px; margin-bottom:14px;">🗑️</div>
        <h2 style="margin:0 0 12px; color:#1f2937;">
            Ürünü Sil
        </h2>
        <p style="color:#475569; line-height:1.6;">
            <strong id="deleteProductName"></strong>
            adlı ürünü silmek istediğine emin misin?
        </p>
        <p style="color:#dc2626; font-size:13px;">
            Bu işlem geri alınamaz.
        </p>
        <div style="display:flex; justify-content:flex-end;
                    gap:12px; margin-top:24px;">
            <button type="button" id="cancelProductDelete"
                style="padding:11px 20px; border-radius:9px;
                       border:1px solid #d1d5db; background:white;
                       cursor:pointer;">
                Vazgeç
            </button>
            <button type="button" id="confirmProductDelete"
                style="padding:11px 20px; border-radius:9px;
                       border:none; background:#dc2626;
                       color:white; cursor:pointer;">
                Evet, Sil
            </button>
        </div>
    `;

            overlay.appendChild(modal);
            document.body.appendChild(overlay);

            modal.querySelector("#deleteProductName").textContent = productName;

            function closeModal(result) {
                overlay.remove();
                document.removeEventListener("keydown", handleEscape);
                resolve(result);
            }

            function handleEscape(event) {
                if (event.key === "Escape") {
                    closeModal(false);
                }
            }

            document.addEventListener("keydown", handleEscape);

            modal.querySelector("#cancelProductDelete").onclick = function () {
                closeModal(false);
            };

            modal.querySelector("#confirmProductDelete").onclick = function () {
                closeModal(true);
            };
        });

        if (!confirmed) return;


        const productId = row.dataset.productId;

        if (!productId) {

            showToast("Ürün ID'si bulunamadı. Silme işlemi yapılamadı.", "error");

            return;
        }

        try {
            const response = await fetch(`/api/products/${productId}`, {
                method: "DELETE"
            });

            const result = await response.json();


            if (!response.ok || !result.success) {
                showErrorToast(
                    result.message || "Ürün silinirken bir hata oluştu."
                );
                return;
            }


        } catch (error) {
            console.error("Ürün silme hatası:", error);

            showToast("Backend bağlantı hatası. Ürün silinemedi.", "error");

            return;
        }
        row.remove();

        updateDashboardStats();
        checkCriticalStock();
        updateExpiryStatuses();
        updateAnalyticsReport();

        // Ürün sayısını ve arama sonucunu güncelle
        productSearch.dispatchEvent(new Event("input"));


        showSuccessToast(
            "Ürün başarıyla silindi!",
            "Ürün envanterden kaldırıldı."
        );

    });

    updateExpiryStatuses();
    updateDashboardStats();
    checkCriticalStock();

    // Ürün adına ve barkoda göre arama 
    productSearch.addEventListener("input", function () {
        const searchText = productSearch.value
            .trim()
            .toLocaleLowerCase("tr-TR");

        const rows = productsTableBody.querySelectorAll("tr");
        let visibleCount = 0;

        rows.forEach(function (row) {
            const rowText = row.textContent
                .trim()
                .toLocaleLowerCase("tr-TR");

            const matches = rowText.includes(searchText);

            row.hidden = !matches;

            if (matches) {
                visibleCount++;
            }
        });

        productCount.textContent = visibleCount + " ürün";
        noProductsMessage.hidden = visibleCount > 0;

    });


    // Diğer sayfaların içerikleri
    const pageContents = {

        "Satış": `
    <section class="products-page">
        <div class="products-header">
            <div>
                <h2>Satış Yönetimi</h2>
                <p>Eczane satış işlemlerini buradan yönetin.</p>
            </div>

<!-- GÜNLÜK SATIŞ İSTATİSTİKLERİ -->
<div class="daily-sales-stats">

    <div class="daily-stat-card">
        <span>Günlük Ciro</span>
        <h3 id="dailyRevenue">0,00 TL</h3>
    </div>

    <div class="daily-stat-card">
        <span>Satış İşlemi</span>
        <h3 id="dailySalesCount">0</h3>
    </div>

    <div class="daily-stat-card">
        <span>Satılan Ürün Adedi</span>
        <h3 id="dailyQuantity">0</h3>
    </div>

    <div class="daily-stat-card">
        <span>En Çok Satılan Ürün</span>
        <h3 id="dailyTopProduct">-</h3>
    </div>

</div>
        </div>


        <!-- TARIH ARALIKLI SATIS RAPORU -->
        <div class="sales-form-panel" id="rangeReportPanel">
            <h3>Tarih Aralıklı Satış Raporu</h3>
            <p>Belirlediğiniz tarihler arasındaki satışları görüntüleyin.</p>

            <div class="sales-form-grid">
                <div class="form-group">
                    <label for="reportStartDate">Başlangıç Tarihi</label>
                    <input type="date" id="reportStartDate">
                </div>

                <div class="form-group">
                    <label for="reportEndDate">Bitiş Tarihi</label>
                    <input type="date" id="reportEndDate">
                </div>
            </div>

            <button type="button" id="generateRangeReport" class="btn-primary">
                Rapor Oluştur
            </button>

            <div id="rangeReportResult" style="margin-top: 20px;"></div>
        </div>
                
        <div class="sales-form-panel">
            <h3>Yeni Satış Oluştur</h3>

        
<form id="salesForm">

    <!-- MÜŞTERİ SEÇİMİ -->
    <div class="sale-field">
        <label for="saleCustomer">Müşteri</label>
        <select id="saleCustomer">
            <option value="">Müşterisiz Satış</option>
        </select>
        <small class="sale-field-hint">
            Müşteri seçimi isteğe bağlıdır.
        </small>
    </div>

    <!-- ÜRÜN SEÇİMİ -->
    <div class="sale-field">
        <label for="saleProduct">Ürün</label>
        <select id="saleProduct" required>
            <option value="">Ürün seçin</option>
        </select>
    </div>

    <!-- MİKTAR -->
    <div class="sale-field">
        <label for="saleQuantity">Miktar</label>
        <input
            type="number"
            id="saleQuantity"
            min="1"
            step="1"
            value="1"
            required
        >
    </div>

                <p>Mevcut stok: <strong id="saleStock">-</strong></p>
                <p>Birim fiyat: <strong id="salePrice">-</strong></p>
                <p>Toplam tutar: <strong id="saleTotal">0,00 TL</strong></p>

                <button type="submit" class="add-product-btn">
                    Satışı Tamamla
                </button>

                <p id="saleMessage" role="status"></p>
            </form>
        </div>

        <!-- SATIŞ GEÇMİŞİ -->
        <div class="sales-form-panel">
            <h3>Satış Geçmişi</h3>
            <p>Gerçekleştirilen satış işlemlerini buradan görüntüleyebilirsiniz.</p>

            <div class="table-responsive sales-history-container">
                <table class="products-table">
                            
            <thead>
                <tr>
                    <th>Satış No</th>
                    <th>Müşteri</th>
                    <th>Ürün</th>
                    <th>Miktar</th>
                    <th>Birim Fiyat</th>
                    <th>Toplam Tutar</th>
                    <th>Tarih</th>
                    <th>İŞLEM</th>
                </tr>
            </thead>

                    <tbody id="salesHistoryTableBody">
                        <tr>
                            <td colspan="8">
                                Satış geçmişi yükleniyor...
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
    
<!-- SATIŞ İADE ONAY PENCERESİ -->
<div
    class="customer-delete-modal"
    id="saleRefundModal"
    role="dialog"
    aria-modal="true"
    aria-labelledby="saleRefundTitle"
    hidden
>
    <div class="customer-delete-content">

        <div class="customer-delete-icon">
            !
        </div>

        <h3 id="saleRefundTitle">
            Satış İade Onayı
        </h3>

        <p>
            <strong id="refundSaleNumber"></strong>
            numaralı satışı iade etmek istediğinize
            emin misiniz?
        </p>

        <p class="customer-delete-warning">
            İade edilen ürün miktarı tekrar stoğa eklenecektir.
        </p>

        <p id="saleRefundMessage" role="status"></p>

        <div class="customer-delete-actions">
            <button
                type="button"
                id="cancelSaleRefund">
                Vazgeç
            </button>

            <button
                type="button"
                id="confirmSaleRefund">
                Evet, İade Et
            </button>
        </div>

    </div>
</div>

    </section>
`,

        "Müşteriler": `
    <section class="products-page customers-page">

        <!-- SAYFA BAŞLIĞI -->
        <div class="products-header">
            <div>
                <h2>Müşteri Yönetimi</h2>
                <p>Müşteri kayıtlarını görüntüleyin ve yönetin.</p>
            </div>

            <button
                type="button"
                class="add-product-btn"
                id="addCustomerBtn"
            >
                + Yeni Müşteri Ekle
            </button>
        </div>

        <!-- MÜŞTERİ İSTATİSTİKLERİ -->
        <div class="stats-grid">
            <div class="stat-card">
                <span>Toplam Müşteri</span>
                <h3 id="totalCustomersCount">0</h3>
                <p>Kayıtlı müşteri sayısı</p>
            </div>
        </div>

        <!-- MÜŞTERİ ARAMA -->
        <div class="products-toolbar">
            <div class="product-search">
                <span>⌕</span>

                <input
                    type="search"
                    id="customerSearch"
                    placeholder="Ad, soyad veya telefon ile ara..."
                >
            </div>

            <span class="product-count" id="customerCount">
                0 müşteri
            </span>
        </div>

        <!-- MÜŞTERİ TABLOSU -->
        <div class="products-table-container">
            <table class="products-table">
                <thead>
                    <tr>
                        <th>Ad Soyad</th>
                        <th>Telefon</th>
                        <th>E-posta</th>
                        <th>İşlemler</th>
                    </tr>
                </thead>

                <tbody id="customersTableBody">
                    <tr>
                        <td colspan="4" class="no-products">
                            Henüz müşteri kaydı bulunmuyor.
                        </td>
                    </tr>
                </tbody>
            </table>
        </div>

        <!-- MÜŞTERİ EKLEME / DÜZENLEME MODALI -->
        <div
            class="customer-modal"
            id="customerModal"
            hidden
        >
            <div class="customer-modal-content">

                <div class="customer-modal-header">
                    <div>
                        <h3>Yeni Müşteri Ekle</h3>
                        <p>Müşteri bilgilerini doldurun.</p>
                    </div>

                    <button
                        type="button"
                        id="closeCustomerModal"
                        class="customer-modal-close"
                        aria-label="Pencereyi kapat"
                    >
                        &times;
                    </button>
                </div>

                <form id="customerForm">

                    <!-- AD SOYAD -->
                    <div class="customer-form-group">
                        <label for="customerName">
                            Ad Soyad *
                        </label>

                        <input
                            type="text"
                            id="customerName"
                            minlength="2"
                            maxlength="120"
                            placeholder="Örn. Ayşe Yılmaz"
                            required
                        >
                    </div>

                    <!-- TELEFON -->
                    <div class="customer-form-group">
                        <label for="customerPhone">
                            Telefon *
                        </label>

                        <input
                            type="tel"
                            id="customerPhone"
                            minlength="11"
                            maxlength="11"
                            pattern="05[0-9]{9}"
                            inputmode="numeric"
                            title="Telefon numarası 05 ile başlamalı ve 11 rakam olmalıdır."
                            placeholder="05XXXXXXXXX"
                            required
                        >
                    </div>

                    <!-- E-POSTA -->
                    <div class="customer-form-group">
                        <label for="customerEmail">
                            E-posta
                        </label>

                        <input
                            type="email"
                            id="customerEmail"
                            placeholder="ornek@email.com"
                        >
                    </div>

                    <!-- NOTLAR -->
                    <div class="customer-form-group">
                        <label for="customerNotes">
                            Notlar
                        </label>

                        <textarea
                            id="customerNotes"
                            rows="3"
                            maxlength="500"
                            placeholder="İsteğe bağlı not..."
                        ></textarea>
                    </div>

                    <!-- FORM MESAJI -->
                    <p
                        id="customerFormMessage"
                        role="status"
                    ></p>

                    <!-- FORM BUTONLARI -->
                    <div class="customer-form-actions">
                        <button
                            type="button"
                            id="cancelCustomerModal"
                            class="customer-cancel-btn"
                        >
                            İptal
                        </button>

                        <button
                            type="submit"
                            class="add-product-btn"
                            id="saveCustomerBtn"
                        >
                            Müşteriyi Kaydet
                        </button>
                    </div>

                </form>
            </div>
        </div>

        <!-- MÜŞTERİ SİLME ONAY MODALI -->
        <div
            class="customer-delete-modal"
            id="customerDeleteModal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="customerDeleteTitle"
            hidden
        >
            <div class="customer-delete-content">

                <!-- UYARI SİMGESİ -->
                <div class="customer-delete-icon">
                    !
                </div>

                <!-- BAŞLIK -->
                <h3 id="customerDeleteTitle">
                    Müşteriyi Sil
                </h3>

                <!-- SİLİNECEK MÜŞTERİ -->
                <p>
                    <strong id="deleteCustomerName"></strong>
                    adlı müşteriyi silmek istediğinize
                    emin misiniz?
                </p>

                <!-- UYARI MESAJI -->
                <p class="customer-delete-warning">
                    Bu işlem geri alınamaz.
                </p>

                <!-- SİLME MESAJI -->
                <p
                    id="customerDeleteMessage"
                    role="status"
                ></p>

                <!-- SİLME BUTONLARI -->
                <div class="customer-delete-actions">

                    <button
                        type="button"
                        id="cancelCustomerDelete"
                        class="customer-cancel-btn"
                    >
                        İptal
                    </button>

                    <button
                        type="button"
                        id="confirmCustomerDelete"
                        class="customer-confirm-delete-btn"
                    >
                        Evet, Sil
                    </button>

                </div>
            </div>
        </div>

<!-- MÜŞTERİ SATIŞ GEÇMİŞİ PENCERESİ -->
<div id="customerHistoryModal" class="customer-modal" hidden>

    <div class="customer-modal-content customer-history-content">

        <div class="customer-modal-header">
            <h3>Müşteri Satış Geçmişi</h3>

            <button
                type="button"
                id="closeCustomerHistoryModal"
                class="customer-modal-close">
                &times;
            </button>
        </div>

        <p id="customerHistoryName"></p>

        <div class="table-responsive">
            <table class="products-table">
                <thead>
                    <tr>
                        <th>Satış No</th>
                        <th>Ürün</th>
                        <th>Miktar</th>
                        <th>Tutar</th>
                        <th>Tarih</th>
                        <th>Durum</th>
                    </tr>
                </thead>

                <tbody id="customerHistoryTableBody">
                    <tr>
                        <td colspan="6">
                            Satış geçmişi yükleniyor...
                        </td>
                    </tr>
                </tbody>
            </table>
        </div>

        <p>
            Toplam Harcama:
            <strong id="customerHistoryTotal">0,00 TL</strong>
        </p>

    </div>
</div>

    </section>
`,

        "Analiz": `
    <section class="products-page analytics-page">

        <div class="products-header">
            <div>
                <h2>Analiz ve Raporlar</h2>
                <p>Eczanenizin stok durumunu ve ürün dağılımını inceleyin.</p>
            </div>
            <span class="demo-label">Stok Raporu</span>
        </div>

        <div class="stats-grid">
            <div class="stat-card">
                <span>Toplam Ürün</span>
                <h3 id="reportTotalProducts">0</h3>
                <p>Envanterdeki ürün çeşidi</p>
            </div>

            <div class="stat-card">
                <span>Kritik Stok</span>
                <h3 id="reportCriticalStock">0</h3>
                <p id="reportCriticalStockDescription">Kritik stok sınırındaki ürünler</p>
                </div>
            <div class="stat-card">
                <span>Toplam Stok Adedi</span>
                <h3 id="reportStockQuantity">0</h3>
                <p>Envanterdeki toplam miktar</p>
            </div>

            <div class="stat-card">
                <span>Yaklaşan SKT</span>
                <h3 id="reportExpiryWarning">0</h3>
                <p>Son kullanma tarihi kontrolü gereken ürün</p>
            </div>
        </div>

        <div class="content-grid">
            <section class="content-card">
                <h3>Stok Durumu</h3>
                <p>Ürünlerin stok seviyelerine göre dağılımı.</p>

                <div class="report-stat-row">
                    <span>Normal stok</span>
                    <strong id="reportNormalCount">0</strong>
                </div>
                <div class="report-progress">
                    <div id="reportNormalBar" class="report-progress-normal"></div>
                </div>

                <div class="report-stat-row">
                    <span>Düşük stok</span>
                    <strong id="reportLowCount">0</strong>
                </div>
                <div class="report-progress">
                    <div id="reportLowBar" class="report-progress-low"></div>
                </div>

                <div class="report-stat-row">
                    <span>Kritik stok</span>
                    <strong id="reportCriticalCount">0</strong>
                </div>
                <div class="report-progress">
                    <div id="reportCriticalBar" class="report-progress-critical"></div>
                </div>
            </section>

            <section class="content-card">
                <h3>Envanter Özeti</h3>
                <p>Mevcut ürün kayıtlarına dayalı genel görünüm.</p>

                <div class="report-summary">
                    <span>Stok toplam değeri</span>
                    <strong id="reportInventoryValue">0,00 TL</strong>
                </div>

                <div class="report-summary">
                    <span>Ortalama ürün stoğu</span>
                    <strong id="reportAverageStock">0</strong>
                </div>

                <div class="report-summary">
                    <span>Stok takibi</span>
                    <strong class="report-status">Aktif</strong>
                </div>
            </section>
        </div>

        <p class="demo-note">
            Raporlar, sistemde kayıtlı ürün ve stok bilgileri üzerinden hesaplanır.
        </p>

    </section>
`,


        "AI Asistanı": `
    <section class="products-page ai-page">
        <div class="products-header">
            <div>
                <h2>AI Eczane Asistanı</h2>
                <p>Eczane stoklarınız ve ürünleriniz hakkında sorular sorun.</p>
            </div>
            <span class="demo-label">Akıllı Asistan</span>
        </div>

        <div class="ai-chat-container">
            <div class="ai-chat-header">
                <div class="ai-avatar">AI</div>
                <div>
                    <h3>Eczane Asistanı</h3>
                    <p>Size yardımcı olmaya hazırım.</p>
                </div>
            </div>

            <div id="aiChatMessages" class="ai-chat-messages">
                <div class="ai-message assistant-message">
                    <div class="ai-message-label">AI Asistanı</div>
                    Merhaba! Eczane otomasyonunuza hoş geldiniz.
                    Stok, ürünler ve son kullanma tarihleri hakkında
                    sorularınızı buradan yazabilirsiniz.
                </div>
            </div>

            <div class="ai-suggestions">
                <button type="button" class="ai-suggestion">
                    Kritik stoktaki ürünleri göster
                </button>
                <button type="button" class="ai-suggestion">
                    Son kullanma tarihi yaklaşan ürünleri listele
                </button>
                <button type="button" class="ai-suggestion">
                    Toplam stok değerini göster
                </button>
            </div>

            <form id="aiChatForm" class="ai-chat-form">
                <input
                    type="text"
                    id="aiChatInput"
                    placeholder="Eczanenizle ilgili bir soru yazın..."
                    autocomplete="off"
                    required
                >
                <button type="submit" aria-label="Mesaj gönder">
                    Gönder
                </button>
            </form>


            <p class="ai-disclaimer">
                AI yanıtları için backend bağlantısı gereklidir.
            </p>
        </div>

        <!-- AKILLI STOK ANALİZİ -->
        <div class="ai-stock-analysis">
            <div class="products-header">
                <div>
                    <h2>Akıllı Stok Analizi</h2>
                    <p>
                        Son 30 günlük satışlara göre stok tükenme
                        tahminlerini görüntüleyin.
                    </p>
                </div>
            </div>
         
<div id="aiStockWarning" class="ai-stock-warning" hidden>
    <div class="ai-stock-warning-title">
        ⚠️ Stok Risk Uyarısı
    </div>

    <p id="aiStockWarningText"></p>
</div>

            <div class="products-table-container">
                <table class="products-table">
                    <thead>
                        <tr>
                            <th>Ürün Adı</th>
                            <th>Mevcut Stok</th>
                            <th>30 Günlük Satış</th>
                            <th>Günlük Ortalama</th>
                            <th>Tahmini Kalan Gün</th>
                            <th>Risk Durumu</th>
                            <th>Sipariş Önerisi</th>
                            <th>Önerilen Miktar</th>
                        </tr>
                    </thead>
                    <tbody id="aiStockTableBody">
                        <tr>
                            <td colspan="8">
                                Analiz verileri yükleniyor...
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
    </section>
`,

        "Ayarlar": `
    <section class="products-page settings-page">

        <div class="products-header">
            <div>
                <h2>Ayarlar</h2>
                <p>Eczane bilgilerinizi ve uygulama tercihlerinizi yönetin.</p>
            </div>
            <span class="settings-label">EczaneAI Yönetim</span>
        </div>

        <div class="settings-grid">

            <!-- ECZANE BİLGİLERİ -->
            <div class="settings-card">
                <div class="settings-card-header">
                    <span class="settings-icon">✚</span>
                    <div>
                        <h3>Eczane Bilgileri</h3>
                        <p>İşletmenize ait temel bilgiler</p>
                    </div>
                </div>

                <div class="settings-form">
                    <div class="settings-field">
                        <label for="pharmacyName">Eczane Adı</label>
                        <input type="text" id="pharmacyName"
                               placeholder="Eczane adını girin">
                    </div>

                    <div class="settings-field">
                        <label for="pharmacyPhone">Telefon Numarası</label>
                        <input type="tel" id="pharmacyPhone"
                               placeholder="05XX XXX XX XX">
                    </div>

                    <div class="settings-field">
                        <label for="pharmacyEmail">E-posta Adresi</label>
                        <input type="email" id="pharmacyEmail"
                               placeholder="eczane@ornek.com">
                    </div>

                    <button type="button"
                            class="settings-save-btn"
                            id="savePharmacySettings">
                        Değişiklikleri Kaydet
                    </button>
                </div>
            </div>

            <!-- STOK VE BİLDİRİM AYARLARI -->
            <div class="settings-card">
                <div class="settings-card-header">
                    <span class="settings-icon">⚙</span>
                    <div>
                        <h3>Stok ve Bildirim Ayarları</h3>
                        <p>Stok uyarılarını yapılandırın</p>
                    </div>
                </div>

                <div class="settings-form">
                    <div class="settings-field">
                        <label for="criticalStockLimit">Kritik Stok Sınırı</label>
                        <input type="number"
                               id="criticalStockLimit"
                               min="0"
                               value="3">
                        <small>Bu miktar ve altındaki ürünler kritik sayılır.</small>
                    </div>

                    <div class="settings-field">
                        <label for="expiryWarningDays">Son Kullanma Tarihi Uyarısı</label>
                        <select id="expiryWarningDays">
                            <option value="7">7 gün önce</option>
                            <option value="15">15 gün önce</option>
                            <option value="30" selected>30 gün önce</option>
                            <option value="60">60 gün önce</option>
                        </select>
                    </div>

                    <button type="button"
                            class="settings-save-btn"
                            id="saveStockSettings">
                        Ayarları Kaydet
                    </button>
                </div>
            </div>

            <!-- SİSTEM BİLGİLERİ -->
            <div class="settings-card settings-system-card">
                <div class="settings-card-header">
                    <span class="settings-icon">▣</span>
                    <div>
                        <h3>Sistem Bilgileri</h3>
                        <p>Uygulama hakkında bilgiler</p>
                    </div>
                </div>

                <div class="settings-info-row">
                    <span>Uygulama</span>
                    <strong>EczaneAI</strong>
                </div>

                <div class="settings-info-row">
                    <span>Sürüm</span>
                    <strong>1.0.0 (Geliştirme)</strong>
                </div>

                <div class="settings-info-row">
                    <span>Teknoloji</span>
                    <strong>Python / Flask</strong>
                </div>

                <div class="settings-info-row">
                    <span>Sistem Durumu</span>
                    <strong class="settings-active">Geliştirme Ortamı</strong>
                </div>
            </div>

        </div>

    </section>
`

    };

    // Kayıtlı ayarları getir
    function getPharmacySettings() {
        try {
            const saved = JSON.parse(
                localStorage.getItem("eczaneAISettings") || "{}"
            );

            return {
                ...DEFAULT_SETTINGS,
                ...saved
            };
        } catch (error) {
            console.error("Ayarlar okunamadı:", error);
            return { ...DEFAULT_SETTINGS };
        }
    }

    // Uygulama açılırken güncel ayarları SQLite'dan yükle
    loadPharmacySettingsFromAPI().then(function (settings) {
        if (settings) {
            updateExpiryStatuses();
            updateDashboardStats();
            checkCriticalStock();
        }
    });


    // SQLite API'den ayarlari yukle
    async function loadPharmacySettingsFromAPI() {
        try {
            const response = await fetch("/api/settings");
            const data = await response.json();

            if (!response.ok || !data.success) {
                throw new Error(data.message || "Ayarlar alinamadi.");
            }

            const settings = {
                ...DEFAULT_SETTINGS,
                ...data.settings
            };

            localStorage.setItem(
                "eczaneAISettings",
                JSON.stringify(settings)
            );

            // API'den gelen güncel ayarları Dashboard'a yansıt
            updateDashboardStats();

            return settings;

        } catch (error) {
            console.error("API ayarlari yuklenemedi:", error);
            return null;
        }
    }

    // Ayarları kaydet


    // Ayarları SQLite API'ye kaydet
    async function savePharmacySettingsData(settings) {
        try {
            const response = await fetch("/api/settings", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(settings)
            });

            const data = await response.json();

            if (!response.ok || !data.success) {
                throw new Error(data.message || "Kaydetme başarısız.");
            }

            localStorage.setItem(
                "eczaneAISettings",
                JSON.stringify(settings)
            );

            return true;
        } catch (error) {
            console.error("Ayarlar kaydedilemedi:", error);
            return false;
        }
    }


    // Ayarlar sayfasını hazırla

    async function initializeSettingsPage() {
        const settingsPage = document.querySelector(".settings-page");

        if (!settingsPage) return;

        const settings =
            await loadPharmacySettingsFromAPI() ||
            getPharmacySettings();

        if (!settingsPage.isConnected) return;


        const pharmacyName = document.getElementById("pharmacyName");
        const pharmacyPhone = document.getElementById("pharmacyPhone");
        const pharmacyEmail = document.getElementById("pharmacyEmail");
        const criticalStockLimit = document.getElementById("criticalStockLimit");
        const expiryWarningDays = document.getElementById("expiryWarningDays");

        if (
            !pharmacyName ||
            !pharmacyPhone ||
            !pharmacyEmail ||
            !criticalStockLimit ||
            !expiryWarningDays
        ) {
            return;
        }

        // Önceden kaydedilen değerleri göster
        pharmacyName.value = settings.pharmacyName;
        pharmacyPhone.value = settings.pharmacyPhone;
        pharmacyEmail.value = settings.pharmacyEmail;
        criticalStockLimit.value = settings.criticalStockLimit;
        expiryWarningDays.value = settings.expiryWarningDays;

        // Eczane bilgilerini kaydet
        document.getElementById("savePharmacySettings")
            ?.addEventListener("click", async function () {

                const updated = getPharmacySettings();

                updated.pharmacyName = pharmacyName.value.trim();
                updated.pharmacyPhone = pharmacyPhone.value.trim();
                updated.pharmacyEmail = pharmacyEmail.value.trim();

                if (
                    updated.pharmacyEmail &&
                    !pharmacyEmail.checkValidity()
                ) {

                    showToast("Lütfen geçerli bir e-posta adresi girin.", "error");

                    return;
                }

                if (await savePharmacySettingsData(updated)) {
                    showToast("Eczane bilgileri başarıyla kaydedildi!", "success");
                } else {
                    showToast("Ayarlar kaydedilemedi.", "error");
                }

            });

        // Stok ve bildirim ayarlarını kaydet
        document.getElementById("saveStockSettings")
            ?.addEventListener("click", async function () {

                const updated = getPharmacySettings();

                const limit = Number(criticalStockLimit.value);
                const days = Number(expiryWarningDays.value);

                if (
                    criticalStockLimit.value.trim() === "" ||
                    !Number.isInteger(limit) ||
                    limit < 0
                ) {
                    alert("Kritik stok sınırı 0 veya daha büyük bir tam sayı olmalı.");
                    return;
                }

                if (![7, 15, 30, 60].includes(days)) {
                    alert("Geçerli bir SKT uyarı süresi seçin.");
                    return;
                }

                updated.criticalStockLimit = limit;
                updated.expiryWarningDays = days;


                if (await savePharmacySettingsData(updated)) {
                    showToast("Stok ve bildirim ayarları başarıyla kaydedildi!", "success");
                } else {
                    showToast("Ayarlar kaydedilemedi.", "error");
                }

            });
    }

    // Sayfalar arasında geçiş
    function showPage(menuName) {
        const normalizedMenuName = menuName
            .replace(/[✧✦▦▤▣♙▥⚙]/g, "")
            .trim()
            .replace(/^AI Asistan$/, "AI Asistanı");


        const isDashboard = normalizedMenuName === "Dashboard";
        const isProducts = normalizedMenuName === "Ürünler";


        // Aktif menüyü güncelle
        menuItems.forEach(function (item) {
            const itemName = item.textContent
                .replace(/[✧▦▤▣♙▥⚙]/g, "")
                .trim();

            item.classList.toggle(
                "active",
                itemName === normalizedMenuName ||
                (itemName === "AI Asistan" && normalizedMenuName === "AI Asistanı")
            );
        });

        // Sayfa başlığı
        pageTitle.textContent = isDashboard
            ? "Eczane Dashboard"
            : normalizedMenuName;

        // Dashboard bölümleri
        dashboardSections.forEach(function (section) {
            section.hidden = !isDashboard;
        });

        // Ürünler bölümü
        productsContainer.hidden = !isProducts;
        // Kritik stok uyarısı sadece Dashboard'da görünsün
        const criticalWarning = document.getElementById(
            "criticalStockWarning"
        );

        if (criticalWarning) {
            criticalWarning.hidden = !isDashboard;
            criticalWarning.style.display = isDashboard ? "block" : "none";
        }

        // DASHBOARD AI ASİSTAN KARTI
        let dashboardAI = document.getElementById("dashboardAI");

        if (!dashboardAI) {
            dashboardAI = document.createElement("section");

            dashboardAI.id = "dashboardAI";
            dashboardAI.className = "dashboard-ai-card";


            dashboardAI.innerHTML = `
    <div class="dashboard-ai-new-header">
        <div class="dashboard-ai-icon">✦</div>

        <div class="dashboard-ai-new-heading">
            <span class="dashboard-ai-label">
                ✨ AKILLI ECZANE YÖNETİMİ
            </span>
            <h2>AI Eczane Asistanı</h2>
        </div>

        <span class="dashboard-ai-new-tag">
            Akıllı Asistan
        </span>
    </div>

    <p class="dashboard-ai-new-description">
        Stok durumunuzu analiz edin, satış verilerinizi
        değerlendirin ve eczane yönetimini kolaylaştırın.
    </p>

    <div class="dashboard-ai-new-features">
        <div class="dashboard-ai-new-feature">
            <span class="dashboard-ai-feature-icon">▣</span>
            <div>
                <strong>Stok Analizi</strong>
                <small>Kritik ürünleri takip edin</small>
            </div>
        </div>

        <div class="dashboard-ai-new-feature">
            <span class="dashboard-ai-feature-icon">▥</span>
            <div>
                <strong>Satış Analizi</strong>
                <small>Satış verilerini inceleyin</small>
            </div>
        </div>
    </div>

    <button type="button" id="openAIAssistant">
        AI Asistanına Git →
    </button>
`;

            const statsGrid = mainContent.querySelector(
                ".stats-grid"
            );

            if (statsGrid) {
                mainContent.insertBefore(dashboardAI, statsGrid);
            } else {
                mainContent.appendChild(dashboardAI);
            }

            dashboardAI.querySelector("#openAIAssistant")
                .addEventListener("click", function () {
                    showPage("AI Asistanı");
                });
        }

        dashboardAI.hidden = !isDashboard;


        if (isDashboard) {
            updateDashboardTotalSales();
        }

        // Diğer sayfalar
        let extraPage = document.querySelector("#extraPage");

        if (!extraPage) {
            extraPage = document.createElement("div");
            extraPage.id = "extraPage";
            mainContent.appendChild(extraPage);
        }

        if (isDashboard || isProducts) {
            extraPage.hidden = true;
            extraPage.innerHTML = "";
        }
        else {
            extraPage.hidden = false;
            extraPage.innerHTML = pageContents[normalizedMenuName] ||
                `<section class="products-page">
                     <h2>${normalizedMenuName}</h2>
                     <p>Bu sayfa henüz hazırlanmadı.</p>
                 </section>`;

            if (normalizedMenuName === "Satış") {
                loadSalesHistory();
                loadDailySalesReport();
            }

            if (normalizedMenuName === "Analiz") {
                updateAnalyticsReport();
            }

            if (normalizedMenuName === "Ayarlar") {
                initializeSettingsPage();
            }
            if (normalizedMenuName === "AI Asistanı") {

                loadAIStockAnalysis();

                const chatForm = document.getElementById("aiChatForm");
                const chatInput = document.getElementById("aiChatInput");
                const chatMessages = document.getElementById("aiChatMessages");
                const suggestionButtons = document.querySelectorAll(".ai-suggestion");

                if (chatForm && chatInput && chatMessages &&
                    !chatForm.dataset.initialized) {

                    chatForm.dataset.initialized = "true";

                    function addChatMessage(message, type) {
                        const bubble = document.createElement("div");
                        bubble.className = "ai-message " +
                            (type === "user" ? "user-message" : "assistant-message");

                        const label = document.createElement("div");
                        label.className = "ai-message-label";
                        label.textContent = type === "user" ? "Siz" : "AI Asistanı";

                        const content = document.createElement("div");
                        content.textContent = message;

                        bubble.append(label, content);

                        chatMessages.appendChild(bubble);
                        chatMessages.scrollTop = chatMessages.scrollHeight;
                    }
                    function addTypingIndicator() {
                        const indicator = document.createElement("div");
                        indicator.id = "aiTypingIndicator";
                        indicator.className = "ai-message assistant-message";
                        indicator.textContent = "Yanıt hazırlanıyor...";

                        chatMessages.appendChild(indicator);
                        chatMessages.scrollTop = chatMessages.scrollHeight;

                        return indicator;
                    }


                    chatForm.addEventListener("submit", async function (event) {
                        event.preventDefault();


                        const question = chatInput.value.trim();

                        if (!question || chatForm.dataset.waiting === "true") {
                            return;
                        }

                        const sendButton = chatForm.querySelector('button[type="submit"]');

                        addChatMessage(question, "user");
                        chatInput.value = "";

                        const typingIndicator = addTypingIndicator();

                        chatForm.dataset.waiting = "true";

                        if (sendButton) {
                            sendButton.disabled = true;
                        }

                        try {
                            const response = await fetch("/api/query", {
                                method: "POST",
                                headers: {
                                    "Content-Type": "application/json"
                                },
                                body: JSON.stringify({ question: question })
                            });

                            const data = await response.json();

                            if (!response.ok || !data.success) {
                                throw new Error(data.message || "İstek başarısız oldu.");
                            }


                            const answerParts = [];

                            if (data.message) {
                                answerParts.push(data.message);
                            }

                            if (data.context) {
                                const contextText = typeof data.context === "string"
                                    ? data.context
                                    : JSON.stringify(data.context, null, 2);

                                answerParts.push("İlgili kaynaklar:\n" + contextText);
                            }

                            const answer = answerParts.join("\n\n") ||
                                "AI asistanından boş yanıt alındı.";


                            typingIndicator.remove();
                            addChatMessage(answer, "assistant");


                        } catch (error) {
                            typingIndicator.remove();

                            addChatMessage(
                                error.message || "AI asistanına şu anda ulaşılamıyor. Lütfen tekrar deneyin.",
                                "assistant"
                            );

                            console.error("AI API hatası:", error);

                        } finally {
                            chatForm.dataset.waiting = "false";

                            if (sendButton) {
                                sendButton.disabled = false;
                            }

                            chatInput.disabled = false;
                            chatInput.focus();
                        }
                    });


                    suggestionButtons.forEach(function (button) {
                        button.addEventListener("click", function () {
                            if (chatForm.dataset.waiting === "true") {
                                return;
                            }

                            chatInput.value = button.textContent.trim();

                            chatForm.requestSubmit();
                        });
                    });

                }
            }

        }
        // Ürünler sayfası açıldığında aramayı sıfırla
        if (isProducts) {
            productSearch.value = "";
            productSearch.dispatchEvent(new Event("input"));
        }
    }

    // Menü tıklamaları
    menuItems.forEach(function (item) {
        item.addEventListener("click", function (event) {
            event.preventDefault();

            const menuName = item.textContent
                .replace(/[✧▦▤▣♙▥⚙]/g, "")
                .trim();

            showPage(menuName);
        });
    });

    // SATIŞ FORMU İŞLEMLERİ

    function populateSaleProducts() {
        const select = document.getElementById("saleProduct");
        const rows = document.querySelectorAll("#productsTableBody tr");

        if (!select) return;

        const selectedValue = select.value;

        select.innerHTML = '<option value="">Ürün seçin</option>';

        rows.forEach(function (row) {
            if (row.cells.length < 8) return;

            const barcode = row.cells[0].textContent.trim();
            const name = row.cells[1].textContent.trim();
            const stock = Number(row.cells[2].textContent.trim());
            const priceText = row.cells[3].textContent
                .replace(/\s*TL/i, "")
                .trim()
                .replace(/\./g, "")
                .replace(",", ".");

            const price = Number(priceText);

            if (!barcode || !name || !Number.isFinite(price)) return;

            const option = document.createElement("option");
            option.value = barcode;
            const expiryDate = row.cells[4].textContent.trim();

            option.textContent =
                name +
                " | Barkod: " + barcode +
                " | Stok: " + stock +
                " | SKT: " + expiryDate;
            option.dataset.price = price;
            option.dataset.stock = stock;

            select.appendChild(option);
        });

        if ([...select.options].some(option => option.value === selectedValue)) {
            select.value = selectedValue;
        }
    }

    function updateSaleSummary() {
        const select = document.getElementById("saleProduct");
        const quantityInput = document.getElementById("saleQuantity");
        const stockElement = document.getElementById("saleStock");
        const priceElement = document.getElementById("salePrice");
        const totalElement = document.getElementById("saleTotal");

        if (!select || !quantityInput) return;

        const option = select.selectedOptions[0];

        if (!option || !option.value) {
            if (stockElement) stockElement.textContent = "-";
            if (priceElement) priceElement.textContent = "-";
            if (totalElement) totalElement.textContent = "0,00 TL";
            return;
        }

        const stock = Number(option.dataset.stock);
        const price = Number(option.dataset.price);
        const quantity = Number(quantityInput.value);

        if (stockElement) stockElement.textContent = stock;
        if (priceElement) {
            priceElement.textContent = price.toLocaleString("tr-TR", {
                style: "currency",
                currency: "TRY"
            });
        }

        const total = Number.isInteger(quantity) && quantity > 0
            ? price * quantity
            : 0;

        if (totalElement) {
            totalElement.textContent = total.toLocaleString("tr-TR", {
                style: "currency",
                currency: "TRY"
            });
        }
    }


    // Satış ekranındaki seçim alanlarını doldur
    mainContent.addEventListener("focusin", function (event) {

        if (event.target.id === "saleProduct") {
            populateSaleProducts();
            updateSaleSummary();
        }

    });

    // Satış sayfası açıldığında müşterileri otomatik yükle
    const salesPageObserver = new MutationObserver(function () {

        const customerSelect = document.getElementById("saleCustomer");

        if (customerSelect && !customerSelect.dataset.loaded) {
            customerSelect.dataset.loaded = "true";
            loadSaleCustomers();
        }

    });

    salesPageObserver.observe(mainContent, {
        childList: true,
        subtree: true
    });

    // Sayfa zaten açıksa da yükle
    const existingCustomerSelect = document.getElementById("saleCustomer");

    if (existingCustomerSelect && !existingCustomerSelect.dataset.loaded) {
        existingCustomerSelect.dataset.loaded = "true";
        loadSaleCustomers();
    }

    // Ürün veya miktar değiştiğinde fiyatları güncelle.
    mainContent.addEventListener("change", function (event) {
        if (event.target.id === "saleProduct") {
            updateSaleSummary();
        }

        if (event.target.id === "saleQuantity") {
            updateSaleSummary();
        }
    });

    mainContent.addEventListener("input", function (event) {
        if (event.target.id === "saleQuantity") {
            updateSaleSummary();
        }
    });

    // TARIH ARALIKLI SATIS RAPORU
    mainContent.addEventListener("click", async function (event) {
        if (event.target.id !== "generateRangeReport") {
            return;
        }

        const startDate = document.getElementById("reportStartDate")?.value;
        const endDate = document.getElementById("reportEndDate")?.value;
        const result = document.getElementById("rangeReportResult");

        if (!result) return;

        if (!startDate || !endDate) {
            result.textContent = "Lütfen başlangıç ve bitiş tarihlerini seçin.";
            return;
        }

        result.textContent = "Rapor hazırlanıyor...";

        try {
            const params = new URLSearchParams({
                start_date: startDate,
                end_date: endDate
            });

            const response = await fetch(`/api/reports/range?${params}`);
            const data = await response.json();

            if (!response.ok || !data.success) {
                throw new Error(data.message || "Rapor alınamadı.");
            }

            result.innerHTML = `
                <div class="daily-sales-stats">
                    <div class="daily-stat-card">
                        <span>Toplam Ciro</span>
                        <h3>${Number(data.total_revenue).toLocaleString("tr-TR", {
                style: "currency",
                currency: "TRY"
            })}</h3>
                    </div>

                    <div class="daily-stat-card">
                        <span>Satış İşlemi</span>
                        <h3>${data.total_sales}</h3>
                    </div>

                    <div class="daily-stat-card">
                        <span>Satılan Ürün Adedi</span>
                        <h3>${data.total_quantity}</h3>
                    </div>
                </div>
            `;
        } catch (error) {
            result.textContent = error.message;
        }
    });

    // GÜNLÜK SATIŞ RAPORUNU YÜKLE
    async function loadDailySalesReport() {
        const revenue = document.getElementById("dailyRevenue");
        const salesCount = document.getElementById("dailySalesCount");
        const quantity = document.getElementById("dailyQuantity");
        const topProduct = document.getElementById("dailyTopProduct");

        if (!revenue || !salesCount || !quantity || !topProduct) {
            return;
        }

        try {
            const response = await fetch("/api/reports/daily");
            const data = await response.json();

            if (!response.ok || !data.success) {
                throw new Error(data.message || "Rapor alınamadı.");
            }

            revenue.textContent = Number(data.total_revenue)
                .toLocaleString("tr-TR", {
                    style: "currency",
                    currency: "TRY"
                });

            salesCount.textContent = data.total_sales;
            quantity.textContent = data.total_quantity;

            topProduct.textContent = data.top_product
                ? data.top_product.product_name
                : "Henüz satış yok";

        } catch (error) {
            console.error("Günlük satış raporu hatası:", error);
            revenue.textContent = "-";
            salesCount.textContent = "-";
            quantity.textContent = "-";
            topProduct.textContent = "Rapor yüklenemedi";
        }
    }

    // SATIŞ GEÇMİŞİNİ VERİTABANINDAN GETİR
    async function loadSalesHistory() {
        const tbody = document.getElementById("salesHistoryTableBody");

        if (!tbody) return;

        try {
            const response = await fetch("/api/sales");
            const result = await response.json();

            if (!response.ok || !result.success) {
                throw new Error(result.message || "Satışlar alınamadı.");
            }

            tbody.innerHTML = "";

            if (result.sales.length === 0) {
                tbody.innerHTML = `
                    <tr>
                        <td colspan="8">Henüz satış yapılmamış.</td>
                    </tr>
                `;
                return;
            }

            result.sales.forEach(function (sale) {
                const row = document.createElement("tr");


                const values = [
                    "#" + sale.id,

                    // Satışın bağlı olduğu müşteri
                    sale.customer_name || "Müşterisiz Satış",

                    sale.product_name,
                    sale.quantity,

                    Number(sale.unit_price).toLocaleString("tr-TR", {
                        minimumFractionDigits: 2
                    }) + " TL",

                    Number(sale.total_price).toLocaleString("tr-TR", {
                        minimumFractionDigits: 2
                    }) + " TL",

                    sale.sale_date
                ];

                values.forEach(function (value) {
                    const cell = document.createElement("td");
                    cell.textContent = value;
                    row.appendChild(cell);
                });

                // İade işlemi sütunu
                const actionCell = document.createElement("td");

                if (sale.status === "refunded") {
                    actionCell.textContent = "İade Edildi";
                } else {
                    const refundButton = document.createElement("button");
                    refundButton.textContent = "İade Et";
                    refundButton.type = "button";
                    refundButton.className = "btn btn-danger";


                    refundButton.addEventListener("click", function () {

                        const refundModal = document.getElementById("saleRefundModal");
                        const refundSaleNumber = document.getElementById("refundSaleNumber");
                        const cancelButton = document.getElementById("cancelSaleRefund");
                        const confirmButton = document.getElementById("confirmSaleRefund");
                        const refundMessage = document.getElementById("saleRefundMessage");

                        if (!refundModal || !refundSaleNumber ||
                            !cancelButton || !confirmButton || !refundMessage) {
                            console.error("İade onay penceresi bulunamadı.");
                            return;
                        }

                        refundSaleNumber.textContent = "#" + sale.id;
                        refundMessage.textContent = "";
                        refundModal.hidden = false;

                        cancelButton.onclick = function () {
                            refundModal.hidden = true;
                        };

                        refundModal.onclick = function (event) {
                            if (event.target === refundModal && !confirmButton.disabled) {
                                refundModal.hidden = true;
                            }
                        };

                        confirmButton.onclick = async function () {
                            confirmButton.disabled = true;
                            cancelButton.disabled = true;
                            refundMessage.textContent = "İade işlemi yapılıyor...";

                            try {
                                await refundSale(sale.id);

                                // Yalnızca başarılı iadede pencereyi kapat
                                refundModal.hidden = true;

                                // Başarılı iade bildirimi
                                showToast(
                                    "Satış başarıyla iade edildi. Ürün stoğa eklendi.",
                                    "success"
                                );

                            } catch (error) {
                                // Hata varsa pencere açık kalır
                                refundMessage.textContent =
                                    error.message || "İade işlemi başarısız oldu.";

                            } finally {
                                confirmButton.disabled = false;
                                cancelButton.disabled = false;
                            }
                        };


                    });


                    actionCell.appendChild(refundButton);
                }

                row.appendChild(actionCell);
                tbody.appendChild(row);

            });

        } catch (error) {
            console.error("Satış geçmişi hatası:", error);
            tbody.innerHTML = `
                <tr>
                    <td colspan="8">Satış geçmişi yüklenemedi.</td>
                </tr>
            `;
        }
    }

    // ==========================================
    // SATIŞ İADE İŞLEMİ
    // ==========================================
    async function refundSale(saleId) {
        // 1. İade işlemini veritabanında gerçekleştir
        try {
            const response = await fetch(`/api/sales/${saleId}/refund`, {
                method: "POST"
            });

            const result = await response.json();

            if (!response.ok || !result.success) {
                throw new Error(
                    result.message || "İade işlemi başarısız."
                );
            }

        } catch (error) {
            console.error("Satış iade hatası:", error);
            throw error;
        }

        // 2. Başarılı iade sonrasında arayüzü güncelle
        try {
            await refreshProductsTable();

            populateSaleProducts();

            await loadSalesHistory();

            await updateDashboardTotalSales();

            await loadDailySalesReport();

        } catch (error) {
            console.error("İade sonrası güncelleme hatası:", error);

            setTimeout(function () {
                showToast(
                    "İade kaydedildi ancak ekran güncellenemedi. Sayfayı yenileyin.",
                    "error"
                );
            }, 500);
        }

        return true;
    }


    async function updateDashboardTotalSales() {
        const totalElement =
            document.getElementById("dashboardTotalSales");

        if (!totalElement) {
            console.warn("Dashboard satış elemanı bulunamadı!");
            return;
        }

        const salesPeriodSelect = document.getElementById("salesPeriodSelect");

        if (salesPeriodSelect && !salesPeriodSelect.dataset.listenerAdded) {
            salesPeriodSelect.addEventListener("change", function () {
                updateDashboardTotalSales();
            });

            salesPeriodSelect.dataset.listenerAdded = "true";
        }


        try {
            const response = await fetch("/api/sales");
            const result = await response.json();

            if (!response.ok || !result.success) {
                throw new Error("Satış verileri alınamadı.");
            }

            const periodSelect = document.getElementById("salesPeriodSelect");
            const selectedPeriod = periodSelect ? periodSelect.value : "year";

            const now = new Date();
            const currentYear = now.getFullYear();
            const currentMonth = now.getMonth() + 1;

            // DASHBOARD - SON 5 SATIŞ
            const recentSalesBody = document.getElementById("dashboardRecentSales");

            if (recentSalesBody) {
                recentSalesBody.innerHTML = "";

                const recentSales = result.sales.slice(0, 5);

                if (recentSales.length === 0) {
                    const row = recentSalesBody.insertRow();
                    const cell = row.insertCell();
                    cell.colSpan = 6;
                    cell.textContent = "Henüz satış kaydı bulunmuyor.";
                } else {
                    recentSales.forEach((sale) => {
                        const row = recentSalesBody.insertRow();

                        const addCell = (value) => {
                            const cell = row.insertCell();
                            cell.textContent = value;
                            return cell;
                        };

                        addCell(sale.product_name || "Bilinmeyen ürün");
                        addCell(sale.barcode || "—");
                        addCell(sale.quantity);
                        addCell(Number(sale.total_price || 0).toLocaleString("tr-TR", {
                            style: "currency",
                            currency: "TRY"
                        }));
                        addCell(
                            sale.sale_date
                                ? sale.sale_date.slice(0, 16).replace(
                                    /^(\d{4})-(\d{2})-(\d{2}) (\d{2}:\d{2})$/,
                                    "$3.$2.$1 $4"
                                )
                                : "—"
                        );
                        addCell(sale.status === "refunded" ? "İade Edildi" : "Tamamlandı");
                    });
                }
            }


            // İade edilmeyen satışları ayır
            const completedSales = result.sales.filter(
                sale => sale.status === "completed"
            );

            // Dashboard toplam satış tutarı
            const totalSales = completedSales.reduce(
                (total, sale) => total + Number(sale.total_price || 0),
                0
            );

            // Seçilen dönemin satışları: Satış Raporu için
            const filteredSales = completedSales.filter((sale) => {
                const saleYear = Number(sale.sale_date.slice(0, 4));
                const saleMonth = Number(sale.sale_date.slice(5, 7));

                return saleYear === currentYear &&
                    (selectedPeriod === "year" || saleMonth === currentMonth);
            });

            const reportTotal = filteredSales.reduce(
                (total, sale) => total + Number(sale.total_price || 0),
                0
            );

            // SATIŞ ÖZETİ - Gerçek veriler
            const todaySalesElement = document.getElementById("todaySalesTotal");
            const lastWeekSalesElement = document.getElementById("lastWeekSalesTotal");

            const today = new Date();
            const todayString = [
                today.getFullYear(),
                String(today.getMonth() + 1).padStart(2, "0"),
                String(today.getDate()).padStart(2, "0")
            ].join("-");


            // Bugünkü satışlar (iadeler hariç)
            const todaySales = completedSales
                .filter(sale => sale.sale_date.slice(0, 10) === todayString)
                .reduce(
                    (sum, sale) => sum + Number(sale.total_price || 0),
                    0
                );
            // Geçen takvim haftası: Pazartesi - Pazar
            const thisMonday = new Date(
                today.getFullYear(), today.getMonth(), today.getDate()
            );
            const dayOfWeek = (thisMonday.getDay() + 6) % 7;
            thisMonday.setDate(thisMonday.getDate() - dayOfWeek);

            const lastMonday = new Date(thisMonday);
            lastMonday.setDate(lastMonday.getDate() - 7);


            const lastWeekSales = completedSales

                .filter(sale => {
                    const [year, month, day] = sale.sale_date
                        .slice(0, 10)
                        .split("-")
                        .map(Number);

                    const saleDate = new Date(year, month - 1, day);

                    return saleDate >= lastMonday && saleDate < thisMonday;
                })
                .reduce((sum, sale) => sum + Number(sale.total_price || 0), 0);

            if (todaySalesElement) {
                todaySalesElement.textContent = todaySales.toLocaleString("tr-TR", {
                    style: "currency",
                    currency: "TRY"
                });
            }

            if (lastWeekSalesElement) {
                lastWeekSalesElement.textContent = lastWeekSales.toLocaleString("tr-TR", {
                    style: "currency",
                    currency: "TRY"
                });
            }


            const salesChart = document.getElementById("salesChart");

            if (salesChart) {
                const monthNames = [
                    "Oca", "Şub", "Mar", "Nis", "May", "Haz",
                    "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"
                ];

                const periods = selectedPeriod === "year"
                    ? monthNames.map((name, index) => ({
                        label: name,
                        number: index + 1
                    }))
                    : Array.from(
                        { length: new Date(currentYear, currentMonth, 0).getDate() },
                        (_, index) => ({
                            label: String(index + 1),
                            number: index + 1
                        })
                    );

                const totals = periods.map((period) => {
                    return filteredSales.reduce((sum, sale) => {
                        const saleMonth = Number(sale.sale_date.slice(5, 7));
                        const saleDay = Number(sale.sale_date.slice(8, 10));

                        const matches = selectedPeriod === "year"
                            ? saleMonth === period.number
                            : saleDay === period.number;

                        return matches
                            ? sum + Number(sale.total_price || 0)
                            : sum;
                    }, 0);
                });

                const maxTotal = Math.max(...totals, 1);

                salesChart.innerHTML = periods.map((period, index) => {
                    const amount = totals[index];
                    const height = amount > 0
                        ? Math.max((amount / maxTotal) * 100, 4)
                        : 0;

                    return `
            <div class="chart-bar" title="${period.label}: ${amount.toLocaleString("tr-TR", {
                        style: "currency",
                        currency: "TRY"
                    })}">
                <div class="bar-stack">
                    <div class="bar-sales" style="height: ${height}%;"></div>
                </div>
                <span>${period.label}</span>
            </div>
        `;
                }).join("");
            }

            // Satış Raporu - gerçek satış toplamı
            const reportTotalElement = document.getElementById("salesReportTotal");
            const monthlyAverageElement = document.getElementById("salesReportMonthlyAverage");

            if (reportTotalElement) {
                reportTotalElement.textContent = reportTotal.toLocaleString("tr-TR", {
                    style: "currency",
                    currency: "TRY"
                });
            }

            if (monthlyAverageElement) {
                const monthlyAverage = selectedPeriod === "year"
                    ? reportTotal / currentMonth
                    : reportTotal;

                monthlyAverageElement.textContent = monthlyAverage.toLocaleString("tr-TR", {
                    style: "currency",
                    currency: "TRY"
                });
            }


            totalElement.textContent =
                totalSales.toLocaleString("tr-TR", {
                    style: "currency",
                    currency: "TRY"
                });


        } catch (error) {
            console.error("Dashboard satış hatası:", error);
            totalElement.textContent = "—";

            const recentSalesBody = document.getElementById("dashboardRecentSales");

            if (recentSalesBody) {
                recentSalesBody.innerHTML = "";

                const row = recentSalesBody.insertRow();
                const cell = row.insertCell();

                cell.colSpan = 6;
                cell.textContent = "Satış verileri yüklenemedi. Lütfen tekrar deneyin.";
            }
        }

    }

    // Satışı tamamla ve SQLite veritabanına kaydet.
    mainContent.addEventListener("submit", async function (event) {
        if (event.target.id !== "salesForm") return;

        event.preventDefault();

        const select = document.getElementById("saleProduct");
        const quantityInput = document.getElementById("saleQuantity");
        const message = document.getElementById("saleMessage");
        const submitButton = event.target.querySelector('button[type="submit"]');

        const barcode = select.value;
        const quantity = Number(quantityInput.value);

        if (!barcode || !Number.isInteger(quantity) || quantity < 1) {
            message.textContent = "Lütfen ürün ve geçerli bir miktar seçin.";
            return;
        }

        const rows = document.querySelectorAll("#productsTableBody tr");
        let selectedRow = null;

        rows.forEach(function (row) {
            if (row.cells[0]?.textContent.trim() === barcode) {
                selectedRow = row;
            }
        });

        if (!selectedRow) {
            message.textContent = "Ürün tablosunda bulunamadı.";
            return;
        }

        const productId = Number(selectedRow.dataset.productId);

        if (!Number.isInteger(productId) || productId < 1) {
            message.textContent = "Ürün ID bilgisi bulunamadı.";
            return;
        }

        const currentStock = Number(selectedRow.cells[2].textContent.trim());

        if (quantity > currentStock) {
            message.textContent =
                "Yetersiz stok! Mevcut stok: " + currentStock;
            return;
        }

        // Satış için seçilen müşteriyi al
        const customerSelect = document.getElementById("saleCustomer");

        const customerId = customerSelect && customerSelect.value !== ""
            ? Number(customerSelect.value)
            : null;

        // Aynı satışın iki kez gönderilmesini önle.
        if (submitButton) submitButton.disabled = true;
        message.textContent = "Satış kaydediliyor...";

        try {
            const response = await fetch("/api/sales", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    product_id: productId,
                    quantity: quantity,
                    customer_id: customerId
                })
            });

            const result = await response.json();

            if (!response.ok || !result.success) {
                message.textContent =
                    result.message || "Satış kaydedilemedi.";
                return;
            }

            // Stok yalnızca API başarılı olduktan sonra değişir.
            const newStock = Number(result.remaining_stock);
            selectedRow.cells[2].textContent = newStock;

            const stockBadge =
                selectedRow.cells[5]?.querySelector(".stock-status");


            if (stockBadge) {

                const settings = getPharmacySettings();



                const criticalLimit = Number(settings.criticalStockLimit);


                stockBadge.className = "stock-status";

                if (newStock === 0) {
                    stockBadge.classList.add("stock-critical");
                    stockBadge.textContent = "Stok Tükendi";
                } else if (newStock <= criticalLimit) {
                    stockBadge.classList.add("stock-critical");
                    stockBadge.textContent = "Kritik stok";
                } else if (newStock <= criticalLimit + 5) {
                    stockBadge.classList.add("stock-low");
                    stockBadge.textContent = "Azalan stok";
                } else {
                    stockBadge.classList.add("stock-normal");
                    stockBadge.textContent = "Normal";
                }
            }

            message.textContent =
                "Satış başarıyla kaydedildi! Satış No: " +
                result.sale_id +
                " | Kalan stok: " + newStock;

            updateDashboardStats();
            checkCriticalStock();
            populateSaleProducts();
            loadSalesHistory();
            loadDailySalesReport();


            select.value = "";
            quantityInput.value = "1";

            if (customerSelect) {
                customerSelect.value = "";
            }

            updateSaleSummary();
        } catch (error) {
            console.error("Satış hatası:", error);
            message.textContent =
                "Sunucuya bağlanılamadı. Satış durumunu kontrol edin.";
        } finally {
            if (submitButton) submitButton.disabled = false;
        }
    });

    // ==========================================
    // SATIŞ EKRANINA MÜŞTERİLERİ YÜKLE
    // ==========================================
    async function loadSaleCustomers() {
        const customerSelect = document.getElementById("saleCustomer");

        if (!customerSelect) return;

        try {
            const response = await fetch("/api/customers");
            const result = await response.json();

            if (!response.ok || !result.success) {
                throw new Error(result.message || "Müşteriler yüklenemedi.");
            }

            const selectedCustomerId = customerSelect.value;

            customerSelect.innerHTML = "";

            customerSelect.add(new Option("Müşterisiz Satış", ""));

            result.customers.forEach(customer => {
                customerSelect.add(
                    new Option(
                        `${customer.name} - ${customer.phone}`,
                        String(customer.id)
                    )
                );
            });

            customerSelect.value = selectedCustomerId;

            if (customerSelect.selectedIndex === -1) {
                customerSelect.value = "";
            }

        } catch (error) {
            console.error("Satış müşteri yükleme hatası:", error);

            customerSelect.innerHTML = "";
            customerSelect.add(new Option("Müşteriler yüklenemedi", ""));
            customerSelect.disabled = true;
        }
    }

    // ==============================
    // MÜŞTERİ YÖNETİMİ
    // ==============================

    let customers = [];

    function renderCustomers(searchText = "") {
        const tbody = document.getElementById("customersTableBody");
        const count = document.getElementById("customerCount");
        const total = document.getElementById("totalCustomersCount");

        if (!tbody || !count || !total) return;

        const term = searchText.toLocaleLowerCase("tr-TR");

        const filtered = customers.filter(customer =>
            `${customer.name} ${customer.phone} ${customer.email}`
                .toLocaleLowerCase("tr-TR")
                .includes(term)
        );

        total.textContent = customers.length;
        count.textContent = `${filtered.length} müşteri`;

        if (filtered.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="4" class="no-products">
                        ${customers.length === 0
                    ? "Henüz müşteri kaydı bulunmuyor."
                    : "Aramanızla eşleşen müşteri bulunamadı."}
                    </td>
                </tr>
            `;
            return;
        }

        tbody.innerHTML = filtered.map(customer => `
            <tr>
                <td>${escapeCustomerText(customer.name)}</td>
                <td>${escapeCustomerText(customer.phone)}</td>
                <td>${escapeCustomerText(customer.email || "-")}</td>
               
       <td>
    
                <div class="customer-action-buttons">

                    <button
                        type="button"
                        class="customer-history-btn"
                        data-customer-id="${customer.id}">
                        Satış Geçmişi
                    </button>

                    <button
                        type="button"
                        class="edit-customer-btn"
                        data-customer-id="${customer.id}">
                        Düzenle
                    </button>

                    <button
                        type="button"
                        class="delete-customer-btn"
                        data-customer-id="${customer.id}">
                        Sil
                    </button>

                </div>

      </td>
           </tr>
        `).join("");
    }

    function escapeCustomerText(value) {
        return String(value).replace(/[&<>"']/g, char => ({
            "&": "&amp;",
            "<": "&lt;",
            ">": "&gt;",
            '"': "&quot;",
            "'": "&#39;"
        })[char]);
    }



    async function setupCustomerPage() {
        const addButton = document.getElementById("addCustomerBtn");
        const searchInput = document.getElementById("customerSearch");
        const tbody = document.getElementById("customersTableBody");

        const modal = document.getElementById("customerModal");
        const form = document.getElementById("customerForm");
        const closeButton = document.getElementById("closeCustomerModal");
        const cancelButton = document.getElementById("cancelCustomerModal");
        const saveButton = document.getElementById("saveCustomerBtn");
        const message = document.getElementById("customerFormMessage");

        const deleteModal = document.getElementById("customerDeleteModal");
        const deleteCustomerName = document.getElementById("deleteCustomerName");
        const cancelDeleteButton = document.getElementById("cancelCustomerDelete");
        const confirmDeleteButton = document.getElementById("confirmCustomerDelete");
        const deleteMessage = document.getElementById("customerDeleteMessage");

        let customerToDeleteId = null;
        let editingCustomerId = null;


        async function openCustomerHistory(customerId) {
            const historyModal = document.getElementById("customerHistoryModal");
            const historyName = document.getElementById("customerHistoryName");
            const historyBody = document.getElementById("customerHistoryTableBody");
            const historyTotal = document.getElementById("customerHistoryTotal");
            const closeHistoryButton = document.getElementById("closeCustomerHistoryModal");

            const customer = customers.find(
                item => Number(item.id) === Number(customerId)
            );

            if (!historyModal || !historyName || !historyBody ||
                !historyTotal || !closeHistoryButton || !customer) {
                return;
            }

            historyName.textContent = customer.name;
            historyTotal.textContent = "0,00 TL";
            historyBody.innerHTML = '<tr><td colspan="6">Yükleniyor...</td></tr>';
            historyModal.hidden = false;

            const closeHistory = () => {
                historyModal.hidden = true;
            };

            closeHistoryButton.onclick = closeHistory;

            historyModal.onclick = event => {
                if (event.target === historyModal) closeHistory();
            };

            try {
                const response = await fetch("/api/sales");
                const result = await response.json();

                if (!response.ok || !result.success) {
                    throw new Error(result.message || "Satış geçmişi alınamadı.");
                }

                const customerSales = result.sales.filter(
                    sale => Number(sale.customer_id) === Number(customerId)
                );

                historyBody.innerHTML = "";

                if (customerSales.length === 0) {
                    historyBody.innerHTML =
                        '<tr><td colspan="6">Bu müşterinin henüz satışı yok.</td></tr>';
                    return;
                }

                let total = 0;

                customerSales.forEach(sale => {
                    const row = document.createElement("tr");

                    const isRefunded = sale.status === "refunded";

                    if (!isRefunded) {
                        total += Number(sale.total_price);
                    }

                    const values = [
                        "#" + sale.id,
                        sale.product_name,
                        sale.quantity,
                        Number(sale.total_price).toLocaleString("tr-TR", {
                            minimumFractionDigits: 2
                        }) + " TL",
                        sale.sale_date,
                        isRefunded ? "İade Edildi" : "Tamamlandı"
                    ];

                    values.forEach(value => {
                        const cell = document.createElement("td");
                        cell.textContent = value;
                        row.appendChild(cell);
                    });

                    historyBody.appendChild(row);
                });

                historyTotal.textContent = total.toLocaleString("tr-TR", {
                    minimumFractionDigits: 2,
                    maximumFractionDigits: 2
                }) + " TL";

            } catch (error) {
                console.error("Müşteri satış geçmişi hatası:", error);
                historyBody.innerHTML = "";
                const row = historyBody.insertRow();
                const cell = row.insertCell();
                cell.colSpan = 6;
                cell.textContent = "Satış geçmişi yüklenemedi.";
            }
        }


        if (!addButton || !modal || !form || !tbody ||
            !deleteModal || !deleteCustomerName ||
            !cancelDeleteButton || !confirmDeleteButton || !deleteMessage) {
            console.error("Müşteri sayfasında gerekli HTML elemanları bulunamadı.");
            return;
        }

        if (addButton.dataset.ready === "true") return;
        addButton.dataset.ready = "true";

        // ==========================================
        // MÜŞTERİ EKLEME / DÜZENLEME MODALI
        // ==========================================

        function closeModal() {
            modal.hidden = true;
            editingCustomerId = null;
            form.reset();
            message.textContent = "";
        }

        addButton.addEventListener("click", function () {
            editingCustomerId = null;
            form.reset();
            message.textContent = "";

            modal.querySelector(".customer-modal-header h3").textContent =
                "Yeni Müşteri Ekle";

            saveButton.textContent = "Müşteriyi Kaydet";
            modal.hidden = false;

            document.getElementById("customerName").focus();
        });

        closeButton.addEventListener("click", closeModal);
        cancelButton.addEventListener("click", closeModal);

        modal.addEventListener("click", function (event) {
            if (event.target === modal) {
                closeModal();
            }
        });

        // ==========================================
        // MÜŞTERİ KAYDETME / GÜNCELLEME
        // ==========================================

        form.addEventListener("submit", async function (event) {
            event.preventDefault();

            const customerData = {
                name: document.getElementById("customerName").value.trim(),
                phone: document.getElementById("customerPhone").value.trim(),
                email: document.getElementById("customerEmail").value.trim(),
                notes: document.getElementById("customerNotes").value.trim()
            };

            if (!customerData.name || !customerData.phone) {
                message.textContent = "Ad soyad ve telefon zorunludur.";
                return;
            }

            if (!/^05[0-9]{9}$/.test(customerData.phone)) {
                message.textContent =
                    "Telefon 05 ile başlamalı ve 11 rakam olmalıdır.";
                return;
            }

            const isEditing = editingCustomerId !== null;

            saveButton.disabled = true;
            message.textContent = isEditing
                ? "Müşteri güncelleniyor..."
                : "Müşteri kaydediliyor...";

            try {
                const response = await fetch(
                    isEditing
                        ? `/api/customers/${editingCustomerId}`
                        : "/api/customers",
                    {
                        method: isEditing ? "PUT" : "POST",
                        headers: {
                            "Content-Type": "application/json"
                        },
                        body: JSON.stringify(customerData)
                    }
                );

                const result = await response.json();

                if (!response.ok || !result.success) {
                    throw new Error(
                        result.message || "Müşteri kaydedilemedi."
                    );
                }

                closeModal();
                await loadCustomers();

                showToast(
                    isEditing
                        ? "Müşteri başarıyla güncellendi."
                        : "Müşteri başarıyla eklendi.",
                    "success"
                );

            } catch (error) {
                message.textContent = error.message;

            } finally {
                saveButton.disabled = false;
            }
        });

        // ==========================================
        // MÜŞTERİ ARAMA
        // ==========================================

        searchInput?.addEventListener("input", function () {
            renderCustomers(this.value);
        });

        // ==========================================
        // DÜZENLE VE SİL BUTONLARI
        // ==========================================

        tbody.addEventListener("click", function (event) {
            const historyButton = event.target.closest(".customer-history-btn");
            if (historyButton) {
                const customerId = Number(historyButton.dataset.customerId);

                if (Number.isSafeInteger(customerId) && customerId > 0) {
                    openCustomerHistory(customerId);
                }

                return;
            }


            // DÜZENLE
            const editButton = event.target.closest(".edit-customer-btn");

            if (editButton) {
                const customerId = Number(editButton.dataset.customerId);

                const customer = customers.find(
                    item => Number(item.id) === customerId
                );

                if (!customer) {
                    alert("Müşteri bulunamadı.");
                    return;
                }

                editingCustomerId = customerId;

                document.getElementById("customerName").value =
                    customer.name || "";

                document.getElementById("customerPhone").value =
                    customer.phone || "";

                document.getElementById("customerEmail").value =
                    customer.email || "";

                document.getElementById("customerNotes").value =
                    customer.notes || "";

                modal.querySelector(".customer-modal-header h3").textContent =
                    "Müşteriyi Düzenle";

                saveButton.textContent = "Değişiklikleri Kaydet";
                message.textContent = "";

                modal.hidden = false;
                return;
            }

            // SİL
            const deleteButton = event.target.closest(".delete-customer-btn");

            if (!deleteButton) return;

            const customerId = Number(deleteButton.dataset.customerId);

            if (!Number.isSafeInteger(customerId) || customerId <= 0) {
                alert("Geçersiz müşteri ID.");
                return;
            }

            const customer = customers.find(
                item => Number(item.id) === customerId
            );

            if (!customer) {
                alert("Müşteri bulunamadı.");
                return;
            }

            customerToDeleteId = customerId;
            deleteCustomerName.textContent = customer.name;
            deleteMessage.textContent = "";

            deleteModal.hidden = false;
        });

        // ==========================================
        // MÜŞTERİ SİLME ONAY MODALI
        // ==========================================

        function closeDeleteModal() {
            deleteModal.hidden = true;
            customerToDeleteId = null;
            deleteMessage.textContent = "";
        }

        cancelDeleteButton.addEventListener("click", closeDeleteModal);

        deleteModal.addEventListener("click", function (event) {
            if (event.target === deleteModal &&
                !confirmDeleteButton.disabled) {
                closeDeleteModal();
            }
        });

        confirmDeleteButton.addEventListener("click", async function () {
            if (customerToDeleteId === null) return;

            confirmDeleteButton.disabled = true;
            cancelDeleteButton.disabled = true;
            confirmDeleteButton.textContent = "Siliniyor...";
            deleteMessage.textContent = "";

            try {
                const response = await fetch(
                    `/api/customers/${customerToDeleteId}`,
                    {
                        method: "DELETE"
                    }
                );

                const result = await response.json();

                if (!response.ok || !result.success) {
                    throw new Error(
                        result.message || "Müşteri silinemedi."
                    );
                }
                             closeDeleteModal();
                await loadCustomers();

                showToast(
                    "Müşteri başarıyla silindi.",
                    "success"
                );

            } catch (error) {
                console.error("Müşteri silme hatası:", error);
                deleteMessage.textContent = error.message;

            } finally {
                confirmDeleteButton.disabled = false;
                cancelDeleteButton.disabled = false;
                confirmDeleteButton.textContent = "Evet, Sil";
            }
        });

        // ==========================================
        // MÜŞTERİLERİ VERİTABANINDAN YÜKLE
        // ==========================================

        await loadCustomers();
    }

    // SQLite veritabanından müşterileri getir
    async function loadCustomers() {
        try {
            const response = await fetch("/api/customers");
            const result = await response.json();

            if (!response.ok || !result.success) {
                throw new Error(
                    result.message || "Müşteriler yüklenemedi."
                );
            }

            customers = result.customers;

            const searchInput = document.getElementById("customerSearch");
            renderCustomers(searchInput?.value || "");

        } catch (error) {
            console.error("Müşteri yükleme hatası:", error);

            const tbody = document.getElementById("customersTableBody");
            if (tbody) {
                tbody.innerHTML = `
                <tr>
                    <td colspan="4">
                        Müşteriler yüklenirken hata oluştu.
                    </td>
                </tr>
            `;
            }
        }
    }


    // Sayfa değişimlerinde müşteri ekranını kontrol et
    const customerObserver = new MutationObserver(() => {
        if (document.getElementById("customersTableBody")) {
            setupCustomerPage();
        }
    });

    customerObserver.observe(mainContent, {
        childList: true,
        subtree: true
    });

    // İlk açılışta yalnızca müşteri ekranı mevcutsa çalıştır
    if (document.getElementById("customersTableBody")) {
        setupCustomerPage();
    }


    // ==============================
    // ANALİZ RAPORLARINI GÜNCELLE
    // ==============================

    function updateAnalyticsReport() {
        const tbody = productsContainer.querySelector("#productsTableBody");

        if (!tbody) {
            console.error("Ürün tablosu bulunamadı.");
            return;
        }

        // Ayarlardan kayıtlı kritik stok sınırını al
        const settings = getPharmacySettings();

        const criticalLimit = Math.max(
            0,
            Number(settings.criticalStockLimit) || 0
        );

        const lowLimit = criticalLimit + 5;
        const rows = Array.from(tbody.querySelectorAll("tr"))
            .filter(row => row.cells.length >= 8);

        let totalStock = 0;
        let criticalCount = 0;
        let lowCount = 0;
        let normalCount = 0;
        let inventoryValue = 0;
        let expiryWarningCount = 0;

        rows.forEach(function (row) {

            const stock = Number(
                row.cells[2].textContent.trim()
            ) || 0;

            // Ürün fiyatını oku
            const priceText = row.cells[3].textContent
                .replace(/[^\d,.-]/g, "")
                .replace(/\./g, "")
                .replace(",", ".");

            const price = Number(priceText) || 0;

            totalStock += stock;
            inventoryValue += stock * price;

            // Ayarlara göre stok sınıflandırması
            if (stock <= criticalLimit) {
                criticalCount++;
            } else if (stock <= lowLimit) {
                lowCount++;
            } else {
                normalCount++;
            }

            // Mevcut SKT durumunu kontrol et
            const expiryText = row.cells[4].textContent.trim();
            const [day, month, year] = expiryText.split(".");

            const expiryStatus = getExpiryStatus(
                `${year}-${month}-${day}`
            );

            if (expiryStatus.className === "expiry-warning") {
                expiryWarningCount++;
            }
        });

        const totalProducts = rows.length;

        // HTML değerlerini güncelle
        const setText = (id, value) => {
            const element = document.getElementById(id);
            if (element) {
                element.textContent = value;
            }
        };

        setText("reportTotalProducts", totalProducts);
        setText("reportCriticalStock", criticalCount);
        setText(
            "reportCriticalStockDescription",
            `Stoku ${criticalLimit} veya daha az olan ürün`
        );
        setText("reportStockQuantity", totalStock);
        setText("reportExpiryWarning", expiryWarningCount);

        setText("reportNormalCount", normalCount);
        setText("reportLowCount", lowCount);
        setText("reportCriticalCount", criticalCount);

        setText(
            "reportInventoryValue",
            inventoryValue.toLocaleString("tr-TR", {
                style: "currency",
                currency: "TRY"
            })
        );

        setText(
            "reportAverageStock",
            totalProducts
                ? (totalStock / totalProducts).toLocaleString("tr-TR", {
                    maximumFractionDigits: 1
                })
                : "0"
        );

        // Grafik yüzdeleri
        const denominator = totalProducts || 1;

        const setBar = (id, count) => {
            const element = document.getElementById(id);

            if (element) {
                element.style.width =
                    `${(count / denominator) * 100}%`;
            }
        };

        setBar("reportNormalBar", normalCount);
        setBar("reportLowBar", lowCount);
        setBar("reportCriticalBar", criticalCount);

    }
    updateAnalyticsReport();
    showPage("Dashboard");
});

