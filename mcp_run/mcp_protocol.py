from typing import TypedDict
import traceback

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.tools import Tool

from .client import Client


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


def convert_tool(client, tool):
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


class MCPServer(FastMCP):
    client: Client

    def __init__(self, client: Client | None = None, **kw):
        self.client = client or Client()
        super().__init__(**kw)
        self.update_tools()

    def update_tools(self):
        for t in self.client.tools.values():
            fn = convert_tool(self.client, t)
            self._tool_manager._tools[t.name] = Tool.from_function(
                fn=fn,
                name=t.name,
                description=t.description,
            )
