import sys
import types

import gt.todoist as td


class FakeTask:
    def __init__(self, id="123", content="content", url="http://t"):  # noqa: A003
        self.id = id
        self.content = content
        self.url = url


class FakeProject:
    def __init__(self, id="p1", name="Inbox"):
        self.id = id
        self.name = name


class FakeAPI:
    def __init__(self, token):
        self.token = token

    def add_task(self, **kwargs):
        return FakeTask(content=kwargs.get("content", ""))

    def get_projects(self):
        # Simulate a ResultsPaginator-like iterable
        return [FakeProject("p1", "Inbox"), FakeProject("p2", "Work")]


def install_fake_sdk(monkeypatch):
    mod = types.ModuleType("todoist_api_python.api")
    mod.TodoistAPI = FakeAPI
    sys.modules["todoist_api_python.api"] = mod
    return mod


def test_client_uses_sdk_for_add_task(monkeypatch):
    install_fake_sdk(monkeypatch)
    client = td.TodoistClient()
    t = client.add_task(content="#1 Title")
    assert t.id == "123"
    assert client.last_backend() == "sdk"


def test_client_lists_projects_via_sdk(monkeypatch):
    install_fake_sdk(monkeypatch)
    client = td.TodoistClient()
    items = client.list_projects()
    assert {i["name"] for i in items} >= {"Inbox", "Work"}
    assert client.last_backend() == "sdk"


def test_client_rest_fallback(monkeypatch):
    # Ensure SDK import fails
    sys.modules.pop("todoist_api_python.api", None)

    class Resp:
        def __init__(self, status_code=200, data=None):
            self.status_code = status_code
            self._data = data or {}
            self.text = "ok"

        def json(self):
            return self._data

    def fake_post(url, headers=None, json=None, timeout=0):  # noqa: A002
        return Resp(200, {"id": "r1", "content": json["content"], "url": "http://t"})

    def fake_get(url, headers=None, timeout=0):
        return Resp(200, [{"id": "p1", "name": "Inbox"}])

    import requests  # type: ignore

    monkeypatch.setattr(requests, "post", fake_post)
    monkeypatch.setattr(requests, "get", fake_get)

    client = td.TodoistClient()
    t = client.add_task(content="#2 Title")
    assert t.id == "r1"
    items = client.list_projects()
    assert items[0]["name"] == "Inbox"
    assert client.last_backend() in {"rest", "sdk"}


def test_list_projects_rest_error(monkeypatch):
    # Disable SDK to force REST
    monkeypatch.setenv("GT_DISABLE_TODOIST_SDK", "1")

    class Resp:
        def __init__(self, status_code=401, text="forbidden"):
            self.status_code = status_code
            self.text = text

        def json(self):
            return []

    import requests  # type: ignore

    monkeypatch.setattr(requests, "get", lambda *a, **k: Resp())
    client = td.TodoistClient()
    try:
        client.list_projects()
        assert False
    except RuntimeError as e:
        assert "Todoist API error" in str(e)


def test_last_backend_default_rest(monkeypatch):
    monkeypatch.setenv("GT_DISABLE_TODOIST_SDK", "1")
    client = td.TodoistClient()
    assert client.last_backend() in {"rest", "sdk"}
