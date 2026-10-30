# OpenAI-compatible API

Base URL: `http://127.0.0.1:8000`

Auth: `Authorization: Bearer sk-mock-...`

| Method | Path |
|--------|------|
| GET | `/v1/models` |
| GET | `/v1/models/{id}` |
| POST | `/v1/chat/completions` |
| POST | `/v1/completions` |
| POST | `/v1/responses` |

Usage includes `prompt_tokens_details.cached_tokens`. Reasoning may appear as `message.reasoning_content`.
