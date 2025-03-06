from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Dict, List
from datetime import datetime
import json


class MCPRunError(Exception):
    """Base exception class for MCP-related errors"""

    pass


class InvalidUserError(MCPRunError):
    """Raised when attempting to access or modify a profile belonging to another user"""

    def __init__(self, user: str):
        self.user = user
        super().__init__(
            f"Cannot access profile for user '{user}' - only '~' (self) is allowed"
        )


class ProfileSlug(str):
    """
    A profile identifier consisting of a username and profile name separated by a slash.

    Format: "{username}/{profile_name}"

    Special cases:
    - "~" as username refers to the current authenticated user
    - An empty username is converted to "~"

    Examples:
        ProfileSlug("alice", "dev")  # -> "alice/dev"
        ProfileSlug("~", "prod")     # -> "~/prod" (current user)
        ProfileSlug.parse("bob/test") # -> ProfileSlug("bob", "test")
        ProfileSlug.parse("myprof")   # -> ProfileSlug("~", "myprof")
    """

    def __new__(cls, user: str, name: str) -> "ProfileSlug":
        """Create a new ProfileSlug"""
        if not name:
            raise ValueError("Profile name cannot be empty")
        if user == "":
            user = "~"
        return str.__new__(cls, f"{user}/{name}")

    def __repr__(self):
        return f"ProfileSlug('{self.user}', '{self.name}')"

    @property
    def user(self) -> str:
        """The username portion of the slug"""
        return self.split("/")[0]

    @property
    def name(self) -> str:
        """The profile name portion of the slug"""
        return self.split("/")[1]

    @staticmethod
    def parse(s: str) -> "ProfileSlug":
        """
        Parse a string into a ProfileSlug.

        If no username is provided (no slash), assumes current user ("~").
        """
        if "/" not in s:
            return ProfileSlug("~", s)
        user, name = s.split("/", 1)
        return ProfileSlug(user, name)

    @staticmethod
    def current_user(profile_name: str) -> "ProfileSlug":
        """Create a ProfileSlug for the current user ("~")"""
        return ProfileSlug("~", profile_name)

    def _current_user(self, user: str) -> "ProfileSlug":
        """
        Convert this slug to reference the current user if possible.

        Raises:
            InvalidUserError: If the slug references another user's profile
        """
        if self.user == "~" or self.user == user:
            return ProfileSlug("~", self.name)
        raise InvalidUserError(self.user)


@dataclass
class Tool:
    """
    Represents a callable tool provided by a servlet.

    A tool is a discrete function that can be called with specific input parameters
    defined by its input schema. Tools are provided by servlets and represent the
    primary way to interact with servlet functionality.
    """

    name: str
    """The unique identifier for this tool within its servlet"""

    description: str
    """Human-readable description of the tool's purpose and usage"""

    input_schema: dict
    """
    JSON Schema defining the expected input parameters.

    This schema validates the input dictionary passed to tool.call()
    """

    servlet: Optional[Servlet] = None
    """The servlet instance that provides this tool"""

    def __str__(self) -> str:
        """Return a human-readable representation of the tool"""
        return f"{self.servlet.name}.{self.name}" if self.servlet else self.name


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
