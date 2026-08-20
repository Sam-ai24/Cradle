from __future__ import annotations

import hashlib
from pathlib import Path

from cradle.knowledge.http import _get_bytes

#: A persistent, on-disk cache for large bulk downloads (DepMap's ~100MB
#: CSVs, scPerturb's 46-120MB h5ad files) that would be wasteful to
#: re-fetch on every call — unlike the small per-entity REST responses
#: the other Layer 6 connectors handle, these sources hand back whole
#: files. Persists across runs (not a tempdir) since the whole point is
#: avoiding repeat downloads of the same multi-hundred-megabyte file.
CACHE_DIR = Path.home() / ".cradle" / "cache"


def cached_download(url: str, *, timeout: float = 120.0) -> Path:
    """Download `url` to the cache directory, keyed by a hash of the URL,
    and return the local path — skipping the download entirely if a
    previous call already fetched it.
    """
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_key = hashlib.sha256(url.encode("utf-8")).hexdigest()[:24]
    suffix = Path(url).suffix or ".bin"
    cache_path = CACHE_DIR / f"{cache_key}{suffix}"

    if not cache_path.exists():
        body, _ = _get_bytes(url, {}, timeout)
        cache_path.write_bytes(body)

    return cache_path
