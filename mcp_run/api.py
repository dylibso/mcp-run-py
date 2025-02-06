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

    def tasks(self):
        """
        List tasks
        """
        return f"{self.base}/api/users/~/tasks"

    def create_task(self, profile, task):
        """
        Create task
        """
        return f"{self.base}/api/tasks/~/{profile}/{task}"

    def task_signed_url(self, profile, task):
        """
        Get a signed URL for a task
        """
        return f"{self.base}/api/tasks/~/{profile}/{task}/signed"

    def task_runs(self, profile, task):
        """
        Get a list of runs
        """
        return f"{self.base}/api/runs/~/{profile}/{task}"

    def profiles(self, user: str = "~"):
        """
        List profiles
        """
        return f"{self.base}/api/profiles/{user}"

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
