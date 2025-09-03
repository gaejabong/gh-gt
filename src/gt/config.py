from __future__ import annotations

import json
import os
import stat
from typing import Any, Dict, Optional


def _config_path() -> str:
    if os.name == "nt":
        base = os.getenv("APPDATA", os.path.expanduser("~\\AppData\\Roaming"))
        return os.path.join(base, "gh-gt", "config.json")
    else:
        base = os.getenv("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
        return os.path.join(base, "gh-gt", "config.json")


def _ensure_parent_dir(path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)


def _chmod_600(path: str) -> None:
    try:
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
    except Exception:
        pass


def read_config() -> Dict[str, Any]:
    path = _config_path()
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except Exception:
        return {}


def write_config(data: Dict[str, Any]) -> None:
    path = _config_path()
    _ensure_parent_dir(path)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)
        f.write("\n")
    _chmod_600(path)


def get_default_project_id() -> Optional[str]:
    return read_config().get("default_project_id")


def set_default_project_id(project_id: Optional[str]) -> None:
    cfg = read_config()
    if project_id:
        cfg["default_project_id"] = project_id
    else:
        cfg.pop("default_project_id", None)
    write_config(cfg)

