"""Copilot session events -> Turn. Bodies are JSON arrays of {"type", "data"} events."""

import json
from decimal import Decimal
from typing import Any

from deploy_workflow.model.providers import ErrorKind, ProviderError, parse
from deploy_workflow.model.redact import Redactor
from deploy_workflow.model.turn import ToolCall, Turn, Usage


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
    assert result == Turn(
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
    result = turn(usage(), start("c1", "read", "[1,2]"))
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


def test_length_maps_to_max_tokens() -> None:
    assert turn(usage(finishReason="length")).stop_reason == "max_tokens"


def test_unknown_finish_reason_is_other() -> None:
    assert turn(usage(finishReason="content_filter")).stop_reason == "other"
    assert turn(usage()).stop_reason == "other"
