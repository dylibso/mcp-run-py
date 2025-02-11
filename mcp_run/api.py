from dataclasses import dataclass
import urllib

from .types import ProfileSlug, InvalidUserError


def fix_profile(p: ProfileSlug, only_self=False):
    if only_self:
        if p.user != "~":
            raise InvalidUserError(p.user)
    return str(p)


@dataclass
class Api:
    """
    Manages mcp.run endpoints
    """

    base: str
    """
    mcp.run base URL
    """

    def current_user(self):
        return f"{self.base}/api/users/~"

    def installations(self, profile: ProfileSlug):
        """
        List installations
        """
        profile = fix_profile(profile)
        return f"{self.base}/api/profiles/{profile}/installations"

    def install(self, profile: ProfileSlug):
        """
        Install a servlet to a profile
        """
        profile = fix_profile(profile, only_self=True)
        return f"{self.base}/api/profiles/{profile}/installations"

    def uninstall(self, profile: ProfileSlug, installation: str):
        """
        Uninstall a servlet from a profile
        """
        profile = fix_profile(profile, only_self=True)
        return f"{self.base}/api/profiles/{profile}/installations/{installation}"

    def tasks(self):
        """
        List tasks
        """
        return f"{self.base}/api/users/~/tasks"

    def create_task(self, profile: ProfileSlug, task: str):
        """
        Create task
        """
        profile = fix_profile(profile, only_self=True)
        return f"{self.base}/api/tasks/{profile}/{task}"

    def task_signed_url(self, profile: ProfileSlug, task: str):
        """
        Get a signed URL for a task
        """
        profile = fix_profile(profile, only_self=True)
        return f"{self.base}/api/tasks/{profile}/{task}/signed"

    def task_runs(self, profile: ProfileSlug, task: str):
        """
        Get a list of runs
        """
        profile = fix_profile(profile, only_self=True)
        return f"{self.base}/api/runs/{profile}/{task}"

    def profiles(self, user: str = "~"):
        """
        List profiles for a user
        """
        return f"{self.base}/api/profiles/{user}"

    def public_profiles(self):
        """
        List public profiles
        """
        return f"{self.base}/api/profiles"

    def delete_profile(self, profile: ProfileSlug):
        """
        Delete profile
        """
        profile = fix_profile(profile, only_self=True)
        return f"{self.base}/api/profiles/{profile}"

    def create_profile(self, profile):
        """
        Create a new profile
        """
        profile = fix_profile(profile, only_self=True)
        return f"{self.base}/api/profiles/{profile}"

    def search(self, query):
        """
        Search servlets
        """
        query = urllib.parse.quote_plus(query)
        return f"{self.base}/api/servlets?q={query}"

    def content(self, addr: str):
        """
        Get the data associated with a content address
        """
        return f"{self.base}/api/c/{addr}"
