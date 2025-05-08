import util  # noqa: F401
from mcp_run import Client  # Import the mcp.run client

import asyncio


async def run():
    client = Client()

    async with client.mcp_stdio().connect() as session:
        results = await session.call_tool(
            "eval-js_eval-js", arguments={"code": "'Hello, world!'"}
        )

        # Iterate over the results
        for content in results.content:
            print(content.text)


asyncio.run(run())
