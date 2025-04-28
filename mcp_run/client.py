from dataclasses import dataclass
from typing import Iterator, Dict, List, TypedDict
from datetime import datetime, timedelta
import logging
import traceback
import json

import requests
import extism as ext

from .api import Api
from .types import Servlet, ServletSearchResult, CallResult, Tool, ProfileSlug
from .profile import Profile
from .task import Task, TaskRun
from .plugin import InstalledPlugin
from .config import ClientConfig, _default_session_id


@dataclass
class UserEmail:
    """
    Represents an email address associated with a user account.

    Attributes:
        email: The email address string
        primary: Whether this is the user's primary email
        verified: Whether the email has been verified
    """

    email: str
    primary: bool
    verified: bool


@dataclass
class User:
    """
    Represents an mcp.run user account.

    Attributes:
        username: The user's login name
        emails: List of email addresses associated with this account
    """

    username: str
    emails: List[UserEmail]

    @property
    def primary_email(self) -> UserEmail | None:
        """Get the user's primary email address if one exists."""
        return next((e for e in self.emails if e.primary), None)

    @property
    def verified_emails(self) -> List[UserEmail]:
        """Get all verified email addresses for this user."""
        return [e for e in self.emails if e.verified]


def _convert_type(t):
    if t == "string":
        return str
    elif t == "boolean":
        return bool
    elif t == "number":
        return float
    elif t == "integer":
        return int
    elif t == "object":
        return dict
    elif t == "array":
        return list
    raise TypeError(f"Unhandled conversion type: {t}")


class Client:
    """
    Main client for interacting with the mcp.run API.

    The Client class manages authentication, caching, and provides methods for:
    - Managing profiles and installations
    - Creating and running tasks
    - Installing and calling tools/servlets
    - Searching the mcp.run registry

    Example:
        ```python
        client = Client()

        # List available profiles
        for profile in client.list_profiles():
            print(f"{profile.slug}: {profile.description}")

        # Install and use a tool
        results = client.call_tool("tool-name", params={"param": "value"})
        ```

    Args:
        session_id: Optional session ID for authentication. If not provided,
                   will attempt to load from environment.
        config: Optional ClientConfig instance to customize behavior.
        log_level: Optional logging level (e.g. logging.INFO).
    """

    config: ClientConfig
    """
    Client configuration
    """

    session_id: str
    """
    mcp.run session ID
    """

    logger: logging.Logger
    """
    Python logger
    """

    api: Api
    """
    mcp.run api endpoints
    """

    install_cache: Dict[str, Servlet]
    """
    Cache of Installs
    """

    plugin_cache: Dict[str, InstalledPlugin]
    """
    Cache of InstalledPlugins
    """

    last_installations_request: Dict[str, str]
    """
    Date header from last installations request
    """

    _user: User | None = None

    def __init__(
        self,
        session_id: str | None = None,
        config: ClientConfig | None = None,
        log_level: int | None = None,
        *args,
        **kw,
    ):
        if session_id is None:
            session_id = _default_session_id()
        if config is None:
            config = ClientConfig(*args, **kw)
        self.session_id = session_id
        self.api = Api(config.base_url)
        self.install_cache = {}
        self.plugin_cache = {}
        self.logger = config.logger
        self.config = config
        self._user = None
        self.last_installations_request = {}

        if log_level is not None:
            self.configure_logging(level=log_level)

    def _fix_profile(
        self, profile: str | ProfileSlug | Profile | None, user=False
    ) -> ProfileSlug:
        if user:
            return self._fix_profile(profile, user=False)._current_user(
                self.user.username
            )
        if profile is None:
            return ProfileSlug.parse(self.config.profile) or ProfileSlug("~", "default")
        elif isinstance(profile, Profile):
            return ProfileSlug.parse(profile.slug)
        elif isinstance(profile, str):
            return ProfileSlug.parse(profile)
        return ProfileSlug.parse(profile)

    def _make_pydantic_function(self, tool: Tool):
        props = tool.input_schema["properties"]
        t = {k: _convert_type(v["type"]) for k, v in props.items()}
        InputType = TypedDict("Input", t)

        def f(input: InputType):
            try:
                res = self.call_tool(tool=tool.name, params=input)
                out = ""
                for t in res.content:
                    if hasattr(t, "text"):
                        out += t.text
                    else:
                        out += json.dumps(t)
                    out += "\n"
                return out
            except Exception as exc:
                return f"ERROR call to tool {tool.name} failed: {traceback.format_exception(exc)}"

        return f

    def configure_logging(self, *args, **kw):
        """
        Configure logging using logging.basicConfig
        """
        return logging.basicConfig(*args, **kw)

    def clear_cache(self):
        self.last_installations_request = {}
        self.install_cache = {}
        self.plugin_cache = {}

    @property
    def user(self) -> User:
        """
        Get current logged in user
        """
        if self._user is not None:
            return self._user
        url = self.api.current_user()
        res = requests.get(url, cookies={"sessionId": self.session_id})
        res.raise_for_status()
        data = res.json()
        self._user = User(
            username=data["username"],
            emails=[
                UserEmail(
                    email=x["email"], primary=x["primary"], verified=x["verified"]
                )
                for x in data["emails"]
            ],
        )
        return self._user

    def set_profile(self, profile: str | ProfileSlug | Profile):
        """
        Select a profile
        """
        profile = self._fix_profile(profile, user=True)

        if profile != self.config.profile:
            self.config.profile = profile
            self.clear_cache()

    def create_task(
        self,
        task_name: str,
        provider: str,
        prompt: str,
        *,
        profile: Profile | ProfileSlug | str | None = None,
    ) -> Task:
        """
        Create a new task for running AI model prompts.

        Args:
            task_name: Name to identify this task
            provider: The mcp.run provider to use (e.g. "openai", "anthropic")
            prompt: The prompt text to send to the model
            profile: Optional profile to create task under. Defaults to current profile.

        Returns:
            A new Task instance

        Raises:
            requests.HTTPError: If the API request fails
            ValueError: If required settings are missing

        Example:
            ```python
            task = client.create_task(
                "summarize",
                provider="openai",
                prompt="Summarize this text: ...",
            )
            result = task.run()
            ```
        """
        profile = self._fix_profile(profile, user=True)
        url = self.api.create_task(profile, task_name)
        self.logger.info(f"Creating mcp.run task {url}")
        data = {
            "provider": provider,
            "prompt": prompt,
        }
        res = requests.put(url, cookies={"sessionId": self.session_id}, json=data)
        res.raise_for_status()
        data = res.json()
        return Task(
            _client=self,
            name=data["name"],
            task_slug=data["slug"],
            provider=data["provider"],
            settings=data.get("settings", {}),
            prompt=prompt,
            created_at=datetime.fromisoformat(data["created_at"]),
            modified_at=datetime.fromisoformat(data["modified_at"]),
        )

    def create_profile(
        self,
        name: str,
        description: str = "",
        is_public: bool = False,
        set_current: bool = False,
    ) -> Profile:
        """
        Create a new profile
        """
        params = {"description": description, "is_public": is_public}
        url = self.api.create_profile(profile=ProfileSlug("~", name))
        self.logger.info(f"Creating profile {name} {url}")
        res = requests.post(url, cookies={"sessionId": self.session_id}, json=params)
        res.raise_for_status()
        data = res.json()
        p = Profile(
            _client=self,
            slug=ProfileSlug("~", name),
            description=data["description"],
            is_public=data["is_public"],
            created_at=datetime.fromisoformat(data["created_at"]),
            modified_at=datetime.fromisoformat(data["modified_at"]),
        )
        if set_current:
            self.set_profile(name)
        return p

    def list_user_profiles(self) -> Iterator[Profile]:
        """
        List all profiles created by the logged in user
        """
        url = self.api.profiles()
        self.logger.info(f"Listing mcp.run profiles from {url}")
        res = requests.get(url, cookies={"sessionId": self.session_id})
        res.raise_for_status()
        data = res.json()
        for p in data:
            profile = Profile(
                _client=self,
                slug=ProfileSlug.parse(p["slug"]),
                description=p["description"],
                is_public=p["is_public"],
                created_at=datetime.fromisoformat(p["created_at"]),
                modified_at=datetime.fromisoformat(p["modified_at"]),
            )
            yield profile

    def list_public_profiles(self) -> Iterator[Profile]:
        """
        List all public profiles
        """
        url = self.api.public_profiles()
        self.logger.info(f"Listing mcp.run public profiles from {url}")
        res = requests.get(url, cookies={"sessionId": self.session_id})
        res.raise_for_status()
        data = res.json()
        for p in data:
            profile = Profile(
                _client=self,
                slug=ProfileSlug.parse(p["slug"]),
                description=p["description"],
                is_public=p["is_public"],
                created_at=datetime.fromisoformat(p["created_at"]),
                modified_at=datetime.fromisoformat(p["modified_at"]),
            )
            yield profile

    def list_profiles(self) -> Iterator[Profile]:
        """
        List all public and user profiles
        """
        for profile in self.list_user_profiles():
            yield profile
        for profile in self.list_public_profiles():
            yield profile

    def list_tasks(
        self, profile: Profile | ProfileSlug | str | None = None
    ) -> Iterator[Task]:
        """
        List all tasks associated with the configured profile
        """
        profile = self._fix_profile(profile, user=True)
        url = self.api.tasks()
        self.logger.info(f"Listing mcp.run tasks from {url}")
        res = requests.get(url, cookies={"sessionId": self.session_id})
        res.raise_for_status()
        data = res.json()
        for t in data:
            task = Task(
                _client=self,
                name=t["name"],
                task_slug=t["slug"],
                provider=t["provider"],
                settings=t.get("settings", {}),
                prompt=t["prompt"],
                created_at=datetime.fromisoformat(t["created_at"]),
                modified_at=datetime.fromisoformat(t["modified_at"]),
            )
            if task.profile != str(profile):
                continue
            yield task

    def list_task_runs(
        self, task: Task | str, profile: Profile | ProfileSlug | str | None = None
    ) -> Iterator[TaskRun]:
        """
        List all tasks runs associated with the configured profile
        """
        profile = self._fix_profile(profile, user=True)
        if isinstance(task, str):
            task = self.tasks[task]
        url = self.api.task_runs(profile, task.name)
        self.logger.info(f"Listing mcp.run task runs from {url}")
        res = requests.get(url, cookies={"sessionId": self.session_id})
        res.raise_for_status()
        data = res.json()
        for t in data:
            run = TaskRun(
                _client=self,
                _task=task,
                name=t["name"],
                status=t["status"],
                results_list=t["results"],
                created_at=datetime.fromisoformat(t["created_at"]),
                modified_at=datetime.fromisoformat(t["modified_at"]),
            )
            if run._task.profile != profile:
                continue
            yield run

    @property
    def tasks(self) -> Dict[str, Task]:
        """
        Get all tasks keyed by task name
        """
        t = {}
        for task in self.list_tasks():
            t[task.name] = task
        return t

    @property
    def profiles(self) -> Dict[str, Dict[str, Profile]]:
        """
        Get all profiles, including public profiles, keyed by user and profile name
        """
        p = {}
        for profile in self.list_user_profiles():
            if profile.slug.user not in p:
                p[profile.slug.user] = {}
            p[profile.slug.user][profile.slug.name] = profile
            p["~"] = p[profile.slug.user]
        for profile in self.list_public_profiles():
            if profile.slug.user not in p:
                p[profile.slug.user] = {}
            p[profile.slug.user][profile.slug.name] = profile
        return p

    def list_installs(
        self,
        profile: str | Profile | ProfileSlug | None = None,
    ) -> Iterator[Servlet]:
        """
        List all installed servlets, this will make an HTTP
        request each time
        """
        profile = self._fix_profile(profile)
        url = self.api.installations(profile)
        self.logger.info(f"Listing installed mcp.run servlets from {url}")
        headers = {}
        last = self.last_installations_request.get(profile)
        if last is not None:
            headers["if-modified-since"] = last
        res = requests.get(
            url,
            headers=headers,
            cookies={
                "sessionId": self.session_id,
            },
        )
        res.raise_for_status()
        if res.status_code == 301 or res.status_code == 304:
            self.logger.debug(f"No changes since {last}")
            for v in self.install_cache.values():
                yield v
            return
        data = res.json()
        self.logger.debug(f"Got installed servlets from {url}: {data}")
        self.last_installations_request[profile] = res.headers.get("Date")
        for install in data["installs"]:
            binding = install["binding"]
            tools = install["servlet"]["meta"]["schema"]
            if "tools" in tools:
                tools = tools["tools"]
            else:
                tools = [tools]
            install = Servlet(
                binding_id=binding["id"],
                content_addr=binding["contentAddress"],
                name=install.get("name", ""),
                slug=ProfileSlug.parse(install["servlet"]["slug"]),
                settings=install["settings"],
                tools={},
                has_oauth=install["servlet"]["has_client"],
            )
            for tool in tools:
                install.tools[tool["name"]] = Tool(
                    name=tool["name"],
                    description=tool["description"],
                    input_schema=tool["inputSchema"],
                    servlet=install,
                )
            self.install_cache[install.name] = install
            if install.name in self.plugin_cache:
                del self.plugin_cache[install.name]
            yield install

    @property
    def installs(self) -> Dict[str, Servlet]:
        """
        Get all installed servlets, this will returned cached Installs if
        the cache timeout hasn't been reached
        """
        for install in self.list_installs():
            continue
        return self.install_cache

    def uninstall(self, servlet: Servlet | str, profile: Profile | None = None):
        """
        Uninstall a servlet
        """
        profile_name = self.config.profile
        if profile is not None:
            profile_name = profile.name
        if isinstance(servlet, Servlet):
            servlet = servlet.name
        url = self.api.uninstall(profile_name, servlet)
        res = requests.delete(
            url,
            cookies={
                "sessionId": self.session_id,
            },
        )
        res.raise_for_status()
        if profile is None:
            self.clear_cache()

    def install(
        self,
        servlet: Servlet | ServletSearchResult,
        name: str | None = None,
        allow_update: bool = True,
        config: dict | None = None,
        network: dict | None = None,
        filesystem: dict | None = None,
        profile: Profile | None = None,
    ):
        """
        Install a servlet
        """
        profile_name = self.config.profile
        if profile is not None:
            profile_name = profile.name
        settings = {}
        if config is not None:
            settings["config"] = config
        if network is not None:
            settings["network"] = network
        if filesystem is not None:
            settings["filesystem"] = filesystem
        params = {
            "servlet_slug": servlet.slug,
            "settings": settings,
            "allow_update": allow_update,
        }
        if name is not None:
            params["name"] = name
        url = self.api.install(profile_name)
        res = requests.post(
            url,
            json=params,
            cookies={
                "sessionId": self.session_id,
            },
        )
        res.raise_for_status()
        if profile is None:
            self.clear_cache()

    @property
    def tools(self) -> Dict[str, Tool]:
        """
        Get all tools from all installed servlets
        """
        installs = self.installs
        tools = {}
        for install in installs.values():
            for tool in install.tools.values():
                tools[tool.name] = tool
        return tools

    def tool(self, name: str) -> Tool | None:
        """
        Get a tool by name
        """
        for install in self.installs.values():
            for tool in install.tools.values():
                if tool.name == name:
                    return tool
        return None

    def search(self, query: str) -> Iterator[ServletSearchResult]:
        """
        Search for tools on mcp.run
        """
        url = self.api.search(query)
        res = requests.get(
            url,
            cookies={
                "sessionId": self.session_id,
            },
        )
        data = res.json()
        for servlet in data:
            yield ServletSearchResult(
                slug=ProfileSlug.parse(servlet["slug"]),
                meta=servlet.get("meta", {}),
                installation_count=servlet["installation_count"],
                visibility=servlet["visibility"],
                created_at=datetime.fromisoformat(servlet["created_at"]),
                modified_at=datetime.fromisoformat(servlet["modified_at"]),
            )

    def plugin(
        self,
        install: Servlet,
        cache: bool = True,
        wasi: bool | None = None,
        functions: List[ext.Function] | None = None,
        wasm: List[Dict[str, bytes]] | None = None,
    ) -> InstalledPlugin:
        """
        Instantiate an installed servlet, turning it into an InstalledPlugin

        Args:
            install: The servlet to instantiate
            wasi: Whether to enable WASI
            functions: Optional list of Extism functions to include
            wasm: Optional list of additional WASM modules

        Returns:
            An InstalledPlugin instance
        """
        if install.has_oauth:
            res = requests.get(
                self.api.oauth(self.config.profile, install.name),
                cookies={
                    "sessionId": self.session_id,
                },
            )
            res.raise_for_status()
            oauth = res.json()["oauth_info"]
        else:
            oauth = None
        wasi = wasi or True
        cache_ok = cache and wasi and functions is None and wasm is None
        if cache_ok:
            cached: InstalledPlugin | None = self.plugin_cache.get(install.name)
            if cached is not None:
                if (
                    cached._timestamp + timedelta(minutes=4, seconds=30)
                    > datetime.now()
                ):
                    self.logger.info(f"Found cached {install.name} instance")
                    return cached
                else:
                    self.logger.info(
                        f"Found cached {install.name}, but oauth token update is needed"
                    )
                    del self.plugin_cache[install.name]
        if install.content is None:
            self.logger.info(
                f"Fetching servlet Wasm for {install.name}: {install.content_addr}"
            )
            res = requests.get(
                self.api.content(install.content_addr),
                cookies={
                    "sessionId": self.session_id,
                },
            )
            install.content = res.content
        perm = install.settings["permissions"]
        wasm_modules = [{"data": install.content}]
        if wasm is not None:
            wasm_modules.extend(wasm)
        manifest = {
            "wasm": wasm_modules,
            "allowed_paths": perm["filesystem"].get("volumes", {}),
            "allowed_hosts": perm["network"].get("domains", []),
            "config": install.settings.get("config", {}),
        }

        if oauth is not None:
            manifest["config"][oauth["config_name"]] = oauth["access_token"]

        if functions is None:
            functions = []
        p = InstalledPlugin(
            install, ext.Plugin(manifest, wasi=wasi, functions=functions)
        )
        if cache_ok:
            self.plugin_cache[install.name] = p
        return p

    def call_tool(
        self,
        tool: str | Tool,
        params: dict | None = None,
        *,
        wasi: bool = True,
        functions: List[ext.Function] | None = None,
        wasm: List[Dict[str, bytes]] | None = None,
    ) -> CallResult:
        """
        Call a tool with the given input parameters.

        This method handles looking up the tool, instantiating the necessary plugin,
        and executing the tool call with the provided parameters.

        Args:
            tool: Name of the tool or Tool instance to call
            params: Dictionary of input parameters matching the tool's schema
            wasi: Whether to enable WASI support for the tool
            functions: Optional list of additional Extism functions to include
            wasm: Optional list of additional WASM modules to load

        Returns:
            CallResult containing the tool's output and metadata

        Raises:
            ValueError: If the tool is not found or input validation fails
            RuntimeError: If the tool execution fails

        Example:
            ```python
            # Call by name
            result = client.call_tool("compress-image", {
                "image": image_bytes,
                "format": "jpeg",
                "quality": 85
            })

            # Call using Tool instance
            tool = client.get_tool("compress-image")
            result = client.call_tool(tool, {...})
            ```
        """
        if isinstance(tool, str):
            found_tool = self.tool(tool)
            if found_tool is None:
                raise ValueError(f"Tool '{tool}' not found")
            tool = found_tool
        plugin = self.plugin(tool.servlet, wasi=wasi, functions=functions, wasm=wasm)
        return plugin.call(tool=tool.name, input=params or {})

    def delete_profile(self, profile: str | Profile | ProfileSlug):
        """
        Delete a profile
        """
        profile = self._fix_profile(profile, user=True)
        url = self.api.delete_profile(profile)
        res = requests.delete(
            url,
            cookies={
                "sessionId": self.session_id,
            },
        )
        res.raise_for_status()
