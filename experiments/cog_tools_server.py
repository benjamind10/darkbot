"""
Standalone MCP stdio server exposing two DarkBot tools:
  - list_cogs   : list all cog files in bot/cogs/
  - count_lines : count lines in a given cog file

Started automatically by the Agent SDK as a subprocess.
Not meant to be run directly.
"""

import asyncio
from pathlib import Path

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

COGS_DIR = Path(__file__).parent.parent / "bot" / "cogs"

app = Server("darkbot-cog-tools")


@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="list_cogs",
            description="List all cog (.py) files in bot/cogs/.",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="count_lines",
            description="Count lines in a cog file under bot/cogs/.",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "e.g. 'Music.py'"}
                },
                "required": ["filename"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "list_cogs":
        if not COGS_DIR.exists():
            text = "bot/cogs directory not found"
        else:
            text = "\n".join(sorted(f.name for f in COGS_DIR.glob("*.py")))
        return [TextContent(type="text", text=text)]

    if name == "count_lines":
        filename = arguments.get("filename", "")
        path = COGS_DIR / filename
        if not path.exists():
            return [TextContent(type="text", text=f"File not found: {filename}")]
        count = len(path.read_text(encoding="utf-8").splitlines())
        return [TextContent(type="text", text=f"{filename}: {count} lines")]

    return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def main() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
