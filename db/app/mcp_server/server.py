"""MCP sunucusu (stdio). LLM uygulaması bu araçlar dışında veritabanına erişemez.

Çalıştırma (genelde bir MCP istemcisi tarafından başlatılır):  python -m app.mcp_server.server
ÖNEMLİ: stdio sunucuları stdout'a yazmamalıdır (protokol bozulur); loglar stderr'e gider.

Not (FR-04.8): Kullanıcı bazlı yetkilendirme Flask katmanında yapılır; Flask doğrulanmış user_id'yi
araçlara iletir. Bu sunucu, aldığı user_id'yi yalnızca denetim kaydı için kullanır.
"""
import logging
import sys

from mcp.server.fastmcp import FastMCP

from app.mcp_server import tools

logging.basicConfig(stream=sys.stderr, level=logging.INFO)

mcp = FastMCP("pharmacy-assistant-db")


@mcp.tool()
def get_database_schema(user_id: int | None = None) -> dict:
    """Yapay zekânın erişmesine izin verilen veritabanı şemasını (görünümler, sütunlar, Türkçe açıklamalar) döndürür."""
    return tools.get_database_schema(user_id)


@mcp.tool()
def get_table_info(table_name: str, user_id: int | None = None) -> dict:
    """İzin verilen tek bir tablonun (görünümün) sütunlarını ve açıklamalarını döndürür."""
    return tools.get_table_info(table_name, user_id)


@mcp.tool()
def execute_readonly_sql(sql: str, user_id: int | None = None) -> dict:
    """Tek bir salt okunur PostgreSQL SELECT sorgusunu güvenlik kontrolünden geçirip çalıştırır.
    Sonuç satır sayısı sınırlıdır; izin verilmeyen sorgular reddedilir."""
    return tools.execute_readonly_sql(sql, user_id)


@mcp.tool()
def get_database_statistics(user_id: int | None = None) -> dict:
    """İzin verilen görünümler için genel istatistikleri (satır sayıları, satış tarih aralığı, kritik stok sayısı) döndürür."""
    return tools.get_database_statistics(user_id)


if __name__ == "__main__":
    mcp.run(transport="stdio")
