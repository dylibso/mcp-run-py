import os
import json
import logging
from pathlib import Path
from dataclasses import dataclass, field
from datetime import timedelta

from .types import ProfileSlug


def _parse_mcpx_config(filename: str | Path) -> str | None:
    with open(filename) as f:
        j = json.loads(f.read())
        auth: str = j["authentication"][0][1]
        s = auth.split("=", maxsplit=1)
        return s[1]
    return None


def _default_session_id() -> str:
    # Allow session id to be specified using MCP_RUN_SESSION_ID
    id = os.environ.get("MCP_RUN_SESSION_ID", os.environ.get("MCPX_SESSION_ID"))
    if id is not None:
        return id

    # Try ~/.config/mcpx/config.json for Linux/macOS
    user = Path(os.path.expanduser("~"))
    dot_config = user / ".config" / "mcpx" / "config.json"
    if dot_config.exists():
        return _parse_mcpx_config(dot_config)

    # Try Windows paths
    windows_config = Path(os.path.expandvars("%LOCALAPPDATA%/mcpx/config.json"))
    if windows_config.exists():
        return _parse_mcpx_config(windows_config)

    windows_config = Path(os.path.expandvars("%APPDATA%/mcpx/config.json"))
    if windows_config.exists():
        return _parse_mcpx_config(windows_config)

    raise Exception("No mcpx session ID found")


def _default_update_interval():
    ms = os.environ.get(
        "MCP_RUN_UPDATE_INTERVAL", os.environ.get("MCPX_UPDATE_INTERVAL")
    )
    if ms is None:
        return timedelta(minutes=1)
    else:
        return timedelta(milliseconds=int(ms))


@dataclass
class ClientConfig:
    """
    Configures an mcp.run Client
    """

    base_url: str = os.environ.get("MCP_RUN_ORIGIN", "https://www.mcp.run")
    """
    mcp.run base URL
    """

    tool_refresh_time: timedelta = _default_update_interval()
    """
    Length of time to wait between checking for new tools
    """

    logger: logging.Logger = logging.getLogger(__name__)
    """
    Python logger
    """

    profile: ProfileSlug = field(default_factory=lambda: ProfileSlug("~", "default"))
    """
    mcp.run profile name
    """

    def configure_logging(self, *args, **kw):
        """
        Configure logging using logging.basicConfig
        """
        return logging.basicConfig(*args, **kw)

    def with_profile(self, profile: str | ProfileSlug):
        """
        Update the configured profile
        """
        if isinstance(profile, ProfileSlug):
            self.profile = profile
        else:
            self.profile = ProfileSlug.parse(profile)
        return self
