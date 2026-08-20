from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Any

#: Identify Cradle to the public APIs it queries, per common API etiquette
#: (several of these services ask callers to set a real User-Agent).
_USER_AGENT = "Cradle/0.0 (+https://github.com/; research knowledge-layer connector)"
_DEFAULT_TIMEOUT = 20.0
_MAX_RETRIES = 3
_BACKOFF_BASE_SECONDS = 0.5


class HttpError(RuntimeError):
    def __init__(self, url: str, status: int | None, message: str) -> None:
        super().__init__(f"GET {url} failed ({status}): {message}")
        self.url = url
        self.status = status


def _is_transient(exc: Exception) -> bool:
    """A timeout, connection failure, or 5xx is worth retrying — a live
    public API blipping mid-request isn't a code bug (observed directly:
    a UniProt read timeout failed a conformance run, then succeeded on the
    very next attempt seconds later). A 4xx (bad request, not found,
    unauthorized) means retrying the identical request will fail the same
    way every time, so it's raised immediately instead.
    """
    if isinstance(exc, urllib.error.HTTPError):
        return exc.code >= 500
    return isinstance(exc, urllib.error.URLError)  # includes socket.timeout


def _get_bytes(url: str, headers: dict[str, str], timeout: float) -> tuple[bytes, int]:
    request = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT, **headers})
    last_exc: Exception | None = None

    for attempt in range(_MAX_RETRIES + 1):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.read(), response.status
        except urllib.error.HTTPError as exc:
            if not _is_transient(exc) or attempt == _MAX_RETRIES:
                raise HttpError(url, exc.code, exc.read().decode("utf-8", errors="replace")) from exc
            last_exc = exc
        except urllib.error.URLError as exc:
            if attempt == _MAX_RETRIES:
                raise HttpError(url, None, str(exc.reason)) from exc
            last_exc = exc
        time.sleep(_BACKOFF_BASE_SECONDS * (2**attempt))

    raise HttpError(url, None, str(last_exc))  # unreachable; satisfies type checkers


def get_text(url: str, *, headers: dict[str, str] | None = None, timeout: float = _DEFAULT_TIMEOUT) -> str:
    """GET `url` and return the raw response body as text — for the rare
    source (KEGG's flat-file REST API) that doesn't speak JSON.
    """
    body, _ = _get_bytes(url, headers or {}, timeout)
    return body.decode("utf-8", errors="replace")


def get_json(url: str, *, headers: dict[str, str] | None = None, timeout: float = _DEFAULT_TIMEOUT) -> Any:
    """GET `url` and parse the response body as JSON.

    Uses stdlib `urllib` rather than adding `requests` as a core dependency
    — every connector needs only a GET-and-parse-JSON, and that's exactly
    what the standard library already provides. Retries transient failures
    (timeouts, connection errors, 5xx) with backoff; a 4xx is raised
    immediately since retrying an identical bad request can't help.
    """
    body, status = _get_bytes(url, headers or {}, timeout)
    try:
        return json.loads(body)
    except json.JSONDecodeError as exc:
        raise HttpError(url, status, f"response was not valid JSON: {exc}") from exc
