"""CopilotAdapter against a fake client. No runtime, no network, no provider.

The fake imports the SDK only to build real ``SessionEvent`` objects and a real
``ToolInvocation``; the adapter under test imports nothing from the SDK. The fake plays a
script: ``Emit`` delivers an event, ``Invoke`` delivers ``tool.execution_start`` and calls the
registered tool handler in a task, ``Idle`` delivers ``session.idle``, ``Await`` waits for every
started handler to return before the script goes on.
"""

import asyncio
import json
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path, PureWindowsPath
from typing import Any

import pytest
from copilot.generated.session_events import SessionEvent
from copilot.tools import ToolInvocation

from deploy_workflow.model import copilot_adapter
from deploy_workflow.model.adapter import (
    _REFLECTED_RAW,
    AdapterReply,
    LivePauseInForce,
    recorded_adapter,
)
from deploy_workflow.model.copilot import event_record
from deploy_workflow.model.copilot_adapter import ClientOptions, CopilotAdapter, _Call
from deploy_workflow.model.handoff import HandoffExecutor
from deploy_workflow.model.record import CallLog, export_recording
from deploy_workflow.model.redact import Redactor
from deploy_workflow.model.turn import (
    Message,
    ModelSpec,
    ToolCall,
    ToolSpec,
    TurnRequest,
    dump_json,
)
from tests.test_handoff_loop import check, task

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
    handler_arguments: dict[str, Any] | None = None  # the handler is invoked with these instead


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
        self.followups: list[list[Step]] = []  # scripts played by the later sends (nudges)

    def on(self, handler: Callable[[Any], None]) -> Callable[[], None]:
        self.handlers.append(handler)
        return lambda: self.handlers.remove(handler)

    async def send(self, text: str, /) -> str:
        self.sent.append(text)
        if self._played is None:
            self._played = asyncio.ensure_future(self._play())
        elif self.followups:  # a later send is a nudge: the next follow-up script answers it
            self.script = self.followups.pop(0)
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
            ToolInvocation(
                tool_call_id=step.call_id,
                tool_name=step.name,
                arguments=step.arguments
                if step.handler_arguments is None
                else step.handler_arguments,
            )
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
        self.force_stopped = 0
        self.sessions: list[FakeSession] = []
        self.followups: list[list[Step]] = []

    async def start(self) -> None:
        self.started += 1

    async def list_models(self) -> list[dict[str, Any]]:
        return self.models

    async def create_session(self, **options: Any) -> FakeSession:
        session = FakeSession(self.script, options)
        session.followups = self.followups
        self.sessions.append(session)
        return session

    async def stop(self) -> None:
        self.stopped += 1

    async def force_stop(self) -> None:
        self.force_stopped += 1


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
            client_factory=kwargs.pop("client_factory", self.factory),
            **kwargs,
        )
        self.adapters.append(adapter)
        return adapter

    def released(self) -> None:
        """Wait for the background release of every exchange (close() joins it)."""
        for adapter in self.adapters:
            adapter.close()

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


def call(
    adapter: CopilotAdapter, req: TurnRequest, index: int = 0, digest: str = DIGEST
) -> AdapterReply:
    return adapter.complete(req, invocation_digest=digest, call_index=index, reservation_id="r")


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


def test_invalid_reservation_id_is_not_sent(rig: Rig) -> None:
    reply = rig.make(text_script()).complete(
        request(), invocation_digest=DIGEST, call_index=0, reservation_id="../x"
    )
    assert reply.kind == "not_sent" and reply.error_class == "InvalidDigest"
    assert rig.options == [] and not (rig.home_root / ".copilot-home").exists()


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
    assert home == rig.home_root / ".copilot-home" / DIGEST / "r" and home.is_dir()
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
    rig.released()
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
    rig.released()
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
    rig.released()
    assert rig.session.aborted == 1 and rig.session.disconnected == 1


def test_overall_timeout_before_usage_is_sent_unknown(rig: Rig) -> None:
    started = time.monotonic()
    reply = call(rig.make([], idle_s=30.0, overall_s=0.3), request())
    assert reply.kind == "sent_unknown" and reply.error_class == "OverallTimeout"
    assert time.monotonic() - started < 10
    rig.released()
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
    rig.released()
    assert rig.session.disconnected == 1 and rig.client.stopped == 1


def test_session_error_text_and_archived_body_hold_no_home_directory(rig: Rig) -> None:
    # S03-A04/C03: the runtime's own error names local files. Expected by hand: each home
    # directory ("/home/jane.doe", r"C:\Users\Jane Doe") becomes "<home>"; the error type, the
    # rest of the message and the status are kept.
    message = r"ENOENT: open '/home/jane.doe/.copilot/c.json' and C:\Users\Jane Doe\AppData\x.js"
    data = {"errorType": "fs", "message": message, "statusCode": 500}
    reply = call(rig.make([Emit(wire("session.error", data))]), request())
    scrubbed = r"ENOENT: open '<home>/.copilot/c.json' and <home>\AppData\x.js"
    assert (reply.kind, reply.error_class, reply.http_status) == (
        "sent_unknown",
        "SessionError",
        500,
    )
    assert reply.message == f"fs: {scrubbed}"
    assert reply.raw is not None and b"jane.doe" not in reply.raw and b"Jane Doe" not in reply.raw
    (event,) = json.loads(reply.raw)
    assert event["data"]["message"] == scrubbed
    assert event["data"]["statusCode"] == 500
    rig.released()


def test_a_private_path_is_replaced_only_as_whole_segments() -> None:
    # S03-C03: "/home/jan" is not a prefix to cut out of "/home/janet" or "/home/jan.doe"; a
    # path ending in a separator, or followed by a sentence's ".", still is replaced.
    paths = ["/home/jan", "/opt/run/"]
    text = "/home/janet/x /home/jan.doe/y /home/jan/z /home/jan. /opt/run/bin"
    expected = "/home/janet/x /home/jan.doe/y <path>/z <path>. <path>bin"
    assert copilot_adapter._paths_in(text, paths) == expected


def test_model_mismatch_is_sent_usage(rig: Rig) -> None:
    script: list[Step] = [said("x"), usage(model="other-model"), Idle()]
    reply = call(rig.make(script), request())
    assert reply.kind == "sent_usage" and reply.error_class == "ModelMismatch"
    assert reply.usage is not None and reply.raw is not None
    rig.released()
    assert rig.session.disconnected == 1


def test_model_mismatch_without_counts_or_charge_is_sent_unknown(rig: Rig, tmp_path: Path) -> None:
    # The usage event names another model and carries no token field and no copilotUsage: no
    # count and no charge, so the paid amount is unknown (the other Copilot paths say the same).
    # The call record is cost unknown, the export writes sent_unknown, and the replay gives the
    # same kind and class the live reply had.
    script: list[Step] = [
        said("x"),
        Emit(wire("assistant.usage", {"model": "other-model"})),
        Idle(),
    ]
    adapter = rig.make(script, idle_s=2.0)
    run, exported = _run_and_export(rig, tmp_path, adapter)
    (rec,) = CallLog(run, Redactor()).records()
    assert (rec["error_class"], rec["http_status"], rec["cost_status"]) == (
        "ModelMismatch", 200, "unknown",
    )  # fmt: skip
    assert exported["response"]["kind"] == "sent_unknown"
    (out := tmp_path / "rec").mkdir()
    (out / "r.jsonl").write_bytes((tmp_path / "out.jsonl").read_bytes())
    replayed = recorded_adapter(SPEC, out).complete(
        request(),
        invocation_digest=exported["invocation_digest"],
        call_index=exported["call_index"],
        reservation_id="r",
    )
    assert (replayed.kind, replayed.error_class) == ("sent_unknown", "ModelMismatch")


def test_model_mismatch_with_a_zero_charge_stays_sent_usage(rig: Rig) -> None:
    script: list[Step] = [
        said("x"),
        usage(model="other-model", copilotUsage={"totalNanoAiu": 0}),
        Idle(),
    ]
    reply = call(rig.make(script), request())
    assert reply.kind == "sent_usage" and reply.error_class == "ModelMismatch"
    assert reply.billed_usd == Decimal(0)


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
    rig.released()
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
    awaited = adapter._states[DIGEST].pending["c1"]  # the future the handler is blocked on
    started = time.monotonic()
    adapter.close()
    assert time.monotonic() - started < 2
    assert awaited.cancelled()
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
    assert reply.kind == "not_sent" and reply.error_class == copilot_adapter.PRE_SEND_FAILURE
    assert reply.message is not None and reply.message.startswith("AdapterClosed")


def _run_and_export(
    rig: Rig, tmp_path: Path, adapter: CopilotAdapter
) -> tuple[Path, dict[str, Any]]:
    run = tmp_path / "run"
    run.mkdir()
    executor = HandoffExecutor(run, adapter=adapter, cap_usd=Decimal(10), check=check)
    try:
        executor(task())
    except RuntimeError:
        pass  # the loop stops on the failed call; the record is what is checked
    out = tmp_path / "out.jsonl"
    assert export_recording(run, out, Redactor()) == 1
    return run, json.loads(out.read_text(encoding="utf-8").splitlines()[0])


def test_closed_adapter_through_the_executor_exports_not_sent(rig: Rig, tmp_path: Path) -> None:
    adapter = rig.make(text_script())
    adapter.close()
    run, exported = _run_and_export(rig, tmp_path, adapter)
    (rec,) = CallLog(run, Redactor()).records()
    assert rec["error_class"] == copilot_adapter.PRE_SEND_FAILURE
    assert exported["response"]["kind"] == "not_sent"


def test_zero_cost_usage_timeout_keeps_a_billed_zero(rig: Rig, tmp_path: Path) -> None:
    adapter = rig.make(
        [said("part"), usage(copilotUsage={"totalNanoAiu": 0})], idle_s=0.2, overall_s=30.0
    )
    run, exported = _run_and_export(rig, tmp_path, adapter)
    (rec,) = CallLog(run, Redactor()).records()
    assert rec["http_status"] is None and rec["error_class"] == "IdleTimeout"
    assert rec["cost_status"] == "billed" and rec["settled_usd"] == "0"
    assert exported["response"]["kind"] == "sent_usage"
    assert exported["response"]["billed_usd"] == "0"
    (out := tmp_path / "rec").mkdir()
    (out / "r.jsonl").write_bytes((tmp_path / "out.jsonl").read_bytes())
    replayed = recorded_adapter(SPEC, out).complete(
        request(),
        invocation_digest=exported["invocation_digest"],
        call_index=exported["call_index"],
        reservation_id="r",
    )
    assert replayed.kind == "sent_usage" and replayed.billed_usd == Decimal(0)


def test_pre_send_failure_text_is_bounded_and_holds_no_absolute_path(
    rig: Rig, tmp_path: Path
) -> None:
    install = tmp_path / "install"
    frame = f"    at start ({install}/lib/index.js:10:5)\n    at main (/Users/x/AppData/Local/n.js:1:1)\n"
    rig.client = OpenFails(RuntimeError("boom\n" + frame * 2000))
    adapter = rig.make([])
    run, _ = _run_and_export(rig, tmp_path, adapter)
    (rec,) = CallLog(run, Redactor()).records()
    text = str(rec["error"])
    assert text.startswith("PreSendFailure: RuntimeError")
    assert len(text) <= 500
    assert str(install) not in text and "/Users/x/AppData" not in text
    assert "<path>" in text


def test_windows_paths_with_spaces_are_scrubbed_from_error_text(rig: Rig, tmp_path: Path) -> None:
    install = tmp_path / "Copilot Install Dir"
    install.mkdir()
    runtime = install / "copilot-runtime"
    runtime.write_text("#!/bin/sh\n")
    profile, local = r"C:\Users\Jane Doe", r"C:\Users\Jane Doe\AppData\Local"
    files = r"C:\Program Files"
    environ = {
        **rig.environ,
        "COPILOT_CLI_PATH": str(runtime),
        "USERPROFILE": profile,
        "LOCALAPPDATA": local,
        "ProgramFiles": files,
    }
    frames = (
        f"at a ({local}\\x\\y.js:1:1)\nat b ({files}\\GitHub Copilot\\bin\\copilot.exe:2:2)\n"
        f"at c ({install}/lib.js:3:3)\n"
    )
    rig.client = OpenFails(RuntimeError("boom\n" + frames * 50))
    adapter = rig.make([], environ=environ)
    run, _ = _run_and_export(rig, tmp_path, adapter)
    (rec,) = CallLog(run, Redactor()).records()
    text = str(rec["error"])
    assert len(text) <= 500
    for secret in ("Jane Doe", "Program Files", "GitHub Copilot", "Copilot Install Dir"):
        assert secret not in text


# ---------------------------------------------------------------- fix round 1


class HangingSession(FakeSession):
    """A wedged runtime: abort is slow, disconnect never returns."""

    async def abort(self) -> None:
        self.aborted += 1
        await asyncio.sleep(0.5)

    async def disconnect(self) -> None:
        self.disconnected += 1
        await asyncio.Event().wait()


class HangingClient(FakeClient):
    async def create_session(self, **options: Any) -> FakeSession:
        session = HangingSession(self.script, options)
        self.sessions.append(session)
        return session

    async def stop(self) -> None:
        self.stopped += 1
        await asyncio.Event().wait()


@pytest.fixture
def small_bounds(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("_DISCONNECT_S", "_STOP_S", "_FORCE_S"):
        monkeypatch.setattr(copilot_adapter, name, 0.3)


def test_second_model_call_is_not_billed_as_the_first(rig: Rig) -> None:
    script: list[Step] = [
        said(""),
        usage(finishReason="tool_calls", numToolCalls=1, copilotUsage={"totalNanoAiu": 1000}),
        said("I could not find that tool."),  # the announced call never reaches a handler
        usage(copilotUsage={"totalNanoAiu": 2000}),
        Idle(),
    ]
    started = time.monotonic()
    reply = call(rig.make(script, idle_s=5.0, overall_s=30.0), request())
    assert time.monotonic() - started < 3  # the second usage ended the call, no idle wait
    assert reply.kind == "sent_unknown" and reply.usage is None and reply.billed_usd is None
    assert reply.raw is not None


def test_two_usage_events_in_a_timeout_body_are_sent_unknown(rig: Rig) -> None:
    adapter = rig.make(text_script())
    records = [
        event_record(SessionEvent.from_dict(usage(copilotUsage={"totalNanoAiu": n}).event))
        for n in (1000, 2000)
    ]
    body = dump_json(records).encode()
    call_ = _Call(request(), DIGEST, 0, "medium", 0.0, 0.0, "r")
    reply = adapter._timeout_reply(call_, body, body, "IdleTimeout")
    assert reply.kind == "sent_unknown" and reply.usage is None and reply.billed_usd is None


def test_slow_teardown_does_not_lose_the_reply(rig: Rig, monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("_DISCONNECT_S", "_STOP_S"):
        monkeypatch.setattr(copilot_adapter, name, 1.0)
    rig.client = HangingClient([])
    adapter = rig.make(text_script(), overall_s=1.0)
    started = time.monotonic()
    reply = call(adapter, request())
    assert time.monotonic() - started < 0.8  # the 2 s release is not on the reply's path
    assert reply.kind == "ok" and reply.billed_usd == Decimal("0.00000123456")
    with pytest.raises(RuntimeError, match="stop failed"):
        adapter.close()
    assert rig.client.force_stopped == 1


def test_outer_timeout_keeps_usage(rig: Rig, small_bounds: None) -> None:
    rig.client = HangingClient([])
    script: list[Step] = [said("part"), usage(copilotUsage={"totalNanoAiu": 5000})]
    adapter = rig.make(script, idle_s=30.0, overall_s=0.3)
    reply = call(adapter, request())
    assert reply.kind == "sent_usage" and reply.usage is not None
    assert reply.error_class == "OverallTimeout" and rig.session.aborted == 1
    with pytest.raises(RuntimeError):
        adapter.close()
    assert rig.client.stopped == 1 and rig.client.force_stopped == 1


def test_stop_has_the_sdk_shutdown_budget_and_a_failed_stop_is_forced(
    rig: Rig, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert copilot_adapter._STOP_S >= 30  # shutdown RPC 10 + graceful 10 + terminate 5 + kill 5
    monkeypatch.setattr(copilot_adapter, "_STOP_S", 0.3)
    monkeypatch.setattr(copilot_adapter, "_DISCONNECT_S", 0.3)
    rig.client = HangingClient([])
    adapter = rig.make(text_script())
    assert call(adapter, request()).kind == "ok"
    with pytest.raises(RuntimeError, match="stop failed"):
        adapter.close()
    assert rig.client.force_stopped == 1


def test_close_releases_many_kept_exchanges(rig: Rig, small_bounds: None) -> None:
    clients: list[HangingClient] = []

    def factory(options: ClientOptions) -> HangingClient:
        clients.append(HangingClient(tool_script()))
        return clients[-1]

    adapter = rig.make(tool_script(), client_factory=factory)
    for n in "123":
        reply = call(adapter, request(), digest=n * 64)
        assert reply.kind == "ok" and reply.turn is not None
        assert reply.turn.stop_reason == "tool_use"
    started = time.monotonic()
    with pytest.raises(RuntimeError):
        adapter.close()
    assert time.monotonic() - started < 3  # one exchange's budget, not three
    assert len(clients) == 3 and all(c.stopped + c.force_stopped >= 1 for c in clients)
    assert adapter._thread is not None and not adapter._thread.is_alive()
    adapter.close()  # released: a no-op


def test_cancelled_handler_is_tool_call_lost(rig: Rig) -> None:
    adapter = rig.make(tool_script())
    assert call(adapter, request()).kind == "ok"
    task = rig.session.tasks["c1"]

    async def cancel() -> None:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)

    assert adapter._loop is not None
    asyncio.run_coroutine_threadsafe(cancel(), adapter._loop).result(5)
    answer = Message("tool", "PAGE TEXT", tool_call_id="c1")
    second = call(adapter, request(*tool_turn_history(), answer), 1)
    assert second.kind == "sent_unknown" and second.error_class == "ToolCallLost"
    assert "c1" not in rig.session.results


def test_nudge_after_text_turn_uses_the_same_session(rig: Rig) -> None:
    adapter = rig.make(text_script("FIRST"))
    rig.client.followups = [text_script("SECOND")]
    first = call(adapter, request())
    assert first.turn is not None and first.turn.stop_reason == "end"
    history = (SYSTEM, USER, Message("assistant", "FIRST"))
    second = call(adapter, request(*history, Message("user", "NUDGE")), 1)
    assert second.kind == "ok" and second.turn is not None and second.turn.text == "SECOND"
    assert len(rig.client.sessions) == 1 and rig.session.sent == ["hello", "NUDGE"]
    assert rig.session.disconnected == 0


def test_refused_replay_keeps_the_live_exchange(rig: Rig) -> None:
    adapter = rig.make(tool_script())
    assert call(adapter, request()).kind == "ok"
    replay = call(adapter, request(), 0)
    assert replay.kind == "not_sent" and replay.error_class == "ExchangeExists"
    assert DIGEST in adapter._states and rig.session.disconnected == 0
    assert len(rig.client.sessions) == 1
    answer = Message("tool", "PAGE TEXT", tool_call_id="c1")
    assert call(adapter, request(*tool_turn_history(), answer), 1).kind == "ok"


def test_max_tokens_turn_with_calls_keeps_its_handlers(rig: Rig) -> None:
    script: list[Step] = [
        said(""),
        usage(finishReason="length", numToolCalls=1),
        Invoke("c1", "read_pages", {"p": 1}),
        Await(),
        *text_script(),
    ]
    adapter = rig.make(script)
    first = call(adapter, request())
    assert first.turn is not None and first.turn.stop_reason == "max_tokens"
    assert first.turn.tool_calls and not rig.session.tasks["c1"].done()
    answer = Message("tool", "PAGE TEXT", tool_call_id="c1")
    assert call(adapter, request(*tool_turn_history(), answer), 1).kind == "ok"
    assert rig.session.results == {"c1": "PAGE TEXT"}


def test_invocation_differing_from_start_event_is_mismatch(rig: Rig) -> None:
    script: list[Step] = [
        said(""),
        usage(finishReason="tool_calls", numToolCalls=1, copilotUsage={"totalNanoAiu": 100}),
        Invoke("c1", "read_pages", {"p": 1}, handler_arguments={"p": 2}),
        Await(),
    ]
    reply = call(rig.make(script), request())
    assert reply.kind == "sent_usage" and reply.error_class == "ToolCallMismatch"
    assert reply.usage is not None and reply.billed_usd == Decimal("0.000000001")


def test_tool_turn_waits_for_every_start_event(rig: Rig) -> None:
    script: list[Step] = [
        said(""),
        usage(finishReason="tool_calls", numToolCalls=1),
        Invoke("c1", "read_pages", {"p": 1}),
        Await(),
    ]
    reply = call(rig.make(script), request())
    assert reply.turn is not None and [c.call_id for c in reply.turn.tool_calls] == ["c1"]


def test_runtime_environment_is_allowlisted(rig: Rig) -> None:
    secret = "ghp_" + "G" * 36
    env = {
        **rig.environ,
        "PATH": "/usr/bin",
        "LC_ALL": "C",
        "https_proxy": "http://proxy",
        "OPENAI_API_KEY": "sk-secret-value",
        "ANTHROPIC_API_KEY": "plainvalue-anthropic",
        "GH_TOKEN": secret,
        "GITHUB_TOKEN": secret,
        "PATHEXT": ".EXE",
        "WINDIR": "C:/W",
        "USERNAME": "u",
    }
    call(rig.make(text_script(), environ=env), request())
    (options,) = rig.options
    assert dict(options.env) == {
        "PATH": "/usr/bin",
        "LC_ALL": "C",
        "https_proxy": "http://proxy",
        "PATHEXT": ".EXE",
        "WINDIR": "C:/W",
        "USERNAME": "u",
    }
    assert TOKEN not in repr(dict(options.env)) and options.token == TOKEN


def test_options_repr_hides_the_token() -> None:
    options = ClientOptions("/opt/copilot", TOKEN, "/tmp/home", {"PATH": "/bin"})
    assert TOKEN not in repr(options) and TOKEN not in str(options)
    assert "PATH" not in repr(options)


def test_windows_paths_are_scrubbed(rig: Rig) -> None:
    home = str(PureWindowsPath(r"C:\Users\eric\Documents\final-workflow") / ".copilot-home" / "d")
    runtime = str(PureWindowsPath(r"C:\Users\eric\AppData\Local\copilot\copilot.exe"))
    options = ClientOptions(runtime, "t", home)
    adapter = rig.make(text_script())
    for error in (
        FileNotFoundError(3, "The system cannot find the path specified", home),
        PermissionError(13, "Access is denied", runtime),
    ):
        for text in (str(error), repr(error), str(error).upper(), str(error).replace("\\", "/")):
            assert "eric" not in adapter._scrub(text, options).lower(), text


def test_existing_home_is_refused(rig: Rig) -> None:
    (rig.home_root / ".copilot-home" / DIGEST / "r").mkdir(parents=True)
    reply = call(rig.make(text_script()), request())
    assert reply.kind == "not_sent" and reply.error_class == "HomeExists"
    assert reply.message == "HomeExists" and rig.options == []
    ignore = Path(__file__).resolve().parents[2] / ".gitignore"
    assert ".copilot-home/" in ignore.read_text(encoding="utf-8").splitlines()


class SendFails(FakeSession):
    async def send(self, text: str, /) -> str:
        await asyncio.sleep(0)
        raise RuntimeError("runtime went away")


class SendFailsClient(FakeClient):
    async def create_session(self, **options: Any) -> FakeSession:
        session = SendFails(self.script, options)
        self.sessions.append(session)
        return session


def test_sdk_exception_is_an_adapter_error_that_exports(rig: Rig, tmp_path: Path) -> None:
    rig.client = SendFailsClient([])
    adapter = rig.make([])
    run = tmp_path / "run"
    run.mkdir()
    executor = HandoffExecutor(run, adapter=adapter, cap_usd=Decimal(10), check=check)
    with pytest.raises(RuntimeError, match="cpos_live_stopped: sent_unknown"):
        executor(task())
    (rec,) = CallLog(run, Redactor()).records()
    assert rec["error_class"] == "AdapterError"
    assert str(rec["error"]).startswith("AdapterError: RuntimeError")
    assert export_recording(run, tmp_path / "out.jsonl", Redactor()) == 1


class OpenFails(FakeClient):
    def __init__(self, error: BaseException) -> None:
        super().__init__([])
        self.error = error

    async def create_session(self, **options: Any) -> FakeSession:
        raise self.error


@pytest.mark.parametrize(
    "error, message",
    [
        (RuntimeError("session refused"), "RuntimeError"),
        (TimeoutError(), "OverallTimeout"),
    ],
)
def test_pre_send_failure_is_not_sent_that_exports_and_replays(
    rig: Rig, tmp_path: Path, error: BaseException, message: str
) -> None:
    rig.client = OpenFails(error)
    adapter = rig.make([])
    run = tmp_path / "run"
    run.mkdir()
    executor = HandoffExecutor(run, adapter=adapter, cap_usd=Decimal(10), check=check)
    with pytest.raises(RuntimeError):
        executor(task())
    (rec,) = CallLog(run, Redactor()).records()
    assert rec["error_class"] == copilot_adapter.PRE_SEND_FAILURE
    assert message in str(rec["error"])
    if message == "RuntimeError":
        assert str(rec["error"]).startswith("PreSendFailure: RuntimeError")
    assert export_recording(run, tmp_path / "out.jsonl", Redactor()) == 1
    exported = json.loads((tmp_path / "out.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert exported["response"]["kind"] == "not_sent"
    assert exported["response"]["error_class"] == copilot_adapter.PRE_SEND_FAILURE
    (out := tmp_path / "rec").mkdir()
    (out / "r.jsonl").write_bytes((tmp_path / "out.jsonl").read_bytes())
    replayed = recorded_adapter(SPEC, out).complete(
        request(),
        invocation_digest=exported["invocation_digest"],
        call_index=exported["call_index"],
        reservation_id="r",
    )
    assert replayed.kind == "not_sent" and replayed.error_class == copilot_adapter.PRE_SEND_FAILURE


def test_profile_path_ending_at_a_space_leaves_no_surname(rig: Rig, tmp_path: Path) -> None:
    environ = {**rig.environ, "USERPROFILE": r"C:\Users\Jane Doe"}
    rig.client = OpenFails(RuntimeError(r"mkdir 'C:\Users\Jane Doe' failed"))
    adapter = rig.make([], environ=environ)
    run, _ = _run_and_export(rig, tmp_path, adapter)
    (rec,) = CallLog(run, Redactor()).records()
    assert "Doe" not in str(rec["error"]) and "Jane" not in str(rec["error"])


def test_relative_or_root_values_do_not_erase_ordinary_text(rig: Rig, tmp_path: Path) -> None:
    environ = {**rig.environ, "COPILOT_CLI_PATH": "copilot-runtime", "HOME": "/"}
    rig.client = OpenFails(RuntimeError("failed after 3/4 retries at step 1.2"))
    (tmp_path / "copilot-runtime").write_text("#!/bin/sh\n")
    adapter = rig.make([], environ=environ)
    run, _ = _run_and_export(rig, tmp_path, adapter)
    (rec,) = CallLog(run, Redactor()).records()
    assert "after 3/4 retries at step 1.2" in str(rec["error"])
