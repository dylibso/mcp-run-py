from typing import Any, Dict
from dataclasses import dataclass
from contextlib import asynccontextmanager

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.tools import Tool

from mcp.client.session import ClientSession
from mcp.client.sse import sse_client
from mcp.client.stdio import stdio_client, StdioServerParameters

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
class MCPClientConfig:
    sse_url: str | None = None
    sse_headers: Dict[str, Any] | None = None
    sse_timeout: float = 5
    sse_read_timeout: float = 60 * 5
    stdio_cwd: str | None = None
    stdio_env: Dict[str, str] | None = None


class MCPClient:
    client: Client
    config: MCPClientConfig

    def __init__(
        self, config: MCPClientConfig | None = None, client: Client | None = None
    ):
        self.config = config or MCPClientConfig()
        self.client = client or Client()

    @asynccontextmanager
    async def _run_session(self, read, write):
        async with ClientSession(
            read,
            write,
        ) as session:
            await session.initialize()
            yield session

    @asynccontextmanager
    async def run_sse(self):
        async with sse_client(
            self.config.sse_url,
            headers=self.config.sse_headers,
            timeout=self.config.sse_timeout,
            sse_read_timeout=self.config.sse_read_timeout,
        ) as (read, write):
            async with self._run_session(read, write) as session:
                yield session

    @asynccontextmanager
    async def run_stdio(self):
        async with stdio_client(
            server=StdioServerParameters(
                command="npx",
                args=["--yes", "@dylibso/mcpx"],
                cwd=self.config.stdio_cwd,
                env=self.config.stdio_env,
            )
        ) as (read, write):
            async with self._run_session(read, write) as session:
                yield session

    @asynccontextmanager
    async def run(self):
        if self.config.sse_url is not None:
            async with self.run_sse() as c:
                yield c
        else:
            async with self.run_stdio() as c:
                yield c
