from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Dict, Optional
from collections.abc import Iterable

from .keychain import get_token
from .util import log_debug


@dataclass
class TodoistTask:
    id: str
    content: str
    url: Optional[str] = None


class TodoistClient:
    def __init__(self, token: Optional[str] = None) -> None:
        self.token = token or get_token()
        if not self.token:
            raise RuntimeError(
                "Todoist token not found. Run 'gh gt auth todoist --token <TOKEN> --save keychain' or set TODOIST_API_TOKEN."
            )

        self._lib_client = None
        self._default_backend = "rest"
        self._last_backend: Optional[str] = None
        try:
            from todoist_api_python.api import TodoistAPI  # type: ignore

            self._lib_client = TodoistAPI(self.token)
            self._default_backend = "sdk"
        except Exception as e:
            log_debug(f"todoist-api-python unavailable, will use REST fallback: {e}")

    def add_task(
        self,
        *,
        content: str,
        description: Optional[str] = None,
        project_id: Optional[str] = None,
        section_id: Optional[str] = None,
        priority: Optional[int] = None,
        due_string: Optional[str] = None,
        labels: Optional[list[str]] = None,
    ) -> TodoistTask:
        if self._lib_client is not None:
            log_debug("Todoist backend: sdk")
            self._last_backend = "sdk"
            try:
                task = self._lib_client.add_task(
                    content=content,
                    description=description,
                    project_id=project_id,
                    section_id=section_id,
                    priority=priority,
                    due_string=due_string,
                    labels=labels,
                )
                return TodoistTask(id=str(task.id), content=task.content, url=getattr(task, "url", None))
            except Exception as e:
                raise RuntimeError(f"Todoist add_task failed: {e}")

        # Fallback: direct REST
        log_debug("Todoist backend: rest")
        self._last_backend = "rest"
        import requests  # type: ignore

        headers = {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}
        payload: Dict[str, Any] = {"content": content}
        if description:
            payload["description"] = description
        if project_id:
            payload["project_id"] = project_id
        if section_id:
            payload["section_id"] = section_id
        if priority:
            payload["priority"] = priority
        if due_string:
            payload["due_string"] = due_string
        if labels:
            payload["labels"] = labels

        resp = requests.post("https://api.todoist.com/rest/v2/tasks", headers=headers, json=payload, timeout=20)
        if resp.status_code >= 400:
            detail = resp.text
            raise RuntimeError(f"Todoist API error {resp.status_code}: {detail}")
        data = resp.json()
        return TodoistTask(id=str(data.get("id")), content=data.get("content", ""), url=data.get("url"))

    def list_projects(self) -> list[dict[str, str]]:
        """Return a list of projects with 'id' and 'name' keys."""
        # Try SDK first; normalize shapes; on any issue, fall back to REST.
        if self._lib_client is not None:
            try:
                raw = self._lib_client.get_projects()
                # Normalize any iterable (e.g., ResultsPaginator) and flatten one level
                if isinstance(raw, Iterable) and not isinstance(raw, (str, bytes, dict)):
                    seq = list(raw)
                else:
                    seq = [raw]
                flat: list[object] = []
                for item in seq:
                    if isinstance(item, Iterable) and not isinstance(item, (str, bytes, dict)):
                        flat.extend(list(item))
                    else:
                        flat.append(item)

                out: list[dict[str, str]] = []
                for p in flat:
                    if hasattr(p, "id") and hasattr(p, "name"):
                        out.append({"id": str(getattr(p, "id")), "name": str(getattr(p, "name"))})
                    elif isinstance(p, dict):
                        pid = p.get("id")
                        name = p.get("name")
                        if pid and name:
                            out.append({"id": str(pid), "name": str(name)})

                log_debug(
                    f"SDK get_projects normalized: items={len(out)} (raw_type={type(raw).__name__}, first_type={(type(flat[0]).__name__ if flat else 'none')})",
                )
                if out:
                    log_debug("Todoist backend (projects): sdk")
                    self._last_backend = "sdk"
                    return out
                else:
                    log_debug("SDK get_projects returned no usable items; falling back to REST")
            except Exception as e:
                log_debug(f"SDK get_projects error: {e}; falling back to REST")

        # REST fallback
        log_debug("Todoist backend (projects): rest")
        self._last_backend = "rest"
        import requests  # type: ignore

    def last_backend(self) -> str:
        return self._last_backend or self._default_backend

        headers = {"Authorization": f"Bearer {self.token}"}
        resp = requests.get("https://api.todoist.com/rest/v2/projects", headers=headers, timeout=20)
        if resp.status_code >= 400:
            raise RuntimeError(f"Todoist API error {resp.status_code}: {resp.text}")
        items = resp.json() or []
        out: list[dict[str, str]] = []
        for it in items:
            if isinstance(it, dict):
                pid = it.get("id")
                name = it.get("name")
                if pid and name:
                    out.append({"id": str(pid), "name": str(name)})
        return out
