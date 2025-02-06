from dataclasses import dataclass
from datetime import datetime


@dataclass
class Profile:
    """
    mcp.run profile
    """

    name: str
    username: str
    description: str
    is_public: bool
    created_at: datetime
    modified_at: datetime
