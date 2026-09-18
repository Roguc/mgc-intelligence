"""Classify Platform items. Assistant text never mixes with tool/runtime dumps."""
from __future__ import annotations

ASSISTANT_TYPES = {"message", "output_text", "assistant_message", "agent.message"}
TOOL_TYPES = {
    "web_search", "web_search_call", "web_search_result",
    "create_subagent_call", "send_subagent_input_call", "wait_for_subagents_call",
    "interrupt_subagent_call", "agent_message",
    "computer_call", "computer_call_output", "tool_call", "tool_result",
}
SHELL_TYPES = {"command", "command_execution", "shell_call", "shell", "bash", "local_shell_call"}
HTTP_TYPES = {"http_request", "http_response", "fetch"}
BROWSER_TYPES = {"browser", "browser_call", "computer"}
KIND_TOOLS = {
    "web_search": "web_search",
    "shell": "shell",
    "http": "http",
    "browser": "browser",
    "tool_call": "tool_call",
    "tool_output": "tool_output",
    "error": "error",
}


def text_of(item: dict) -> str:
    chunks = []
    content = item.get("content") or item.get("output") or item.get("text")
    if isinstance(content, str) and content.strip():
        chunks.append(content)
    if isinstance(content, list):
        for part in content:
            if not isinstance(part, dict) or part.get("type") in {"input_text"}:
                continue
            piece = str(part.get("text") or part.get("output_text") or "").strip()
            if piece:
                chunks.append(piece)
    return "\n".join(chunks).strip()


def looks_like_runtime_pollution(text: str) -> bool:
    blob = (text or "").strip()
    if not blob:
        return False
    head = blob[:800].casefold()
    if head.startswith("<!doctype") or head.startswith("<html") or head.startswith("<?xml"):
        return True
    if "<script" in head or "cloudfront" in head or "access denied" in head:
        return True
    if "command not found" in head or head.startswith("rg:") or "/usr/bin/" in head:
        return True
    if blob.count("<") > 30 and ("href=" in blob.casefold() or "</div>" in blob.casefold()):
        return True
    return False


def classify_item(item: dict) -> dict | None:
    if not isinstance(item, dict) or item.get("role") == "user":
        return None
    itype = str(item.get("type") or "").casefold()
    name = str(item.get("name") or item.get("command") or "")
    text = text_of(item)
    blob = " ".join([name, str(item.get("command") or ""), text[:400]]).casefold()
    kind = "system"
    if "web_search" in itype:
        kind = "web_search"
    elif itype in HTTP_TYPES or itype.startswith("http"):
        kind = "http"
    elif any(token in itype for token in BROWSER_TYPES):
        kind = "browser"
    elif itype in SHELL_TYPES or "shell" in itype:
        kind = "http" if any(token in blob for token in ("curl ", "wget ", "http_request")) else "shell"
        if "command not found" in text.casefold() or "timed out" in text.casefold():
            kind = "error"
    elif "subagent" in itype:
        kind = "tool_call"
    elif itype in TOOL_TYPES or "tool" in itype or "function" in itype or "mcp" in itype:
        kind = "tool_call" if "output" not in itype else "tool_output"
    elif looks_like_runtime_pollution(text):
        kind = "runtime"
    elif item.get("role") == "assistant" or itype in ASSISTANT_TYPES or itype.endswith("message"):
        kind = "assistant"
    elif text and not itype:
        kind = "assistant" if not looks_like_runtime_pollution(text) else "runtime"
    if kind == "assistant" and looks_like_runtime_pollution(text):
        kind = "runtime"
    return {
        "kind": kind,
        "type": item.get("type"),
        "name": name or None,
        "text": text,
        "usage": item.get("usage") if isinstance(item.get("usage"), dict) else {},
        "item_id": item.get("id"),
        "turn_id": item.get("turn_id") or item.get("turn"),
        "sources": _item_sources(item),
    }


def _item_sources(item: dict) -> list:
    rows = []
    action = item.get("action") if isinstance(item.get("action"), dict) else {}
    for src in action.get("sources") or []:
        if isinstance(src, dict) and src.get("url"):
            rows.append({"url": src.get("url"), "title": src.get("title"), "origin": "tool_event"})
    if isinstance(item.get("content"), list):
        for part in item["content"]:
            if not isinstance(part, dict):
                continue
            for ann in part.get("annotations") or []:
                if isinstance(ann, dict) and ann.get("url"):
                    rows.append({"url": ann.get("url"), "title": ann.get("title"), "origin": "annotation"})
    return rows


def split_turn(items: list) -> dict:
    events = [event for item in (items or []) if (event := classify_item(item))]
    assistant = [event["text"] for event in events if event["kind"] == "assistant" and event.get("text")]
    tools_used = []
    for event in events:
        labels = []
        mapped = KIND_TOOLS.get(event["kind"])
        if mapped:
            labels.append(mapped)
        if str(event.get("type") or "").casefold() == "command_execution" and "shell" not in labels:
            labels.append("shell")
        for label in labels:
            if label not in tools_used:
                tools_used.append(label)
    usage = {}
    for event in events:
        if event.get("usage"):
            usage = event["usage"]
    tool_sources = []
    for event in events:
        if event["kind"] == "web_search":
            tool_sources.extend(event.get("sources") or [])
    return {
        "events": events,
        "assistant_output_raw": "\n\n".join(assistant).strip(),
        "tools_used": tools_used,
        "usage": usage,
        "tool_sources": tool_sources,
    }
