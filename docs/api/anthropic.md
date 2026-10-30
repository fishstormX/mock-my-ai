# Anthropic-compatible API

| Method | Path |
|--------|------|
| GET | `/anthropic/v1/models` |
| POST | `/v1/messages` |
| POST | `/anthropic/v1/messages` |

Auth: `x-api-key: sk-ant-mock-...` (or Bearer).

Thinking blocks use `"type": "thinking"`. Tool use uses `"type": "tool_use"`.
