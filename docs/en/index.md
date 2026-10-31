# Mock My AI — Agent integration

**Mock My AI** is an OpenAI / Anthropic / Gemini-compatible **mock API**.  
It never calls a real model provider. Use it to wire coding agents, SDKs, and CI.

| | Local | Demo |
|---|-------|------|
| **Base URL** | `http://127.0.0.1:8000` | `https://aimock.fishmaple.cn` |
| **OpenAI-style base** | `http://127.0.0.1:8000/v1` | `https://aimock.fishmaple.cn/v1` |
| **GitHub** | [fishstormX/mock-my-ai](https://github.com/fishstormX/mock-my-ai) | |

!!! warning "No real inference"
    Every completion is corpus / custom Q&A text. Treat replies as mock data.

## Sample API keys

| Family | Key |
|--------|-----|
| OpenAI-style | `sk-mock-openai-demo-key-0123456789abcdef` |
| Anthropic-style | `sk-ant-mock-anthropic-demo-key-0123456789` |
| Gemini-style | `AIzaMockGeminiDemoKey0123456789abcdef` |

Console-issued keys also work. Prefix keys (`sk-mock-…`) are accepted only when `accept_prefix_keys` is enabled.

## Connect your agent

1. [Overview — auth, models, SSE, ping→pong](agents/overview.md)
2. [OpenAI Python / JS SDK](agents/openai.md)
3. [Codex CLI](agents/codex.md)
4. [Anthropic / Claude Code](agents/anthropic.md)
5. [Gemini generateContent](agents/gemini.md)
6. [Hermes & generic OpenAI-compatible](agents/hermes.md)

## Also

- [Quickstart (run the server)](quickstart.md)
- [Configuration](guides/configuration.md)
- [API shapes: OpenAI](api/openai.md) · [Anthropic](api/anthropic.md) · [Gemini](api/gemini.md)

中文文档 → [中文](../zh/index.md)
