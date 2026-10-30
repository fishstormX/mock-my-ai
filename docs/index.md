# Mock My AI

**Mock My AI** is an open-source server that speaks the shapes of popular AI provider APIs — OpenAI, Anthropic, and Google Gemini — while returning **fake but schema-correct** responses from a multilingual corpus.

Use it to:

- Develop and test clients without spending tokens
- Demo agent / tool loops safely (echo, list files only by default)
- Validate SDKs against Chat Completions, Completions, Responses, Messages, and `generateContent`

!!! warning "No real inference"
    This project **never** calls OpenAI, Anthropic, Gemini, or any other upstream model provider.

## Features (Phase 1)

- OpenAI-compatible: `/v1/chat/completions`, `/v1/completions`, `/v1/responses`, `/v1/models`
- Anthropic-compatible: `/v1/messages`, `/anthropic/v1/models`
- Gemini-compatible: `/v1beta/models/{model}:generateContent`
- Language-aware corpus (en / zh / ja / es / fr, ≥1000 segments each)
- Realistic token + `cached_tokens` accounting (DeepSeek series 90–99%)
- Optional thinking / reasoning blocks and mock search
- Configurable tool loops (0–10 rounds), safe tools only
- Custom models (YAML) and custom Q&A overrides

## Quick links

- [Quickstart](quickstart.md)
- [Configuration](guides/configuration.md)
- Interactive API docs when the server is running: `/api/docs`
