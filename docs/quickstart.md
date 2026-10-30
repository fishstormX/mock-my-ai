# Quickstart

## Run with uv

```bash
uv sync --extra docs
uv run python scripts/generate_corpus.py   # if corpus missing
uv run mock-my-ai
# → http://127.0.0.1:8000
```

## Run with Docker Compose

```bash
docker compose up --build
```

## Sample keys

| Provider family | Sample key |
|-----------------|------------|
| OpenAI-style | `sk-mock-openai-demo-key-0123456789abcdef` |
| Anthropic-style | `sk-ant-mock-anthropic-demo-key-0123456789` |
| Gemini-style | `AIzaMockGeminiDemoKey0123456789abcdef` |

Any key starting with `sk-mock-`, `sk-ant-mock-`, or `AIzaMock` is accepted.

## Curl examples

### OpenAI Chat Completions

```bash
curl -s http://127.0.0.1:8000/v1/chat/completions \
  -H "Authorization: Bearer sk-mock-openai-demo-key-0123456789abcdef" \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-4o-mini","messages":[{"role":"user","content":"你好，介绍一下天气"}],"mock_thinking":true}'
```

### Anthropic Messages

```bash
curl -s http://127.0.0.1:8000/v1/messages \
  -H "x-api-key: sk-ant-mock-anthropic-demo-key-0123456789" \
  -H "anthropic-version: 2023-06-01" \
  -H "Content-Type: application/json" \
  -d '{"model":"claude-sonnet-4-5","max_tokens":256,"messages":[{"role":"user","content":"Hello"}]}'
```

### Gemini generateContent

```bash
curl -s "http://127.0.0.1:8000/v1beta/models/gemini-2.5-flash:generateContent" \
  -H "x-goog-api-key: AIzaMockGeminiDemoKey0123456789abcdef" \
  -H "Content-Type: application/json" \
  -d '{"contents":[{"role":"user","parts":[{"text":"Bonjour"}]}]}'
```

### List models

```bash
curl -s http://127.0.0.1:8000/v1/models \
  -H "Authorization: Bearer sk-mock-openai-demo-key-0123456789abcdef"
```
