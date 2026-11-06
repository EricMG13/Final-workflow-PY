"""Copilot session events -> Turn. Bodies are JSON arrays of {"type", "data"} events."""

import json
import uuid
from decimal import Decimal
from typing import Any

from deploy_workflow.model.copilot import event_record
from deploy_workflow.model.providers import ErrorKind, ProviderError, parse
from deploy_workflow.model.redact import Redactor
from deploy_workflow.model.turn import ToolCall, Turn, Usage, dump_json

TEXT_TURN = Turn(
    "done",
    (),
    Usage(
        input_tokens=12,
        cached_read_tokens=4,
        cache_write_tokens=0,
        output_tokens=7,
        reasoning_tokens=2,
    ),
    "end",
    "gpt-6.1-sol",
    "api-1",
    200,
    billed_usd=Decimal("0.000123"),
)


def usage(**extra: Any) -> dict[str, Any]:
    return {
        "type": "assistant.usage",
        "data": {"model": "gpt-6.1-sol", "inputTokens": 1, "outputTokens": 2, **extra},
    }


def message(content: str) -> dict[str, Any]:
    return {"type": "assistant.message", "data": {"content": content}}


def start(call_id: str, name: str, arguments: Any) -> dict[str, Any]:
    return {
        "type": "tool.execution_start",
        "data": {"toolCallId": call_id, "toolName": name, "arguments": arguments},
    }


def run(*events: dict[str, Any]) -> Turn | ProviderError:
    return parse("copilot", 200, json.dumps(list(events)).encode(), {}, Redactor())


def turn(*events: dict[str, Any]) -> Turn:
    result = run(*events)
    assert isinstance(result, Turn), result
    return result


def error(*events: dict[str, Any]) -> ProviderError:
    result = run(*events)
    assert isinstance(result, ProviderError), result
    return result


def test_text_turn() -> None:
    result = turn(
        usage(
            inputTokens=12,
            cacheReadTokens=4,
            cacheWriteTokens=0,
            outputTokens=7,
            reasoningTokens=2,
            copilotUsage={"totalNanoAiu": 12300000},
            cost=0.5,
            finishReason="stop",
            apiCallId="api-1",
        ),
        message("done"),
        {"type": "session.idle", "data": {}},
    )
    assert result == TEXT_TURN


def test_tool_turn() -> None:
    result = turn(
        usage(finishReason="tool_calls", numToolCalls=2),
        start("c1", "read", {"p": 1}),
        start("c2", "write", {}),
    )
    assert result.stop_reason == "tool_use"
    assert result.tool_calls == (ToolCall("c1", "read", {"p": 1}), ToolCall("c2", "write", {}))
    assert result.text == ""


def test_non_object_arguments_are_bad_arguments() -> None:
    result = turn(usage(finishReason="tool_calls", numToolCalls=1), start("c1", "read", "[1,2]"))
    assert result.tool_calls == (ToolCall("c1", "read", {}, bad_arguments='"[1,2]"'),)


def test_tool_count_mismatch_is_unparsable() -> None:
    result = error(
        usage(finishReason="tool_calls", numToolCalls=1),
        start("c1", "a", {}),
        start("c2", "b", {}),
    )
    assert result.error_class == "UnparsableReply"
    assert result.kind is ErrorKind.SENT_CHARGE_UNKNOWN


def test_tool_calls_without_count_are_unparsable() -> None:
    result = error(usage(finishReason="tool_calls"), start("c1", "a", {}))
    assert result.error_class == "UnparsableReply"


def test_usage_without_cost_has_no_billed_usd() -> None:
    assert turn(usage(cost=0.5)).billed_usd is None
    assert turn(usage(copilotUsage={"totalNanoAiu": 0})).billed_usd == Decimal(0)
    for bad in ("12300000.5", "-1", '"12300000"'):
        body = '[{"type":"assistant.usage","data":{"copilotUsage":{"totalNanoAiu":' + bad + "}}}]"
        result = parse("copilot", 200, body.encode(), {}, Redactor())
        assert isinstance(result, Turn)
        assert result.billed_usd is None
    whole = '[{"type":"assistant.usage","data":{"copilotUsage":{"totalNanoAiu":12300000.0}}}]'
    result = parse("copilot", 200, whole.encode(), {}, Redactor())
    assert isinstance(result, Turn)
    assert result.billed_usd == Decimal("0.000123")


def test_nano_aiu_keeps_its_digits() -> None:
    # synthetic-body scope: the SDK types the field as float; a live value is exact only below 2**53
    result = turn(usage(copilotUsage={"totalNanoAiu": 123456789012345678}))
    assert result.billed_usd == Decimal("1234567.89012345678")


def test_key_split_across_messages_is_reflected() -> None:
    key = "ghp_" + "A" * 36
    result = error(message(key[:24]), message(key[24:]), usage())
    assert result.error_class == "KeyReflected"


def test_key_in_event_text_is_reflected() -> None:
    result = error(message("see ghp_" + "A" * 36), usage())
    assert result.error_class == "KeyReflected"


def test_two_usage_events_are_unparsable() -> None:
    assert error(usage(), usage()).error_class == "UnparsableReply"


def test_no_usage_is_unparsable() -> None:
    assert error(message("hi")).error_class == "UnparsableReply"


def test_not_a_list_is_unparsable() -> None:
    result = parse("copilot", 200, b"{}", {}, Redactor())
    assert isinstance(result, ProviderError)
    assert result.error_class == "UnparsableReply"


def test_session_error_with_usage_is_sent_usage() -> None:
    err = {
        "type": "session.error",
        "data": {"errorType": "provider", "message": "upstream 503", "statusCode": 503},
    }
    result = error(usage(outputTokens=9), err)
    assert result.kind is ErrorKind.SENT_CHARGE_USAGE
    assert result.error_class == "SessionError"
    assert result.http_status == 503
    assert result.usage is not None
    assert result.usage.output_tokens == 9
    assert "upstream 503" in result.message
    assert error(err).kind is ErrorKind.SENT_CHARGE_UNKNOWN


def test_length_without_calls_is_reply_cut() -> None:
    result = error(usage(finishReason="length", outputTokens=9, apiCallId="a1"))
    assert result.error_class == "ReplyCut"
    assert result.kind is ErrorKind.SENT_CHARGE_USAGE
    assert result.usage is not None
    assert result.usage.output_tokens == 9
    assert result.request_id == "a1"
    body = json.dumps([usage(finishReason="length")]).encode()
    cut = parse("copilot", 200, body, {}, Redactor(), cut_as_turn=True)
    assert isinstance(cut, Turn)
    assert cut.stop_reason == "max_tokens"


def test_length_with_calls_is_a_max_tokens_turn() -> None:
    result = turn(usage(finishReason="length", numToolCalls=1), start("c1", "a", {}))
    assert result.stop_reason == "max_tokens"
    assert len(result.tool_calls) == 1


def test_calls_under_stop_are_unparsable() -> None:
    for extra in ({"finishReason": "stop"}, {"finishReason": "stop", "numToolCalls": 1}, {}):
        assert error(usage(**extra), start("c1", "a", {})).error_class == "UnparsableReply"


def test_anthropic_finish_words() -> None:
    assert turn(usage(finishReason="end_turn")).stop_reason == "end"
    result = turn(usage(finishReason="tool_use", numToolCalls=1), start("c1", "a", {}))
    assert result.stop_reason == "tool_use"
    assert error(usage(finishReason="max_tokens")).error_class == "ReplyCut"


def test_duplicate_tool_call_id_is_unparsable() -> None:
    result = error(
        usage(finishReason="tool_calls", numToolCalls=2), start("c", "a", {}), start("c", "b", {})
    )
    assert result.error_class == "UnparsableReply"


def test_absent_arguments_are_empty() -> None:
    absent = {"type": "tool.execution_start", "data": {"toolCallId": "c1", "toolName": "a"}}
    for event in (absent, start("c1", "a", None)):
        result = turn(usage(finishReason="tool_calls", numToolCalls=1), event)
        assert result.tool_calls == (ToolCall("c1", "a", {}),)


def test_sub_agent_start_is_unparsable() -> None:
    sub = start("c1", "a", {})
    sub["data"]["parentToolCallId"] = "p1"
    result = error(usage(finishReason="tool_calls", numToolCalls=1), sub)
    assert result.error_class == "UnparsableReply"


def test_non_string_content_is_unparsable() -> None:
    for content in (["a"], {"t": 1}, None, 7):
        result = error(
            message("kept"), {"type": "assistant.message", "data": {"content": content}}, usage()
        )
        assert result.error_class == "UnparsableReply"


def test_usage_without_counts_makes_error_unknown() -> None:
    err = {"type": "session.error", "data": {"errorType": "x", "message": "m"}}
    bare = {"type": "assistant.usage", "data": {"model": "m"}}
    assert error(bare, err).kind is ErrorKind.SENT_CHARGE_UNKNOWN


def test_nano_aiu_above_the_digit_cap_is_unpriced() -> None:
    assert turn(usage(copilotUsage={"totalNanoAiu": 10**45})).billed_usd is None


def test_real_sdk_events_round_trip() -> None:
    from copilot.generated.session_events import SessionEvent

    def ev(kind: str, data: dict[str, Any]) -> Any:
        return SessionEvent.from_dict(
            {
                "id": str(uuid.uuid4()),
                "timestamp": "2026-11-06T10:00:00.000Z",
                "type": kind,
                "data": data,
            }
        )

    events = [
        ev(
            "assistant.usage",
            {
                "model": "gpt-6.1-sol",
                "inputTokens": 12,
                "cacheReadTokens": 4,
                "cacheWriteTokens": 0,
                "outputTokens": 7,
                "reasoningTokens": 2,
                "copilotUsage": {"totalNanoAiu": 12300000, "tokenDetails": []},
                "cost": 0.5,
                "finishReason": "stop",
                "apiCallId": "api-1",
            },
        ),
        ev("assistant.message", {"content": "done", "messageId": "m1"}),
        ev("session.idle", {}),
    ]
    body = dump_json([event_record(e) for e in events]).encode()
    result = parse("copilot", 200, body, {}, Redactor())
    assert result == TEXT_TURN


def test_unknown_finish_reason_is_other() -> None:
    assert turn(usage(finishReason="content_filter")).stop_reason == "other"
    assert turn(usage()).stop_reason == "other"
