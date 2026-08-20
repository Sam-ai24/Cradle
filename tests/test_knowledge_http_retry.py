from __future__ import annotations

import io
import urllib.error

import pytest

from cradle.knowledge import http


class _FakeResponse:
    def __init__(self, body: bytes, status: int = 200) -> None:
        self._body = body
        self.status = status

    def read(self) -> bytes:
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False


def test_transient_url_error_is_retried_then_succeeds(monkeypatch):
    calls = {"count": 0}

    def fake_urlopen(request, timeout):
        calls["count"] += 1
        if calls["count"] < 3:
            raise urllib.error.URLError("timed out")
        return _FakeResponse(b'{"ok": true}')

    monkeypatch.setattr(http.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(http.time, "sleep", lambda seconds: None)  # don't actually wait in tests

    result = http.get_json("https://example.invalid/thing")
    assert result == {"ok": True}
    assert calls["count"] == 3


def test_server_error_is_retried(monkeypatch):
    calls = {"count": 0}

    def fake_urlopen(request, timeout):
        calls["count"] += 1
        if calls["count"] < 2:
            raise urllib.error.HTTPError(
                "https://example.invalid", 503, "Service Unavailable", {}, io.BytesIO(b"")
            )
        return _FakeResponse(b'{"ok": true}')

    monkeypatch.setattr(http.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(http.time, "sleep", lambda seconds: None)

    result = http.get_json("https://example.invalid/thing")
    assert result == {"ok": True}
    assert calls["count"] == 2


def test_not_found_is_raised_immediately_without_retrying(monkeypatch):
    calls = {"count": 0}

    def fake_urlopen(request, timeout):
        calls["count"] += 1
        raise urllib.error.HTTPError(
            "https://example.invalid", 404, "Not Found", {}, io.BytesIO(b"nope")
        )

    monkeypatch.setattr(http.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(http.time, "sleep", lambda seconds: pytest.fail("should not retry a 404"))

    with pytest.raises(http.HttpError) as exc_info:
        http.get_json("https://example.invalid/thing")

    assert calls["count"] == 1
    assert exc_info.value.status == 404


def test_persistent_transient_failure_eventually_raises(monkeypatch):
    def always_times_out(request, timeout):
        raise urllib.error.URLError("timed out")

    monkeypatch.setattr(http.urllib.request, "urlopen", always_times_out)
    monkeypatch.setattr(http.time, "sleep", lambda seconds: None)

    with pytest.raises(http.HttpError):
        http.get_json("https://example.invalid/thing")
