from dataclasses import dataclass
import urllib


@dataclass
class Api:
    """
    Manages mcp.run endpoints
    """

    base: str
    """
    mcp.run base URL
    """

    def installations(self, profile):
        """
        List installations
        """
        if "/" in profile:
            return f"{self.base}/api/profiles/{profile}/installations"
        return f"{self.base}/api/profiles/~/{profile}/installations"

    def install(self, profile):
        """
        Install a servlet to a profile
        """
        return f"{self.base}/api/profiles/~/{profile}/installations"

    def uninstall(self, profile, installation):
        """
        Uninstall a servlet from a profile
        """
        return f"{self.base}/api/profiles/~/{profile}/installations/{installation}"

    def tasks(self):
        """
        List tasks
        """
        return f"{self.base}/api/users/~/tasks"

    def create_task(self, profile, task):
        """
        Create task
        """
        if "/" not in profile:
            profile = f"~/{profile}"
        return f"{self.base}/api/tasks/{profile}/{task}"

    def task_signed_url(self, profile, task):
        """
        Get a signed URL for a task
        """
        if "/" not in profile:
            profile = f"~/{profile}"
        return f"{self.base}/api/tasks/{profile}/{task}/signed"

    def task_runs(self, profile, task):
        """
        Get a list of runs
        """
        if "/" not in profile:
            profile = f"~/{profile}"
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

    def delete_profile(self, profile):
        """
        Delete profile
        """
        return f"{self.base}/api/profiles/~/{profile}"

    def create_profile(self, profile):
        """
        Create a new profile
        """
        if "/" not in profile:
            profile = f"~/{profile}"
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
