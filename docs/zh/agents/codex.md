# Codex CLI

Codex 走 OpenAI 兼容的 Chat Completions 或 Responses。把自定义 provider 指到 Mock My AI。

## 连接参数

| 字段 | 值 |
|-------|-------|
| Base URL | `http://127.0.0.1:8000/v1` 或 `https://aimock.fishmaple.cn/v1` |
| 鉴权 | 通过 `env_key` 或内联 `http_headers` 发 Bearer |
| `wire_api` | `chat` → `/v1/chat/completions` · `responses` → `/v1/responses` |
| 模型 | 例如 `gpt-4o-mini` |

## `~/.codex/config.toml`（chat）

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

导出密钥（示例或控制台）：

```bash
export AIMOCK_API_KEY=sk-mock-openai-demo-key-0123456789abcdef
codex --profile aimock
```

## Responses 协议

```toml
[model_providers.aimock]
name = "Mock My AI"
base_url = "https://aimock.fishmaple.cn/v1"
env_key = "AIMOCK_API_KEY"
wire_api = "responses"
```

Codex 会以 SSE 调用 `/v1/responses`（`stream: true`）。

## 不用 env_key、直接 Bearer

部分环境只认 `http_headers`（不读 `env_key`）。可写成：

```toml
[model_providers.aimock]
name = "Mock My AI"
base_url = "http://127.0.0.1:8000/v1"
wire_api = "chat"
http_headers = { Authorization = "Bearer sk-mock-openai-demo-key-0123456789abcdef" }
```

若使用 `env_key`，请确保进程环境里真有 `AIMOCK_API_KEY`。

## 冒烟

让 Codex 发送 `ping`，期望自定义 Q&A 返回 `pong`。
