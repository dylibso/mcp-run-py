from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Dict, List
from datetime import datetime
import json


class InvalidUserError(BaseException):
    pass


class ProfileSlug(str):
    """
    A slug made of a username and name separated by a slash
    """

    def __new__(cls, user, name):
        if user == '':
            user = '~'
        return str.__new__(cls, f"{user}/{name}")

    @property
    def user(self):
        return self.split("/")[0]

    @property
    def name(self):
        return self.split("/")[1]

    @staticmethod
    def parse(s):
        if "/" not in s:
            return ProfileSlug("~", s)
        return ProfileSlug(*s.split("/"))

    @staticmethod
    def current_user(profile_name):
        return ProfileSlug("~", profile_name)

    def _current_user(self, user) -> ProfileSlug:
        if self.user == "~" or self.user == user:
            return ProfileSlug("~", self.name)
        raise InvalidUserError(self.user)


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

    slug: ProfileSlug
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


@dataclass
class ServletSearchResult:
    """
    Details about a servlet from the search endpoint
    """

    slug: ProfileSlug
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
