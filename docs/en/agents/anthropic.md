# Anthropic SDK / Claude Code

Mock My AI speaks Anthropic **Messages** (`/v1/messages`).

## Connection

| Field | Local | Demo |
|-------|-------|------|
| Base URL | `http://127.0.0.1:8000` | `https://aimock.fishmaple.cn` |
| Auth | `x-api-key: <key>` | |
| Version header | `anthropic-version: 2023-06-01` (optional for mock) | |
| Path | `POST /v1/messages` (also `/anthropic/v1/messages`) | |
| Models | `GET /anthropic/v1/models` | |
| Sample key | `sk-ant-mock-anthropic-demo-key-0123456789` | |

## Python SDK

```bash
pip install anthropic
```

```python
import anthropic

client = anthropic.Anthropic(
    base_url="http://127.0.0.1:8000",
    api_key="sk-ant-mock-anthropic-demo-key-0123456789",
)

msg = client.messages.create(
    model="claude-sonnet-4-5",
    max_tokens=256,
    messages=[{"role": "user", "content": "ping"}],
)
print(msg.content)
```

## Claude Code

Set the Anthropic-compatible base and key in your Claude Code / Anthropic env (names vary by version), for example:

```bash
export ANTHROPIC_BASE_URL=http://127.0.0.1:8000
export ANTHROPIC_API_KEY=sk-ant-mock-anthropic-demo-key-0123456789
# or a console-issued key
```

If your build expects a `/v1` suffix, use `http://127.0.0.1:8000` as root — paths already include `/v1/messages`.

## Curl

```bash
curl -s http://127.0.0.1:8000/v1/messages \
  -H "x-api-key: sk-ant-mock-anthropic-demo-key-0123456789" \
  -H "anthropic-version: 2023-06-01" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-sonnet-4-5",
    "max_tokens": 128,
    "messages": [{"role": "user", "content": "ping"}]
  }'
```

Thinking blocks use `"type": "thinking"`. Tool use uses `"type": "tool_use"`.

See also: [API shape](../api/anthropic.md)
