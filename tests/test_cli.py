import builtins
import sys

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

def test_cli_creates_multiple_tasks(monkeypatch, capsys):
    # Mock GitHub
    import gt.github as gh

    monkeypatch.setattr(gh, "resolve_repo", lambda repo: repo or "alice/proj")
    monkeypatch.setattr(gh, "fetch_issue", lambda repo, n: Issue(number=n, title=f"Title {n}", body="Body", html_url=f"http://i/{n}"))

    # Mock Todoist with counter
    import gt.todoist as td

    calls = {"n": 0}

    class DummyClient:
        def __init__(self, token=None):
            pass

        def add_task(self, **kwargs):
            calls["n"] += 1
            return td.TodoistTask(id=f"t{calls['n']}", content=kwargs["content"], url=f"http://t/{calls['n']}")

        def last_backend(self):
            return "sdk"

    monkeypatch.setattr(td, "TodoistClient", DummyClient)

    rc = cli.main(["101", "102", "103", "--repo", "alice/proj"])  # multiple numbers
    out = capsys.readouterr().out
    assert rc == 0
    assert calls["n"] == 3
    assert out.count("created:") == 3


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


def test_cli_main_labels_and_strip_and_open(monkeypatch, capsys):
    # Mock GitHub
    import gt.github as gh

    monkeypatch.setattr(gh, "resolve_repo", lambda repo: repo or "alice/proj")
    monkeypatch.setattr(
        gh,
        "fetch_issue",
        lambda repo, n: Issue(
            number=n,
            title="Title",
            body="Some `code`\n```\nblock\n```",
            html_url="http://i",
            labels=["bug", "p1"],
        ),
    )

    # Spy open_url
    opened = {}
    # Patch open_url where it's referenced in cli
    monkeypatch.setattr(cli, "open_url", lambda url: opened.setdefault("url", url))

    # Dummy Todoist client capturing params
    import gt.todoist as td

    class DummyClient:
        def __init__(self, token=None):
            pass

        def add_task(self, **kwargs):
            # Ensure labels forwarded and markdown stripped in description
            assert kwargs["labels"] == ["bug", "p1"]
            assert "block" not in kwargs["description"]
            assert "http://i" in kwargs["description"]
            return td.TodoistTask(id="t2", content=kwargs["content"], url="http://t")

        def last_backend(self):
            return "rest"

    monkeypatch.setattr(td, "TodoistClient", DummyClient)

    rc = cli.main(["123", "--repo", "alice/proj", "--labels-as-tags", "--strip-markdown", "--open", "-v"])
    out = capsys.readouterr()
    assert rc == 0
    assert "created: t2" in out.out
    assert opened.get("url") == "http://t"
    assert "Using Todoist rest" in out.err


def test_cli_fetch_issue_error(monkeypatch, capsys):
    import gt.github as gh

    monkeypatch.setattr(gh, "resolve_repo", lambda repo: "alice/p")

    def boom(*a, **k):
        raise RuntimeError("fail")

    monkeypatch.setattr(gh, "fetch_issue", boom)

    rc = cli.main(["1"])
    out = capsys.readouterr()
    assert rc == 1
    assert "Error: fail" in out.err


def test_auth_non_interactive_requires_token(monkeypatch, capsys):
    # Simulate non-tty
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
    monkeypatch.setattr(sys.stdout, "isatty", lambda: False)

    p = cli.build_auth_parser()
    args = p.parse_args(["todoist"])  # no --token
    rc = cli.run_auth(args)
    out = capsys.readouterr()
    assert rc == 2
    assert "--token is required" in out.err


def test_auth_interactive_empty_token(monkeypatch, capsys):
    # Pretend interactive terminal
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)
    # getpass returns empty -> error path
    import getpass

    monkeypatch.setattr(getpass, "getpass", lambda prompt="": "")

    p = cli.build_auth_parser()
    args = p.parse_args(["todoist"])  # no --token triggers interactive
    rc = cli.run_auth(args)
    out = capsys.readouterr()
    assert rc == 2
    assert "빈 토큰" in out.err


def test_auth_interactive_save_file_and_config(monkeypatch, capsys):
    # Interactive session
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)

    # Provide token and choose file (f), then choose to set project (y)
    import getpass

    monkeypatch.setattr(getpass, "getpass", lambda prompt="": "tok")
    answers = iter(["f", "y"])  # save to file; then set project now
    monkeypatch.setattr(builtins, "input", lambda *a, **k: next(answers))

    # Short-circuit project selection flow
    called = {"ok": False}
    monkeypatch.setattr(cli, "run_config_project_interactive", lambda clear=False: called.__setitem__("ok", True) or 0)

    p = cli.build_auth_parser()
    args = p.parse_args(["todoist"])  # triggers interactive
    rc = cli.run_auth(args)
    assert rc == 0
    assert called["ok"] is True


def test_config_project_clear(monkeypatch, capsys):
    rc = cli.run_config_project_interactive(clear=True)
    out = capsys.readouterr()
    assert rc == 0
    assert "default project cleared" in out.out


def test_config_project_no_items(monkeypatch, capsys):
    # Force no projects; show backend message
    import gt.todoist as td

    class DummyClient:
        def last_backend(self):
            return "rest"

        def list_projects(self):
            return []

    monkeypatch.setattr(td, "TodoistClient", lambda *a, **k: DummyClient())
    rc = cli.run_config_project_interactive(clear=False, show_backend=True)
    out = capsys.readouterr()
    assert rc == 1
    assert "Using Todoist rest" in out.err
