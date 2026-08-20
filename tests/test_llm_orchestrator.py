from __future__ import annotations

import os

import pytest

from cradle.ai import available_orchestrators, get_orchestrator
from cradle.contracts.errors import NotConfiguredError
from cradle.registry import discover

pytest.importorskip("litellm")


def _adapter(entry_point_name: str):
    for plugin in discover("ai_model_adapter"):
        if plugin.entry_point_name == entry_point_name:
            return plugin.instance
    pytest.skip(f"'{entry_point_name}' orchestration adapter is not installed")


@pytest.fixture(autouse=True)
def _no_api_keys(monkeypatch):
    """Every test in this file runs as if the researcher configured
    nothing — proving the optional/graceful path is real, not theoretical,
    regardless of what happens to be set in the ambient environment.
    """
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)


@pytest.mark.parametrize("entry_point_name", ["claude", "openrouter"])
def test_adapter_refuses_without_a_key_and_makes_no_network_call(entry_point_name, monkeypatch):
    adapter = _adapter(entry_point_name)
    assert adapter.is_configured is False

    # If predict() tried to reach the network anyway, this would raise a
    # connection error instead of NotConfiguredError, catching the bug
    # a naive "just call litellm and hope" implementation would have.
    def _fail_if_called(*args, **kwargs):
        raise AssertionError(f"{entry_point_name} adapter made a network call without a key")

    monkeypatch.setattr("litellm.completion", _fail_if_called)

    with pytest.raises(NotConfiguredError) as exc_info:
        adapter.predict({"task": "hello"})

    message = str(exc_info.value)
    assert adapter.api_key_env_var in message
    assert adapter.signup_url in message


def test_both_providers_are_registered_and_independently_swappable():
    names = {o.name for o in available_orchestrators()}
    assert {"claude", "openrouter"} <= names


def test_get_orchestrator_lists_every_option_when_none_configured():
    with pytest.raises(NotConfiguredError) as exc_info:
        get_orchestrator()
    message = str(exc_info.value)
    assert "ANTHROPIC_API_KEY" in message
    assert "OPENROUTER_API_KEY" in message


def test_get_orchestrator_returns_whichever_provider_has_a_key(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "fake-key-for-testing-config-path-only")
    adapter = get_orchestrator()
    assert adapter.name == "openrouter"


def test_get_orchestrator_honors_explicit_preference_when_both_configured(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-testing-config-path-only")
    monkeypatch.setenv("OPENROUTER_API_KEY", "fake-key-for-testing-config-path-only")
    assert get_orchestrator(prefer="openrouter").name == "openrouter"
    assert get_orchestrator(prefer="claude").name == "claude"


@pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY") and not os.environ.get("OPENROUTER_API_KEY"),
    reason="no real API key configured in this environment — this is the optional live path",
)
def test_live_call_with_a_real_key_if_one_happens_to_be_configured():
    """Only runs if a researcher actually configured a real key — proves
    the live path works too, without requiring one to exist for the rest
    of the suite (or this session) to pass.
    """
    adapter = get_orchestrator()
    result = adapter.predict({"task": "Reply with exactly one word: pong"})
    assert result["output"]["content"]
    assert result["provenance"]["model"] == adapter.name
