"""The vLLM provider: reasoning shown but never sent back, context read from the server (R9)."""

import httpx
import pytest
from langchain_core.messages import AIMessage
from langchain_core.utils import convert_to_secret_str
from langchain_openai.chat_models.base import _convert_message_to_dict
from openai.types.chat import ChatCompletion

from apl.runner.run import default_model_factory
from apl.runner.settings import Settings
from apl.runner.vllm import VLLMChat, server_context, with_server_context


def _completion(**message_extra: object) -> ChatCompletion:
    return ChatCompletion.model_validate(
        {
            "id": "x",
            "object": "chat.completion",
            "created": 0,
            "model": "qwen3.5-9b",
            "choices": [
                {
                    "index": 0,
                    "finish_reason": "tool_calls",
                    "message": {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "id": "c1",
                                "type": "function",
                                "function": {"name": "look", "arguments": "{}"},
                            }
                        ],
                        **message_extra,
                    },
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        }
    )


def _model() -> VLLMChat:
    key = convert_to_secret_str("EMPTY")
    return VLLMChat(model="qwen3.5-9b", base_url="http://localhost:8001/v1", api_key=key)


def test_reasoning_is_captured() -> None:
    for field in ("reasoning", "reasoning_content"):
        result = _model()._create_chat_result(_completion(**{field: "I should look first."}))
        message = result.generations[0].message
        assert message.additional_kwargs["reasoning_content"] == "I should look first."
        assert isinstance(message, AIMessage) and message.tool_calls[0]["name"] == "look"


def test_no_reasoning_adds_nothing() -> None:
    message = _model()._create_chat_result(_completion()).generations[0].message
    assert "reasoning_content" not in message.additional_kwargs


def test_reasoning_is_not_sent_back() -> None:
    message = AIMessage("", additional_kwargs={"reasoning_content": "secret thoughts"})
    assert "secret thoughts" not in str(_convert_message_to_dict(message))


def test_factory_builds_a_vllm_model() -> None:
    model = default_model_factory(Settings(temperature=0.2), [])
    assert isinstance(model, VLLMChat)
    assert model.model_name == "qwen3.5-9b" and model.max_tokens == 1024
    assert str(model.openai_api_base) == "http://localhost:8001/v1"
    assert model.temperature == 0.2


def test_server_context() -> None:
    def answer(request: httpx.Request) -> httpx.Response:
        assert request.url == "http://localhost:8001/v1/models"
        return httpx.Response(200, json={"data": [{"id": "qwen3.5-9b", "max_model_len": 8192}]})

    assert server_context("http://localhost:8001/v1", httpx.MockTransport(answer)) == 8192


def test_server_context_unreachable() -> None:
    def fail(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused")

    assert server_context("http://localhost:8001/v1", httpx.MockTransport(fail)) is None


def test_with_server_context() -> None:
    def answer(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": [{"max_model_len": 8192}]})

    settings = with_server_context(Settings(), httpx.MockTransport(answer))
    assert settings.num_ctx == 8192 and settings.record()["num_ctx"] == 8192
    ollama = Settings(model="ollama:qwen3:8b")
    assert with_server_context(ollama) is ollama  # no request for other providers


def test_with_server_context_unreachable() -> None:
    def fail(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused")

    with pytest.raises(ValueError, match="cannot reach the vLLM server"):
        with_server_context(Settings(), httpx.MockTransport(fail))
