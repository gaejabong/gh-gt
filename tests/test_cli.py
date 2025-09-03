import builtins

import gt.cli as cli


class Issue:
    def __init__(self, number=1, title="T", body="B", html_url="http://i", labels=None):
        self.number = number
        self.title = title
        self.body = body
        self.html_url = html_url
        self.labels = labels or []


def test_cli_creates_task_with_repo(monkeypatch, capsys):
    # Mock GitHub
    import gt.github as gh

    monkeypatch.setattr(gh, "resolve_repo", lambda repo: repo or "alice/proj")
    monkeypatch.setattr(gh, "fetch_issue", lambda repo, n: Issue(number=n, title="Title", body="Body", html_url="http://i"))

    # Mock Todoist
    import gt.todoist as td

    class DummyClient:
        def __init__(self, token=None):
            pass

        def add_task(self, **kwargs):
            return td.TodoistTask(id="t1", content=kwargs["content"], url="http://t")

        def last_backend(self):
            return "sdk"

    monkeypatch.setattr(td, "TodoistClient", DummyClient)

    rc = cli.main(["123", "--repo", "alice/proj"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "created: t1" in out


def test_config_project_interactive(monkeypatch, capsys, tmp_path):
    # Redirect config file path
    import gt.config as cfg

    cfg_path = tmp_path / "config.json"
    monkeypatch.setattr(cfg, "_config_path", lambda: str(cfg_path))

    # Fake projects and inputs
    import gt.todoist as td

    class DummyClient:
        def __init__(self, token=None):
            pass

        def list_projects(self):
            return [{"id": "p1", "name": "Inbox"}, {"id": "p2", "name": "Work"}]

        def last_backend(self):
            return "sdk"

    monkeypatch.setattr(td, "TodoistClient", DummyClient)
    # Simulate selecting first project
    answers = iter(["1"])  # choose 1
    monkeypatch.setattr(builtins, "input", lambda *a, **k: next(answers))

    rc = cli.main(["config", "project"])
    assert rc == 0
    # Verify saved
    data = cfg.read_config()
    assert data.get("default_project_id") == "p1"

