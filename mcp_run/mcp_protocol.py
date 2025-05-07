from typing import Any, Dict, TextIO
from dataclasses import dataclass

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.tools import Tool
from mcp.client.sse import sse_client
from mcp.client.stdio import stdio_client, StdioServerParameters as StdioClientConfig
from mcp import ClientSession
import os
from contextlib import asynccontextmanager


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


@dataclass
class SSEClientConfig:
    url: str

    headers: Dict[str, Any] | None = None

    timeout: float = 5

    sse_read_timeout: float = 60 * 5


DEVNULL = open(os.devnull, "wb")


@dataclass
class MCPClient:
    config: StdioClientConfig | SSEClientConfig
    session: ClientSession | None = None
    errlog: TextIO = DEVNULL

    @property
    def is_sse(self) -> bool:
        return isinstance(self.config, SSEClientConfig)

    @property
    def is_stdio(self) -> bool:
        return isinstance(self.config, StdioClientConfig)

    @asynccontextmanager
    async def connect(self):
        self.errlog = self.errlog or open(os.devnull)
        if isinstance(self.config, SSEClientConfig):
            async with sse_client(
                self.config.url,
                headers=self.config.headers,
                timeout=self.config.timeout,
                sse_read_timeout=self.config.sse_read_timeout,
            ) as (read, write):
                try:
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        self.session = session
                        yield session
                finally:
                    self.session = None
        elif isinstance(self.config, StdioClientConfig):
            async with stdio_client(self.config, errlog=self.errlog) as (read, write):
                try:
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        self.session = session
                        yield session
                finally:
                    self.session = None
