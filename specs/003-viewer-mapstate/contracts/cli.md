# Contract: CLI and settings changes for M3

This contract adds to specs/002-runner-react/contracts/cli.md. Everything not listed here is
unchanged.

## `apl serve [--port N] [--execute]` (new)

- Starts the viewer on `127.0.0.1:N` (default 8765) and prints
  `Viewer: http://127.0.0.1:8765/ (model vllm:qwen3.5-9b; Ctrl-C to stop)`.
- Loads the settings once at start, from the environment and `.env`, exactly as `apl run` does.
  A settings error exits with code 2.
- For `vllm:`, it reads the context size from the server (research R9). If the server cannot be
  reached, it prints a warning and starts anyway. Browsing and replay work without a model, and
  starting an episode then fails with a shown provider error.
- `--execute` permits episodes with a provider that is not local (research R8). Local providers
  (`ollama:`, `vllm:`) need no flag.
- Ctrl-C stops the server. A running episode is stopped and saved as stopped before it exits
  (exit code 130).
- No packaging change is needed: `apl` is already the entry point.

## `apl run`

- `--arch` accepts `mapstate`.
- For `vllm:` models, the dry run shows `context  from the server (read at --execute)`, and
  `--execute` records the server's `max_model_len` as `num_ctx`.

## Settings (new and changed)

| Variable | Default | Meaning |
| --- | --- | --- |
| `APL_MODEL` | `vllm:qwen3.5-9b` (was `ollama:qwen3:8b`) | `provider:model`; providers `vllm`, `ollama`, `openai`, `anthropic` |
| `APL_BASE_URL` | `http://localhost:8001/v1` | The server for `vllm:` models. Recorded in the settings record as `base_url` (`null` for other providers) |
| `APL_MAX_OUTPUT_TOKENS` | 1,024 for `vllm:`, 4,096 otherwise | Output tokens per model call |
| `APL_NUM_CTX` | 16,384 | Still Ollama only. For `vllm:` the server's value is recorded |

`base_url` is not in the report's `COMPARED` list. The model name and `num_ctx` already
distinguish runs.

## Error classification (research R10)

| Provider error | M2 | M3 |
| --- | --- | --- |
| The prompt does not fit the context (vLLM 400 "maximum context length"; OpenAI `context_length_exceeded`) | Permanent: the run stops, exit 3 | Architecture failure: the episode ends `stopped` with `arch_error` "context window exceeded: …", and the run goes on |
| Other 400/401/403/404/422 | Permanent | Permanent (unchanged) |
| Other provider errors after retries | Infrastructure error | Infrastructure error (unchanged) |
