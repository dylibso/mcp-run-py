import util
from mcp_run import Client  # Import the mcp.run client

client = Client()  # Create the client, this will check the
# default location for the mcp.run config or
# the `MCP_RUN_SESSION_ID` env var can be used
# to specify a valid mcp.run session id

# Get dylibso/featured profile
featured = client.profiles["dylibso"]["featured"]

# List installs
for install in featured.list_installs():
    print(install)

