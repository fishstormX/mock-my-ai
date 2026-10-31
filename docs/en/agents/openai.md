# OpenAI Python / JS SDK

Point the official OpenAI SDK at Mock My AI. Same paths under `/v1`.

## Connection

| Field | Local | Demo |
|-------|-------|------|
| `base_url` | `http://127.0.0.1:8000/v1` | `https://aimock.fishmaple.cn/v1` |
| `api_key` | sample or console key | same |
| Auth header | `Authorization: Bearer …` | |
| Chat path | `POST /v1/chat/completions` | |
| Responses path | `POST /v1/responses` | |
| Models | `GET /v1/models` | |

## Python

```bash
pip install openai
```

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://127.0.0.1:8000/v1",  # or https://aimock.fishmaple.cn/v1
    api_key="sk-mock-openai-demo-key-0123456789abcdef",
)

r = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "ping"}],
)
print(r.choices[0].message.content)  # → pong (custom Q&A)

# Streaming
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

See also: [API shape](../api/openai.md) · [Codex CLI](codex.md)
