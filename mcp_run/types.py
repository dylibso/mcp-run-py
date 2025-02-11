from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Dict, List
from datetime import datetime
import json


@dataclass
class Tool:
    """
    A tool definition
    """

    name: str
    """
    Name of the tool
    """

    description: str
    """
    Information about the tool and how to use it
    """

    input_schema: dict
    """
    Input parameter schema
    """

    servlet: Optional[Servlet] = None
    """
    The servlet the tool belongs to
    """


@dataclass
class Servlet:
    """
    An installed mcp.run servlet
    """

    name: str
    """
    Servlet installation name
    """

    slug: str
    """
    Servlet slug
    """

    binding_id: str
    """
    Servlet binding ID
    """

    content_addr: str
    """
    Content address for WASM module
    """

    settings: dict
    """
    Servlet settings and permissions
    """

    tools: Dict[str, Tool]
    """
    All tools provided by the servlet
    """

    content: bytes | None = None
    """
    Cached WASM module data
    """

    def __eq__(self, other):
        if other is None:
            return False
        return (
            self.tools == other.tools
            and self.settings == other.settings
            and self.content_addr == other.content_addr
            and self.binding_id == other.binding_id
            and self.slug == other.slug
            and self.name == other.name
        )

    @property
    def slug_user(self):
        return self.slug.split("/")[0]

    @property
    def slug_name(self):
        return self.slug.split("/")[1]


@dataclass
class ServletSearchResult:
    """
    Details about a servlet from the search endpoint
    """

    slug: str
    """
    Servlet slug
    """

    meta: dict
    """
    Servlet metadata
    """

    installation_count: int
    """
    Number of times the servlet has been installed
    """

    visibility: str
    """
    Public/private
    """

    created_at: datetime
    """
    Creation timestamp
    """

    modified_at: datetime
    """
    Modification timestamp
    """

    @property
    def slug_user(self):
        return self.slug.split("/")[0]

    @property
    def slug_name(self):
        return self.slug.split("/")[1]


@dataclass
class Content:
    """
    The result of tool calls
    """

    type: str
    """
    The type of content, for example "text" or "image"
    """

    mime_type: str = "text/plain"
    """
    Content mime type
    """

    _data: bytes | None = None
    """
    Result message or data
    """

    @property
    def text(self):
        """
        Get the result message
        """
        return self.data.decode()

    @property
    def json(self):
        """
        Get the result data as json
        """
        return json.loads(self.text)

    @property
    def data(self):
        """
        Get the result as bytes
        """
        return self._data or b""


@dataclass
class CallResult:
    """
    Result of a tool call
    """

    content: List[Content]
    """
    Content returned from a call
    """
