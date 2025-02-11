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

# Create a new profile
profile = client.create_profile("python-test-profile", description="this is a test")

# Update the current profile to the newly created `python-test-profile`
client.set_profile("python-test-profile")

# Search for servlets
r = list(client.search("evaluate javascript"))

# Install
client.install(r[0], name="evaljs")

# List installs
p = client.profiles["~"]["python-test-profile"]
for install in p.list_installs():
    print("python-test-profile", install)

# Uninstall
client.uninstall("evaljs")

# Delete the profile
client.delete_profile(profile)
