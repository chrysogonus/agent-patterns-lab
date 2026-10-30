"""A local vLLM server through its OpenAI-compatible API (research R9)."""

from dataclasses import replace
from typing import Any

import httpx
import openai
from langchain_core.outputs import ChatResult
from langchain_openai import ChatOpenAI

from apl.runner.settings import Settings


class VLLMChat(ChatOpenAI):
    """ChatOpenAI that keeps vLLM's separate reasoning field for display.

    It goes to `additional_kwargs["reasoning_content"]`, which ChatOpenAI never sends back, so
    capturing it does not change what an architecture sends.
    """

    def _create_chat_result(
        self,
        response: dict[str, Any] | openai.BaseModel,
        generation_info: dict[str, Any] | None = None,
    ) -> ChatResult:
        result = super()._create_chat_result(response, generation_info)
        data = response if isinstance(response, dict) else response.model_dump()
        for generation, choice in zip(result.generations, data["choices"], strict=True):
            message = choice["message"]
            reasoning = message.get("reasoning") or message.get("reasoning_content")
            if reasoning:
                generation.message.additional_kwargs["reasoning_content"] = reasoning
        return result


def server_context(base_url: str, transport: httpx.BaseTransport | None = None) -> int | None:
    """The served model's context length (`max_model_len`), or None if the server is not there."""
    try:
        with httpx.Client(transport=transport, timeout=5) as client:
            response = client.get(base_url.rstrip("/") + "/models")
            response.raise_for_status()
            return int(response.json()["data"][0]["max_model_len"])
    except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError):
        return None


def with_server_context(
    settings: Settings, transport: httpx.BaseTransport | None = None
) -> Settings:
    """For a vLLM model, the settings with the server's context length; others unchanged."""
    if not settings.model.startswith("vllm:"):
        return settings
    context = server_context(settings.base_url, transport)
    if context is None:
        raise ValueError(f"cannot reach the vLLM server at {settings.base_url}")
    return replace(settings, num_ctx=context)
