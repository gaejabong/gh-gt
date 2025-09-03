import os
import re
import shlex
import subprocess
import sys
from typing import Optional


def is_ci() -> bool:
    return os.getenv("CI") == "true" or os.getenv("GITHUB_ACTIONS") == "true"


def debug_enabled() -> bool:
    return bool(os.getenv("GH_GT_DEBUG"))


def log_debug(msg: str) -> None:
    if debug_enabled():
        sys.stderr.write(f"[gh-gt] {msg}\n")


def strip_markdown(md: str) -> str:
    # Minimal markdown stripper: remove code fences, images/links formatting, headings, emphasis
    text = re.sub(r"```[\s\S]*?```", "", md)  # code blocks
    text = re.sub(r"`([^`]*)`", r"\1", text)    # inline code
    text = re.sub(r"!?\[([^\]]+)\]\(([^\)]+)\)", r"\1 (\2)", text)  # images/links
    text = re.sub(r"^#+\\s*", "", text, flags=re.MULTILINE)  # headings
    text = re.sub(r"[*_]{1,3}([^*_]+)[*_]{1,3}", r"\1", text)  # emphasis
    text = re.sub(r"> +", "", text)  # blockquote markers
    return text.strip()


def open_url(url: str) -> None:
    try:
        if sys.platform == "darwin":
            subprocess.run(["open", url], check=False)
        elif os.name == "nt":
            os.startfile(url)  # type: ignore[attr-defined]
        else:
            subprocess.run(["xdg-open", url], check=False)
    except Exception:
        pass


def run_gh(args: list[str]) -> subprocess.CompletedProcess:
    cmd = ["gh", *args]
    log_debug("Running: " + shlex.join(cmd))
    return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
