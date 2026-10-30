"""The shared run settings (Constitution I), from the environment and `.env` (research R11)."""

import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path

_KEY_VARS = {"openai": "OPENAI_API_KEY", "anthropic": "ANTHROPIC_API_KEY"}
PROVIDER_DEFAULT = "provider default"


@dataclass(frozen=True, slots=True)
class Settings:
    model: str = "ollama:qwen3:8b"
    temperature: float | None = None  # None: not sent, the provider's default applies
    reasoning_effort: str | None = None
    token_cap: int = 600_000
    max_retries: int = 4
    timeout_s: float = 120
    price_input: float | None = None  # USD per 1M tokens; for the dry run's cost only
    price_output: float | None = None
    # Ollama's context window. Its own default (4,096) would silently cut off long episodes.
    num_ctx: int = 16_384
    # Output tokens per model call. Without it a local model can think endlessly inside one call,
    # where neither the token cap (checked after a call) nor the timeout (per read) can stop it.
    max_output_tokens: int = 4096

    def record(self) -> dict[str, object]:
        """The run conditions, as stored in run.json and compared by the report."""
        from apl.kit import prompt_fingerprint

        return {
            "model": self.model,
            "temperature": PROVIDER_DEFAULT if self.temperature is None else self.temperature,
            "reasoning_effort": self.reasoning_effort or PROVIDER_DEFAULT,
            "token_cap": self.token_cap,
            "max_retries": self.max_retries,
            "timeout_s": self.timeout_s,
            "num_ctx": self.num_ctx if self.model.startswith("ollama:") else None,
            "max_output_tokens": self.max_output_tokens,
            "prompt_fingerprint": prompt_fingerprint(),
        }


def read_env_file(path: Path) -> dict[str, str]:
    """`KEY=VALUE` lines; `#` comments, blank lines, quotes and `export ` are allowed."""
    if not path.is_file():
        return {}
    values = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip().removeprefix("export ")
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
            value = value[1:-1]
        values[key.strip()] = value
    return values


def _env_file(environ: Mapping[str, str]) -> Path:
    return Path(environ.get("APL_ENV_FILE") or os.environ.get("APL_ENV_FILE") or ".env")


def load_settings(environ: Mapping[str, str] | None = None) -> Settings:
    """Settings from `environ`, over the `.env` file.

    Without `environ`, the `.env` values are also put into `os.environ` (without overriding),
    so the provider client finds its API key there.
    """
    if environ is None:
        for key, value in read_env_file(_env_file(os.environ)).items():
            os.environ.setdefault(key, value)
        values: Mapping[str, str] = os.environ
    else:
        values = {**read_env_file(_env_file(environ)), **environ}
    price_input = _parse(values, "APL_PRICE_INPUT", float, _non_negative, _PRICE_RULE)
    price_output = _parse(values, "APL_PRICE_OUTPUT", float, _non_negative, _PRICE_RULE)
    if (price_input is None) != (price_output is None):
        raise ValueError(f"APL_PRICE_INPUT and APL_PRICE_OUTPUT: {_PRICE_RULE}")
    effort = values.get("APL_REASONING_EFFORT") or None
    if effort is not None and not effort.strip():
        raise ValueError(f"APL_REASONING_EFFORT={effort!r}: must be non-empty string when set")
    token_cap = _parse(values, "APL_TOKEN_CAP", int, _positive, "int > 0")
    max_retries = _parse(values, "APL_MAX_RETRIES", int, _non_negative, "int ≥ 0")
    timeout_s = _parse(values, "APL_TIMEOUT_S", float, _positive, "number > 0")
    num_ctx = _parse(values, "APL_NUM_CTX", int, _positive, "int > 0")
    max_output = _parse(values, "APL_MAX_OUTPUT_TOKENS", int, _positive, "int > 0")
    defaults = Settings()
    return Settings(
        model=values.get("APL_MODEL") or defaults.model,
        temperature=_parse(values, "APL_TEMPERATURE", float, _non_negative, "float ≥ 0 when set"),
        reasoning_effort=effort,
        token_cap=defaults.token_cap if token_cap is None else token_cap,
        max_retries=defaults.max_retries if max_retries is None else max_retries,
        timeout_s=defaults.timeout_s if timeout_s is None else timeout_s,
        num_ctx=defaults.num_ctx if num_ctx is None else num_ctx,
        max_output_tokens=defaults.max_output_tokens if max_output is None else max_output,
        price_input=price_input,
        price_output=price_output,
    )


_PRICE_RULE = "USD per 1M tokens, ≥ 0; both or neither"


def _positive(value: float) -> bool:
    return value > 0


def _non_negative(value: float) -> bool:
    return value >= 0


def _parse[N: (int, float)](
    values: Mapping[str, str],
    name: str,
    kind: Callable[[str], N],
    ok: Callable[[N], bool],
    rule: str,
) -> N | None:
    """The variable's value, `None` if unset or empty; `ValueError` naming it if invalid."""
    raw = values.get(name)
    if not raw:
        return None
    try:
        value = kind(raw)
    except ValueError:
        raise ValueError(f"{name}={raw!r}: must be {rule}") from None
    if not ok(value):
        raise ValueError(f"{name}={raw!r}: must be {rule}")
    return value


def required_key_var(model: str) -> str | None:
    """The API key variable the model's provider needs, if the runner knows it."""
    return _KEY_VARS.get(model.partition(":")[0]) if ":" in model else None
