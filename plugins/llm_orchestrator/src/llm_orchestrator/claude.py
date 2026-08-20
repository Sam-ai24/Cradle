from __future__ import annotations

from llm_orchestrator.base import LiteLLMOrchestrationAdapter

#: A researcher can point this at any Claude model without a code change.
DEFAULT_MODEL = "claude-sonnet-5"


def build_adapter() -> LiteLLMOrchestrationAdapter:
    return LiteLLMOrchestrationAdapter(
        name="claude",
        model_env_var="CRADLE_CLAUDE_MODEL",
        default_model=DEFAULT_MODEL,
        api_key_env_var="ANTHROPIC_API_KEY",
        signup_url="https://console.anthropic.com/settings/keys",
    )
