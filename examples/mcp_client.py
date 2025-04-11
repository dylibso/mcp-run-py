import asyncio
import util  # noqa: F401
import mcp_run

mcp = mcp_run.MCPClient()


async def main():
    async with mcp.run() as session:
        print(session)
        tools = await session.list_tools()
        for tool in tools.tools:
            print(tool.name)
        res = await session.call_tool("eval-py_eval-py", {"code": "print(123)"})
        print(res)


asyncio.run(main())
