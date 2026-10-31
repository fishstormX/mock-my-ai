# Gemini generateContent

Compatible with Google Generative Language **generateContent** under `/v1beta`.

## Connection

| Field | Local | Demo |
|-------|-------|------|
| Base URL | `http://127.0.0.1:8000` | `https://aimock.fishmaple.cn` |
| Auth | `x-goog-api-key: <key>` or `?key=` | |
| Path | `POST /v1beta/models/{model}:generateContent` | |
| List | `GET /v1beta/models` | |
| Sample key | `AIzaMockGeminiDemoKey0123456789abcdef` | |

Mirrored under `/gemini/v1beta/...`.

## Curl

```bash
curl -s "http://127.0.0.1:8000/v1beta/models/gemini-2.5-flash:generateContent" \
  -H "x-goog-api-key: AIzaMockGeminiDemoKey0123456789abcdef" \
  -H "Content-Type: application/json" \
  -d '{
    "contents": [{"role": "user", "parts": [{"text": "ping"}]}]
  }'
```

## Python (google-genai style host override)

Exact client options differ by library version. Pattern:

1. Set API endpoint / client options host to `http://127.0.0.1:8000`
2. Pass `AIzaMock…` or a console key as the API key
3. Call `models/{id}:generateContent` with Gemini content parts

```bash
curl -s "https://aimock.fishmaple.cn/v1beta/models/gemini-2.5-flash:generateContent?key=AIzaMockGeminiDemoKey0123456789abcdef" \
  -H "Content-Type: application/json" \
  -d '{"contents":[{"role":"user","parts":[{"text":"Hello"}]}]}'
```

See also: [API shape](../api/gemini.md)
