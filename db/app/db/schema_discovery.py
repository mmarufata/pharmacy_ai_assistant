"""Şema keşfi: yapay zekânın görmesine İZİN VERİLEN şemayı çıkarır.

Kaynak olarak ai_readonly bağlantısının GERÇEKTEN görebildiği nesneler (SQLAlchemy Inspector) kullanılır,
Türkçe açıklamalar ise ai_views.py'den eklenir. Böylece çıktı, gerçek yetkilerle uyumsuz olamaz:
  * Yetki verilmeyen bir görünüm görünürse bile izin listesinde değilse listelenmez.
  * Veritabanında olmayan bir görünüm listelenmez.
"""
from sqlalchemy import Engine, inspect

from app.db.ai_views import AI_SCHEMA_NAME, AI_VIEWS


def discover_ai_schema(engine: Engine) -> dict:
    insp = inspect(engine)
    db_views = set(insp.get_view_names(schema=AI_SCHEMA_NAME))
    tables = []
    for name, meta in AI_VIEWS.items():
        if name not in db_views:
            continue
        described = {c[0]: (c[1], c[2]) for c in meta["columns"]}
        cols = []
        for col in insp.get_columns(name, schema=AI_SCHEMA_NAME):
            if col["name"] not in described:  # izin listesinde olmayan kolon asla gösterilmez
                continue
            cols.append({"name": col["name"], "type": str(col["type"]), "description": described[col["name"]][1]})
        tables.append({"name": name, "description": meta["description"], "columns": cols})
    return {
        "dialect": "postgresql",
        "notes": [
            "Yalnızca SELECT sorgularına izin verilir; tablo adlarını şema öneki olmadan yazın.",
            "Tutarlar TL cinsindendir. Satış analizlerinde genelde sales.status = 'completed' filtresi kullanılır.",
            "Her sorguya en fazla satır limiti otomatik uygulanır.",
        ],
        "tables": tables,
    }


def describe_table(engine: Engine, table_name: str) -> dict | None:
    """İzin verilmeyen veya olmayan tablo için None döner (varlık bilgisi sızdırılmaz)."""
    if not isinstance(table_name, str):
        return None
    wanted = table_name.strip().lower()
    for t in discover_ai_schema(engine)["tables"]:
        if t["name"] == wanted:
            return t
    return None
