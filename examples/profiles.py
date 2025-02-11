import util  # noqa: F401
from mcp_run import Client  # Import the mcp.run client

client = Client()  # Create the client, this will check the
# default location for the mcp.run config or
# the `MCP_RUN_SESSION_ID` env var can be used
# to specify a valid mcp.run session id

# Get dylibso/featured profile
featured = client.profiles["dylibso"]["featured"]

# List installs
print("Featured servlets:")
for install in featured.list_installs():
    print(f"  {install.slug}")

# Create a new profile
print("Creating python-test-profile")
profile = client.create_profile(
    "python-test-profile", description="this is a test", set_current=True
)

# Search for servlets
print("Searching for servlets to evaluate JavaScript code")
r = list(client.search("evaluate javascript"))
print(f"Found {r[0].slug}")

# Install evaljs
print(f"Installing {r[0].slug}")
client.install(r[0], name="evaljs")

# List installed servlets and uninstall them
p = client.profiles["~"]["python-test-profile"]
for install in p.list_installs():
    print("Uninstalling", install.slug)
    client.uninstall(install)

# Delete the profile
print("Deleting python-test-profile")
client.delete_profile(profile)
