# Hermes & generic OpenAI-compatible clients

Any tool that accepts a custom OpenAI base URL works the same way (Hermes, LiteLLM, Continue, OpenWebUI, custom agents, …).

## Connection

| Field | Value |
|-------|-------|
| Base URL | `http://127.0.0.1:8000/v1` or `https://aimock.fishmaple.cn/v1` |
| API key | sample / console Bearer key |
| Chat Completions | `POST {base}/chat/completions` |
| Models | `GET {base}/models` |
| Stream | `"stream": true` → SSE |

## Checklist

1. Set **base URL** to include `/v1` (most OpenAI clones expect this).
2. Set **API key** to `sk-mock-openai-demo-key-0123456789abcdef` or a console key.
3. Pick a model id from `/v1/models` (e.g. `gpt-4o-mini`).
4. Send `ping` once — expect `pong`.

## Environment variables (common pattern)

```bash
export OPENAI_BASE_URL=http://127.0.0.1:8000/v1
export OPENAI_API_KEY=sk-mock-openai-demo-key-0123456789abcdef
```

Some apps use `OPENAI_API_BASE` instead of `OPENAI_BASE_URL` — check the agent docs.

## Curl (generic)

```bash
curl -s "$OPENAI_BASE_URL/chat/completions" \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-4o-mini","messages":[{"role":"user","content":"ping"}]}'
```

## Hermes

If Hermes (or a similar harness) has a provider JSON/YAML:

```yaml
provider: openai
base_url: https://aimock.fishmaple.cn/v1
api_key: sk-mock-openai-demo-key-0123456789abcdef
model: gpt-4o-mini
```

Adjust field names to match Hermes’ schema; the HTTP contract above is what Mock My AI implements.
