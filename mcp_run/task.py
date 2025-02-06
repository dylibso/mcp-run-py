from __future__ import annotations
from dataclasses import dataclass
from typing import List, TYPE_CHECKING
from datetime import datetime, timedelta
from enum import StrEnum
from time import sleep

if TYPE_CHECKING:
    from .client import Client

import requests


@dataclass
class TaskRun:
    """
    mcp.run task run
    """

    _client: Client
    _task: Task
    name: str
    status: str
    results_list: List[object]
    created_at: datetime
    modified_at: datetime
    url: str | None

    def wait(
        self, interval=timedelta(milliseconds=250), timeout: timedelta | None = None
    ):
        start = datetime.now()
        if self.url is None:
            raise Exception("No task URL set")
        done = False
        while not done:
            res = requests.get(
                self.url,
                cookies={"sessionId": self._client.session_id},
                timeout=timeout.total_seconds() if timeout is not None else None,
            )
            res.raise_for_status()
            data = res.json()
            if data["status"] == "running":
                n = datetime.now() - start
                if timeout is not None and (n > timeout or n + interval > timeout):
                    return None
                sleep(interval.total_seconds())
            else:
                done = True
                self.results_list = data["results"]
                self.status = data["status"]
        return self.results(wait=False)

    def results(self, wait=True, *args, **kw):
        if wait and len(self.results_list) == 0:
            self.wait(*args, **kw)
        if self.status == "running":
            return None
        msg = self.results_list[-1]
        if self.status == "error":
            raise Exception(msg["error"])
        r = msg.get("lastMessage", {}).get("content")
        if isinstance(r, list) and len(r) == 1 and r[-1]["type"] == "text":
            r = r[-1]["text"]
        return r


class TaskRunner(StrEnum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


@dataclass
class Task:
    """
    mcp.run task
    """

    _client: "Client"
    """
    Embedded mcp.run client
    """

    name: str
    """
    Task name
    """

    slug: str
    """
    Task full identifier
    """

    runner: TaskRunner
    """
    LLM provider for the task
    """

    model: str
    """
    LLM model
    """

    prompt: str
    """
    Task prompt
    """

    settings: dict
    """
    Task settings
    """

    created_at: datetime
    modified_at: datetime

    @property
    def profile(self) -> str:
        """
        Get the task profile name
        """
        return self.slug.split("/")[1]

    def signed_url(self) -> str:
        """
        Get a signed URL for a task
        """
        url = self._client.api.task_signed_url(self.profile, self.name)
        self._client.logger.info(f"Creating signed url for {self.slug}")
        res = requests.post(url, cookies={"sessionId": self._client.session_id})
        res.raise_for_status()
        data = res.json()
        return data["url"]

    def run(
        self,
        data: dict | None = None,
        signed_url: str | None = None,
        run_id: str | None = None,
    ) -> TaskRun:
        """
        Run a task with the given input data
        """
        if signed_url is None:
            signed_url = self.signed_url()

        if data is None:
            data = {}

        # Setup request headers
        headers = {}
        if run_id is not None:
            headers["run-id"] = run_id

        # Send call to signed url
        res = requests.post(signed_url, headers=headers, json=data)
        res.raise_for_status()
        url = res.json()["url"]

        # Get task run details
        res = requests.get(url, cookies={"sessionId": self._client.session_id})
        res.raise_for_status()
        data = res.json()
        return TaskRun(
            _client=self._client,
            _task=self,
            name=data["name"],
            status=data["status"],
            results_list=data.get("results", []),
            created_at=datetime.fromisoformat(data["created_at"]),
            modified_at=datetime.fromisoformat(data["modified_at"]),
            url=url,
        )
