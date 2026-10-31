# 快速开始

## 用 uv 运行

```bash
git clone https://github.com/fishstormX/mock-my-ai.git
cd mock-my-ai
uv sync --extra docs
uv run python scripts/generate_corpus.py   # 若语料缺失
uv run mock-my-ai
# → http://127.0.0.1:8000
```

## Docker Compose

```bash
docker compose up --build
```

## 冒烟 curl

```bash
curl -s http://127.0.0.1:8000/v1/chat/completions \
  -H "Authorization: Bearer sk-mock-openai-demo-key-0123456789abcdef" \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-4o-mini","messages":[{"role":"user","content":"ping"}]}'
```

期望自定义 Q&A 返回包含 `pong`。

下一步：[Agent 总览](agents/overview.md)
