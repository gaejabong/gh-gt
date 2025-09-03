import sys
import types

import gt.keychain as kc


def test_file_save_and_get(monkeypatch, tmp_path):
    path = tmp_path / "config.json"
    monkeypatch.setattr(kc, "_config_path", lambda: str(path))
    # Remove env to force non-env loading
    monkeypatch.delenv("TODOIST_API_TOKEN", raising=False)
    monkeypatch.delenv("TODOIST_TOKEN", raising=False)

    ok, msg = kc.save_token("hello", where="file")
    assert ok
    token = kc.get_token()
    assert token == "hello"


def test_get_token_prefers_env(monkeypatch):
    monkeypatch.setenv("TODOIST_API_TOKEN", "env-token")
    monkeypatch.delenv("TODOIST_TOKEN", raising=False)
    assert kc.get_token() == "env-token"


def test_save_token_ci_guard(monkeypatch):
    # Force CI guard
    # keychain module imported is_ci symbol; patch there
    monkeypatch.setattr(kc, "is_ci", lambda: True)
    ok, msg = kc.save_token("x", where="file")
    assert not ok
    assert "CI detected" in msg


def test_keyring_roundtrip(monkeypatch):
    # Install fake keyring module
    class FakeKeyring:
        def __init__(self):
            self.store = {}

        class errors:  # noqa: N801 - mimic keyring.errors
            class PasswordDeleteError(Exception):
                pass

        def set_password(self, service, item, token):
            self.store[(service, item)] = token

        def get_password(self, service, item):
            return self.store.get((service, item))

        def delete_password(self, service, item):
            if (service, item) in self.store:
                del self.store[(service, item)]
            else:
                raise FakeKeyring.errors.PasswordDeleteError()

    mod = FakeKeyring()
    m = types.ModuleType("keyring")
    m.set_password = mod.set_password
    m.get_password = mod.get_password
    m.delete_password = mod.delete_password
    class E:  # errors submodule
        class PasswordDeleteError(Exception):
            pass
    m.errors = E
    sys.modules["keyring"] = m

    # Ensure no env wins
    monkeypatch.delenv("TODOIST_API_TOKEN", raising=False)
    monkeypatch.delenv("TODOIST_TOKEN", raising=False)

    ok, _ = kc.save_token("ring", where="keychain")
    assert ok
    assert kc.get_token() == "ring"
    msgs = kc.unset_token()
    assert any("keychain" in s or "deleted" in s for s in msgs)


def test_show_status_outputs(monkeypatch):
    # Ensure deterministic
    monkeypatch.delenv("TODOIST_API_TOKEN", raising=False)
    monkeypatch.delenv("TODOIST_TOKEN", raising=False)
    out = kc.show_status()
    assert "env=unset" in out


def test_unset_token_file_deleted_message(monkeypatch, tmp_path):
    # Point to temp config file
    path = tmp_path / "config.json"
    path.write_text("{\n}\n", encoding="utf-8")
    monkeypatch.setattr(kc, "_config_path", lambda: str(path))

    # Make keyring import fail to exercise file-only path
    sys.modules.pop("keyring", None)

    msgs = kc.unset_token()
    assert any("deleted config file" in m for m in msgs)
