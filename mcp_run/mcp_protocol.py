from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.tools import Tool

from .client import Client


class MCPServer(FastMCP):
    client: Client

    def __init__(self, client: Client | None = None, **kw):
        self.client = client or Client()
        super().__init__(**kw)
        self.update_tools()

    async def list_tools(self) -> list:
        self.update_tools()
        return await super().list_tools()

    async def call_tool(self, name: str, arguments: dict[str, Any]):
        return await super().call_tool(name, arguments)

    def update_tools(self):
        for t in self.client.tools.values():
            fn = self.client._make_pydantic_function(t)
            self._tool_manager._tools[t.name] = Tool.from_function(
                fn=fn,
                name=t.name,
                description=t.description,
            )
