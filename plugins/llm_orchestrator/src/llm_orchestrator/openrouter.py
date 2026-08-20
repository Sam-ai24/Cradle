from __future__ import annotations

from llm_orchestrator.base import LiteLLMOrchestrationAdapter

#: OpenRouter's catalog changes over time; a researcher can override this
#: (CRADLE_OPENROUTER_MODEL) to point at whichever model/provider they
#: prefer without a code change — that's the whole point of routing
#: through OpenRouter rather than one fixed vendor.
DEFAULT_MODEL = "openrouter/anthropic/claude-sonnet-4.5"


def build_adapter() -> LiteLLMOrchestrationAdapter:
    return LiteLLMOrchestrationAdapter(
        name="openrouter",
        model_env_var="CRADLE_OPENROUTER_MODEL",
        default_model=DEFAULT_MODEL,
        api_key_env_var="OPENROUTER_API_KEY",
        signup_url="https://openrouter.ai/keys",
    )
