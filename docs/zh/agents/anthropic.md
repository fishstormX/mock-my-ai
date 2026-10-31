# Anthropic SDK / Claude Code

Mock My AI 提供 Anthropic **Messages**（`/v1/messages`）。

## 连接参数

| 字段 | 本地 | 演示站 |
|-------|-------|------|
| Base URL | `http://127.0.0.1:8000` | `https://aimock.fishmaple.cn` |
| 鉴权 | `x-api-key: <key>` | |
| 版本头 | `anthropic-version: 2023-06-01`（Mock 可选） | |
| 路径 | `POST /v1/messages`（另有 `/anthropic/v1/messages`） | |
| 模型列表 | `GET /anthropic/v1/models` | |
| 示例密钥 | `sk-ant-mock-anthropic-demo-key-0123456789` | |

## Python SDK

```bash
pip install anthropic
```

```python
import anthropic

client = anthropic.Anthropic(
    base_url="http://127.0.0.1:8000",
    api_key="sk-ant-mock-anthropic-demo-key-0123456789",
)

msg = client.messages.create(
    model="claude-sonnet-4-5",
    max_tokens=256,
    messages=[{"role": "user", "content": "ping"}],
)
print(msg.content)
```

## Claude Code

在 Claude Code / Anthropic 相关环境变量里设置兼容 base 与密钥（具体变量名因版本而异），例如：

```bash
export ANTHROPIC_BASE_URL=http://127.0.0.1:8000
export ANTHROPIC_API_KEY=sk-ant-mock-anthropic-demo-key-0123456789
# 或控制台签发的密钥
```

若构建要求带 `/v1` 后缀，根地址仍用 `http://127.0.0.1:8000`——路径本身已含 `/v1/messages`。

## Curl

```bash
curl -s http://127.0.0.1:8000/v1/messages \
  -H "x-api-key: sk-ant-mock-anthropic-demo-key-0123456789" \
  -H "anthropic-version: 2023-06-01" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-sonnet-4-5",
    "max_tokens": 128,
    "messages": [{"role": "user", "content": "ping"}]
  }'
```

思考块为 `"type": "thinking"`，工具调用为 `"type": "tool_use"`。

另见：[协议形态](../api/anthropic.md)
