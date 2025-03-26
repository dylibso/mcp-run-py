import util  # noqa: F401
import mcp_run

client = mcp_run.Client()
mcp = mcp_run.mcp_server(client=client, name="example")
mcp.settings.port = "9999"
mcp.run("sse")
