# Agent integration overview

This page is the contract every client needs: **base URL**, **auth header**, **model id**, and **stream**.

## Environments

| Name | Root | OpenAI-compatible `/v1` |
|------|------|-------------------------|
| Local | `http://127.0.0.1:8000` | `http://127.0.0.1:8000/v1` |
| Demo | `https://aimock.fishmaple.cn` | `https://aimock.fishmaple.cn/v1` |

Health: `GET /healthz`  
Interactive OpenAPI: `/api/docs`  
MkDocs (this site): `/docs/`

## Authentication

| Client family | Header / query | Sample value |
|---------------|----------------|--------------|
| OpenAI / Codex / Hermes | `Authorization: Bearer <key>` | `sk-mock-openai-demo-key-0123456789abcdef` |
| Anthropic / Claude Code | `x-api-key: <key>` (Bearer also accepted) | `sk-ant-mock-anthropic-demo-key-0123456789` |
| Gemini | `x-goog-api-key: <key>` or `?key=` | `AIzaMockGeminiDemoKey0123456789abcdef` |

Create private keys in the web **Console** after sign-up. Console keys are scoped to your account (request logs are isolated per key owner).

## Endpoints by family

| Family | Methods |
|--------|---------|
| OpenAI | `GET /v1/models`, `POST /v1/chat/completions`, `POST /v1/completions`, `POST /v1/responses` |
| Anthropic | `POST /v1/messages`, `POST /anthropic/v1/messages`, `GET /anthropic/v1/models` |
| Gemini | `POST /v1beta/models/{model}:generateContent`, `GET /v1beta/models` (also under `/gemini/…`) |

## Streaming (SSE)

Send `"stream": true` on chat completions or Responses.  
Response `Content-Type: text/event-stream` with `data: …` lines ending in `data: [DONE]`.

```bash
curl -N http://127.0.0.1:8000/v1/chat/completions \
  -H "Authorization: Bearer sk-mock-openai-demo-key-0123456789abcdef" \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-4o-mini","stream":true,"messages":[{"role":"user","content":"hello"}]}'
```

## Custom Q&A: `ping` → `pong`

`data/corpus/custom_qa.json` matches `(?i)\bping\b` and returns `pong`. Useful as a smoke test for any agent:

```bash
curl -s http://127.0.0.1:8000/v1/chat/completions \
  -H "Authorization: Bearer sk-mock-openai-demo-key-0123456789abcdef" \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-4o-mini","messages":[{"role":"user","content":"ping"}]}'
```

## Suggested models

Any id from `GET /v1/models` works. Common picks:

- OpenAI-style: `gpt-4o-mini`, `gpt-4o`
- Anthropic-style: `claude-sonnet-4-5`
- Gemini-style: `gemini-2.5-flash`

## Request log retention (console)

- Only **your** API keys appear in Console → Request logs  
- Kept **6 hours**, **max 20 rows per key**  
- Expand a row for full request / response JSON (secrets stored as prefixes only)
