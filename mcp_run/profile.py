from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

import requests

from .types import Servlet

if TYPE_CHECKING:
    from .client import Client


@dataclass
class Profile:
    """
    mcp.run profile
    """

    _client: Client
    slug: str
    description: str
    is_public: bool
    created_at: datetime
    modified_at: datetime

    @property
    def username(self):
        return self.slug.split("/")[0]

    @property
    def name(self):
        return self.slug.split("/")[1]

    def delete(self):
        self._client.delete_profile(self)

    def list_installs(self):
        return self._client.list_installs(profile=self.slug)

    def install(self, *args, **kw):
        kw["profile"] = self
        return self._client.install(*args, **kw)

    def uninstall(self):
        kw["profile"] = self
        return self._client.uninstall(*args, **kw)
