# Agent 接入总览

所有客户端共用这份契约：**Base URL**、**鉴权头**、**模型 ID**、**是否流式**。

## 环境

| 名称 | 根地址 | OpenAI 兼容 `/v1` |
|------|------|-------------------------|
| 本地 | `http://127.0.0.1:8000` | `http://127.0.0.1:8000/v1` |
| 演示站 | `https://aimock.fishmaple.cn` | `https://aimock.fishmaple.cn/v1` |

健康检查：`GET /healthz`  
交互式 OpenAPI：`/api/docs`  
本站文档：`/docs/`

## 鉴权

| 客户端系列 | Header / 查询参数 | 示例值 |
|---------------|----------------|--------------|
| OpenAI / Codex / Hermes | `Authorization: Bearer <key>` | `sk-mock-openai-demo-key-0123456789abcdef` |
| Anthropic / Claude Code | `x-api-key: <key>`（也接受 Bearer） | `sk-ant-mock-anthropic-demo-key-0123456789` |
| Gemini | `x-goog-api-key: <key>` 或 `?key=` | `AIzaMockGeminiDemoKey0123456789abcdef` |

注册后可在网页 **控制台** 创建私有密钥。控制台密钥归属账号（请求日志按密钥所有者隔离）。

## 按系列的接口

| 系列 | 方法 |
|--------|---------|
| OpenAI | `GET /v1/models`、`POST /v1/chat/completions`、`POST /v1/completions`、`POST /v1/responses` |
| Anthropic | `POST /v1/messages`、`POST /anthropic/v1/messages`、`GET /anthropic/v1/models` |
| Gemini | `POST /v1beta/models/{model}:generateContent`、`GET /v1beta/models`（另有 `/gemini/…`） |

## 流式（SSE）

在 chat completions 或 Responses 上设 `"stream": true`。  
响应 `Content-Type: text/event-stream`，`data: …` 行，以 `data: [DONE]` 结束。

```bash
curl -N http://127.0.0.1:8000/v1/chat/completions \
  -H "Authorization: Bearer sk-mock-openai-demo-key-0123456789abcdef" \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-4o-mini","stream":true,"messages":[{"role":"user","content":"hello"}]}'
```

## 自定义 Q&A：`ping` → `pong`

`data/corpus/custom_qa.json` 匹配 `(?i)\bping\b` 并返回 `pong`，适合做任意 Agent 的冒烟：

```bash
curl -s http://127.0.0.1:8000/v1/chat/completions \
  -H "Authorization: Bearer sk-mock-openai-demo-key-0123456789abcdef" \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-4o-mini","messages":[{"role":"user","content":"ping"}]}'
```

## 推荐模型 ID

`GET /v1/models` 里任意 ID 都可用。常用：

- OpenAI 风格：`gpt-4o-mini`、`gpt-4o`
- Anthropic 风格：`claude-sonnet-4-5`
- Gemini 风格：`gemini-2.5-flash`

## 请求日志保留（控制台）

- 控制台「请求日志」**只显示你自己的密钥**流量  
- 保留 **6 小时**，**每个密钥最多 20 条**  
- 展开行可看完整请求 / 响应 JSON（密钥只存前缀）
