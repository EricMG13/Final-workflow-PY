"""CopilotAdapter against a fake client. No runtime, no network, no provider.

The fake imports the SDK only to build real ``SessionEvent`` objects and a real
``ToolInvocation``; the adapter under test imports nothing from the SDK. The fake plays a
script: ``Emit`` delivers an event, ``Invoke`` delivers ``tool.execution_start`` and calls the
registered tool handler in a task, ``Idle`` delivers ``session.idle``, ``Await`` waits for every
started handler to return before the script goes on.
"""

import asyncio
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from copilot.generated.session_events import SessionEvent
from copilot.tools import ToolInvocation

from deploy_workflow.model.adapter import (
    _REFLECTED_RAW,
    AdapterReply,
    LivePauseInForce,
)
from deploy_workflow.model.copilot import event_record
from deploy_workflow.model.copilot_adapter import ClientOptions, CopilotAdapter
from deploy_workflow.model.redact import Redactor
from deploy_workflow.model.turn import (
    Message,
    ModelSpec,
    ToolCall,
    ToolSpec,
    TurnRequest,
    dump_json,
)

SPEC = ModelSpec("copilot-sol-medium", "copilot", "gpt-6.1-sol", "medium")
DIGEST = "d" * 64
TOKEN = "ghp_" + "A" * 36
RULING_TEXT = (
    "lifts: live-provider-pause\nby: user\ndate: 2026-11-01\nconfigs: copilot-sol-medium\n"
)
TOOL = ToolSpec("read_pages", "Read pages.", {"type": "object", "properties": {"p": {}}})
SYSTEM = Message("system", "SYSTEM TEXT")
USER = Message("user", "hello")


# ---------------------------------------------------------------- the script


@dataclass
class Emit:
    event: dict[str, Any]


@dataclass
class Invoke:
    call_id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class Idle:
    pass


@dataclass
class Await:
    pass


Step = Emit | Invoke | Idle | Await


def wire(kind: str, data: dict[str, Any], agent: str | None = None) -> dict[str, Any]:
    return {
        "type": kind,
        "id": str(uuid.uuid4()),
        "timestamp": "2026-11-06T00:00:00Z",
        "data": data,
        "agentId": agent,
    }


def usage(**extra: Any) -> Emit:
    data = {"model": "gpt-6.1-sol", "inputTokens": 10, "outputTokens": 5, "finishReason": "stop"}
    return Emit(wire("assistant.usage", {**data, **extra}))


def said(content: str, agent: str | None = None) -> Emit:
    return Emit(wire("assistant.message", {"content": content, "messageId": "m"}, agent))


def text_script(content: str = "ANSWER") -> list[Step]:
    return [said(content), usage(copilotUsage={"totalNanoAiu": 123456}), Idle()]


class FakeSession:
    def __init__(self, script: list[Step], options: dict[str, Any]) -> None:
        self.script, self.options = script, options
        self.handlers: list[Callable[[Any], None]] = []
        self.sent: list[str] = []
        self.aborted = 0
        self.disconnected = 0
        self.tasks: dict[str, asyncio.Task[Any]] = {}
        self.results: dict[str, Any] = {}
        self._played: asyncio.Task[None] | None = None

    def on(self, handler: Callable[[Any], None]) -> Callable[[], None]:
        self.handlers.append(handler)
        return lambda: self.handlers.remove(handler)

    async def send(self, text: str, /) -> str:
        self.sent.append(text)
        if self._played is None:  # later sends are nudges: recorded, nothing replayed
            self._played = asyncio.ensure_future(self._play())
        return "message-id"

    async def abort(self) -> None:
        self.aborted += 1

    async def disconnect(self) -> None:
        self.disconnected += 1

    def deliver(self, event: dict[str, Any]) -> None:
        parsed = SessionEvent.from_dict(event)
        for handler in list(self.handlers):
            handler(parsed)

    async def _call(self, step: Invoke) -> None:
        tool = next(t for t in self.options["tools"] if t.name == step.name)
        self.results[step.call_id] = await tool.handler(
            ToolInvocation(tool_call_id=step.call_id, tool_name=step.name, arguments=step.arguments)
        )

    async def _play(self) -> None:
        for step in self.script:
            await asyncio.sleep(0)
            if isinstance(step, Emit):
                self.deliver(step.event)
            elif isinstance(step, Idle):
                self.deliver(wire("session.idle", {}))
            elif isinstance(step, Invoke):
                self.deliver(
                    wire(
                        "tool.execution_start",
                        {
                            "toolCallId": step.call_id,
                            "toolName": step.name,
                            "arguments": step.arguments,
                        },
                    )
                )
                self.tasks[step.call_id] = asyncio.ensure_future(self._call(step))
            else:
                await asyncio.gather(*self.tasks.values(), return_exceptions=True)


class FakeClient:
    def __init__(self, script: list[Step], models: list[dict[str, Any]] | None = None) -> None:
        self.script = script
        self.models = (
            models
            if models is not None
            else [{"id": "gpt-6.1-sol", "supportedReasoningEfforts": ["low", "medium", "high"]}]
        )
        self.started = 0
        self.stopped = 0
        self.sessions: list[FakeSession] = []

    async def start(self) -> None:
        self.started += 1

    async def list_models(self) -> list[dict[str, Any]]:
        return self.models

    async def create_session(self, **options: Any) -> FakeSession:
        session = FakeSession(self.script, options)
        self.sessions.append(session)
        return session

    async def stop(self) -> None:
        self.stopped += 1


class Rig:
    def __init__(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        self.root = tmp_path / "rulings"
        self.root.mkdir()
        self.ruling = self.root / "lift.md"
        self.ruling.write_text(RULING_TEXT, encoding="utf-8")
        self.runtime = tmp_path / "copilot-runtime"
        self.runtime.write_text("#!/bin/sh\n")
        self.home_root = tmp_path
        monkeypatch.chdir(tmp_path)
        self.environ = {"COPILOT_GITHUB_TOKEN": TOKEN, "COPILOT_CLI_PATH": str(self.runtime)}
        self.client = FakeClient([])
        self.options: list[ClientOptions] = []
        self.adapters: list[CopilotAdapter] = []
        self.clock_value = 1000.0

    def factory(self, options: ClientOptions) -> FakeClient:
        self.options.append(options)
        return self.client

    def clock(self) -> float:
        self.clock_value += 1.0
        return self.clock_value

    def make(self, script: list[Step], **kwargs: Any) -> CopilotAdapter:
        self.client.script = script
        adapter = CopilotAdapter(
            SPEC,
            self.ruling,
            environ=kwargs.pop("environ", self.environ),
            clock=self.clock,
            rulings_root=self.root,
            client_factory=self.factory,
            **kwargs,
        )
        self.adapters.append(adapter)
        return adapter

    @property
    def session(self) -> FakeSession:
        return self.client.sessions[0]


@pytest.fixture
def rig(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Any:
    made = Rig(tmp_path, monkeypatch)
    yield made
    for adapter in made.adapters:
        adapter.close()


def request(*messages: Message, tools: tuple[ToolSpec, ...] = (TOOL,)) -> TurnRequest:
    return TurnRequest(messages or (SYSTEM, USER), tools, 1000, "medium")


def call(adapter: CopilotAdapter, req: TurnRequest, index: int = 0) -> AdapterReply:
    return adapter.complete(req, invocation_digest=DIGEST, call_index=index, reservation_id="r")


def tool_script(*, then: list[Step] | None = None) -> list[Step]:
    first: list[Step] = [
        said(""),
        usage(finishReason="tool_calls", numToolCalls=1),
        Invoke("c1", "read_pages", {"p": 1}),
        Await(),
    ]
    return first + (then if then is not None else text_script())


def tool_turn_history() -> tuple[Message, ...]:
    return (
        SYSTEM,
        USER,
        Message("assistant", "", (ToolCall("c1", "read_pages", {"p": 1}),)),
    )


# ---------------------------------------------------------------- refusals before any send


def test_gate_runs_before_environment(rig: Rig) -> None:
    rig.ruling.write_text(RULING_TEXT.replace("copilot-sol-medium", "other"), encoding="utf-8")
    with pytest.raises(LivePauseInForce):
        rig.make(text_script(), environ=None)
    assert rig.options == []


def test_missing_token_is_not_sent(rig: Rig) -> None:
    env = {**rig.environ, "COPILOT_GITHUB_TOKEN": ""}
    reply = call(rig.make(text_script(), environ=env), request())
    assert reply.kind == "not_sent" and reply.error_class == "KeyMissing"
    assert reply.message is not None and "COPILOT_GITHUB_TOKEN" in reply.message
    assert rig.options == [] and rig.client.sessions == []


@pytest.mark.parametrize("runtime", [None, "directory", "absent"])
def test_missing_runtime_is_not_sent(rig: Rig, tmp_path: Path, runtime: str | None) -> None:
    env = {"COPILOT_GITHUB_TOKEN": TOKEN}
    if runtime == "directory":
        env["COPILOT_CLI_PATH"] = str(tmp_path)
    elif runtime == "absent":
        env["COPILOT_CLI_PATH"] = str(tmp_path / "missing")
    reply = call(rig.make(text_script(), environ=env), request())
    assert reply.kind == "not_sent" and reply.error_class == "RuntimeMissing"
    assert reply.message is not None and "COPILOT_CLI_PATH" in reply.message
    assert str(tmp_path) not in reply.message
    assert rig.client.sessions == []


def test_model_not_listed_is_not_sent(rig: Rig) -> None:
    rig.client.models = [{"id": "other", "supportedReasoningEfforts": ["medium"]}]
    reply = call(rig.make(text_script()), request())
    assert reply.kind == "not_sent" and reply.error_class == "ModelUnavailable"
    assert rig.client.sessions == []


def test_effort_not_supported_is_not_sent(rig: Rig) -> None:
    rig.client.models = [{"id": "gpt-6.1-sol", "supportedReasoningEfforts": ["low"]}]
    reply = call(rig.make(text_script()), request())
    assert reply.kind == "not_sent" and reply.error_class == "EffortUnavailable"
    assert rig.client.sessions == []


def test_max_output_tokens_out_of_range_is_not_sent(rig: Rig) -> None:
    big = TurnRequest((SYSTEM, USER), (TOOL,), 10**9, "medium")
    reply = call(rig.make(text_script()), big)
    assert reply.kind == "not_sent" and reply.error_class == "MaxOutputTooLarge"
    assert rig.client.sessions == []


# ---------------------------------------------------------------- the session


def test_first_call_creates_an_empty_mode_session_with_the_tools(rig: Rig) -> None:
    call(rig.make(text_script()), request())
    (options,) = rig.options
    assert options.token == TOKEN and options.runtime == str(rig.runtime)
    home = Path(options.home)
    assert home == rig.home_root / ".copilot-home" / DIGEST and home.is_dir()
    assert rig.client.started == 1
    given = rig.session.options
    assert given["model"] == "gpt-6.1-sol" and given["reasoning_effort"] == "medium"
    assert given["system_message"] == {"mode": "replace", "content": "SYSTEM TEXT"}
    assert given["streaming"] is False and given["session_id"] == DIGEST
    assert list(given["available_tools"]) == ["custom:*"]
    (tool,) = given["tools"]
    assert tool.name == "read_pages" and tool.description == "Read pages."
    assert tool.parameters == dict(TOOL.parameters) and tool.skip_permission is True
    assert rig.session.sent == ["hello"]
    assert callable(given["on_permission_request"])


def test_text_reply_is_ok(rig: Rig) -> None:
    reply = call(rig.make(text_script()), request())
    assert reply.kind == "ok" and reply.http_status == 200 and reply.error_class is None
    assert reply.turn is not None and reply.turn.text == "ANSWER"
    assert reply.billed_usd == Decimal("0.00000123456") == reply.turn.billed_usd
    assert reply.usage == reply.turn.usage and reply.usage is not None
    assert reply.usage.input_tokens == 10 and reply.usage.output_tokens == 5
    assert reply.started_at is not None and reply.finished_at is not None
    assert reply.started_at < reply.finished_at
    events = [
        SessionEvent.from_dict(s.event) if isinstance(s, Emit) else None for s in text_script()
    ]
    records = [event_record(e) for e in events if e is not None]
    records.append({"type": "session.idle", "data": {}})
    assert reply.raw == Redactor.from_environ(rig.environ).bytes_(dump_json(records).encode())
    assert rig.session.disconnected == 1 and rig.client.stopped == 1


def test_tool_calls_block_until_the_next_complete(rig: Rig) -> None:
    adapter = rig.make(tool_script())
    first = call(adapter, request())
    assert first.kind == "ok" and first.turn is not None
    assert first.turn.stop_reason == "tool_use"
    assert first.turn.tool_calls == (ToolCall("c1", "read_pages", {"p": 1}),)
    assert rig.session.disconnected == 0
    assert not rig.session.tasks["c1"].done()  # the handler is still blocked
    second = call(
        adapter,
        request(*tool_turn_history(), Message("tool", "PAGE TEXT", tool_call_id="c1")),
        1,
    )
    assert second.kind == "ok" and second.turn is not None and second.turn.text == "ANSWER"
    assert rig.session.results == {"c1": "PAGE TEXT"}
    assert rig.session.sent == ["hello"]
    assert rig.session.disconnected == 1


def test_user_nudge_after_tool_results_is_sent(rig: Rig) -> None:
    adapter = rig.make(tool_script())
    call(adapter, request())
    nudge = Message("user", "NUDGE")
    reply = call(
        adapter,
        request(*tool_turn_history(), Message("tool", "PAGE TEXT", tool_call_id="c1"), nudge),
        1,
    )
    assert reply.kind == "ok"
    assert rig.session.sent == ["hello", "NUDGE"]


def test_history_mismatch_is_not_sent(rig: Rig) -> None:
    adapter = rig.make(tool_script())
    call(adapter, request())
    altered = (SYSTEM, Message("user", "different"), tool_turn_history()[2])
    reply = call(adapter, request(*altered, Message("tool", "X", tool_call_id="c1")), 1)
    assert reply.kind == "not_sent" and reply.error_class == "HistoryMismatch"
    assert rig.session.results == {}


def test_two_user_messages_in_the_first_request_is_not_sent(rig: Rig) -> None:
    reply = call(rig.make(text_script()), request(SYSTEM, USER, Message("user", "again")))
    assert reply.kind == "not_sent" and reply.error_class == "HistoryMismatch"
    assert rig.client.sessions == []


def test_a_changed_tool_set_is_not_sent(rig: Rig) -> None:
    adapter = rig.make(tool_script())
    call(adapter, request())
    other = ToolSpec("other", "x", {})
    reply = call(
        adapter,
        request(*tool_turn_history(), Message("tool", "X", tool_call_id="c1"), tools=(other,)),
        1,
    )
    assert reply.kind == "not_sent" and reply.error_class == "HistoryMismatch"


def test_call_index_without_session_is_not_sent(rig: Rig) -> None:
    reply = call(rig.make(text_script()), request(), 3)
    assert reply.kind == "not_sent" and reply.error_class == "SessionMissing"
    assert rig.client.sessions == [] and rig.options == []


@pytest.mark.parametrize("answers", [("zzz",), ("c1", "zzz"), ()])
def test_tool_result_mismatch_is_not_sent(rig: Rig, answers: tuple[str, ...]) -> None:
    adapter = rig.make(tool_script())
    call(adapter, request())
    tail = tuple(Message("tool", "X", tool_call_id=i) for i in answers)
    reply = call(adapter, request(*tool_turn_history(), *tail, Message("user", "nudge")), 1)
    assert reply.kind == "not_sent" and reply.error_class == "ToolResultMismatch"
    assert rig.session.results == {} and rig.session.sent == ["hello"]


def test_a_repeated_tool_result_is_not_sent(rig: Rig) -> None:
    adapter = rig.make(tool_script())
    call(adapter, request())
    twice = (Message("tool", "X", tool_call_id="c1"),) * 2
    reply = call(adapter, request(*tool_turn_history(), *twice), 1)
    assert reply.kind == "not_sent" and reply.error_class == "ToolResultMismatch"


# ---------------------------------------------------------------- timeouts


def test_idle_timeout_after_usage_is_sent_usage(rig: Rig) -> None:
    script: list[Step] = [said("part"), usage(copilotUsage={"totalNanoAiu": 100})]
    reply = call(rig.make(script, idle_s=0.2, overall_s=30.0), request())
    assert reply.kind == "sent_usage" and reply.error_class == "IdleTimeout"
    assert reply.usage is not None and reply.usage.input_tokens == 10
    assert reply.billed_usd == Decimal("0.000000001")
    assert reply.raw is not None and b"part" in reply.raw
    assert rig.session.aborted == 1 and rig.session.disconnected == 1


def test_overall_timeout_before_usage_is_sent_unknown(rig: Rig) -> None:
    started = time.monotonic()
    reply = call(rig.make([], idle_s=30.0, overall_s=0.3), request())
    assert reply.kind == "sent_unknown" and reply.error_class == "OverallTimeout"
    assert time.monotonic() - started < 10
    assert rig.session.aborted == 1 and rig.session.disconnected == 1


def test_idle_timeout_before_usage_is_sent_unknown(rig: Rig) -> None:
    reply = call(rig.make([], idle_s=0.2, overall_s=30.0), request())
    assert reply.kind == "sent_unknown" and reply.error_class == "IdleTimeout"


# ---------------------------------------------------------------- outcomes


def test_session_error_is_reported(rig: Rig) -> None:
    script: list[Step] = [Emit(wire("session.error", {"errorType": "boom", "message": "bad"}))]
    reply = call(rig.make(script), request())
    assert reply.kind == "sent_unknown" and reply.error_class == "SessionError"
    assert reply.message is not None and "boom" in reply.message
    assert rig.session.disconnected == 1 and rig.client.stopped == 1


def test_model_mismatch_is_sent_usage(rig: Rig) -> None:
    script: list[Step] = [said("x"), usage(model="other-model"), Idle()]
    reply = call(rig.make(script), request())
    assert reply.kind == "sent_usage" and reply.error_class == "ModelMismatch"
    assert reply.usage is not None and reply.raw is not None
    assert rig.session.disconnected == 1


@pytest.mark.parametrize(
    ("flag", "error_class"), [("isByok", "ByokRouted"), ("isAuto", "AutoRouted")]
)
def test_routed_replies_are_refused(rig: Rig, flag: str, error_class: str) -> None:
    script: list[Step] = [
        said("x"),
        usage(copilotUsage={"totalNanoAiu": 100}, **{flag: True}),
        Idle(),
    ]
    reply = call(rig.make(script), request())
    assert reply.kind == "sent_usage" and reply.error_class == error_class
    assert reply.billed_usd == Decimal("0.000000001") and reply.raw is not None


def test_token_echoed_in_events_is_withheld(rig: Rig) -> None:
    script: list[Step] = [said(f"my token is {TOKEN}"), usage(), Idle()]
    reply = call(rig.make(script), request())
    assert reply.error_class == "KeyReflected"
    assert reply.raw == _REFLECTED_RAW
    assert TOKEN not in repr(reply)
    assert rig.session.disconnected == 1


def test_agent_events_are_ignored(rig: Rig) -> None:
    script: list[Step] = [
        said("SUB-AGENT", agent="agent-1"),
        Emit(wire("assistant.usage", {"model": "x"}, "agent-1")),
        *text_script(),
    ]
    reply = call(rig.make(script), request())
    assert reply.kind == "ok" and reply.turn is not None and reply.turn.text == "ANSWER"
    assert reply.raw is not None and b"SUB-AGENT" not in reply.raw


# ---------------------------------------------------------------- close


def test_close_releases_blocked_handlers(rig: Rig) -> None:
    adapter = rig.make(tool_script())
    first = call(adapter, request())
    assert first.turn is not None and first.turn.stop_reason == "tool_use"
    task = rig.session.tasks["c1"]
    started = time.monotonic()
    adapter.close()
    assert time.monotonic() - started < 2
    assert task.cancelled()
    assert rig.session.disconnected == 1 and rig.client.stopped == 1
    adapter.close()  # idempotent
    assert rig.session.disconnected == 1 and rig.client.stopped == 1


def test_close_before_any_call_is_a_no_op(rig: Rig) -> None:
    adapter = rig.make(text_script())
    adapter.close()
    adapter.close()
    assert rig.options == []


def test_complete_after_close_is_not_sent(rig: Rig) -> None:
    adapter = rig.make(text_script())
    adapter.close()
    reply = call(adapter, request())
    assert reply.kind == "not_sent" and reply.error_class == "AdapterClosed"
