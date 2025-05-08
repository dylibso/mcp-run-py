import util  # noqa: F401
import asyncio

from mcp_run import Client


async def run():
    client = Client()
    async with client.mcp_sse().connect() as session:
        res = await session.list_tools()
        for tool in res.tools:
            print(tool.name)


asyncio.run(run())
