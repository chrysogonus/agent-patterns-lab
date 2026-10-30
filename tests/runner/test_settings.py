"""Shared run settings (data-model "Settings", research R2 and R11)."""

from pathlib import Path

import pytest

from apl.runner.settings import Settings, load_settings, required_key_var


def test_defaults() -> None:
    assert load_settings({}) == Settings(
        model="ollama:qwen3:8b",
        temperature=None,
        reasoning_effort=None,
        token_cap=600_000,
        max_retries=4,
        timeout_s=120,
        price_input=None,
        price_output=None,
        num_ctx=16_384,
    )


def test_every_variable_is_read() -> None:
    settings = load_settings(
        {
            "APL_MODEL": "anthropic:claude-haiku-5-5",
            "APL_TEMPERATURE": "0.5",
            "APL_REASONING_EFFORT": "none",
            "APL_TOKEN_CAP": "1000",
            "APL_MAX_RETRIES": "0",
            "APL_TIMEOUT_S": "2.5",
            "APL_PRICE_INPUT": "0.1",
            "APL_PRICE_OUTPUT": "0.5",
            "APL_NUM_CTX": "8192",
        }
    )
    assert settings == Settings(
        "anthropic:claude-haiku-5-5", 0.5, "none", 1000, 0, 2.5, 0.1, 0.5, 8192
    )


def test_env_file_is_parsed_and_the_environment_wins(tmp_path: Path) -> None:
    env = tmp_path / "test.env"
    env.write_text(
        "# a comment\n\n"
        "APL_MODEL='openai:gpt-6-sol'\n"
        'export APL_TOKEN_CAP="5000"\n'
        "APL_MAX_RETRIES = 7\n"
        "APL_TIMEOUT_S=30\n"
    )
    settings = load_settings({"APL_ENV_FILE": str(env), "APL_TIMEOUT_S": "60"})
    assert settings.model == "openai:gpt-6-sol"
    assert settings.token_cap == 5000
    assert settings.max_retries == 7
    assert settings.timeout_s == 60


def test_env_file_path_falls_back_to_the_process_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env = tmp_path / "other.env"
    env.write_text("APL_TOKEN_CAP=42\n")
    monkeypatch.setenv("APL_ENV_FILE", str(env))
    assert load_settings({}).token_cap == 42


@pytest.mark.parametrize(
    ("name", "value", "rule"),
    [
        ("APL_TEMPERATURE", "-1", "float ≥ 0 when set"),
        ("APL_TEMPERATURE", "warm", "float ≥ 0 when set"),
        ("APL_REASONING_EFFORT", "  ", "non-empty string when set"),
        ("APL_TOKEN_CAP", "0", "int > 0"),
        ("APL_TOKEN_CAP", "1.5", "int > 0"),
        ("APL_MAX_RETRIES", "-1", "int ≥ 0"),
        ("APL_TIMEOUT_S", "0", "number > 0"),
        ("APL_NUM_CTX", "0", "int > 0"),
        ("APL_PRICE_INPUT", "-0.1", "USD per 1M tokens, ≥ 0; both or neither"),
    ],
)
def test_invalid_values_name_the_variable(name: str, value: str, rule: str) -> None:
    environ = {name: value}
    if name == "APL_PRICE_INPUT":
        environ["APL_PRICE_OUTPUT"] = "0.5"
    with pytest.raises(ValueError, match=name) as error:
        load_settings(environ)
    assert rule in str(error.value)


def test_prices_come_in_pairs() -> None:
    with pytest.raises(ValueError, match="both or neither"):
        load_settings({"APL_PRICE_INPUT": "0.1"})


def test_record_marks_provider_defaults() -> None:
    record = load_settings({}).record()
    assert record["temperature"] == "provider default"
    assert record["reasoning_effort"] == "provider default"
    assert record["model"] == "ollama:qwen3:8b" and record["token_cap"] == 600_000
    assert record["num_ctx"] == 16_384
    assert Settings(model="openai:gpt-6-luna").record()["num_ctx"] is None
    assert isinstance(record["prompt_fingerprint"], str) and len(record["prompt_fingerprint"]) == 12
    assert "price_input" not in record  # prices are not run conditions


def test_required_key_var() -> None:
    assert required_key_var("openai:gpt-6-luna") == "OPENAI_API_KEY"
    assert required_key_var("anthropic:claude-haiku-5-5") == "ANTHROPIC_API_KEY"
    assert required_key_var("ollama:qwen3:8b") is None
