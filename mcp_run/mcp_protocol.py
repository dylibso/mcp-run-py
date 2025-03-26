from typing import TypedDict
import traceback

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.tools import Tool

from .client import Client


def wrap_tool(client, tool):
    props = tool.input_schema["properties"]
    t = {k: _convert_type(v["type"]) for k, v in props.items()}
    InputType = TypedDict("Input", t)

    def f(input: InputType):
        try:
            res = client.call_tool(tool=tool.name, params=input)
            return res.content[0].text
        except Exception as exc:
            return f"ERROR call to tool {tool.name} failed: {traceback.format_exception(exc)}"

    return f


def _convert_type(t):
    if t == "string":
        return str
    elif t == "boolean":
        return bool
    elif t == "number":
        return float
    elif t == "integer":
        return int
    elif t == "object":
        return dict
    elif t == "array":
        return list
    raise TypeError(f"Unhandled conversion type: {t}")


def mcp_server(client: Client | None = None, **kw):
    client = client | Client()

    # Create an MCP server
    mcp = FastMCP(**kw)

    for t in client.tools.values():
        fn = wrap_tool(client, t)
        mcp._tool_manager._tools[t.name] = Tool.from_function(
            fn=fn,
            name=t.name,
            description=t.description,
        )

    return mcp
