from __future__ import annotations

import os
from typing import Any

import litellm

from cradle.contracts.ai_model_adapter import ModelPrediction
from cradle.contracts.errors import NotConfiguredError

# LiteLLM otherwise prints its own "give feedback" banner + provider debug
# noise to stderr on every call; researchers who never configured a key
# shouldn't see chatter from a feature they haven't opted into.
litellm.suppress_debug_info = True


class MissingApiKeyError(NotConfiguredError):
    """Raised when a researcher hasn't supplied their own key for this
    provider. AI orchestration is entirely optional — every other Cradle
    layer (simulation, data, curation) works with none of these
    configured — so this is reported as a friendly, actionable message,
    not a stack trace, and the conformance runner treats it as a skip
    rather than a failure (Architecture, Layer 6/NOTICE.md: the same
    pattern already used for BioGRID's missing key and KEGG's license gate).
    """


class ProviderCallError(RuntimeError):
    """The provider rejected or failed the call for a reason other than a
    missing/invalid key (rate limit, bad request, provider outage, ...).
    """


class LiteLLMOrchestrationAdapter:
    """Reasoning/orchestration AI contract (Architecture, Layer 5), backed
    by LiteLLM so any of its 100+ providers can sit behind this same
    adapter shape without Cradle building its own router. This class is
    provider-agnostic; `claude.py` and `openrouter.py` each register one
    thin, named instance of it.

    Never touches raw tensors — the orchestration contract's job is to
    turn a natural-language task plus a tool manifest into a plan and
    structured tool calls into the other typed AI contracts (embedding,
    structure, ...), not to do biology math itself.
    """

    contract_type = "orchestration"

    def __init__(
        self,
        name: str,
        model_env_var: str,
        default_model: str,
        api_key_env_var: str,
        signup_url: str,
    ) -> None:
        self.name = name
        self.model = os.environ.get(model_env_var, default_model)
        self.api_key_env_var = api_key_env_var
        self.signup_url = signup_url

    @property
    def is_configured(self) -> bool:
        return bool(os.environ.get(self.api_key_env_var))

    def _require_api_key(self) -> str:
        api_key = os.environ.get(self.api_key_env_var)
        if not api_key:
            raise MissingApiKeyError(
                f"'{self.name}' is optional and currently off: no {self.api_key_env_var} "
                f"is set. To enable it, get a key from {self.signup_url} and set "
                f"{self.api_key_env_var} in your environment. Every other part of Cradle "
                f"(simulation, data, curation) works fully without this."
            )
        return api_key

    def predict(self, input: dict[str, Any]) -> ModelPrediction:
        api_key = self._require_api_key()

        task = input.get("task", "")
        tools = input.get("tools")
        messages = input.get("messages") or [{"role": "user", "content": task}]

        try:
            response = litellm.completion(
                model=self.model,
                messages=messages,
                tools=tools,
                api_key=api_key,
            )
        except litellm.AuthenticationError as exc:
            raise MissingApiKeyError(
                f"'{self.name}' rejected the credential in {self.api_key_env_var} — "
                f"check it's current and has the right permissions. ({exc})"
            ) from exc
        except Exception as exc:  # noqa: BLE001 - surface any other provider failure clearly
            raise ProviderCallError(f"'{self.name}' call failed: {exc}") from exc

        choice = response.choices[0]
        tool_calls = choice.message.tool_calls or []
        return {
            "output": {
                "content": choice.message.content,
                "tool_calls": [
                    {"name": call.function.name, "arguments": call.function.arguments}
                    for call in tool_calls
                ],
            },
            "provenance": {
                "model": self.name,
                "contract_type": self.contract_type,
                "provider_model_id": self.model,
                "finish_reason": choice.finish_reason,
            },
        }
