# OpenAI-compatible API

| | Local | Demo |
|---|-------|------|
| Root | `http://127.0.0.1:8000` | `https://aimock.fishmaple.cn` |
| Auth | `Authorization: Bearer sk-mock-…` | |

| Method | Path |
|--------|------|
| GET | `/v1/models` |
| GET | `/v1/models/{id}` |
| POST | `/v1/chat/completions` |
| POST | `/v1/completions` |
| POST | `/v1/responses` |

Usage includes `prompt_tokens_details.cached_tokens`. Reasoning may appear as `message.reasoning_content`.  
Streaming: `"stream": true` → SSE.

Agent guide: [OpenAI SDK](../agents/openai.md) · [Codex](../agents/codex.md)
