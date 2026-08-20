from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

#: Identify Cradle to the public APIs it queries, per common API etiquette
#: (several of these services ask callers to set a real User-Agent).
_USER_AGENT = "Cradle/0.0 (+https://github.com/; research knowledge-layer connector)"
_DEFAULT_TIMEOUT = 20.0


class HttpError(RuntimeError):
    def __init__(self, url: str, status: int | None, message: str) -> None:
        super().__init__(f"GET {url} failed ({status}): {message}")
        self.url = url
        self.status = status


def get_text(url: str, *, headers: dict[str, str] | None = None, timeout: float = _DEFAULT_TIMEOUT) -> str:
    """GET `url` and return the raw response body as text — for the rare
    source (KEGG's flat-file REST API) that doesn't speak JSON.
    """
    request = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT, **(headers or {})})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        raise HttpError(url, exc.code, exc.read().decode("utf-8", errors="replace")) from exc
    except urllib.error.URLError as exc:
        raise HttpError(url, None, str(exc.reason)) from exc


def get_json(url: str, *, headers: dict[str, str] | None = None, timeout: float = _DEFAULT_TIMEOUT) -> Any:
    """GET `url` and parse the response body as JSON.

    Uses stdlib `urllib` rather than adding `requests` as a core dependency
    — every connector needs only a GET-and-parse-JSON, and that's exactly
    what the standard library already provides.
    """
    request = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT, **(headers or {})})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read()
            status = response.status
    except urllib.error.HTTPError as exc:
        raise HttpError(url, exc.code, exc.read().decode("utf-8", errors="replace")) from exc
    except urllib.error.URLError as exc:
        raise HttpError(url, None, str(exc.reason)) from exc

    try:
        return json.loads(body)
    except json.JSONDecodeError as exc:
        raise HttpError(url, status, f"response was not valid JSON: {exc}") from exc
