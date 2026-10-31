# Codex CLI

Codex talks OpenAI-compatible Chat Completions or Responses. Point a custom provider at Mock My AI.

## Connection

| Field | Value |
|-------|-------|
| Base URL | `http://127.0.0.1:8000/v1` or `https://aimock.fishmaple.cn/v1` |
| Auth | Bearer via `env_key` or inline `http_headers` |
| `wire_api` | `chat` → `/v1/chat/completions` · `responses` → `/v1/responses` |
| Model | e.g. `gpt-4o-mini` |

## `~/.codex/config.toml` (chat)

```toml
[model_providers.aimock]
name = "Mock My AI"
base_url = "http://127.0.0.1:8000/v1"
env_key = "AIMOCK_API_KEY"
wire_api = "chat"

[profiles.aimock]
model_provider = "aimock"
model = "gpt-4o-mini"
```

Export the key (sample or console):

```bash
export AIMOCK_API_KEY=sk-mock-openai-demo-key-0123456789abcdef
codex --profile aimock
```

## Responses wire API

```toml
[model_providers.aimock]
name = "Mock My AI"
base_url = "https://aimock.fishmaple.cn/v1"
env_key = "AIMOCK_API_KEY"
wire_api = "responses"
```

Codex will POST SSE to `/v1/responses` with `stream: true`.

## Bearer without env_key

Some setups only honor `http_headers` (not `env_key`). Prefer:

```toml
[model_providers.aimock]
name = "Mock My AI"
base_url = "http://127.0.0.1:8000/v1"
wire_api = "chat"
http_headers = { Authorization = "Bearer sk-mock-openai-demo-key-0123456789abcdef" }
```

Or ensure the process environment actually contains `AIMOCK_API_KEY` when using `env_key`.

## Smoke

Ask Codex to send `ping` — expect `pong` from custom Q&A.
