"""S16 review: the Copilot adapter and parser against a fake client. No runtime, no network."""

import asyncio
import json
from decimal import Decimal
from typing import Any

from deploy_workflow.model.copilot_adapter import CopilotAdapter
from deploy_workflow.model.providers import ErrorKind, ProviderError, parse
from deploy_workflow.model.redact import Redactor
from deploy_workflow.model.turn import Message, ToolCall, TurnRequest
from tests.model.test_copilot_adapter import (
    DIGEST,
    SYSTEM,
    TOOL,
    USER,
    Await,
    FakeSession,
    Invoke,
    Rig,
    call,
    request,
    rig,  # noqa: F401 - the fixture
    said,
    text_script,
    tool_script,
    tool_turn_history,
    usage,
)


def _events(*events: dict[str, Any]) -> bytes:
    return json.dumps(list(events)).encode()


def test_a_tool_turn_without_num_tool_calls_keeps_its_exact_charge() -> None:
    body = _events(
        {"type": "assistant.message", "data": {"content": ""}},
        {
            "type": "assistant.usage",
            "data": {
                "model": "gpt-6.1-sol",
                "inputTokens": 10,
                "outputTokens": 5,
                "finishReason": "tool_calls",
                "copilotUsage": {"totalNanoAiu": 1234000000},
            },
        },
        {
            "type": "tool.execution_start",
            "data": {"toolCallId": "c1", "toolName": "read_pages", "arguments": {}},
        },
    )
    outcome = parse("copilot", 200, body, {}, Redactor())
    assert isinstance(outcome, ProviderError) and outcome.error_class == "UnparsableReply"
    assert outcome.kind is ErrorKind.SENT_CHARGE_USAGE
    assert outcome.billed_usd == Decimal("0.01234000000")  # 1.234 AIU at $0.01


def test_a_shape_failure_without_a_charge_stays_unknown() -> None:
    body = _events(
        {
            "type": "assistant.usage",
            "data": {"model": "gpt-6.1-sol", "finishReason": "tool_calls"},
        },
    )
    outcome = parse("copilot", 200, body, {}, Redactor())
    assert isinstance(outcome, ProviderError)
    assert outcome.kind is ErrorKind.SENT_CHARGE_UNKNOWN and outcome.billed_usd is None


def test_a_session_error_with_only_a_charge_settles_from_it() -> None:
    body = _events(
        {"type": "assistant.usage", "data": {"copilotUsage": {"totalNanoAiu": 5000000000}}},
        {"type": "session.error", "data": {"errorType": "x", "statusCode": 503}},
    )
    outcome = parse("copilot", 200, body, {}, Redactor())
    assert isinstance(outcome, ProviderError) and outcome.error_class == "SessionError"
    assert outcome.kind is ErrorKind.SENT_CHARGE_USAGE
    assert outcome.billed_usd == Decimal("0.05000000000")


def test_the_session_turns_off_large_output_files_and_compaction(rig: Rig) -> None:  # noqa: F811
    adapter = rig.make(text_script())
    assert call(adapter, request()).kind == "ok"
    options = rig.session.options
    assert options["large_output"] == {"enabled": False}
    assert options["infinite_sessions"] == {"enabled": False}


def test_bad_arguments_compare_by_value_not_spelling(rig: Rig) -> None:  # noqa: F811
    script: list[Any] = [
        said(""),
        usage(finishReason="tool_calls", numToolCalls=1),
        Invoke("c1", "read_pages", [1e-07]),  # type: ignore[arg-type]
        Await(),
    ]
    adapter = rig.make(script)
    reply = call(adapter, request())
    assert reply.kind == "ok" and reply.turn is not None
    assert reply.turn.tool_calls == (ToolCall("c1", "read_pages", {}, bad_arguments="[1E-7]"),)


def test_end_exchange_stops_the_runtime_before_close(rig: Rig) -> None:  # noqa: F811
    adapter = rig.make(tool_script())
    assert call(adapter, request()).kind == "ok"
    awaited = adapter._states[DIGEST].pending["c1"]
    adapter.end_exchange(DIGEST)
    assert adapter._loop is not None

    async def settled() -> None:
        while DIGEST in adapter._states:
            await asyncio.sleep(0.01)

    asyncio.run_coroutine_threadsafe(settled(), adapter._loop).result(5)
    assert rig.client.stopped == 1 and rig.session.disconnected == 1
    assert awaited.cancelled()


def test_handlers_are_cancelled_only_after_the_session_is_detached(rig: Rig) -> None:  # noqa: F811
    seen: list[bool] = []

    class Watching(FakeSession):
        async def disconnect(self) -> None:
            state = adapter._states[DIGEST]
            seen.extend(f.cancelled() for f in state.pending.values())
            await super().disconnect()

    async def create_session(**options: Any) -> FakeSession:
        session = Watching(rig.client.script, options)
        rig.client.sessions.append(session)
        return session

    rig.client.create_session = create_session  # type: ignore[method-assign]
    adapter = rig.make(tool_script())
    assert call(adapter, request()).kind == "ok"
    adapter.close()
    assert seen == [False]


def test_a_later_call_at_another_effort_is_not_sent(rig: Rig) -> None:  # noqa: F811
    adapter = rig.make(tool_script())
    assert call(adapter, request()).kind == "ok"
    answer = Message("tool", "PAGE", tool_call_id="c1")
    high = TurnRequest((*tool_turn_history(), answer), (TOOL,), 1000, "high")
    reply = call(adapter, high, 1)
    assert reply.kind == "not_sent" and reply.error_class == "EffortMismatch"
    assert DIGEST in adapter._states  # the live exchange is left as it is


def test_the_copilot_adapter_does_not_resend_a_failed_call() -> None:
    assert CopilotAdapter.resends is False
    assert SYSTEM.role == "system" and USER.role == "user"
