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

