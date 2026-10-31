# Hermes 与通用 OpenAI 兼容客户端

凡是支持自定义 OpenAI Base URL 的工具都可以按同一方式接入（Hermes、LiteLLM、Continue、OpenWebUI、自研 Agent 等）。

## 连接参数

| 字段 | 值 |
|-------|-------|
| Base URL | `http://127.0.0.1:8000/v1` 或 `https://aimock.fishmaple.cn/v1` |
| API key | 示例 / 控制台 Bearer 密钥 |
| Chat Completions | `POST {base}/chat/completions` |
| 模型列表 | `GET {base}/models` |
| 流式 | `"stream": true` → SSE |

## 检查清单

1. **Base URL** 带上 `/v1`（多数 OpenAI 兼容客户端如此约定）。
2. **API key** 使用 `sk-mock-openai-demo-key-0123456789abcdef` 或控制台密钥。
3. 从 `/v1/models` 选一个模型 ID（如 `gpt-4o-mini`）。
4. 发一次 `ping`，期望 `pong`。

## 常见环境变量

```bash
export OPENAI_BASE_URL=http://127.0.0.1:8000/v1
export OPENAI_API_KEY=sk-mock-openai-demo-key-0123456789abcdef
```

有的应用用 `OPENAI_API_BASE` 而不是 `OPENAI_BASE_URL`，以该 Agent 文档为准。

## Curl（通用）

```bash
curl -s "$OPENAI_BASE_URL/chat/completions" \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-4o-mini","messages":[{"role":"user","content":"ping"}]}'
```

## Hermes

若 Hermes（或类似 harness）使用 provider JSON/YAML：

```yaml
provider: openai
base_url: https://aimock.fishmaple.cn/v1
api_key: sk-mock-openai-demo-key-0123456789abcdef
model: gpt-4o-mini
```

字段名按 Hermes schema 调整；上面的 HTTP 契约即 Mock My AI 实现的内容。
