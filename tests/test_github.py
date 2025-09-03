import json

import gt.github as gh


def test_resolve_repo_detects(monkeypatch, completed):
    def fake_run(args):
        data = {"owner": {"login": "alice"}, "name": "proj"}
        return completed(stdout=json.dumps(data))

    monkeypatch.setattr(gh, "run_gh", fake_run)
    assert gh.resolve_repo(None) == "alice/proj"


def test_fetch_issue(monkeypatch, completed):
    def fake_run(args):
        data = {
            "title": "Bug: thing",
            "body": "Details here",
            "html_url": "https://github.com/x/y/issues/1",
            "labels": [{"name": "bug"}],
        }
        return completed(stdout=json.dumps(data))

    monkeypatch.setattr(gh, "run_gh", fake_run)
    issue = gh.fetch_issue("alice/proj", 1)
    assert issue.number == 1
    assert issue.title.startswith("Bug")
    assert issue.html_url.endswith("/1")
    assert issue.labels == ["bug"]


def test_resolve_repo_error(monkeypatch, completed):
    def bad_run(args):
        return completed(stdout="", stderr="boom", returncode=1)

    monkeypatch.setattr(gh, "run_gh", bad_run)
    try:
        gh.resolve_repo(None)
        assert False, "expected error"
    except RuntimeError as e:
        assert "boom" in str(e)


def test_fetch_issue_errors(monkeypatch, completed):
    # Non-zero exit
    monkeypatch.setattr(gh, "run_gh", lambda args: completed(stdout="", stderr="nope", returncode=1))
    try:
        gh.fetch_issue("a/b", 1)
        assert False
    except RuntimeError as e:
        assert "nope" in str(e)

    # Missing mandatory fields
    def missing_fields(args):
        data = {"body": "b", "labels": []}  # no title/html_url
        return completed(stdout=json.dumps(data))

    monkeypatch.setattr(gh, "run_gh", missing_fields)
    try:
        gh.fetch_issue("a/b", 2)
        assert False
    except RuntimeError as e:
        assert "missing" in str(e)
