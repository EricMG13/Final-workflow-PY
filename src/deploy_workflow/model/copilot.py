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
    REPLY_CUT,
    ErrorKind,
    ProviderError,
    _BadReply,
    _count,
    _id,
    _snippet,
    _str_or_none,
    _usage_error,
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

# Both vocabularies: OpenAI's words and Anthropic's, whichever the runtime passes through.
_FINISH: Mapping[str, StopReason] = {
    "stop": "end",
    "end_turn": "end",
    "tool_calls": "tool_use",
    "tool_use": "tool_use",
    "length": "max_tokens",
    "max_tokens": "max_tokens",
}

# 1 AI unit = 1 AI credit = $0.01; the wire counts nano-AIU: usd = nano * 1E-9 * 0.01.
_USD_EXPONENT = -11
# An integer-valued count of more than this many digits is not a plausible charge; it is left
# unpriced (None), whether written as a JSON integer or as a decimal, rather than expanded.
_MAX_NANO_DIGITS = 39


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
        not raw.is_finite() or raw != raw.to_integral_value() or raw.adjusted() >= _MAX_NANO_DIGITS
    ):
        return None
    nano = int(raw)
    if nano < 0 or len(str(nano)) > _MAX_NANO_DIGITS:
        return None
    # built from its digits: no context rounding, no float
    return Decimal((0, tuple(int(d) for d in str(nano)), _USD_EXPONENT))


def _events(text: str) -> tuple[list[Any], list[tuple[str, dict[str, Any]]]]:
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
    return body, events


def _tool_call(data: Mapping[str, Any], seen: list[Any]) -> ToolCall:
    call_id, name = _id(data, "toolCallId"), _id(data, "toolName")
    if data.get("parentToolCallId") is not None:
        raise _BadReply("sub-agent tool call")
    seen.append(name)
    arguments = data.get("arguments")
    if arguments is None:
        return ToolCall(call_id, name, {})
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
    counts, billed = _usage(usage_data), _billed_usd(usage_data)
    if counts == Usage() and billed is None:
        return ProviderError(ErrorKind.SENT_CHARGE_UNKNOWN, "SessionError", snippet, status)
    # counts or an exact copilotUsage charge: the call settles from what was reported
    return ProviderError(
        ErrorKind.SENT_CHARGE_USAGE,
        "SessionError",
        snippet,
        status,
        counts,
        billed,
        _str_or_none(usage_data.get("model")),
        _request_id(usage_data),
    )


def parse_events(
    text: str, redactor: Redactor, seen: list[Any], cut_as_turn: bool = False
) -> Turn | ProviderError:
    """The turn one call's session events make. A length-cut reply with no tool call is
    ``ReplyCut`` (CP1H-R16) unless ``cut_as_turn``, which keeps it a max_tokens turn.

    Raises ``_BadReply`` on a body of the wrong shape, except once the call's usage event
    reported an exact ``copilotUsage.totalNanoAiu`` charge: a later shape failure is then an
    ``UnparsableReply`` that is still refused but settles from that charge."""
    body, events = _events(text)
    seen.append(body)
    usages = [d for k, d in events if k == USAGE]
    errors = [d for k, d in events if k == SESSION_ERROR]
    if len(usages) > 1:
        raise _BadReply("more than one assistant.usage event")
    usage_data = usages[0] if usages else None
    contents: list[str] = []
    for kind, data in events:
        if kind == MESSAGE:
            content = data.get("content")
            if not isinstance(content, str):
                raise _BadReply("an assistant.message content is not a string")
            contents.append(content)
    seen.extend(contents)
    seen.append("".join(contents))
    if errors:
        return _session_error(errors[0], usage_data, redactor, seen)
    if usage_data is None:
        raise _BadReply("no assistant.usage event")
    try:
        return _turn(events, usage_data, "".join(contents), seen, cut_as_turn)
    except _BadReply as error:
        return _billed_unparsable(usage_data, error, redactor)


def _billed_unparsable(
    usage_data: Mapping[str, Any], error: _BadReply, redactor: Redactor
) -> ProviderError:
    """A reply refused for its shape after its usage event: with an exact charge it settles
    from that charge (counts kept when they are well formed); without one it stays unknown."""
    billed = _billed_usd(usage_data)
    if billed is None:
        raise error
    try:
        usage = _usage(usage_data)
    except _BadReply:
        usage = Usage()
    model, rid = _str_or_none(usage_data.get("model")), _request_id(usage_data)
    detail = _snippet(redactor, str(error))
    return _usage_error("UnparsableReply", detail, 200, usage, model, rid, billed)


def _check_tool_count(stop: StopReason, expected: int | None, calls: tuple[ToolCall, ...]) -> None:
    """The announced count, the stop reason and the tool calls must agree."""
    if expected is not None and expected != len(calls):
        raise _BadReply(f"tool count {len(calls)} differs from numToolCalls {expected}")
    if stop == "tool_use" and expected is None:
        raise _BadReply("tool count unknown")
    if stop == "tool_use" and not calls:
        raise _BadReply("stop reason tool_use with no tool call")
    if calls and stop not in ("tool_use", "max_tokens"):
        raise _BadReply("tool calls without finishReason tool_calls")


def _turn(
    events: list[tuple[str, dict[str, Any]]],
    usage_data: Mapping[str, Any],
    text: str,
    seen: list[Any],
    cut_as_turn: bool,
) -> Turn | ProviderError:
    calls = tuple(_tool_call(d, seen) for k, d in events if k == TOOL_START)
    if len({c.call_id for c in calls}) != len(calls):
        raise _BadReply("duplicate toolCallId")
    finish = usage_data.get("finishReason")
    stop: StopReason = _FINISH.get(finish, "other") if isinstance(finish, str) else "other"
    _check_tool_count(stop, _count(usage_data, "numToolCalls"), calls)
    usage = _usage(usage_data)
    model, rid = _str_or_none(usage_data.get("model")), _request_id(usage_data)
    billed = _billed_usd(usage_data)
    if stop == "max_tokens" and not calls and not cut_as_turn:
        detail = "finishReason length or max_tokens"
        return _usage_error(REPLY_CUT, detail, 200, usage, model, rid, billed)
    return Turn(text, calls, usage, stop, model, rid, 200, billed)
