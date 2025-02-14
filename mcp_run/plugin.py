import base64
import json
import extism as ext

from .types import Servlet, Content, CallResult


class InstalledPlugin:
    _install: Servlet
    _plugin: ext.Plugin

    def __init__(self, install, plugin):
        self._install = install
        self._plugin = plugin

    def call(self, tool: str | None = None, input: dict = {}) -> CallResult:
        """
        Call a tool with the given input
        """
        if tool is None:
            tool = self._install.name
        j = json.dumps({"params": {"arguments": input, "name": tool}})
        r = self._plugin.call("call", j)
        r = json.loads(r)

        out = []
        for c in r["content"]:
            ty = c["type"]
            if ty == "text":
                out.append(Content(type=ty, _data=c["text"].encode()))
            elif ty == "image":
                out.append(
                    Content(
                        type=ty,
                        _data=base64.b64decode(c["data"]),
                        mime_type=c["mimeType"],
                    )
                )
        return CallResult(content=out)
