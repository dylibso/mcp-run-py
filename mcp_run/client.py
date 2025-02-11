from dataclasses import dataclass
import os
import json
from pathlib import Path
from typing import Iterator, Dict, List
from datetime import datetime, timedelta
import base64
import logging

import requests
import extism as ext

from .api import Api
from .types import Servlet, ServletSearchResult, CallResult, Content, Tool
from .profile import Profile
from .task import TaskRunner, Task, TaskRun


class InstalledPlugin:
    _install: Servlet
    _plugin: ext.Plugin

    def __init__(self, install, plugin):
        self._install = install
        self._plugin = plugin

    def call(self, tool: str | None = None, input: dict = {}) -> CallResult:
        """
        Call a tool with the given input
        """
        if tool is None:
            tool = self._install.name
        j = json.dumps({"params": {"arguments": input, "name": tool}})
        r = self._plugin.call("call", j)
        r = json.loads(r)

        out = []
        for c in r["content"]:
            ty = c["type"]
            if ty == "text":
                out.append(Content(type=ty, _data=c["text"].encode()))
            elif ty == "image":
                out.append(
                    Content(
                        type=ty,
                        _data=base64.b64decode(c["data"]),
                        mime_type=c["mimeType"],
                    )
                )
        return CallResult(content=out)


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

    profile: str = "default"
    """
    mcp.run profile name
    """

    def configure_logging(self, *args, **kw):
        """
        Configure logging using logging.basicConfig
        """
        return logging.basicConfig(*args, **kw)


class Cache[K, T]:
    items: Dict[K, T]
    duration: timedelta
    last_update: datetime | None = None

    def __init__(self, t: timedelta | None = None):
        self.items = {}
        self.last_update = None
        self.duration = t

    def add(self, key: K, item: T):
        self.items[key] = item

    def remove(self, key: K):
        self.items.pop(key, None)

    def get(self, key: K) -> T | None:
        return self.items.get(key)

    def __contains__(self, key: K) -> bool:
        return key in self.items

    def clear(self):
        self.items = {}
        self.last_update = None

    def set_last_update(self):
        self.last_update = datetime.now()

    def needs_refresh(self) -> bool:
        if self.duration is None:
            return False
        if self.last_update is None:
            return True
        now = datetime.now()
        return now - self.last_update >= self.duration


class Client:
    """
    mcp.run API client
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

    install_cache: Cache[str, Servlet]
    """
    Cache of Installs
    """

    plugin_cache: Cache[str, InstalledPlugin]
    """
    Cache of InstalledPlugins
    """

    last_installations_request: Dict[str, str] = {}
    """
    Date header from last installations request
    """

    def __init__(
        self,
        session_id: str | None = None,
        config: ClientConfig | None = None,
        log_level: int | None = None,
    ):
        if session_id is None:
            session_id = _default_session_id()
        if config is None:
            config = ClientConfig()
        self.session_id = session_id
        self.api = Api(config.base_url)
        self.install_cache = Cache(config.tool_refresh_time)
        self.plugin_cache = Cache()
        self.logger = config.logger
        self.config = config

        if log_level is not None:
            self.configure_logging(level=log_level)

    def configure_logging(self, *args, **kw):
        """
        Configure logging using logging.basicConfig
        """
        return logging.basicConfig(*args, **kw)

    def clear_cache(self):
        self.last_installations_request = {}
        self.install_cache.clear()
        self.plugin_cache.clear()

    def set_profile(self, profile: str | Profile):
        """
        Select a profile
        """
        if isinstance(profile, Profile):
            profile = profile.slug
        if profile != self.config.profile:
            self.config.profile = profile
            self.clear_cache()

    def create_task(
        self,
        task_name: str,
        runner: TaskRunner,
        model: str,
        prompt: str,
        api_key: str | None = None,
        settings: dict | None = None,
    ) -> Task:
        """
        Create a new task
        """
        if api_key is None and runner.lower() == "openai":
            api_key = os.environ.get("OPENAI_API_KEY")
        elif api_key is None and runner.lower() == "anthropic":
            api_key = os.environ.get("ANTHROPIC_API_KEY")
        url = self.api.create_task(self.config.profile, task_name)
        self.logger.info(f"Creating mcp.run task {url}")
        settings = settings or {}
        if "key" not in settings and api_key is not None:
            settings["key"] = api_key
        data = {
            "runner": runner,
            runner: {
                "prompt": prompt,
                "model": model,
            },
            "settings": settings,
        }
        res = requests.put(url, cookies={"sessionId": self.session_id}, json=data)
        res.raise_for_status()
        data = res.json()
        return Task(
            _client=self,
            name=data["name"],
            slug=data["slug"],
            runner=data["runner"],
            settings=data["settings"],
            prompt=prompt,
            model=model,
            created_at=datetime.fromisoformat(data["created_at"]),
            modified_at=datetime.fromisoformat(data["modified_at"]),
        )

    def create_profile(
        self, name: str, description: str = "", is_public: bool = False
    ) -> Profile:
        """
        Create a new profile
        """
        params = {"description": description, "is_public": is_public}
        url = self.api.create_profile(name)
        self.logger.info(f"Creating profile {name} {url}")
        res = requests.post(url, cookies={"sessionId": self.session_id}, json=params)
        res.raise_for_status()
        data = res.json()
        return Profile(
            _client=self,
            slug=data["slug"],
            description=data["description"],
            is_public=data["is_public"],
            created_at=datetime.fromisoformat(data["created_at"]),
            modified_at=datetime.fromisoformat(data["modified_at"]),
        )

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
                slug=p["slug"],
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
                slug=p["slug"],
                description=p["description"],
                is_public=p["is_public"],
                created_at=datetime.fromisoformat(p["created_at"]),
                modified_at=datetime.fromisoformat(p["modified_at"]),
            )
            yield profile

    def list_tasks(self) -> Iterator[Task]:
        """
        List all tasks associated with the configured profile
        """
        url = self.api.tasks()
        self.logger.info(f"Listing mcp.run tasks from {url}")
        res = requests.get(url, cookies={"sessionId": self.session_id})
        res.raise_for_status()
        data = res.json()
        for t in data:
            task = Task(
                _client=self,
                name=t["name"],
                slug=t["slug"],
                runner=t["runner"],
                settings=t.get("settings", {}),
                prompt=t[t["runner"]]["prompt"],
                model=t[t["runner"]]["model"],
                created_at=datetime.fromisoformat(t["created_at"]),
                modified_at=datetime.fromisoformat(t["modified_at"]),
            )
            if task.profile != self.config.profile:
                continue
            yield task

    def list_task_runs(self, task: Task | str) -> Iterator[TaskRun]:
        """
        List all tasks runs associated with the configured profile
        """
        if isinstance(task, Task):
            task = task.name
        url = self.api.task_runs(self.config.profile, task)
        self.logger.info(f"Listing mcp.run task runs from {url}")
        res = requests.get(url, cookies={"sessionId": self.session_id})
        res.raise_for_status()
        data = res.json()
        for t in data:
            task = Task(
                _client=self,
                name=t["name"],
                slug=t["slug"],
                runner=t["runner"],
                settings=t.get("settings", {}),
                prompt=t[t["runner"]]["prompt"],
                model=t[t["runner"]]["model"],
                created_at=datetime.fromisoformat(t["created_at"]),
                modified_at=datetime.fromisoformat(t["modified_at"]),
            )
            if task.profile != self.config.profile:
                continue
            yield task

    @property
    def tasks(self) -> Dict[str, Task]:
        """
        Get all tasks keyed by task name
        """
        t = {}
        for task in self.list_tasks():
            t[task.name] = t
        return t

    @property
    def profiles(self) -> Dict[str, Dict[str, Profile]]:
        """
        Get all profiles, including public profiles, keyed by user and profile name
        """
        p = {}
        for profile in self.list_user_profiles():
            if profile.username not in p:
                p[profile.username] = {}
            p[profile.username][profile.name] = profile
            p["~"] = p[profile.username]
        for profile in self.list_public_profiles():
            if profile.username not in p:
                p[profile.username] = {}
            p[profile.username][profile.name] = profile
        return p

    def list_installs(self, profile: str | Profile | None = None) -> Iterator[Servlet]:
        """
        List all installed servlets, this will make an HTTP
        request each time
        """
        if profile is None:
            profile = self.config.profile
        elif isinstance(profile, Profile):
            profile = profile.slug
        url = self.api.installations(profile)
        self.logger.info(f"Listing installed mcp.run servlets from {url}")
        headers = {}
        if self.last_installations_request.get(profile) is not None:
            headers["if-modified-since"] = self.last_installations_request
        res = requests.get(
            url,
            headers=headers,
            cookies={
                "sessionId": self.session_id,
            },
        )
        res.raise_for_status()
        if res.status_code == 301:
            self.logger.debug(f"No changes since {self.last_installations_request}")
            for v in self.install_cache.items.values():
                yield v
            return
        self.last_installations_request[profile] = res.headers.get("Date")
        data = res.json()
        self.logger.debug(f"Got installed servlets from {url}: {data}")
        for install in data["installs"]:
            binding = install["binding"]
            tools = install["servlet"]["meta"]["schema"]
            if "tools" in tools:
                tools = tools["tools"]
            else:
                tools = [tools]
            install = Servlet(
                installed=True,
                binding_id=binding["id"],
                content_addr=binding["contentAddress"],
                name=install.get("name", ""),
                slug=install["servlet"]["slug"],
                settings=install["settings"],
                tools={},
            )
            for tool in tools:
                install.tools[tool["name"]] = Tool(
                    name=tool["name"],
                    description=tool["description"],
                    input_schema=tool["inputSchema"],
                    servlet=install,
                )
            yield install

    @property
    def installs(self) -> Dict[str, Servlet]:
        """
        Get all installed servlets, this will returned cached Installs if
        the cache timeout hasn't been reached
        """
        if self.install_cache.needs_refresh():
            self.logger.info("Cache expired, fetching installs")
            visited = set()
            for install in self.list_installs():
                if install != self.install_cache.get(install.name):
                    self.install_cache.add(install.name, install)
                    self.plugin_cache.remove(install.name)
                visited.add(install.name)
            for install_name in self.install_cache.items:
                if install_name not in visited:
                    self.install_cache.remove(install_name)
                    self.plugin_cache.remove(install_name)
            self.install_cache.set_last_update()
        return self.install_cache.items

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
                slug=servlet["slug"],
                meta=servlet.get("meta", {}),
                installation_count=servlet["installation_count"],
                visibility=servlet["visibility"],
                created_at=datetime.fromisoformat(servlet["created_at"]),
                modified_at=datetime.fromisoformat(servlet["modified_at"]),
            )

    def plugin(
        self,
        install: Servlet,
        wasi: bool = True,
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
        if not install.installed:
            raise Exception(f"Servlet {install.name} must be installed before use")
        cache_name = f"{install.name}-{wasi}"
        if functions is not None:
            for func in functions:
                cache_name += "-"
                cache_name += str(hash(func.pointer))
        cache_name = str(hash(cache_name))
        cached = self.plugin_cache.get(cache_name)
        if cached is not None:
            return cached
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
        if functions is None:
            functions = []
        p = InstalledPlugin(
            install, ext.Plugin(manifest, wasi=wasi, functions=functions)
        )
        self.plugin_cache.add(install.name, p)
        return p

    def call(
        self,
        tool: str | Tool,
        input: dict = {},
        wasi: bool = True,
        functions: List[ext.Function] | None = None,
        wasm: List[Dict[str, bytes]] | None = None,
    ) -> CallResult:
        """
        Call a tool with the given input

        Args:
            tool: Name of the tool or Tool instance to call
            input: Dictionary of input parameters for the tool
            wasi: Whether to enable WASI
            functions: Optional list of Extism functions to include
            wasm: Optional list of additional WASM modules

        Returns:
            CallResult containing the tool's output
        """
        if isinstance(tool, str):
            found_tool = self.tool(tool)
            if found_tool is None:
                raise ValueError(f"Tool '{tool}' not found")
            tool = found_tool
        plugin = self.plugin(tool.servlet, wasi=wasi, functions=functions, wasm=wasm)
        return plugin.call(tool=tool.name, input=input)

    def delete_profile(self, profile: str | Profile):
        """
        Delete a profile
        """
        if isinstance(profile, Profile):
            profile = profile.name
        url = self.api.delete_profile(profile)
        res = requests.delete(
            url,
            cookies={
                "sessionId": self.session_id,
            },
        )
        res.raise_for_status()
