"""MCP sunucusu testleri: araç kaydı ve gerçek stdio protokolü üzerinden uçtan uca çağrı."""
import asyncio
import json
import os
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.db

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_TOOLS = {"get_database_schema", "get_table_info", "execute_readonly_sql", "get_database_statistics"}


def test_server_exposes_exactly_the_four_tools(db):
    from app.mcp_server.server import mcp
    tools = asyncio.run(mcp.list_tools())
    assert {t.name for t in tools} == EXPECTED_TOOLS   # fazladan (örn. 'run_any_sql') araç yok


def test_every_tool_has_a_description(db):
    from app.mcp_server.server import mcp
    for t in asyncio.run(mcp.list_tools()):
        assert t.description and len(t.description) > 20


def _stdio_call(tool, args):
    """Sunucuyu ayrı süreç olarak başlatıp gerçek MCP istemcisiyle çağırır."""
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    params = StdioServerParameters(
        command=sys.executable, args=["-m", "app.mcp_server.server"], cwd=str(ROOT),
        env={**os.environ, "PYTHONPATH": str(ROOT)},
    )

    async def go():
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                listed = await session.list_tools()
                result = await session.call_tool(tool, args) if tool else None
                return {t.name for t in listed.tools}, result

    return asyncio.run(asyncio.wait_for(go(), timeout=60))


def _payload(result):
    if getattr(result, "structuredContent", None):
        sc = result.structuredContent
        return sc.get("result", sc)
    return json.loads(result.content[0].text)


def test_stdio_end_to_end_valid_query(db):
    names, result = _stdio_call("execute_readonly_sql", {"sql": "SELECT name FROM products ORDER BY name LIMIT 2"})
    assert names == EXPECTED_TOOLS
    data = _payload(result)
    assert data["status"] == "ok" and data["row_count"] == 2


def test_stdio_end_to_end_blocked_query(db):
    _, result = _stdio_call("execute_readonly_sql", {"sql": "DROP TABLE products"})
    data = _payload(result)
    assert data["status"] == "rejected" and data["code"] == "FORBIDDEN_STATEMENT"


def test_stdio_schema_tool(db):
    _, result = _stdio_call("get_database_schema", {})
    data = _payload(result)
    assert data["status"] == "ok" and len(data["tables"]) == 8
