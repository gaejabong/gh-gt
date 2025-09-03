import os
import sys
import types
from pathlib import Path
import pytest

# Ensure src/ is importable as package root before tests import modules
_root = Path(__file__).resolve().parents[1]
_src = _root / "src"
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))


@pytest.fixture(autouse=True)
def _set_env_token(monkeypatch):
    # Ensure no interactive prompts during tests
    monkeypatch.setenv("TODOIST_API_TOKEN", "test-token")
    # Force keyring to a null backend to avoid touching real keychain
    monkeypatch.setenv("PYTHON_KEYRING_BACKEND", "keyring.backends.null.Keyring")
    # Ensure SDK is disabled in tests that expect REST fallback
    monkeypatch.setenv("GT_DISABLE_TODOIST_SDK", "1")
    # Avoid CI guard interfering with save_token during unit tests
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)


class Completed:
    def __init__(self, stdout="", stderr="", returncode=0):
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode


@pytest.fixture
def completed():
    return Completed
