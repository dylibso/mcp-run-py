# mcp-run
[![PyPI](https://img.shields.io/pypi/v/mcp-run)](https://pypi.org/project/mcp-run/)


A Python client for https://www.mcp.run

## Dependencies

- `uv`
- `npm`

## mcp.run Setup

You will need to get an mcp.run session ID by running:

```bash
npx --yes -p @dylibso/mcpx gen-session --write
```

This will generate a new session and write the session ID to a configuration file that can be used
by `mcp-run`.
 
If you need to store the session ID in  an environment variable you can run `gen-session`
without the `--write` flag:

```bash
npx --yes -p @dylibso/mcpx gen-session
```

which should output something like:

```
Login successful!
Session: kabA7w6qH58H7kKOQ5su4v3bX_CeFn4k.Y4l/s/9dQwkjv9r8t/xZFjsn2fkLzf+tkve89P1vKhQ
```

Then set the `MPC_RUN_SESSION_ID` environment variable:

```
$ export MCP_RUN_SESSION_ID=kabA7w6qH58H7kKOQ5su4v3bX_CeFn4k.Y4l/s/9dQwkjv9r8t/xZFjsn2fkLzf+tkve89P1vKhQ
```

## Python Usage

### Installation

Using `uv`:

```bash
uv add mcp-run
```

Or `pip`:

```bash
pip install mcp-run
```

### Example code

```python
from mcp_run import Client  # Import the mcp.run client

client = Client()  # Create the client, this will check the
# default location for the mcp.run config or
# the `MCP_RUN_SESSION_ID` env var can be used
# to specify a valid mcp.run session id

# Call a tool with the given input
results = client.call_tool("eval-js", params={"code": "'Hello, world!'"})

# Iterate over the results
for content in results.content:
    print(content.text)
```

More examples can be found in the [examples/](https://github.com/dylibso/mcp-run-py/tree/main/examples) directory
