"""GitHub Copilot SDK adapter: the parsing half.

One call's raw body is the JSON array of the session events observed for that call, each
``{"type": <event type>, "data": <event data as camelCase wire keys>}``. ``parse_events`` maps it
to the ``Turn`` the loop prices and records. This half imports nothing from the ``copilot`` SDK
package (the SDK is top-level ``copilot``; this module is ``deploy_workflow.model.copilot``).
"""

from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal
from typing import Any

from deploy_workflow.model.providers import (
    ErrorKind,
    ProviderError,
    _BadReply,
    _count,
    _id,
    _snippet,
    _str_or_none,
)
from deploy_workflow.model.redact import Redactor
from deploy_workflow.model.turn import (
    StopReason,
    ToolCall,
    Turn,
    TurnError,
    Usage,
    dump_json,
    load_json,
)

USAGE = "assistant.usage"
MESSAGE = "assistant.message"
TOOL_START = "tool.execution_start"
SESSION_ERROR = "session.error"

_FINISH: Mapping[str, StopReason] = {
    "stop": "end",
    "tool_calls": "tool_use",
    "length": "max_tokens",
}

# 1 AI unit = 1 AI credit = $0.01; the wire counts nano-AIU: usd = nano * 1E-9 * 0.01.
_USD_EXPONENT = -11
# A count above this many digits is not a plausible charge; it is left unpriced (None) rather than
# expanded into an enormous integer.
_MAX_NANO_DIGITS = 38


def event_record(event: Any) -> dict[str, Any]:
    """One SDK session event as the body's ``{"type", "data"}`` object."""
    return {"type": event.type.value, "data": event.data.to_dict()}


def _billed_usd(data: Mapping[str, Any]) -> Decimal | None:
    """The charge from ``copilotUsage.totalNanoAiu``, exact; None when absent, negative,
    non-integer-valued or non-numeric. The experimental ``cost`` field is ignored."""
    usage = data.get("copilotUsage")
    raw = usage.get("totalNanoAiu") if isinstance(usage, dict) else None
    if isinstance(raw, bool) or not isinstance(raw, int | Decimal):
        return None
    if isinstance(raw, Decimal) and (
        not raw.is_finite() or raw != raw.to_integral_value() or raw.adjusted() > _MAX_NANO_DIGITS
    ):
        return None
    nano = int(raw)
    if nano < 0:
        return None
    # built from its digits: no context rounding, no float
    return Decimal((0, tuple(int(d) for d in str(nano)), _USD_EXPONENT))


def _events(text: str) -> list[tuple[str, dict[str, Any]]]:
    try:
        body = load_json(text)
    except TurnError:
        raise _BadReply("reply is not JSON") from None
    if not isinstance(body, list):
        raise _BadReply("reply is not a JSON array of events")
    events: list[tuple[str, dict[str, Any]]] = []
    for item in body:
        kind = item.get("type") if isinstance(item, dict) else None
        data = item.get("data") if isinstance(item, dict) else None
        if not isinstance(kind, str) or not isinstance(data, dict):
            raise _BadReply("an event is not an object with a type and data")
        events.append((kind, data))
    return events


def _tool_call(data: Mapping[str, Any], seen: list[Any]) -> ToolCall:
    call_id, name = _id(data, "toolCallId"), _id(data, "toolName")
    seen.append(name)
    arguments = data.get("arguments")
    if isinstance(arguments, dict):
        seen.append(arguments)
        return ToolCall(call_id, name, arguments)
    try:
        raw = dump_json(arguments)
    except TurnError:
        raise _BadReply("tool arguments cannot be written as JSON") from None
    seen.append(raw)
    return ToolCall(call_id, name, {}, bad_arguments=raw)


def _usage(data: Mapping[str, Any]) -> Usage:
    return Usage(
        input_tokens=_count(data, "inputTokens"),
        cached_read_tokens=_count(data, "cacheReadTokens"),
        cache_write_tokens=_count(data, "cacheWriteTokens"),
        output_tokens=_count(data, "outputTokens"),
        reasoning_tokens=_count(data, "reasoningTokens"),
    )


def _request_id(data: Mapping[str, Any]) -> str | None:
    return _str_or_none(data.get("apiCallId")) or _str_or_none(data.get("providerCallId"))


def _session_error(
    data: Mapping[str, Any],
    usage_data: Mapping[str, Any] | None,
    redactor: Redactor,
    seen: list[Any],
) -> ProviderError:
    parts = [_str_or_none(data.get("errorType")), _str_or_none(data.get("message"))]
    detail = ": ".join(p for p in parts if p)
    seen.append(detail)
    code = data.get("statusCode")
    status = code if isinstance(code, int) and not isinstance(code, bool) else None
    snippet = _snippet(redactor, detail)
    if usage_data is None:
        return ProviderError(ErrorKind.SENT_CHARGE_UNKNOWN, "SessionError", snippet, status)
    return ProviderError(
        ErrorKind.SENT_CHARGE_USAGE,
        "SessionError",
        snippet,
        status,
        _usage(usage_data),
        _billed_usd(usage_data),
        _str_or_none(usage_data.get("model")),
        _request_id(usage_data),
    )


def parse_events(
    text: str, redactor: Redactor, seen: list[Any], cut_as_turn: bool = False
) -> Turn | ProviderError:
    """The turn one call's session events make. ``cut_as_turn`` exists for old recordings of
    other providers and is ignored here. Raises ``_BadReply`` on a body of the wrong shape."""
    events = _events(text)
    usages = [d for k, d in events if k == USAGE]
    errors = [d for k, d in events if k == SESSION_ERROR]
    if len(usages) > 1:
        raise _BadReply("more than one assistant.usage event")
    usage_data = usages[0] if usages else None
    contents: list[str] = []
    for kind, data in events:
        if kind == MESSAGE and isinstance(data.get("content"), str):
            contents.append(data["content"])
    seen.extend(contents)
    seen.append("".join(contents))
    if errors:
        return _session_error(errors[0], usage_data, redactor, seen)
    if usage_data is None:
        raise _BadReply("no assistant.usage event")
    calls = tuple(_tool_call(d, seen) for k, d in events if k == TOOL_START)
    finish = usage_data.get("finishReason")
    stop: StopReason = _FINISH.get(finish, "other") if isinstance(finish, str) else "other"
    expected = _count(usage_data, "numToolCalls")
    if expected is not None and expected != len(calls):
        raise _BadReply(f"tool count {len(calls)} differs from numToolCalls {expected}")
    if stop == "tool_use" and expected is None:
        raise _BadReply("tool count unknown")
    if stop == "tool_use" and not calls:
        raise _BadReply("stop reason tool_use with no tool call")
    return Turn(
        "".join(contents),
        calls,
        _usage(usage_data),
        stop,
        _str_or_none(usage_data.get("model")),
        _request_id(usage_data),
        200,
        _billed_usd(usage_data),
    )
