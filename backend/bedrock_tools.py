"""Bedrock Converse tool definitions and execution for the career twin chat loop."""

from __future__ import annotations

import json as _json
from typing import Any, Dict, Generator, List, Optional

from botocore.exceptions import ClientError

from calendar_client import create_interview_event, get_available_slots
from pushover_client import send_pushover

MAX_TOOL_ROUNDS = 8

# Passed to bedrock_client.converse(..., toolConfig=CHAT_TOOL_CONFIG)
CHAT_TOOL_CONFIG: Dict[str, Any] = {
    "tools": [
        {
            "toolSpec": {
                "name": "get_interview_availability",
                "description": (
                    "Returns upcoming free interview slots on Michel's calendar within "
                    "weekdays 12:00-15:00 America/New_York with at least 15 minutes between meetings. "
                    "Each slot includes start_iso, end_iso, and display. "
                    "Optionally pass target_date (YYYY-MM-DD) or target_weekday (e.g. Tuesday) to focus results. "
                    "If no target is provided, it returns the next available slots. "
                    "Call this BEFORE quoting specific times or dates."
                ),
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": {
                            "num_slots": {
                                "type": "integer",
                                "description": "Number of slots to return (1–10). Default 3.",
                            },
                            "target_date": {
                                "type": "string",
                                "description": "Optional date filter in YYYY-MM-DD format.",
                            },
                            "target_weekday": {
                                "type": "string",
                                "description": "Optional weekday filter, e.g. Monday, Tuesday.",
                            },
                        },
                    }
                },
            }
        },
        {
            "toolSpec": {
                "name": "book_interview",
                "description": (
                    "Creates a Google Calendar interview event after the visitor confirmed a "
                    "specific slot. Use start_iso and end_iso exactly from a slot returned by "
                    "get_interview_availability."
                ),
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": {
                            "start_iso": {
                                "type": "string",
                                "description": "Event start (ISO datetime from an availability slot).",
                            },
                            "end_iso": {
                                "type": "string",
                                "description": "Event end (ISO datetime from an availability slot).",
                            },
                            "visitor_name": {"type": "string"},
                            "visitor_email": {"type": "string"},
                            "company": {"type": "string"},
                            "role": {"type": "string"},
                            "summary": {
                                "type": "string",
                                "description": "Short summary of the conversation or meeting purpose.",
                            },
                        },
                        "required": ["start_iso", "end_iso"],
                    }
                },
            }
        },
        {
            "toolSpec": {
                "name": "notify_owner",
                "description": (
                    "Sends Michel an immediate Pushover notification (e.g. recruiter showed "
                    "strong interest, or after booking)."
                ),
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "message": {"type": "string"},
                        },
                        "required": ["title", "message"],
                    }
                },
            }
        },
    ]
}


def run_tool(name: str, tool_input: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Execute one tool; return a JSON-serializable dict for the model."""
    args = tool_input or {}
    try:
        if name == "get_interview_availability":
            n = int(args.get("num_slots") or 3)
            n = max(1, min(n, 10))
            slots = get_available_slots(
                num_slots=n,
                target_date=args.get("target_date"),
                target_weekday=args.get("target_weekday"),
            )
            if not slots:
                return {
                    "ok": True,
                    "slots": [],
                    "hint": "No slots returned—calendar may be unavailable or fully busy in the window.",
                }
            return {"ok": True, "slots": slots}

        if name == "book_interview":
            start = args.get("start_iso")
            end = args.get("end_iso")
            if not start or not end:
                return {"ok": False, "error": "start_iso and end_iso are required."}
            link = create_interview_event(
                start_iso=start,
                end_iso=end,
                visitor_name=args.get("visitor_name") or "Website visitor",
                visitor_email=args.get("visitor_email"),
                company=args.get("company") or "",
                role=args.get("role") or "",
                summary_text=args.get("summary") or "",
            )
            return {
                "ok": link is not None,
                "calendar_link": link,
                "message": "Event created." if link else "Calendar not configured or booking failed.",
            }

        if name == "notify_owner":
            title = args.get("title") or "Career twin"
            message = args.get("message") or ""
            ok = send_pushover(title=title, message=message)
            return {"ok": ok, "sent": ok}

        return {"ok": False, "error": f"Unknown tool: {name}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _assistant_text_from_blocks(content: List[Dict]) -> str:
    parts: List[str] = []
    for block in content or []:
        if isinstance(block, dict) and "text" in block:
            parts.append(block["text"])
    return "\n".join(parts).strip()


def _collect_tool_uses(content: List[Dict]) -> List[Dict[str, Any]]:
    out = []
    for block in content or []:
        if isinstance(block, dict) and "toolUse" in block:
            tu = block["toolUse"]
            out.append(
                {
                    "name": tu.get("name"),
                    "toolUseId": tu.get("toolUseId"),
                    "input": tu.get("input") or {},
                }
            )
    return out


def converse_with_tools(
    bedrock_client,
    model_id: str,
    system_text: str,
    prior_turns: List[Dict],
    user_message: str,
) -> str:
    """
    Multi-turn Converse loop with client-side tool execution (Bedrock tool use).
    prior_turns: stored messages {role, content} with string content only.
    """
    messages: List[Dict] = []
    for msg in prior_turns[-50:]:
        messages.append(
            {"role": msg["role"], "content": [{"text": msg["content"]}]}
        )
    messages.append({"role": "user", "content": [{"text": user_message}]})

    inference = {
        "maxTokens": 4096,
        "temperature": 0.7,
        "topP": 0.9,
    }

    for _round in range(MAX_TOOL_ROUNDS):
        try:
            response = bedrock_client.converse(
                modelId=model_id,
                system=[{"text": system_text}],
                messages=messages,
                toolConfig=CHAT_TOOL_CONFIG,
                inferenceConfig=inference,
            )
        except ClientError as e:
            err = e.response.get("Error", {})
            code = err.get("Code", "")
            msg = err.get("Message", "")
            if code == "ValidationException" and (
                "tool" in msg.lower() or "toolConfig" in msg.lower()
            ):
                print(
                    "Tool use not accepted by model; falling back to plain Converse:",
                    msg,
                )
                return _converse_plain(
                    bedrock_client, model_id, system_text, messages, inference
                )
            raise

        stop = response.get("stopReason")
        out_msg = response.get("output", {}).get("message") or {}
        content = out_msg.get("content") or []

        # Always append assistant message for the next round
        messages.append(out_msg)

        if stop == "tool_use":
            tool_uses = _collect_tool_uses(content)
            if not tool_uses:
                txt = _assistant_text_from_blocks(content)
                if txt:
                    return txt
                return (
                    "I wasn't able to complete that action. Please try again or rephrase."
                )

            result_blocks: List[Dict] = []
            for tu in tool_uses:
                result = run_tool(tu["name"], tu.get("input"))
                result_blocks.append(
                    {
                        "toolResult": {
                            "toolUseId": tu["toolUseId"],
                            "content": [{"json": result}],
                        }
                    }
                )
            messages.append({"role": "user", "content": result_blocks})
            continue

        # end_turn, max_tokens, etc.
        text = _assistant_text_from_blocks(content)
        if text:
            return text
        return "I'm not sure how to respond to that—could you try asking in another way?"

    return (
        "I hit the limit for tool steps in one turn. Please send another message to continue."
    )


def _converse_plain(bedrock_client, model_id, system_text, messages, inference):
    """Single-shot Converse without tools (fallback)."""
    response = bedrock_client.converse(
        modelId=model_id,
        system=[{"text": system_text}],
        messages=messages,
        inferenceConfig=inference,
    )
    content = response.get("output", {}).get("message", {}).get("content") or []
    return _assistant_text_from_blocks(content) or "(no response)"


# ---------------------------------------------------------------------------
# Streaming variants
# ---------------------------------------------------------------------------

def _rebuild_content_from_blocks(blocks: Dict[int, Dict]) -> List[Dict]:
    """Turn the accumulated block map back into a Converse-style content list."""
    content: List[Dict] = []
    for idx in sorted(blocks):
        blk = blocks[idx]
        if blk["type"] == "text":
            if not blk["text"]:
                continue
            content.append({"text": blk["text"]})
        elif blk["type"] == "toolUse":
            input_obj = {}
            raw = blk.get("input_json", "")
            if raw:
                try:
                    input_obj = _json.loads(raw)
                except _json.JSONDecodeError:
                    input_obj = {}
            content.append({
                "toolUse": {
                    "toolUseId": blk["toolUse"]["toolUseId"],
                    "name": blk["toolUse"]["name"],
                    "input": input_obj,
                }
            })
    return content


def _converse_stream_plain(
    bedrock_client, model_id, system_text, messages, inference,
) -> Generator[str, None, None]:
    """Streaming fallback without tools."""
    resp = bedrock_client.converse_stream(
        modelId=model_id,
        system=[{"text": system_text}],
        messages=messages,
        inferenceConfig=inference,
    )
    got_text = False
    for event in resp["stream"]:
        if "contentBlockDelta" in event:
            delta = event["contentBlockDelta"]["delta"]
            if "text" in delta:
                got_text = True
                yield delta["text"]
    if not got_text:
        yield "(no response)"


def converse_stream_with_tools(
    bedrock_client,
    model_id: str,
    system_text: str,
    prior_turns: List[Dict],
    user_message: str,
) -> Generator[str, None, None]:
    """
    Multi-turn Converse loop with client-side tool execution.

    Uses non-streaming ``converse`` for all rounds because some models
    (e.g. openai.gpt-oss-120b-1) produce garbled tool-input JSON via
    ``converse_stream``.  The final text is yielded in small chunks so
    the SSE transport can deliver it progressively to the browser.
    """
    messages: List[Dict] = []
    for msg in prior_turns[-50:]:
        messages.append(
            {"role": msg["role"], "content": [{"text": msg["content"]}]}
        )
    messages.append({"role": "user", "content": [{"text": user_message}]})

    inference = {
        "maxTokens": 4096,
        "temperature": 0.7,
        "topP": 0.9,
    }

    converse_kwargs = dict(
        modelId=model_id,
        system=[{"text": system_text}],
        toolConfig=CHAT_TOOL_CONFIG,
        inferenceConfig=inference,
    )

    for _round in range(MAX_TOOL_ROUNDS):
        # --- non-streaming round (reliable tool input) ---
        try:
            response = bedrock_client.converse(messages=messages, **converse_kwargs)
        except ClientError as e:
            err = e.response.get("Error", {})
            code = err.get("Code", "")
            msg_text = err.get("Message", "")
            if code == "ValidationException" and (
                "tool" in msg_text.lower() or "toolconfig" in msg_text.lower()
            ):
                print("Tool use not supported; falling back to plain stream:", msg_text)
                yield from _converse_stream_plain(
                    bedrock_client, model_id, system_text, messages, inference
                )
                return
            raise

        stop = response.get("stopReason")
        out_msg = response.get("output", {}).get("message") or {}
        content = out_msg.get("content") or []
        messages.append(out_msg)

        if stop == "tool_use":
            tool_uses = _collect_tool_uses(content)
            if not tool_uses:
                txt = _assistant_text_from_blocks(content)
                if txt:
                    yield txt
                else:
                    yield "I wasn't able to complete that action. Please try again or rephrase."
                return

            result_blocks: List[Dict] = []
            for tu in tool_uses:
                result = run_tool(tu["name"], tu.get("input"))
                result_blocks.append({
                    "toolResult": {
                        "toolUseId": tu["toolUseId"],
                        "content": [{"json": result}],
                    }
                })
            messages.append({"role": "user", "content": result_blocks})
            continue

        # --- final text response: yield in small chunks for streaming feel ---
        text = _assistant_text_from_blocks(content)
        if text:
            for i in range(0, len(text), 8):
                yield text[i : i + 8]
        else:
            yield "I'm not sure how to respond to that—could you try asking in another way?"
        return

    yield "I hit the limit for tool steps in one turn. Please send another message to continue."
