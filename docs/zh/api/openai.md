# OpenAI 兼容 API

| | 本地 | 演示站 |
|---|-------|------|
| 根地址 | `http://127.0.0.1:8000` | `https://aimock.fishmaple.cn` |
| 鉴权 | `Authorization: Bearer sk-mock-…` | |

| 方法 | 路径 |
|--------|------|
| GET | `/v1/models` |
| GET | `/v1/models/{id}` |
| POST | `/v1/chat/completions` |
| POST | `/v1/completions` |
| POST | `/v1/responses` |

Usage 含 `prompt_tokens_details.cached_tokens`。推理可能出现在 `message.reasoning_content`。  
流式：`"stream": true` → SSE。

接入指南：[OpenAI SDK](../agents/openai.md) · [Codex](../agents/codex.md)
