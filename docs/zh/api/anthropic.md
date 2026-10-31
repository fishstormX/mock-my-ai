# Anthropic 兼容 API

鉴权：`x-api-key: sk-ant-mock-…`（也接受 Bearer）。

| 方法 | 路径 |
|--------|------|
| GET | `/anthropic/v1/models` |
| POST | `/v1/messages` |
| POST | `/anthropic/v1/messages` |

思考：`"type": "thinking"`。工具：`"type": "tool_use"`。

接入指南：[Anthropic / Claude Code](../agents/anthropic.md)
