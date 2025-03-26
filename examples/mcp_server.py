import util  # noqa: F401
import mcp_run

mcp = mcp_run.MCPServer(name="example")
mcp.settings.port = "9999"
mcp.run("sse")
