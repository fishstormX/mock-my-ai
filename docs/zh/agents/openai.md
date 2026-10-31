# OpenAI Python / JS SDK

把官方 OpenAI SDK 的地址指到 Mock My AI，路径仍是 `/v1`。

## 连接参数

| 字段 | 本地 | 演示站 |
|-------|-------|------|
| `base_url` | `http://127.0.0.1:8000/v1` | `https://aimock.fishmaple.cn/v1` |
| `api_key` | 示例密钥或控制台密钥 | 同左 |
| 鉴权头 | `Authorization: Bearer …` | |
| Chat | `POST /v1/chat/completions` | |
| Responses | `POST /v1/responses` | |
| 模型列表 | `GET /v1/models` | |

## Python

```bash
pip install openai
```

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://127.0.0.1:8000/v1",  # 或 https://aimock.fishmaple.cn/v1
    api_key="sk-mock-openai-demo-key-0123456789abcdef",
)

r = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "ping"}],
)
print(r.choices[0].message.content)  # → pong（自定义 Q&A）

# 流式
stream = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "hello"}],
    stream=True,
)
for chunk in stream:
    delta = chunk.choices[0].delta.content
    if delta:
        print(delta, end="")
```

## JavaScript / TypeScript

```bash
npm install openai
```

```js
import OpenAI from "openai";

const client = new OpenAI({
  baseURL: "http://127.0.0.1:8000/v1",
  apiKey: "sk-mock-openai-demo-key-0123456789abcdef",
});

const r = await client.chat.completions.create({
  model: "gpt-4o-mini",
  messages: [{ role: "user", content: "ping" }],
});
console.log(r.choices[0].message.content);
```

## Curl

```bash
curl -s http://127.0.0.1:8000/v1/chat/completions \
  -H "Authorization: Bearer sk-mock-openai-demo-key-0123456789abcdef" \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-4o-mini","messages":[{"role":"user","content":"ping"}]}'
```

另见：[协议形态](../api/openai.md) · [Codex CLI](codex.md)
