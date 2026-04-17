import asyncio
from pathlib import Path

from ideahub_mcp.server import build_server


def test_build_server_registers_ten_tools(tmp_home: Path) -> None:
    s = build_server()
    tools = asyncio.run(s.list_tools())
    names = {t.name for t in tools}
    assert names == {
        "capture", "dump", "search", "list", "get",
        "related", "annotate", "archive", "link", "recognize",
    }
