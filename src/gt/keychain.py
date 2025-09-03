from __future__ import annotations

import json
import os
import stat
from dataclasses import dataclass
from typing import Optional, Tuple

from .util import is_ci, log_debug


SERVICE = "gh-gt"
ACCOUNT = "default"
ITEM = "todoist_token"


def _config_path() -> str:
    if os.name == "nt":
        base = os.getenv("APPDATA", os.path.expanduser("~\\AppData\\Roaming"))
        return os.path.join(base, "gh-gt", "config.json")
    else:
        base = os.getenv("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
        return os.path.join(base, "gh-gt", "config.json")


def _ensure_parent_dir(path: str) -> None:
    parent = os.path.dirname(path)
    os.makedirs(parent, exist_ok=True)


def _chmod_600(path: str) -> None:
    try:
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
    except Exception:
        pass


def get_token() -> Optional[str]:
    # 1) env
    token = os.getenv("TODOIST_API_TOKEN") or os.getenv("TODOIST_TOKEN")
    if token:
        return token

    # 2) keychain via keyring
    try:
        import keyring  # type: ignore

        token = keyring.get_password(SERVICE, ITEM)
        if token:
            return token
    except Exception as e:
        log_debug(f"keyring unavailable: {e}")

    # 3) file config
    path = _config_path()
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            t = data.get("todoist_token")
            if isinstance(t, str) and t:
                return t
    except FileNotFoundError:
        return None
    except Exception as e:
        log_debug(f"failed to read config file: {e}")
    return None


def save_token(token: str, where: str = "keychain") -> Tuple[bool, str]:
    if is_ci():
        return False, "CI detected; refusing to save token. Use env vars."

    where = (where or "").lower()
    if where not in {"keychain", "file", "auto", ""}:
        return False, "invalid save target (use: keychain|file|auto)"
    target = where or "auto"

    if target in ("keychain", "auto"):
        try:
            import keyring  # type: ignore

            keyring.set_password(SERVICE, ITEM, token)
            return True, "saved to keychain"
        except Exception as e:
            if target == "keychain":
                return False, f"failed to save to keychain: {e}"
            log_debug(f"keychain save failed; falling back to file: {e}")

    # file fallback
    try:
        path = _config_path()
        _ensure_parent_dir(path)
        data = {"todoist_token": token}
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f)
            f.write("\n")
        _chmod_600(path)
        return True, f"saved to file: {path}"
    except Exception as e:
        return False, f"failed to save to file: {e}"


def unset_token() -> list[str]:
    messages: list[str] = []
    # keychain
    try:
        import keyring  # type: ignore

        try:
            keyring.delete_password(SERVICE, ITEM)
            messages.append("deleted from keychain")
        except keyring.errors.PasswordDeleteError:  # type: ignore
            pass
        except Exception as e:
            messages.append(f"keychain delete failed: {e}")
    except Exception:
        pass

    # file
    try:
        path = _config_path()
        if os.path.exists(path):
            os.remove(path)
            messages.append("deleted config file")
    except Exception as e:
        messages.append(f"file delete failed: {e}")

    if not messages:
        messages.append("no stored token found")
    return messages


def show_status() -> str:
    env = "set" if (os.getenv("TODOIST_API_TOKEN") or os.getenv("TODOIST_TOKEN")) else "unset"

    kc = "unknown"
    try:
        import keyring  # type: ignore

        kc_val = keyring.get_password(SERVICE, ITEM)
        kc = "present" if kc_val else "absent"
    except Exception:
        kc = "unavailable"

    path = _config_path()
    file_state = "present" if os.path.exists(path) else "absent"

    return f"env={env}, keychain={kc}, file={file_state}"
