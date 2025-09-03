import sys

from gt.util import strip_markdown
import gt.util as util


def test_strip_markdown_basic():
    md = "# Title\nSome `code` and a [link](http://ex).\n> quote\n````\nblock\n````"
    out = strip_markdown(md)
    assert "Title" in out
    assert "code" in out
    assert "link (http://ex)" in out
    assert "quote" in out
    assert "block" not in out  # code block removed


def test_run_gh_builds_command(monkeypatch):
    calls = {}

    def fake_run(cmd, stdout=None, stderr=None, text=None):  # noqa: A002
        calls["cmd"] = cmd
        class R:
            returncode = 0
            stdout = "{}"
            stderr = ""
        return R()

    monkeypatch.setattr(util.subprocess, "run", fake_run)
    res = util.run_gh(["--version"])  # just to exercise
    assert calls["cmd"][0] == "gh"
    assert res.returncode == 0


def test_open_url_branches(monkeypatch):
    opened = {"args": None}

    def fake_run(args, check=False):
        opened["args"] = args

    # darwin
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(util.subprocess, "run", fake_run)
    util.open_url("http://x")
    assert opened["args"][0] == "open"

    # linux
    monkeypatch.setattr(sys, "platform", "linux")
    util.open_url("http://y")
    assert opened["args"][0] == "xdg-open"


def test_log_debug_writes_when_enabled(monkeypatch, capsys):
    monkeypatch.setenv("GH_GT_DEBUG", "1")
    util.log_debug("hello")
    err = capsys.readouterr().err
    assert "hello" in err


def test_open_url_windows_branch(monkeypatch):
    opened = {}
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(util.os, "name", "nt", raising=False)
    monkeypatch.setattr(util.os, "startfile", lambda url: opened.setdefault("url", url), raising=False)
    util.open_url("http://w")
    assert opened.get("url") == "http://w"
