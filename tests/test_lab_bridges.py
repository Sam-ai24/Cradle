from __future__ import annotations

import sys

import pytest

from cradle.contracts.errors import NotConfiguredError
from cradle.lab.bridges import check_bridge


def test_check_bridge_finds_and_runs_a_real_configured_executable(monkeypatch):
    """No real NAMD/ChimeraX binary is available to test against, so this
    proves the *mechanism* — resolve via env var, then actually execute
    and capture output — against a real, always-present executable
    (this test's own Python interpreter) instead.
    """
    monkeypatch.setenv("CRADLE_TEST_BRIDGE_PATH", sys.executable)

    status = check_bridge(
        "test-bridge", "CRADLE_TEST_BRIDGE_PATH", fallback_names=[], version_args=("--version",)
    )

    assert status.executable_path == sys.executable
    assert "Python" in status.version_output


def test_check_bridge_raises_not_configured_when_env_var_unset(monkeypatch):
    monkeypatch.delenv("CRADLE_TEST_BRIDGE_PATH", raising=False)

    with pytest.raises(NotConfiguredError, match="bring-your-own-license"):
        check_bridge(
            "test-bridge",
            "CRADLE_TEST_BRIDGE_PATH",
            fallback_names=["definitely-not-a-real-executable-xyz"],
        )


def test_check_bridge_raises_not_configured_for_a_bogus_configured_path(monkeypatch):
    monkeypatch.setenv("CRADLE_TEST_BRIDGE_PATH", "definitely-not-on-path-xyz")

    with pytest.raises(NotConfiguredError, match="not a runnable executable"):
        check_bridge("test-bridge", "CRADLE_TEST_BRIDGE_PATH", fallback_names=[])


def test_check_bridge_raises_not_configured_for_a_real_but_unexecutable_file(
    monkeypatch, tmp_path
):
    """The configured path exists on disk (passes the first resolution
    check) but isn't a real executable — proves the second failure mode
    (execution itself failing) is caught too, not just a missing path.
    """
    not_executable = tmp_path / "not_a_real_binary"
    not_executable.write_text("not a real executable", encoding="utf-8")
    monkeypatch.setenv("CRADLE_TEST_BRIDGE_PATH", str(not_executable))

    with pytest.raises(NotConfiguredError, match="could not execute it"):
        check_bridge("test-bridge", "CRADLE_TEST_BRIDGE_PATH", fallback_names=[])
