from __future__ import annotations

import json
import time
from collections.abc import Iterator
from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from mock_my_ai.auth import require_api_key
from mock_my_ai.generation import MockResult, generate_mock, new_id, usage_openai
from mock_my_ai.models_catalog import all_openai_compat_models, to_openai_list_item

router = APIRouter(tags=["OpenAI Compatible"])


class ChatMessage(BaseModel):
    role: str
    content: Any = None
    name: str | None = None
    tool_call_id: str | None = None
    tool_calls: list[dict[str, Any]] | None = None


class ChatCompletionsRequest(BaseModel):
    model: str = "gpt-4o-mini"
    messages: list[ChatMessage]
    temperature: float | None = 1.0
    max_tokens: int | None = None
    stream: bool | None = False
    tools: list[dict[str, Any]] | None = None
    tool_choice: Any = None
    # Mock My AI extensions
    mock_thinking: bool | None = None
    mock_search: bool | None = None
    mock_tool_rounds: int | None = None
    mock_seed: int | None = None


class CompletionsRequest(BaseModel):
    model: str = "gpt-3.5-turbo-instruct"
    prompt: Any = ""
    max_tokens: int | None = 256
    temperature: float | None = 1.0
    stream: bool | None = False
    mock_thinking: bool | None = None
    mock_search: bool | None = None
    mock_seed: int | None = None


class ResponsesRequest(BaseModel):
    model: str = "gpt-4o-mini"
    input: Any = None
    instructions: str | None = None
    tools: list[dict[str, Any]] | None = None
    temperature: float | None = 1.0
    stream: bool | None = False
    mock_thinking: bool | None = None
    mock_search: bool | None = None
    mock_tool_rounds: int | None = None
    mock_seed: int | None = None


def _messages_as_dicts(messages: list[ChatMessage]) -> list[dict[str, Any]]:
    return [m.model_dump(exclude_none=True) for m in messages]


def _prompt_to_text(prompt: Any) -> str:
    if isinstance(prompt, str):
        return prompt
    if isinstance(prompt, list):
        parts = []
        for p in prompt:
            if isinstance(p, str):
                parts.append(p)
            elif isinstance(p, dict) and "text" in p:
                parts.append(str(p["text"]))
        return "\n".join(parts)
    return str(prompt or "")


def _input_to_messages(inp: Any, instructions: str | None) -> list[dict[str, Any]]:
    msgs: list[dict[str, Any]] = []
    if instructions:
        msgs.append({"role": "system", "content": instructions})
    if isinstance(inp, str):
        msgs.append({"role": "user", "content": inp})
    elif isinstance(inp, list):
        for item in inp:
            if isinstance(item, str):
                msgs.append({"role": "user", "content": item})
            elif isinstance(item, dict):
                role = item.get("role", "user")
                content = item.get("content", item.get("text", ""))
                msgs.append({"role": role, "content": content})
    elif isinstance(inp, dict):
        msgs.append({"role": inp.get("role", "user"), "content": inp.get("content", "")})
    return msgs


def _chunk_text(text: str, size: int = 32) -> list[str]:
    if not text:
        return [""]
    chunks: list[str] = []
    i = 0
    n = len(text)
    while i < n:
        end = min(i + size, n)
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


def _sse_data(data: dict[str, Any] | str) -> str:
    """Classic OpenAI chat SSE: data-only lines (no event:)."""
    payload = data if isinstance(data, str) else json.dumps(data, ensure_ascii=False)
    return f"data: {payload}\n\n"


def _sse_event(event: str, data: dict[str, Any]) -> str:
    """Responses API SSE: event name + data JSON (type also inside data)."""
    payload = json.dumps(data, ensure_ascii=False)
    return f"event: {event}\ndata: {payload}\n\n"


_SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}


@router.get("/v1/models")
async def list_models(_: str | None = Depends(require_api_key)) -> dict[str, Any]:
    created = int(time.time())
    data = [to_openai_list_item(m, created=created) for m in all_openai_compat_models()]
    return {"object": "list", "data": data}


@router.get("/v1/models/{model_id:path}")
async def retrieve_model(model_id: str, _: str | None = Depends(require_api_key)) -> dict[str, Any]:
    for m in all_openai_compat_models():
        if m["id"] == model_id:
            return to_openai_list_item(m)
    return to_openai_list_item({"id": model_id, "owned_by": "mock-my-ai"})


def _build_chat_message(result: MockResult) -> tuple[dict[str, Any], str]:
    message: dict[str, Any] = {"role": "assistant", "content": result.text}
    finish = "stop"

    if result.thinking:
        message["reasoning_content"] = result.thinking

    if result.tool_rounds:
        first = result.tool_rounds[0]["calls"]
        message["tool_calls"] = [
            {
                "id": c["id"],
                "type": "function",
                "function": {
                    "name": c["function"]["name"],
                    "arguments": c["function"]["arguments"],
                },
            }
            for c in first
        ]
        message["content"] = None
        finish = "tool_calls"

    return message, finish


def _build_chat_completion(result: MockResult, model: str) -> dict[str, Any]:
    message, finish = _build_chat_message(result)
    return {
        "id": new_id("chatcmpl"),
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": message,
                "finish_reason": finish,
                "logprobs": None,
            }
        ],
        "usage": usage_openai(result),
        "mock_my_ai": {
            "lang": result.lang,
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


def _iter_chat_completions_sse(result: MockResult, model: str) -> Iterator[str]:
    """Classic OpenAI chat.completion.chunk SSE ending with data: [DONE]."""
    created = int(time.time())
    chunk_id = new_id("chatcmpl")
    message, finish = _build_chat_message(result)

    # Role opener
    yield _sse_data(
        {
            "id": chunk_id,
            "object": "chat.completion.chunk",
            "created": created,
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "delta": {"role": "assistant", "content": ""},
                    "finish_reason": None,
                    "logprobs": None,
                }
            ],
        }
    )

    if result.thinking:
        for piece in _chunk_text(result.thinking, size=40):
            yield _sse_data(
                {
                    "id": chunk_id,
                    "object": "chat.completion.chunk",
                    "created": created,
                    "model": model,
                    "choices": [
                        {
                            "index": 0,
                            "delta": {"reasoning_content": piece},
                            "finish_reason": None,
                            "logprobs": None,
                        }
                    ],
                }
            )

    if finish == "tool_calls" and message.get("tool_calls"):
        # Emit tool_calls as incremental deltas (index + function fields)
        for i, tc in enumerate(message["tool_calls"]):
            yield _sse_data(
                {
                    "id": chunk_id,
                    "object": "chat.completion.chunk",
                    "created": created,
                    "model": model,
                    "choices": [
                        {
                            "index": 0,
                            "delta": {
                                "tool_calls": [
                                    {
                                        "index": i,
                                        "id": tc["id"],
                                        "type": "function",
                                        "function": {
                                            "name": tc["function"]["name"],
                                            "arguments": "",
                                        },
                                    }
                                ]
                            },
                            "finish_reason": None,
                            "logprobs": None,
                        }
                    ],
                }
            )
            args = tc["function"]["arguments"] or ""
            for piece in _chunk_text(args, size=40):
                yield _sse_data(
                    {
                        "id": chunk_id,
                        "object": "chat.completion.chunk",
                        "created": created,
                        "model": model,
                        "choices": [
                            {
                                "index": 0,
                                "delta": {
                                    "tool_calls": [
                                        {
                                            "index": i,
                                            "function": {"arguments": piece},
                                        }
                                    ]
                                },
                                "finish_reason": None,
                                "logprobs": None,
                            }
                        ],
                    }
                )
    else:
        text = message.get("content") or ""
        for piece in _chunk_text(text):
            yield _sse_data(
                {
                    "id": chunk_id,
                    "object": "chat.completion.chunk",
                    "created": created,
                    "model": model,
                    "choices": [
                        {
                            "index": 0,
                            "delta": {"content": piece},
                            "finish_reason": None,
                            "logprobs": None,
                        }
                    ],
                }
            )

    yield _sse_data(
        {
            "id": chunk_id,
            "object": "chat.completion.chunk",
            "created": created,
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "delta": {},
                    "finish_reason": finish,
                    "logprobs": None,
                }
            ],
            "usage": usage_openai(result),
        }
    )
    yield _sse_data("[DONE]")


@router.post("/v1/chat/completions")
async def chat_completions(
    body: ChatCompletionsRequest,
    _: str | None = Depends(require_api_key),
) -> Any:
    result = generate_mock(
        model=body.model,
        messages=_messages_as_dicts(body.messages),
        tools=body.tools,
        enable_thinking=body.mock_thinking,
        enable_search=body.mock_search,
        force_tool_rounds=body.mock_tool_rounds,
        seed=body.mock_seed,
    )

    if body.stream:
        return StreamingResponse(
            _iter_chat_completions_sse(result, body.model),
            media_type="text/event-stream",
            headers=_SSE_HEADERS,
        )

    return _build_chat_completion(result, body.model)


@router.post("/v1/completions")
async def completions(
    body: CompletionsRequest,
    _: str | None = Depends(require_api_key),
) -> dict[str, Any]:
    prompt = _prompt_to_text(body.prompt)
    result = generate_mock(
        model=body.model,
        prompt=prompt,
        enable_thinking=body.mock_thinking,
        enable_search=body.mock_search,
        seed=body.mock_seed,
    )
    return {
        "id": new_id("cmpl"),
        "object": "text_completion",
        "created": int(time.time()),
        "model": body.model,
        "choices": [
            {
                "text": result.text,
                "index": 0,
                "logprobs": None,
                "finish_reason": "stop",
            }
        ],
        "usage": usage_openai(result),
        "mock_my_ai": {"lang": result.lang, "search_results": result.search_results},
    }


def _responses_usage(result: MockResult) -> dict[str, Any]:
    return {
        "input_tokens": result.prompt_tokens,
        "output_tokens": result.completion_tokens,
        "total_tokens": result.total_tokens,
        "input_tokens_details": {"cached_tokens": result.cached_tokens},
        "output_tokens_details": {
            "reasoning_tokens": len(result.thinking.split()) if result.thinking else 0
        },
    }


def _build_responses_output(result: MockResult) -> tuple[list[dict[str, Any]], str]:
    output_items: list[dict[str, Any]] = []
    if result.thinking:
        output_items.append(
            {
                "type": "reasoning",
                "id": new_id("rs"),
                "summary": [{"type": "summary_text", "text": result.thinking[:200]}],
                "content": [{"type": "reasoning_text", "text": result.thinking}],
            }
        )

    if result.tool_rounds:
        for c in result.tool_rounds[0]["calls"]:
            output_items.append(
                {
                    "type": "function_call",
                    "id": new_id("fc"),
                    "call_id": c["id"],
                    "name": c["name"],
                    "arguments": c["function"]["arguments"],
                }
            )
        status = "completed"
    else:
        output_items.append(
            {
                "type": "message",
                "id": new_id("msg"),
                "role": "assistant",
                "status": "completed",
                "content": [{"type": "output_text", "text": result.text}],
            }
        )
        status = "completed"
    return output_items, status


def _build_responses_payload(result: MockResult, model: str) -> dict[str, Any]:
    output_items, status = _build_responses_output(result)
    return {
        "id": new_id("resp"),
        "object": "response",
        "created_at": int(time.time()),
        "status": status,
        "model": model,
        "output": output_items,
        "usage": _responses_usage(result),
        "mock_my_ai": {
            "lang": result.lang,
            "text": result.text,
            "tool_rounds": result.tool_rounds,
            "search_results": result.search_results,
        },
    }


def _iter_responses_sse(result: MockResult, model: str) -> Iterator[str]:
    """OpenAI Responses API SSE sequence ending with response.completed.

    Typical text sequence Codex expects:
      response.created
      response.in_progress
      response.output_item.added
      response.content_part.added
      response.output_text.delta (×N)
      response.output_text.done
      response.content_part.done
      response.output_item.done
      response.completed
    """
    seq = 0

    def next_seq() -> int:
        nonlocal seq
        seq += 1
        return seq

    resp_id = new_id("resp")
    created_at = int(time.time())
    usage = _responses_usage(result)

    base_response: dict[str, Any] = {
        "id": resp_id,
        "object": "response",
        "created_at": created_at,
        "status": "in_progress",
        "model": model,
        "output": [],
        "error": None,
        "incomplete_details": None,
        "usage": None,
    }

    yield _sse_event(
        "response.created",
        {
            "type": "response.created",
            "sequence_number": next_seq(),
            "response": dict(base_response),
        },
    )
    yield _sse_event(
        "response.in_progress",
        {
            "type": "response.in_progress",
            "sequence_number": next_seq(),
            "response": dict(base_response),
        },
    )

    final_output: list[dict[str, Any]] = []
    output_index = 0

    # Optional reasoning item (no delta stream for simplicity — emit whole)
    if result.thinking:
        rs_id = new_id("rs")
        rs_item = {
            "type": "reasoning",
            "id": rs_id,
            "summary": [{"type": "summary_text", "text": result.thinking[:200]}],
            "content": [{"type": "reasoning_text", "text": result.thinking}],
        }
        yield _sse_event(
            "response.output_item.added",
            {
                "type": "response.output_item.added",
                "sequence_number": next_seq(),
                "output_index": output_index,
                "item": {
                    "type": "reasoning",
                    "id": rs_id,
                    "summary": [],
                    "content": [],
                },
            },
        )
        yield _sse_event(
            "response.output_item.done",
            {
                "type": "response.output_item.done",
                "sequence_number": next_seq(),
                "output_index": output_index,
                "item": rs_item,
            },
        )
        final_output.append(rs_item)
        output_index += 1

    if result.tool_rounds:
        for c in result.tool_rounds[0]["calls"]:
            fc_id = new_id("fc")
            args = c["function"]["arguments"] or ""
            item_start = {
                "type": "function_call",
                "id": fc_id,
                "call_id": c["id"],
                "name": c["name"],
                "arguments": "",
                "status": "in_progress",
            }
            yield _sse_event(
                "response.output_item.added",
                {
                    "type": "response.output_item.added",
                    "sequence_number": next_seq(),
                    "output_index": output_index,
                    "item": item_start,
                },
            )
            for piece in _chunk_text(args, size=40):
                yield _sse_event(
                    "response.function_call_arguments.delta",
                    {
                        "type": "response.function_call_arguments.delta",
                        "sequence_number": next_seq(),
                        "item_id": fc_id,
                        "output_index": output_index,
                        "delta": piece,
                    },
                )
            yield _sse_event(
                "response.function_call_arguments.done",
                {
                    "type": "response.function_call_arguments.done",
                    "sequence_number": next_seq(),
                    "item_id": fc_id,
                    "output_index": output_index,
                    "arguments": args,
                },
            )
            item_done = {
                "type": "function_call",
                "id": fc_id,
                "call_id": c["id"],
                "name": c["name"],
                "arguments": args,
                "status": "completed",
            }
            yield _sse_event(
                "response.output_item.done",
                {
                    "type": "response.output_item.done",
                    "sequence_number": next_seq(),
                    "output_index": output_index,
                    "item": item_done,
                },
            )
            final_output.append(item_done)
            output_index += 1
    else:
        msg_id = new_id("msg")
        text = result.text or ""
        item_start = {
            "type": "message",
            "id": msg_id,
            "role": "assistant",
            "status": "in_progress",
            "content": [],
        }
        yield _sse_event(
            "response.output_item.added",
            {
                "type": "response.output_item.added",
                "sequence_number": next_seq(),
                "output_index": output_index,
                "item": item_start,
            },
        )
        content_index = 0
        part = {"type": "output_text", "text": "", "annotations": []}
        yield _sse_event(
            "response.content_part.added",
            {
                "type": "response.content_part.added",
                "sequence_number": next_seq(),
                "item_id": msg_id,
                "output_index": output_index,
                "content_index": content_index,
                "part": part,
            },
        )
        for piece in _chunk_text(text):
            yield _sse_event(
                "response.output_text.delta",
                {
                    "type": "response.output_text.delta",
                    "sequence_number": next_seq(),
                    "item_id": msg_id,
                    "output_index": output_index,
                    "content_index": content_index,
                    "delta": piece,
                },
            )
        yield _sse_event(
            "response.output_text.done",
            {
                "type": "response.output_text.done",
                "sequence_number": next_seq(),
                "item_id": msg_id,
                "output_index": output_index,
                "content_index": content_index,
                "text": text,
            },
        )
        part_done = {"type": "output_text", "text": text, "annotations": []}
        yield _sse_event(
            "response.content_part.done",
            {
                "type": "response.content_part.done",
                "sequence_number": next_seq(),
                "item_id": msg_id,
                "output_index": output_index,
                "content_index": content_index,
                "part": part_done,
            },
        )
        item_done = {
            "type": "message",
            "id": msg_id,
            "role": "assistant",
            "status": "completed",
            "content": [part_done],
        }
        yield _sse_event(
            "response.output_item.done",
            {
                "type": "response.output_item.done",
                "sequence_number": next_seq(),
                "output_index": output_index,
                "item": item_done,
            },
        )
        final_output.append(item_done)

    completed = {
        "id": resp_id,
        "object": "response",
        "created_at": created_at,
        "status": "completed",
        "model": model,
        "output": final_output,
        "error": None,
        "incomplete_details": None,
        "usage": usage,
        "mock_my_ai": {
            "lang": result.lang,
            "text": result.text,
            "tool_rounds": result.tool_rounds,
            "search_results": result.search_results,
        },
    }
    yield _sse_event(
        "response.completed",
        {
            "type": "response.completed",
            "sequence_number": next_seq(),
            "response": completed,
        },
    )


@router.post("/v1/responses")
async def responses_api(
    body: ResponsesRequest,
    _: str | None = Depends(require_api_key),
) -> Any:
    messages = _input_to_messages(body.input, body.instructions)
    result = generate_mock(
        model=body.model,
        messages=messages,
        tools=body.tools,
        enable_thinking=body.mock_thinking,
        enable_search=body.mock_search,
        force_tool_rounds=body.mock_tool_rounds,
        seed=body.mock_seed,
    )

    if body.stream:
        return StreamingResponse(
            _iter_responses_sse(result, body.model),
            media_type="text/event-stream",
            headers=_SSE_HEADERS,
        )

    return _build_responses_payload(result, body.model)
