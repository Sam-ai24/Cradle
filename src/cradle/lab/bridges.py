"""Phase 12: bring-your-own-license bridges.

NAMD and ChimeraX are named in the roadmap as "optional bring-your-own-
license bridges for academic-only deployments, never bundled defaults" —
Cradle never ships or downloads either; a researcher who already has one
installed points Cradle at it. Neither has a PyPI package (confirmed
directly: `pip index versions namd`/`chimerax` both report no matching
distribution) and neither binary is available on this machine to test
against, so this module deliberately stays at the layer that *is*
verifiable without one: detecting a configured executable and confirming
it actually runs, tested for real against a real binary
(`tests/test_lab_bridges.py` uses the Python interpreter itself as the
stand-in executable). Translating a `cradle.md.MDManifest` into NAMD's own
PSF/parameter-file config format is real, non-trivial work this
deliberately does not attempt untested against the real engine — same
"don't ship untested complexity" rule Phase 11 applied to the Dockerfile,
just one step earlier in the pipeline.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from cradle.contracts.errors import NotConfiguredError


@dataclass
class BridgeStatus:
    name: str
    executable_path: str
    version_output: str


def _resolve_executable(name: str, env_var: str, fallback_names: list[str]) -> str:
    configured = os.environ.get(env_var)
    if configured:
        if shutil.which(configured) or Path(configured).exists():
            return configured
        raise NotConfiguredError(
            f"{env_var}='{configured}' is set but not a runnable executable — "
            f"check the path to your own {name} installation."
        )

    for candidate in fallback_names:
        found = shutil.which(candidate)
        if found:
            return found

    raise NotConfiguredError(
        f"'{name}' is an optional bring-your-own-license bridge — Cradle never bundles "
        f"or downloads it. Install {name} yourself (academic/non-commercial license, per "
        f"NOTICE.md), then set {env_var} to its executable path."
    )


def check_bridge(
    name: str,
    env_var: str,
    fallback_names: list[str],
    version_args: tuple[str, ...] = ("--version",),
) -> BridgeStatus:
    """Resolve `name`'s executable (via `env_var` or PATH) and confirm it
    actually runs, returning what it printed. Raises `NotConfiguredError`
    (the same skip-not-fail signal Phase 3/5's license/key gates use) if
    no executable is configured, or if a configured one fails to execute.
    """
    executable = _resolve_executable(name, env_var, fallback_names)
    try:
        result = subprocess.run(
            [executable, *version_args], capture_output=True, text=True, timeout=30
        )
    except OSError as exc:
        raise NotConfiguredError(f"found '{executable}' but could not execute it: {exc}") from exc

    return BridgeStatus(
        name=name,
        executable_path=executable,
        version_output=(result.stdout or result.stderr).strip(),
    )


def check_namd() -> BridgeStatus:
    """Best-effort default invocation, not verified against a real NAMD
    binary (unavailable in this environment) — NAMD historically prints a
    version banner and usage message when run with no arguments rather
    than accepting a `--version` flag, so `version_args` defaults to none;
    confirm this against your own installation and adjust if needed.
    """
    return check_bridge("namd", "CRADLE_NAMD_PATH", ["namd3", "namd2"], version_args=())


def check_chimerax() -> BridgeStatus:
    """Best-effort default invocation, not verified against a real
    ChimeraX binary (unavailable in this environment) — `--nogui --silent
    --exit` is ChimeraX's documented headless-script pattern; confirm
    against your own installation and adjust if needed.
    """
    return check_bridge(
        "chimerax",
        "CRADLE_CHIMERAX_PATH",
        ["chimerax", "ChimeraX"],
        version_args=("--nogui", "--silent", "--exit"),
    )
