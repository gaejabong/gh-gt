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

