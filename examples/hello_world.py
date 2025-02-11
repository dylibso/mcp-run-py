import util  # noqa: F401
from mcp_run import Client  # Import the mcp.run client

client = Client()  # Create the client, this will check the
# default location for the mcp.run config or
# the `MCP_RUN_SESSION_ID` env var can be used
# to specify a valid mcp.run session id

# Call a tool with the given input
results = client.call("eval-js", {"code": "'Hello, world!'"})

# Iterate over the results
for content in results.content:
    print(content.text)
