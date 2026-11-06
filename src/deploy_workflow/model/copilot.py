"""GitHub Copilot SDK adapter: the parsing half.

One call's raw body is the JSON array of the session events observed for that call, each
``{"type": <event type>, "data": <event data as camelCase wire keys>}``. ``parse_events`` maps it
to the ``Turn`` the loop prices and records. This half imports nothing from the ``copilot`` SDK
package (the SDK is top-level ``copilot``; this module is ``deploy_workflow.model.copilot``).
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import dataclasses
import os
import re
import threading
import time
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any, Protocol, cast

from deploy_workflow.model.adapter import (
    _REFLECTED_RAW,
    _UNPARSABLE_RAW,
    KEY_VARIABLES,
    AdapterReply,
    GateResult,
    _reply_from_error,
    check_live_gate,
)
from deploy_workflow.model.providers import (
    MAX_OUTPUT_TOKENS,
    REPLY_CUT,
    ErrorKind,
    ProviderConfigError,
    ProviderError,
    _BadReply,
    _count,
    _id,
    _snippet,
    _str_or_none,
    _usage_error,
    effort_for,
    parse,
)
from deploy_workflow.model.redact import Redactor
from deploy_workflow.model.transport import IDLE_S, OVERALL_S
from deploy_workflow.model.turn import (
    Message,
    ModelSpec,
    StopReason,
    ToolCall,
    Turn,
    TurnError,
    TurnRequest,
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
    counts = _usage(usage_data) if usage_data is not None else None
    if usage_data is None or counts is None or counts == Usage():
        return ProviderError(ErrorKind.SENT_CHARGE_UNKNOWN, "SessionError", snippet, status)
    return ProviderError(
        ErrorKind.SENT_CHARGE_USAGE,
        "SessionError",
        snippet,
        status,
        counts,
        _billed_usd(usage_data),
        _str_or_none(usage_data.get("model")),
        _request_id(usage_data),
    )


def parse_events(
    text: str, redactor: Redactor, seen: list[Any], cut_as_turn: bool = False
) -> Turn | ProviderError:
    """The turn one call's session events make. A length-cut reply with no tool call is
    ``ReplyCut`` (CP1H-R16) unless ``cut_as_turn``, which keeps it a max_tokens turn. Raises ``_BadReply`` on a body of the wrong shape."""
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
    calls = tuple(_tool_call(d, seen) for k, d in events if k == TOOL_START)
    if len({c.call_id for c in calls}) != len(calls):
        raise _BadReply("duplicate toolCallId")
    finish = usage_data.get("finishReason")
    stop: StopReason = _FINISH.get(finish, "other") if isinstance(finish, str) else "other"
    expected = _count(usage_data, "numToolCalls")
    if expected is not None and expected != len(calls):
        raise _BadReply(f"tool count {len(calls)} differs from numToolCalls {expected}")
    if stop == "tool_use" and expected is None:
        raise _BadReply("tool count unknown")
    if stop == "tool_use" and not calls:
        raise _BadReply("stop reason tool_use with no tool call")
    if calls and stop not in ("tool_use", "max_tokens"):
        raise _BadReply("tool calls without finishReason tool_calls")
    usage = _usage(usage_data)
    model, rid = _str_or_none(usage_data.get("model")), _request_id(usage_data)
    billed = _billed_usd(usage_data)
    if stop == "max_tokens" and not calls and not cut_as_turn:
        return _usage_error(REPLY_CUT, "finishReason length", 200, usage, model, rid, billed)
    return Turn("".join(contents), calls, usage, stop, model, rid, 200, billed)


# ---------------------------------------------------------------- the adapter
#
# One isolated SDK session per module exchange (invocation digest). The adapter's own thread runs
# an asyncio loop; ``complete`` is synchronous and submits one coroutine per call. The SDK is
# imported only by ``real_client``; everything above it talks to ``ClientLike``/``SessionLike``.

REJECT = "reject"  # the one permission verdict: ``real_client`` maps it to the SDK's reject result
_RUNTIME_VARIABLE = "COPILOT_CLI_PATH"
_TOKEN_VARIABLE = KEY_VARIABLES["copilot"]
_DIGEST = re.compile(r"[A-Za-z0-9_-]{1,128}")
_TOOL_FINISH = ("tool_calls", "tool_use")
_TEARDOWN_S = 5.0  # each disconnect/stop of a dropped session
_OUTER_SLACK_S = 5.0  # the synchronous wait outlasts the coroutine's own overall bound
_INVOKED = object()  # queue marker: a tool handler was called


@dataclass(frozen=True)
class ClientOptions:
    runtime: str
    token: str
    home: str


@dataclass(frozen=True)
class ToolDef:
    """A tool as the adapter hands it over; ``real_client`` builds the SDK ``Tool`` from it."""

    name: str
    description: str
    handler: Callable[[Any], Awaitable[str]]
    parameters: dict[str, Any]
    skip_permission: bool = True


class SessionLike(Protocol):
    def on(self, handler: Callable[[Any], None], /) -> Callable[[], None]: ...
    async def send(self, text: str, /) -> str: ...
    async def abort(self) -> None: ...
    async def disconnect(self) -> None: ...


class ClientLike(Protocol):
    async def start(self) -> None: ...
    async def list_models(self) -> list[dict[str, Any]]: ...
    async def create_session(self, **options: Any) -> SessionLike: ...
    async def stop(self) -> None: ...


ClientFactory = Callable[[ClientOptions], ClientLike]


def reject_permission(request: Any, invocation: Any) -> str:
    """Every permission request is refused: the session has only handler-backed tools, which
    never ask, so a request means the runtime wants something we did not offer."""
    return REJECT


class _SdkClient:
    """The SDK client behind ``ClientLike``: converts the adapter's neutral types to the SDK's."""

    def __init__(self, client: Any, tool: Any, result: Any, reject: Any) -> None:
        self._client, self._tool, self._result, self._reject = client, tool, result, reject

    async def start(self) -> None:
        await self._client.start()

    async def list_models(self) -> list[dict[str, Any]]:
        return [m.to_dict() for m in await self._client.list_models()]

    async def create_session(self, **options: Any) -> SessionLike:
        options["tools"] = [self._sdk_tool(t) for t in options["tools"]]
        decide = options["on_permission_request"]

        async def permission(request: Any, invocation: Any) -> Any:
            if decide(request, invocation) != REJECT:
                raise ValueError("unknown permission verdict")
            # generated/rpc.py: PermissionDecisionReject, wire kind "reject" (line 33263 of the
            # 1.0.28 wheel; PermissionDecisionKind has no "reject" member, the variant class does)
            return self._reject(feedback="this session offers no permission-gated tool")

        options["on_permission_request"] = permission
        session: SessionLike = await self._client.create_session(**options)
        return session

    def _sdk_tool(self, definition: ToolDef) -> Any:
        async def run(invocation: Any) -> Any:
            return self._result(text_result_for_llm=await definition.handler(invocation))

        return self._tool(
            name=definition.name,
            description=definition.description,
            handler=run,
            parameters=definition.parameters,
            skip_permission=definition.skip_permission,
        )

    async def stop(self) -> None:
        await self._client.stop()


def real_client(options: ClientOptions) -> ClientLike:
    """The only place the SDK is imported."""
    from copilot import CopilotClient, RuntimeConnection, Tool, ToolResult
    from copilot.generated.rpc import PermissionDecisionReject

    client = CopilotClient(
        connection=RuntimeConnection.for_stdio(path=options.runtime),
        github_token=options.token,
        use_logged_in_user=False,
        mode="empty",
        base_directory=options.home,
        log_level="none",
    )
    return _SdkClient(client, Tool, ToolResult, PermissionDecisionReject)


class _Refuse(Exception):
    """A refusal before anything was sent: becomes a ``not_sent`` reply."""

    def __init__(self, error_class: str, message: str) -> None:
        super().__init__(message)
        self.error_class, self.message = error_class, message


@dataclass
class _State:
    """One exchange's session, the history the adapter has seen, and the handlers it holds."""

    client: ClientLike
    queue: asyncio.Queue[Any] = field(default_factory=asyncio.Queue)
    session: SessionLike | None = None
    unsubscribe: Callable[[], None] | None = None
    tool_names: frozenset[str] = frozenset()
    history: tuple[Message, ...] = ()
    pending: dict[str, asyncio.Future[str]] = field(default_factory=dict)
    invoked: int = 0


@dataclass(frozen=True)
class _Call:
    request: TurnRequest
    digest: str
    index: int
    effort: str
    started: float
    deadline: float


def _same(a: Message, b: Message) -> bool:
    return (a.role, a.text, a.tool_calls, a.tool_call_id) == (
        b.role,
        b.text,
        b.tool_calls,
        b.tool_call_id,
    )


def _plan_first(request: TurnRequest) -> tuple[str, str]:
    """(system text, user text) of a first request: system messages and exactly one user."""
    rest = [m for m in request.messages if m.role != "system"]
    if len(rest) != 1 or rest[0].role != "user":
        raise _Refuse("HistoryMismatch", "a first request needs exactly one user message")
    system = "\n\n".join(m.text for m in request.messages if m.role == "system")
    return system, rest[0].text


def _plan_next(request: TurnRequest, state: _State) -> tuple[dict[str, str], str | None]:
    """(answers by tool_call_id, user text to send) of a later request; refuses, changing
    nothing, unless the request extends the history by exactly the pending answers."""
    messages, seen = request.messages, state.history
    if len(messages) < len(seen) or not all(_same(a, b) for a, b in zip(seen, messages)):
        raise _Refuse("HistoryMismatch", "the request does not extend the history seen")
    if frozenset(t.name for t in request.tools) != state.tool_names:
        raise _Refuse("HistoryMismatch", "the request's tools differ from the session's")
    answers: dict[str, str] = {}
    user: str | None = None
    for message in messages[len(seen) :]:
        if message.role == "tool" and user is None and message.tool_call_id is not None:
            if message.tool_call_id in answers:
                raise _Refuse("ToolResultMismatch", "a tool call has more than one result")
            answers[message.tool_call_id] = message.text
        elif message.role == "user" and user is None:
            user = message.text
        else:
            raise _Refuse("HistoryMismatch", "the request's tail is not tool results, then a user")
    if answers.keys() != state.pending.keys():
        raise _Refuse("ToolResultMismatch", "tool results do not match the calls issued")
    if not answers and user is None:
        raise _Refuse("HistoryMismatch", "the request adds nothing to send")
    return answers, user


def _check_model(models: list[dict[str, Any]], model: str, effort: str) -> None:
    entry = next((m for m in models if m.get("id") == model), None)
    if entry is None:
        raise _Refuse("ModelUnavailable", f"the runtime does not list {model}")
    efforts = entry.get("supportedReasoningEfforts")
    if isinstance(efforts, list) and effort not in efforts:
        raise _Refuse("EffortUnavailable", f"{model} does not support effort {effort}")


def _usage_data(records: list[dict[str, Any]]) -> dict[str, Any] | None:
    return next((r["data"] for r in records if r["type"] == USAGE), None)


def _routing_error(turn: Turn, records: list[dict[str, Any]], model: str) -> str | None:
    if turn.reported_model != model:
        return "ModelMismatch"
    data = _usage_data(records) or {}
    if data.get("isByok") is True:
        return "ByokRouted"
    return "AutoRouted" if data.get("isAuto") is True else None


class CopilotAdapter:
    """Every construction runs the R2 gate; the environment is read at the first ``complete``."""

    def __init__(
        self,
        model: ModelSpec,
        ruling: Path,
        *,
        environ: Mapping[str, str] | None = None,
        clock: Callable[[], float] = time.time,
        rulings_root: Path | None = None,
        client_factory: ClientFactory = real_client,
        idle_s: float = IDLE_S,
        overall_s: float = OVERALL_S,
    ) -> None:
        self._gate = check_live_gate(model, ruling, rulings_root=rulings_root)  # first
        self.config_id = model.config_id
        self._ruling = Path(ruling)
        self._model = model
        self._environ = environ  # None: os.environ, read only at the first complete
        self._clock = clock
        self._factory = client_factory
        self._idle_s, self._overall_s = idle_s, overall_s
        self._cached: tuple[Redactor, str | None, str | None] | None = None
        self._states: dict[str, _State] = {}
        self._lock = threading.Lock()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._closed = False

    @property
    def ruling(self) -> Path | None:
        return self._ruling

    @property
    def gate(self) -> GateResult:
        return self._gate

    # -------------------------------------------------------- synchronous side

    def _credentials(self) -> tuple[Redactor, str | None, str | None]:
        """Redactor, token and runtime path, read once; None for a missing token, or for a
        runtime variable that is unset or not an existing regular file."""
        if self._cached is None:
            environ = os.environ if self._environ is None else self._environ
            runtime = environ.get(_RUNTIME_VARIABLE) or None
            if runtime is not None and not Path(runtime).is_file():
                runtime = None
            self._cached = (
                Redactor.from_environ(environ),
                environ.get(_TOKEN_VARIABLE) or None,
                runtime,
            )
        return self._cached

    def _not_sent(self, error_class: str, message: str, started: float) -> AdapterReply:
        return AdapterReply(
            "not_sent", None, None, None, error_class, None, started, self._clock(),
            message=message,
        )  # fmt: skip

    def _loop_running(self) -> asyncio.AbstractEventLoop:
        with self._lock:
            if self._loop is None:
                loop = asyncio.new_event_loop()
                self._thread = threading.Thread(
                    target=self._run, args=(loop,), daemon=True, name="copilot-adapter"
                )
                self._loop = loop
                self._thread.start()
            return self._loop

    @staticmethod
    def _run(loop: asyncio.AbstractEventLoop) -> None:
        asyncio.set_event_loop(loop)
        loop.run_forever()

    def complete(
        self,
        request: TurnRequest,
        *,
        invocation_digest: str,
        call_index: int,
        reservation_id: str,
    ) -> AdapterReply:
        """One model call: send what the exchange needs and wait for the call's boundary."""
        started = self._clock()
        redactor, token, runtime = self._credentials()
        if self._closed:
            return self._not_sent("AdapterClosed", "the adapter is closed", started)
        if token is None:
            return self._not_sent("KeyMissing", f"{_TOKEN_VARIABLE} is not set or empty", started)
        if runtime is None:
            return self._not_sent(
                "RuntimeMissing", f"{_RUNTIME_VARIABLE} is not set to an existing file", started
            )
        if not _DIGEST.fullmatch(invocation_digest):
            return self._not_sent("InvalidDigest", "the invocation digest is not a name", started)
        if not 1 <= request.max_output_tokens <= MAX_OUTPUT_TOKENS:
            return self._not_sent(
                "MaxOutputTooLarge",
                f"max_output_tokens {request.max_output_tokens} outside 1..{MAX_OUTPUT_TOKENS}",
                started,
            )
        try:
            effort = effort_for(self._model, request.effort)
        except ProviderConfigError as error:
            return self._not_sent(type(error).__name__, redactor.text(str(error)), started)
        loop = self._loop_running()
        call = _Call(
            request, invocation_digest, call_index, effort, started, loop.time() + self._overall_s
        )
        future = asyncio.run_coroutine_threadsafe(
            self._exchange(call, ClientOptions(runtime, token, ""), redactor), loop
        )
        try:
            return future.result(timeout=self._overall_s + _OUTER_SLACK_S)
        except concurrent.futures.TimeoutError:
            future.cancel()
            error_class, text = "OverallTimeout", "the exchange outlasted its overall bound"
        except concurrent.futures.CancelledError:
            error_class, text = "AdapterClosed", "the adapter was closed during the call"
        return AdapterReply(
            "sent_unknown", None, None, None, error_class, None, started, self._clock(),
            message=text,
        )  # fmt: skip

    def close(self) -> None:
        """Cancel blocked handlers, disconnect sessions, stop clients and the loop; idempotent.
        A failed disconnect or stop is raised, after everything else was released."""
        with self._lock:
            if self._closed:
                return
            self._closed = True
            loop, thread = self._loop, self._thread
        if loop is None or thread is None:
            return
        notes = asyncio.run_coroutine_threadsafe(self._shutdown(), loop).result(
            timeout=_TEARDOWN_S * 4
        )
        loop.call_soon_threadsafe(loop.stop)
        thread.join()
        loop.close()
        if notes:
            raise RuntimeError("; ".join(notes))

    # -------------------------------------------------------- the loop side

    async def _shutdown(self) -> list[str]:
        notes: list[str] = []
        for state in list(self._states.values()):
            for future in state.pending.values():
                future.cancel()
        await asyncio.sleep(0)
        for digest in list(self._states):
            notes += await self._drop(digest)
        others = asyncio.all_tasks() - {asyncio.current_task()}
        for task in others:
            task.cancel()
        await asyncio.gather(*others, return_exceptions=True)
        return notes

    async def _drop(self, digest: str) -> list[str]:
        """Forget an exchange: cancel its handlers, disconnect, stop. Returns the failures of
        the disconnect and stop (the reply is already decided; they ride on it as a note)."""
        state = self._states.pop(digest, None)
        if state is None:
            return []
        if state.unsubscribe is not None:
            state.unsubscribe()
        for future in state.pending.values():
            future.cancel()
        notes = [
            note
            for note in (
                await _attempt("disconnect", state.session.disconnect() if state.session else None),
                await _attempt("stop", state.client.stop()),
            )
            if note
        ]
        return notes

    def _post(self, state: _State, item: Any) -> None:
        try:
            here = asyncio.get_running_loop()
        except RuntimeError:
            here = None
        if here is self._loop:
            state.queue.put_nowait(item)
        elif self._loop is not None:
            self._loop.call_soon_threadsafe(state.queue.put_nowait, item)

    def _tool_def(self, spec: Any, state: _State) -> ToolDef:
        async def handler(invocation: Any) -> str:
            call_id = str(invocation.tool_call_id)
            if call_id in state.pending:
                raise ValueError("a tool call id was issued twice")
            future: asyncio.Future[str] = asyncio.get_running_loop().create_future()
            state.pending[call_id] = future
            state.invoked += 1
            self._post(state, _INVOKED)
            return await future

        return ToolDef(spec.name, spec.description, handler, dict(spec.parameters))

    async def _open(
        self, call: _Call, options: ClientOptions, system: str, deadline: float
    ) -> _State:
        home = Path.cwd() / ".copilot-home" / call.digest
        home.mkdir(parents=True, exist_ok=True)
        client = self._factory(dataclasses.replace(options, home=str(home)))
        state = _State(client)
        self._states[call.digest] = state
        async with asyncio.timeout_at(deadline):
            await client.start()
            _check_model(await client.list_models(), self._model.model, call.effort)
            tools = [self._tool_def(spec, state) for spec in call.request.tools]
            state.tool_names = frozenset(t.name for t in tools)
            state.session = await client.create_session(
                model=self._model.model,
                reasoning_effort=call.effort,
                system_message={"mode": "replace", "content": system},
                tools=tools,
                available_tools=["custom:*"],
                on_permission_request=reject_permission,
                streaming=False,
                session_id=call.digest,
            )
        state.unsubscribe = state.session.on(lambda event: self._on_event(state, event))
        return state

    def _on_event(self, state: _State, event: Any) -> None:
        if not getattr(event, "agent_id", None):  # a sub-agent's events are not this call's
            self._post(state, event)

    async def _exchange(
        self, call: _Call, options: ClientOptions, redactor: Redactor
    ) -> AdapterReply:
        sent = False  # from the first send or tool result on, the runtime may have acted
        try:
            answers: dict[str, str]
            nudge: str | None
            if call.index == 0:
                if call.digest in self._states:
                    raise _Refuse("HistoryMismatch", "this exchange already has a session")
                system, first_user = _plan_first(call.request)
                state = await self._open(call, options, system, call.deadline)
                sent, answers, nudge = True, {}, first_user
                state.invoked = 0
            else:
                found = self._states.get(call.digest)
                if found is None:
                    raise _Refuse("SessionMissing", "no session for this exchange; never resent")
                state = found
                answers, nudge = _plan_next(call.request, state)
                sent, state.invoked = True, 0
            await self._deliver(state, answers, nudge, call.deadline)
            records, timeout = await self._collect(state, call.deadline)
            return await self._settle(call, state, records, timeout, redactor)
        except _Refuse as refusal:
            notes = await self._drop(call.digest) if call.index == 0 else []
            return self._with_notes(
                self._not_sent(refusal.error_class, refusal.message, call.started), notes
            )
        except TimeoutError:
            return await self._failed(call, sent, "OverallTimeout", "the exchange timed out")
        except Exception as error:  # noqa: BLE001 - dropped, and reported as a sent_unknown/not_sent reply
            text = self._scrub(redactor.exception(error), options)
            return await self._failed(call, sent, type(error).__name__, text)

    def _scrub(self, text: str, options: ClientOptions) -> str:
        return text.replace(options.runtime, "<runtime>").replace(str(Path.cwd()), "<cwd>")

    async def _failed(self, call: _Call, sent: bool, error_class: str, text: str) -> AdapterReply:
        notes = await self._drop(call.digest)
        if not sent:
            return self._with_notes(self._not_sent(error_class, text, call.started), notes)
        reply = AdapterReply(
            "sent_unknown", None, None, None, error_class, None, call.started, self._clock(),
            message=text,
        )  # fmt: skip
        return self._with_notes(reply, notes)

    @staticmethod
    def _with_notes(reply: AdapterReply, notes: list[str]) -> AdapterReply:
        if not notes:
            return reply
        joined = "; ".join(([reply.message] if reply.message else []) + notes)
        return dataclasses.replace(reply, message=joined)

    async def _deliver(
        self, state: _State, answers: dict[str, str], nudge: str | None, deadline: float
    ) -> None:
        for call_id, text in answers.items():
            future = state.pending.pop(call_id)
            if not future.done():
                future.set_result(text)
        if nudge is not None:
            assert state.session is not None
            async with asyncio.timeout_at(deadline):
                await state.session.send(nudge)

    async def _collect(
        self, state: _State, deadline: float
    ) -> tuple[list[dict[str, Any]], str | None]:
        """The call's event records up to its boundary, and the timeout class if it timed out."""
        loop = asyncio.get_running_loop()
        records: list[dict[str, Any]] = []
        while not _boundary(records, state.invoked):
            remaining = deadline - loop.time()
            if remaining <= 0:
                return records, "OverallTimeout"
            try:
                item = await asyncio.wait_for(state.queue.get(), min(self._idle_s, remaining))
            except TimeoutError:
                return records, "OverallTimeout" if remaining <= self._idle_s else "IdleTimeout"
            if item is not _INVOKED:
                records.append(event_record(item))
        return records, None

    async def _settle(
        self,
        call: _Call,
        state: _State,
        records: list[dict[str, Any]],
        timeout: str | None,
        redactor: Redactor,
    ) -> AdapterReply:
        body = dump_json(records).encode("utf-8")
        raw = redactor.bytes_(body)
        if timeout is not None:
            assert state.session is not None
            failure = await _attempt("abort", state.session.abort())
            notes = [failure] if failure else []
            reply = self._timeout_reply(call, records, body, raw, timeout)
            return self._with_notes(reply, notes + await self._drop(call.digest))
        outcome = parse("copilot", 200, body, {}, redactor)
        finished = self._clock()
        if isinstance(outcome, ProviderError):
            if outcome.error_class == "KeyReflected":
                raw = _REFLECTED_RAW
            elif outcome.error_class == "UnparsableReply":
                raw = _UNPARSABLE_RAW
            reply = _reply_from_error(outcome, raw, 200, {}, call.started, finished)
            return self._with_notes(reply, await self._drop(call.digest))
        wrong = _routing_error(outcome, records, self._model.model)
        if wrong is None and outcome.stop_reason == "tool_use":
            if state.pending.keys() == {c.call_id for c in outcome.tool_calls}:
                state.history = (
                    *call.request.messages,
                    Message("assistant", outcome.text, outcome.tool_calls),
                )
                return self._ok(call, outcome, raw, finished)
            wrong = "ToolCallMismatch"
        notes = await self._drop(call.digest)
        if wrong is None:
            return self._with_notes(self._ok(call, outcome, raw, finished), notes)
        reply = AdapterReply(
            "sent_usage", None, raw, 200, wrong, None, call.started, finished,
            outcome.usage, outcome.billed_usd,
            message=f"the reply was refused: {wrong}",
        )  # fmt: skip
        return self._with_notes(reply, notes)

    @staticmethod
    def _ok(call: _Call, turn: Turn, raw: bytes, finished: float) -> AdapterReply:
        return AdapterReply(
            "ok", turn, raw, 200, None, None, call.started, finished, turn.usage, turn.billed_usd
        )  # fmt: skip

    def _timeout_reply(
        self, call: _Call, records: list[dict[str, Any]], body: bytes, raw: bytes, timeout: str
    ) -> AdapterReply:
        if raw != body:  # a key is in the events so far: none of them is kept
            raw = _REFLECTED_RAW
        # read back as the parser reads a body: a charge written 100.0 is the integer 100
        data = _usage_data(cast(list[dict[str, Any]], load_json(body.decode("utf-8"))))
        counts: Usage | None = None
        if data is not None:
            try:
                counts = _usage(data)
            except _BadReply:
                counts = None
        finished = self._clock()
        text = f"no further event within the {timeout} bound"
        if data is None or counts is None or counts == Usage():
            return AdapterReply(
                "sent_unknown", None, raw, None, timeout, None, call.started, finished,
                message=text,
            )  # fmt: skip
        return AdapterReply(
            "sent_usage", None, raw, None, timeout, None, call.started, finished,
            counts, _billed_usd(data), message=text,
        )  # fmt: skip


async def _attempt(name: str, step: Awaitable[None] | None) -> str | None:
    """Run one release step (abort, disconnect, stop) within its bound. The reply is already
    decided, so a failure is returned as a note that rides on the reply, never swallowed."""
    if step is None:
        return None
    try:
        await asyncio.wait_for(step, _TEARDOWN_S)
    except Exception as error:  # noqa: BLE001 - returned as the reply's note
        return f"{name} failed: {type(error).__name__}"
    return None


def _boundary(records: list[dict[str, Any]], invoked: int) -> bool:
    """The call is complete: a session error; or usage and every announced handler invoked
    (tool turn) or an idle event (any other turn); or idle with no usage (a malformed call
    that ``parse`` will name)."""
    kinds = {r["type"] for r in records}
    if SESSION_ERROR in kinds:
        return True
    data = _usage_data(records)
    if data is None:
        return "session.idle" in kinds
    announced = data.get("numToolCalls")
    tool_turn = data.get("finishReason") in _TOOL_FINISH
    if isinstance(announced, int) and not isinstance(announced, bool) and announced > 0:
        return invoked >= announced
    if tool_turn:  # tool turn that announces no count: parse names it, nothing else will come
        return True
    return "session.idle" in kinds
