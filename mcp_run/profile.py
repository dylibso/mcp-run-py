from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

from .types import ProfileSlug

if TYPE_CHECKING:
    from .client import Client


@dataclass
class Profile:
    """
    mcp.run profile
    """

    _client: Client
    slug: ProfileSlug
    description: str
    is_public: bool
    created_at: datetime
    modified_at: datetime

    def delete(self):
        self._client.delete_profile(self)

    def list_installs(self):
        return self._client.list_installs(profile=self)

    def install(self, *args, **kw):
        kw["profile"] = self
        return self._client.install(*args, **kw)

    def uninstall(self, *args, **kw):
        kw["profile"] = self
        return self._client.uninstall(*args, **kw)
