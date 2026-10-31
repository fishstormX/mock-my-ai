# Mock My AI — Agent 接入指南

**Mock My AI** 是兼容 OpenAI / Anthropic / Gemini 的 **Mock API**。  
不会调用任何真实模型厂商，适合联调 coding agent、SDK 与 CI。

| | 本地 | 演示站 |
|---|-------|------|
| **Base URL** | `http://127.0.0.1:8000` | `https://aimock.fishmaple.cn` |
| **OpenAI 风格 base** | `http://127.0.0.1:8000/v1` | `https://aimock.fishmaple.cn/v1` |
| **GitHub** | [fishstormX/mock-my-ai](https://github.com/fishstormX/mock-my-ai) | |

!!! warning "无真实推理"
    所有补全都是语料 / 自定义 Q&A，请当作 Mock 数据。

## 示例密钥

| 系列 | 密钥 |
|--------|-----|
| OpenAI 风格 | `sk-mock-openai-demo-key-0123456789abcdef` |
| Anthropic 风格 | `sk-ant-mock-anthropic-demo-key-0123456789` |
| Gemini 风格 | `AIzaMockGeminiDemoKey0123456789abcdef` |

控制台签发的密钥同样可用。仅当开启 `accept_prefix_keys` 时才接受任意 `sk-mock-…` 前缀密钥。

## 接入你的 Agent

1. [总览 — 鉴权、模型、SSE、ping→pong](agents/overview.md)
2. [OpenAI Python / JS SDK](agents/openai.md)
3. [Codex CLI](agents/codex.md)
4. [Anthropic / Claude Code](agents/anthropic.md)
5. [Gemini generateContent](agents/gemini.md)
6. [Hermes 与通用 OpenAI 兼容客户端](agents/hermes.md)

## 其他

- [快速开始（跑服务）](quickstart.md)
- [配置](guides/configuration.md)
- [协议形态：OpenAI](api/openai.md) · [Anthropic](api/anthropic.md) · [Gemini](api/gemini.md)

English docs → [English](../en/index.md)
