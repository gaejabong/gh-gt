from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from typing import Optional

from .util import run_gh


@dataclass
class Issue:
    number: int
    title: str
    body: str
    html_url: str
    labels: list[str]


def resolve_repo(provided: Optional[str]) -> str:
    if provided:
        return provided
    # Use gh to detect from cwd
    proc = run_gh(["repo", "view", "--json", "owner,name"])
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "failed to detect repository; use --repo owner/repo")
    data = json.loads(proc.stdout)
    owner = data.get("owner", {}).get("login") or data.get("owner", {}).get("name") or data.get("owner")
    name = data.get("name")
    if not owner or not name:
        raise RuntimeError("could not resolve owner/name from gh repo view output")
    return f"{owner}/{name}"


def fetch_issue(repo: str, number: int) -> Issue:
    path = f"/repos/{repo}/issues/{number}"
    proc = run_gh([
        "api",
        "-H",
        "Accept: application/vnd.github+json",
        "-H",
        "X-GitHub-Api-Version: 2022-11-28",
        path,
    ])
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or f"failed to fetch issue {number}")
    data = json.loads(proc.stdout)
    title = data.get("title") or ""
    body = data.get("body") or ""
    html_url = data.get("html_url") or ""
    labels = [lbl.get("name", "") for lbl in data.get("labels", []) if isinstance(lbl, dict)]
    if not title or not html_url:
        raise RuntimeError("unexpected GitHub issue payload; missing title or html_url")
    return Issue(number=number, title=title, body=body, html_url=html_url, labels=labels)
