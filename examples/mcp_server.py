import util  # noqa: F401
import mcp_run

mcp = mcp_run.MCPServer(name="example")


# @mcp.tool()
# def add_two_numbers(a: int, b: int) -> int:
#     return a + b


mcp.settings.port = 9999
mcp.run("sse")
