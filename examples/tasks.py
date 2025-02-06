from mcp_run import Client  # Import the mcp.run client

client = Client()  # Create the client, this will check the
# default location for the mcp.run config or
# the `MCP_RUN_SESSION_ID` env var can be used
# to specify a valid mcp.run session id

# Create a new task
my_task = client.create_task(
    "my-task", runner="openai", model="gpt-4o", prompt="write a greeting for {{ name }}"
)

# Run it
task_run = my_task.run({"name": "World"})
print(task_run.results())

# Retreive the task
task = client.tasks["my-task"]

# Run it again
task_run = my_task.run({"name": "Bob"})
print(task_run.results())

