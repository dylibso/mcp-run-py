import util  # noqa: F401
from mcp_run import Client  # Import the mcp.run client

import asyncio


async def run():
    client = Client()

    tool = client.tools["eval-js"]

    plugin = client.plugin(tool)
    results = plugin.call({"code": "'Hello, world!'"})

    for content in results:
        print(content["text"])


asyncio.run(run())
