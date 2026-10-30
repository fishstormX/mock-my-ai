from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from mock_my_ai.auth import require_api_key
from mock_my_ai.generation import MockResult, generate_mock, new_id, usage_anthropic
from mock_my_ai.models_catalog import anthropic_models

router = APIRouter(tags=["Anthropic Compatible"])


class AnthropicMessage(BaseModel):
    role: str
    content: Any


class MessagesRequest(BaseModel):
    model: str = "claude-3-5-sonnet-20241022"
    messages: list[AnthropicMessage]
    max_tokens: int = 1024
    system: Any = None
    temperature: float | None = None
    tools: list[dict[str, Any]] | None = None
    stream: bool | None = False
    thinking: dict[str, Any] | None = None
    mock_thinking: bool | None = None
    mock_search: bool | None = None
    mock_tool_rounds: int | None = None
    mock_seed: int | None = None


@router.get("/anthropic/v1/models")
async def list_anthropic_models(_: str | None = Depends(require_api_key)) -> dict[str, Any]:
    # Anthropic-style listing (simplified)
    data = [
        {
            "type": "model",
            "id": m["id"],
            "display_name": m["id"],
            "created_at": "2024-01-01T00:00:00Z",
        }
        for m in anthropic_models()
    ]
    return {"data": data, "has_more": False}


def _build_content_blocks(result: MockResult) -> tuple[list[dict[str, Any]], str]:
    content_blocks: list[dict[str, Any]] = []
    if result.thinking:
        content_blocks.append(
            {
                "type": "thinking",
                "thinking": result.thinking,
            }
        )

    stop_reason = "end_turn"
    if result.tool_rounds:
        for c in result.tool_rounds[0]["calls"]:
            content_blocks.append(
                {
                    "type": "tool_use",
                    "id": c["id"],
                    "name": c["name"],
                    "input": c["arguments"],
                }
            )
        stop_reason = "tool_use"
    else:
        content_blocks.append({"type": "text", "text": result.text})
    return content_blocks, stop_reason


def _build_message_payload(result: MockResult, model: str) -> dict[str, Any]:
    content_blocks, stop_reason = _build_content_blocks(result)
    return {
        "id": new_id("msg"),
        "type": "message",
        "role": "assistant",
        "model": model,
        "content": content_blocks,
        "stop_reason": stop_reason,
        "stop_sequence": None,
        "usage": usage_anthropic(result),
        "mock_my_ai": {
            "lang": result.lang,
            "text": result.text,
            "tool_rounds": [
                {
                    "round": tr["round"],
                    "calls": [
                        {
                            "id": c["id"],
                            "name": c["name"],
                            "arguments": c["arguments"],
                            "result": c["result"],
                        }
                        for c in tr["calls"]
                    ],
                }
                for tr in result.tool_rounds
            ],
            "search_results": result.search_results,
        },
    }


def _chunk_text(text: str, size: int = 32) -> list[str]:
    if not text:
        return [""]
    chunks: list[str] = []
    i = 0
    n = len(text)
    while i < n:
        end = min(i + size, n)
        # Prefer breaking on whitespace / punctuation when nearby
        if end < n:
            window = text[i:end]
            for sep in ("。", "！", "？", ".", "!", "?", "\n", "，", ",", " "):
                pos = window.rfind(sep)
                if pos >= max(8, size // 4):
                    end = i + pos + 1
                    break
        chunks.append(text[i:end])
        i = end
    return chunks or [""]


def _sse(event: str, data: dict[str, Any] | str) -> str:
    payload = data if isinstance(data, str) else json.dumps(data, ensure_ascii=False)
    return f"event: {event}\ndata: {payload}\n\n"


def _iter_anthropic_sse(result: MockResult, model: str) -> Iterator[str]:
    content_blocks, stop_reason = _build_content_blocks(result)
    msg_id = new_id("msg")
    usage = usage_anthropic(result)

    yield _sse(
        "message_start",
        {
            "type": "message_start",
            "message": {
                "id": msg_id,
                "type": "message",
                "role": "assistant",
                "model": model,
                "content": [],
                "stop_reason": None,
                "stop_sequence": None,
                "usage": {
                    "input_tokens": usage["input_tokens"],
                    "output_tokens": 0,
                    "cache_read_input_tokens": usage.get("cache_read_input_tokens", 0),
                },
            },
        },
    )

    for index, block in enumerate(content_blocks):
        btype = block.get("type")
        if btype == "thinking":
            yield _sse(
                "content_block_start",
                {
                    "type": "content_block_start",
                    "index": index,
                    "content_block": {"type": "thinking", "thinking": ""},
                },
            )
            for piece in _chunk_text(block.get("thinking") or ""):
                yield _sse(
                    "content_block_delta",
                    {
                        "type": "content_block_delta",
                        "index": index,
                        "delta": {"type": "thinking_delta", "thinking": piece},
                    },
                )
            yield _sse(
                "content_block_stop",
                {"type": "content_block_stop", "index": index},
            )
        elif btype == "text":
            yield _sse(
                "content_block_start",
                {
                    "type": "content_block_start",
                    "index": index,
                    "content_block": {"type": "text", "text": ""},
                },
            )
            for piece in _chunk_text(block.get("text") or ""):
                yield _sse(
                    "content_block_delta",
                    {
                        "type": "content_block_delta",
                        "index": index,
                        "delta": {"type": "text_delta", "text": piece},
                    },
                )
            yield _sse(
                "content_block_stop",
                {"type": "content_block_stop", "index": index},
            )
        elif btype == "tool_use":
            yield _sse(
                "content_block_start",
                {
                    "type": "content_block_start",
                    "index": index,
                    "content_block": {
                        "type": "tool_use",
                        "id": block["id"],
                        "name": block["name"],
                        "input": {},
                    },
                },
            )
            partial = json.dumps(block.get("input") or {}, ensure_ascii=False)
            # Emit input as one or more input_json_delta chunks
            for piece in _chunk_text(partial, size=40):
                yield _sse(
                    "content_block_delta",
                    {
                        "type": "content_block_delta",
                        "index": index,
                        "delta": {"type": "input_json_delta", "partial_json": piece},
                    },
                )
            yield _sse(
                "content_block_stop",
                {"type": "content_block_stop", "index": index},
            )

    yield _sse(
        "message_delta",
        {
            "type": "message_delta",
            "delta": {"stop_reason": stop_reason, "stop_sequence": None},
            "usage": {"output_tokens": usage["output_tokens"]},
        },
    )
    yield _sse("message_stop", {"type": "message_stop"})


@router.post("/v1/messages")
@router.post("/anthropic/v1/messages")
async def create_message(
    body: MessagesRequest,
    _: str | None = Depends(require_api_key),
) -> Any:
    msgs: list[dict[str, Any]] = []
    if body.system:
        if isinstance(body.system, str):
            msgs.append({"role": "system", "content": body.system})
        elif isinstance(body.system, list):
            text = " ".join(
                p.get("text", "") if isinstance(p, dict) else str(p) for p in body.system
            )
            msgs.append({"role": "system", "content": text})
    for m in body.messages:
        msgs.append({"role": m.role, "content": m.content})

    thinking_flag = body.mock_thinking
    if thinking_flag is None and body.thinking:
        thinking_flag = True

    result = generate_mock(
        model=body.model,
        messages=msgs,
        tools=body.tools,
        enable_thinking=thinking_flag,
        enable_search=body.mock_search,
        force_tool_rounds=body.mock_tool_rounds,
        seed=body.mock_seed,
    )

    if body.stream:
        return StreamingResponse(
            _iter_anthropic_sse(result, body.model),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    return _build_message_payload(result, body.model)
