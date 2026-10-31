# Gemini generateContent

兼容 Google Generative Language 的 **generateContent**（`/v1beta`）。

## 连接参数

| 字段 | 本地 | 演示站 |
|-------|-------|------|
| Base URL | `http://127.0.0.1:8000` | `https://aimock.fishmaple.cn` |
| 鉴权 | `x-goog-api-key: <key>` 或 `?key=` | |
| 路径 | `POST /v1beta/models/{model}:generateContent` | |
| 列表 | `GET /v1beta/models` | |
| 示例密钥 | `AIzaMockGeminiDemoKey0123456789abcdef` | |

另有镜像路径 `/gemini/v1beta/...`。

## Curl

```bash
curl -s "http://127.0.0.1:8000/v1beta/models/gemini-2.5-flash:generateContent" \
  -H "x-goog-api-key: AIzaMockGeminiDemoKey0123456789abcdef" \
  -H "Content-Type: application/json" \
  -d '{
    "contents": [{"role": "user", "parts": [{"text": "ping"}]}]
  }'
```

## Python（google-genai 类主机覆盖）

具体参数因库版本而异，通用做法：

1. 把 API endpoint / client host 设为 `http://127.0.0.1:8000`
2. 使用 `AIzaMock…` 或控制台密钥
3. 调用 `models/{id}:generateContent`，body 为 Gemini content parts

```bash
curl -s "https://aimock.fishmaple.cn/v1beta/models/gemini-2.5-flash:generateContent?key=AIzaMockGeminiDemoKey0123456789abcdef" \
  -H "Content-Type: application/json" \
  -d '{"contents":[{"role":"user","parts":[{"text":"Hello"}]}]}'
```

另见：[协议形态](../api/gemini.md)
