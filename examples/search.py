from mcp_run import Client  # Import the mcp.run client

client = Client()  # Create the client, this will check the
# default location for the mcp.run config or
# the `MCP_RUN_SESSION_ID` env var can be used
# to specify a valid mcp.run session id

results = client.search("fetch")  # Search for servlets that mention the
# word "fetch"

# Iterate through results and print the slug
for result in results:
    print(result["slug"])
