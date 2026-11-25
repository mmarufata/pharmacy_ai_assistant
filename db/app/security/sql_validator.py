"""LLM tarafından üretilen SQL için yapısal güvenlik doğrulaması (SQLGlot AST tabanlı).

Bu katman, veritabanı izinlerinin (ai_readonly rolü + yalnızca 'ai' görünümleri) YERİNE değil, onlarla BİRLİKTE çalışır:
  1. Bu doğrulayıcı  : kötü niyetli/hatalı yapıyı çalıştırmadan reddeder, LIMIT ekler.
  2. Veritabanı rolü : doğrulayıcı atlatılsa bile yazma/DDL/izinsiz tablo erişimini engeller.

Kural özeti:
  - Tek bir ifade; kökü SELECT (veya UNION/INTERSECT/EXCEPT) olmalı
  - Ağaçta INSERT/UPDATE/DELETE/DDL/COPY/SET/INTO/FOR UPDATE/LATERAL/UNNEST/parametre yok
  - Yalnızca izin verilen görünümler (şema öneki yoksa veya 'ai'); sistem katalogları yok
  - Kolonlar izin verilen şemaya göre çözümlenir (bilinmeyen kolon reddedilir)
  - Yalnızca izin listesindeki fonksiyonlar (pg_sleep, current_setting, query_to_xml vb. reddedilir)
  - Çalıştırılacak SQL, orijinal metin değil doğrulanmış ağaçtan yeniden üretilir; LIMIT zorlanır
Kullanıcıya dönen mesajlar şema, kimlik bilgisi veya sistem ayrıntısı içermez.
"""
from dataclasses import dataclass

import sqlglot
from sqlglot import exp
from sqlglot.errors import SqlglotError
from sqlglot.optimizer.qualify import qualify

from app.db.ai_views import AI_SCHEMA_NAME, sqlglot_schema

MAX_SQL_LENGTH = 4000
DIALECT = "postgres"

# Türkçe, kullanıcıya gösterilebilir güvenli mesajlar
MESSAGES = {
    "EMPTY": "Sorgu boş.",
    "TOO_LONG": "Sorgu çok uzun.",
    "PARSE_ERROR": "Sorgu anlaşılamadı veya desteklenmeyen bir yapı içeriyor.",
    "MULTIPLE_STATEMENTS": "Yalnızca tek bir sorgu çalıştırılabilir.",
    "NOT_SELECT": "Yalnızca okuma (SELECT) sorgularına izin verilir.",
    "FORBIDDEN_STATEMENT": "Bu sorgu türüne izin verilmez.",
    "FORBIDDEN_CONSTRUCT": "Sorgu izin verilmeyen bir yapı içeriyor.",
    "FORBIDDEN_FUNCTION": "Sorgu izin verilmeyen bir fonksiyon içeriyor.",
    "TABLE_NOT_ALLOWED": "Sorgu erişime izin verilmeyen bir tabloya başvuruyor.",
    "COLUMN_NOT_ALLOWED": "Sorgu bilinmeyen veya erişime izin verilmeyen bir sütuna başvuruyor.",
}

# Ağaçta bulunması durumunda sorguyu reddeden düğüm türleri (sürümlere göre var olanlar alınır)
_FORBIDDEN_NAMES = [
    "Insert", "Update", "Delete", "Merge", "Create", "Drop", "Alter", "AlterTable", "Command", "Set", "SetItem",
    "Copy", "TruncateTable", "Grant", "Revoke", "Into", "Lock", "Transaction", "Commit", "Rollback", "Use",
    "Pragma", "Show", "Describe", "Analyze", "Kill", "Declare", "Call", "Execute", "Attach", "Detach",
    "Comment", "LoadData", "Refresh", "Cache", "Uncache",
    # tablo kontrolünden kaçan kaynaklar
    "Unnest", "Lateral", "Placeholder", "Parameter", "SessionParameter", "Star_",
]
FORBIDDEN_NODES = tuple(getattr(exp, n) for n in _FORBIDDEN_NAMES if hasattr(exp, n))

# Sistem/oturum bilgisi sızdıran, sqlglot'ta ayrı sınıf olan fonksiyonlar
_SYSTEM_INFO_NAMES = ["CurrentVersion", "CurrentUser", "SessionUser", "CurrentDatabase", "CurrentSchema",
                      "CurrentSchemas", "CurrentCatalog"]
SYSTEM_INFO_NODES = tuple(getattr(exp, n) for n in _SYSTEM_INFO_NAMES if hasattr(exp, n))

# sqlglot'un 'anonim' (bilinmeyen) saydığı fonksiyonlardan izin verilenler. Küçük harfle.
ALLOWED_ANONYMOUS_FUNCTIONS = {
    "to_char", "date_part", "age", "string_agg", "array_agg", "btrim", "initcap", "split_part",
    "regexp_replace", "date_bin", "make_date", "to_date", "trunc", "mod", "div", "sign", "sqrt",
}
# İzin listesinde olsa bile her zaman yasak adlar/önekler
FORBIDDEN_FUNCTION_PREFIXES = ("pg_", "lo_", "dblink", "set_config", "current_setting", "query_to_xml",
                               "xpath", "txid_", "version", "current_user", "session_user", "inet_",
                               "has_", "to_regclass")


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    sql: str | None = None       # çalıştırılacak, yeniden üretilmiş SQL (yalnızca ok=True iken)
    code: str | None = None      # hata kodu (loglama için güvenli)
    message: str | None = None   # kullanıcıya gösterilebilir güvenli mesaj

    @staticmethod
    def reject(code: str) -> "ValidationResult":
        return ValidationResult(ok=False, code=code, message=MESSAGES[code])


def _ident_name(ident: exp.Identifier) -> str:
    """Tırnaksız tanımlayıcılar PostgreSQL'de küçük harfe katlanır."""
    return ident.name if ident.args.get("quoted") else ident.name.lower()


def _with_clause(node: exp.Expression):
    """WITH bloğunu döndürür. sqlglot sürümüne göre anahtar 'with' veya 'with_' olabilir."""
    return node.args.get("with_") or node.args.get("with")


def _visible_cte_names(table: exp.Table) -> set[str]:
    """Bu tablo referansının bulunduğu noktada GÖRÜNEN CTE adları (kapsama duyarlı).

    * Bir sorgunun gövdesi, o sorgunun WITH bloğundaki tüm CTE'leri görür.
    * Bir CTE'nin tanımı yalnızca KENDİSİNDEN ÖNCE tanımlanan CTE'leri görür;
      kendini yalnızca WITH RECURSIVE ise görür. Aksi halde 'WITH pg_tables AS (SELECT * FROM pg_tables)'
      gibi bir tanım, içteki gerçek sistem tablosu referansını sahte bir CTE referansı gibi gösterirdi.
    """
    names: set[str] = set()
    prev: exp.Expression = table
    cur = table.parent
    while cur is not None:
        if isinstance(cur, exp.With):
            ctes = list(cur.expressions)
            idx = next((i for i, c in enumerate(ctes) if c is prev), None)
            if idx is not None:
                upto = idx + 1 if cur.args.get("recursive") else idx
                names |= {_ident_name(c.args["alias"].this) for c in ctes[:upto] if c.args.get("alias")}
        else:
            with_clause = _with_clause(cur)
            if with_clause is not None and prev is not with_clause:
                names |= {_ident_name(c.args["alias"].this) for c in with_clause.expressions if c.args.get("alias")}
        prev, cur = cur, cur.parent
    return names


def validate_select_sql(sql: str, max_rows: int = 500) -> ValidationResult:
    if sql is None or not sql.strip():
        return ValidationResult.reject("EMPTY")
    if len(sql) > MAX_SQL_LENGTH:
        return ValidationResult.reject("TOO_LONG")

    # 1) Ayrıştır ve tek ifade olduğunu doğrula
    try:
        statements = [t for t in sqlglot.parse(sql, dialect=DIALECT) if t is not None]
    except SqlglotError:
        return ValidationResult.reject("PARSE_ERROR")
    if len(statements) != 1:
        return ValidationResult.reject("MULTIPLE_STATEMENTS" if len(statements) > 1 else "EMPTY")
    tree = statements[0]

    # 2) Kök yalnızca SELECT / küme işlemi olabilir
    if not isinstance(tree, (exp.Select, exp.Union)):
        return ValidationResult.reject("NOT_SELECT" if isinstance(tree, (exp.Values, exp.Subquery)) else "FORBIDDEN_STATEMENT")

    # 3) Yasak düğümler (gömülü DML, INTO, FOR UPDATE, LATERAL, UNNEST, parametre vb.)
    for node in tree.walk():
        if isinstance(node, FORBIDDEN_NODES):
            return ValidationResult.reject("FORBIDDEN_CONSTRUCT")

    # 4) Fonksiyon izin listesi
    for func in tree.find_all(exp.Func):
        if isinstance(func, SYSTEM_INFO_NODES):
            return ValidationResult.reject("FORBIDDEN_FUNCTION")
        if isinstance(func, exp.Anonymous):
            name = str(func.name).lower()
            if name in ALLOWED_ANONYMOUS_FUNCTIONS and not name.startswith(FORBIDDEN_FUNCTION_PREFIXES):
                continue
            return ValidationResult.reject("FORBIDDEN_FUNCTION")
        # Tipli fonksiyonların SQL adları da yasak öneklere karşı kontrol edilir
        sql_name = (func.sql_name() or "").lower()
        if sql_name.startswith(FORBIDDEN_FUNCTION_PREFIXES):
            return ValidationResult.reject("FORBIDDEN_FUNCTION")

    # 5) Tablo izin listesi
    allowed_views = set(sqlglot_schema())
    for table in tree.find_all(exp.Table):
        if not isinstance(table.this, exp.Identifier):
            return ValidationResult.reject("FORBIDDEN_CONSTRUCT")  # generate_series(...) gibi tablo fonksiyonları
        if table.args.get("catalog"):
            return ValidationResult.reject("TABLE_NOT_ALLOWED")
        db = table.args.get("db")
        if db is not None:
            if _ident_name(db) != AI_SCHEMA_NAME:
                return ValidationResult.reject("TABLE_NOT_ALLOWED")
            table.set("db", None)  # 'ai.products' -> 'products' (search_path zaten 'ai')
        name = _ident_name(table.this)
        if db is None and name in _visible_cte_names(table):
            continue
        if name not in allowed_views:
            return ValidationResult.reject("TABLE_NOT_ALLOWED")

    # 6) Kolon doğrulaması: izin verilen şemaya göre çözümle (bilinmeyen/izinsiz kolon hata verir)
    try:
        qualify(tree.copy(), schema=sqlglot_schema(), dialect=DIALECT, validate_qualify_columns=True)
    except SqlglotError:
        return ValidationResult.reject("COLUMN_NOT_ALLOWED")

    # 7) LIMIT zorla: yoksa ekle, çok büyükse düşür
    limit = tree.args.get("limit")
    current = None
    if limit is not None and isinstance(limit.expression, exp.Literal) and limit.expression.is_int:
        current = int(limit.expression.this)
    if current is None or current > max_rows:
        # max_rows + 1: çalıştırıcı bir fazla satır görürse sonucun KIRPILDIĞINI anlayabilir (truncated bayrağı).
        tree = tree.limit(max_rows + 1, copy=False)

    # 8) Yürütülecek SQL doğrulanmış ağaçtan üretilir (orijinal metin değil)
    return ValidationResult(ok=True, sql=tree.sql(dialect=DIALECT, comments=False))
