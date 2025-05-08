from typing import Any, Dict, TextIO
from dataclasses import dataclass
from datetime import timedelta

from mcp.client.sse import sse_client
from mcp.client.stdio import stdio_client, StdioServerParameters as StdioClientConfig
from mcp import ClientSession
import os
import atexit
from contextlib import asynccontextmanager


@dataclass
class SSEClientConfig:
    """
    Configuration for MCP SSE clients
    """

    url: str
    """
    SSE URL
    """

    headers: Dict[str, Any] | None = None
    """
    HTTP request headers for SSE client
    """

    timeout: timedelta | None = None
    """
    Connection timeout
    """

    sse_read_timeout: timedelta | None = None
    """
    Read timeout
    """


DEVNULL = open(os.devnull, "wb")
atexit.register(lambda x: x.close(), DEVNULL)


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
        if self.is_sse:
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
        elif self.is_stdio:
            async with stdio_client(self.config, errlog=self.errlog) as (read, write):
                try:
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        self.session = session
                        yield session
                finally:
                    self.session = None
        else:
            raise ValueError(
                f"Expected either SSEClientConfig or StdioClientConfig but got {type(self.config)}"
            )
