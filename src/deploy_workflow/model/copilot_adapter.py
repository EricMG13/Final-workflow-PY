"""GitHub Copilot SDK adapter: one isolated SDK session per module exchange.

The parsing half is ``deploy_workflow.model.copilot``. Only ``real_client`` imports the SDK.
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
from pathlib import Path
from typing import Any, Protocol, cast

from deploy_workflow.model.adapter import (
    _REFLECTED_RAW,
    _UNPARSABLE_RAW,
    COPILOT_RUNTIME_VARIABLE,
    KEY_VARIABLES,
    AdapterReply,
    GateResult,
    _reply_from_error,
    check_live_gate,
)
from deploy_workflow.model.copilot import (
    SESSION_ERROR,
    TOOL_START,
    USAGE,
    _billed_usd,
    _usage,
    event_record,
)
from deploy_workflow.model.providers import (
    MAX_OUTPUT_TOKENS,
    ProviderConfigError,
    ProviderError,
    _BadReply,
    _snippet,
    effort_for,
    parse,
)
from deploy_workflow.model.redact import Redactor, home_paths
from deploy_workflow.model.reply_classes import (
    ADAPTER_CLOSED,
    ADAPTER_ERROR,
    AUTO_ROUTED,
    BYOK_ROUTED,
    IDLE_TIMEOUT,
    MODEL_MISMATCH,
    OVERALL_TIMEOUT,
    PRE_SEND_FAILURE,
    TOOL_CALL_LOST,
    TOOL_CALL_MISMATCH,
)
from deploy_workflow.model.transport import IDLE_S, OVERALL_S
from deploy_workflow.model.turn import (
    Message,
    ModelSpec,
    Turn,
    TurnError,
    TurnRequest,
    Usage,
    dump_json,
    load_json,
)

# ---------------------------------------------------------------- the adapter
#
# One isolated SDK session per module exchange (invocation digest). The adapter's own thread runs
# an asyncio loop; ``complete`` is synchronous and submits one coroutine per call. The SDK is
# imported only by ``real_client``; everything above it talks to ``ClientLike``/``SessionLike``.

REJECT = "reject"  # the one permission verdict: ``real_client`` maps it to the SDK's reject result
_ABSOLUTE_PATH = re.compile(r"(?:[A-Za-z]:)?[\\/](?:[^\s\\/:()'\"<>]+[\\/])+[^\s\\/:()'\"<>]*")
_SEGMENT = r"[^\s\\/:()'\"<>.,;]"  # a path-name character that cannot end a sentence
_PROFILE_VARIABLES = (
    "USERPROFILE", "HOME", "APPDATA", "LOCALAPPDATA", "ProgramFiles", "ProgramFiles(x86)",
)  # fmt: skip
# Windows drive paths whose folders may hold spaces ("C:\\Users\\Jane Doe\\...\\x.js"): the file
# name ends at a space, a folder name does not.
_ROOT = r"(?:[A-Za-z]:|<path>)"
_WINDOWS_PATH = re.compile(
    rf"{_ROOT}\\(?:[^\\/:*?\"<>|\r\n()]+\\)*[^\s\\/:*?\"<>|()']*"  # backslashes: folders may hold spaces
    rf"|{_ROOT}/(?:[^\s\\/:*?\"<>|()']+/)*[^\s\\/:*?\"<>|()']*"
)
_TOKEN_VARIABLE = KEY_VARIABLES["copilot"]
_DIGEST = re.compile(r"[A-Za-z0-9_-]{1,128}")
_TOOL_FINISH = ("tool_calls", "tool_use")
# Bounds of the release of one exchange. STOP_S covers the SDK's own stop: shutdown RPC 10 s,
# graceful exit 10 s, terminate 5 s, kill 5 s (client.py, 1.0.28); force_stop follows a failure.
_ABORT_S = 5.0  # on the reply's path (timeouts only)
_DISCONNECT_S = 5.0
_STOP_S = 30.0
_FORCE_S = 5.0
_JOIN_S = 5.0
_OUTER_SLACK_S = 5.0  # the synchronous wait outlasts the coroutine's own overall bound
_CLOSE_SLACK_S = 2.0
_ENV_ALLOWED = frozenset(
    {
        "PATH",
        "HOME",
        "USERPROFILE",
        "TMPDIR",
        "TEMP",
        "TMP",
        "SYSTEMROOT",
        "WINDIR",
        "PATHEXT",
        "USERNAME",
        "SYSTEMDRIVE",
        "COMSPEC",
        "APPDATA",
        "LOCALAPPDATA",
        "PROGRAMDATA",
        "LANG",
        "SSL_CERT_FILE",
        "SSL_CERT_DIR",
        "REQUESTS_CA_BUNDLE",
        "NODE_EXTRA_CA_CERTS",
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "NO_PROXY",
    }
)
_INVOKED = object()  # queue marker: a tool handler was called


def _teardown_budget() -> float:
    """One exchange's whole release: disconnect, stop, then force_stop."""
    return _DISCONNECT_S + _STOP_S + _FORCE_S


def runtime_environment(environ: Mapping[str, str]) -> dict[str, str]:
    """The allowlisted part of ``environ`` the runtime process may see (never a provider key,
    never GH_TOKEN/GITHUB_TOKEN: the token travels only through ``github_token``)."""
    return {
        k: v for k, v in environ.items() if k.upper() in _ENV_ALLOWED or k.upper().startswith("LC_")
    }


@dataclass(frozen=True)
class ClientOptions:
    runtime: str
    token: str = field(repr=False)
    home: str
    env: Mapping[str, str] = field(default_factory=dict, repr=False)
    private_paths: tuple[str, ...] = field(default=(), repr=False)  # also scrubbed from errors


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
    async def force_stop(self) -> None: ...


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

    async def force_stop(self) -> None:
        await self._client.force_stop()


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
        env=dict(options.env),
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
    # (tool_call_id -> (tool_name, arguments)) of the handler invocations of the current call
    calls: dict[str, tuple[str, Any]] = field(default_factory=dict)
    releasing: asyncio.Task[None] | None = None


class _ToolCallLost(Exception):
    """A pending handler was already finished (cancelled by the SDK): its result has no taker."""


@dataclass(frozen=True)
class _Creds:
    redactor: Redactor
    token: str | None = field(repr=False)
    runtime: str | None
    env: Mapping[str, str] = field(repr=False)


@dataclass(frozen=True)
class _Call:
    request: TurnRequest
    digest: str
    index: int
    effort: str
    started: float
    deadline: float
    reservation: str


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
        return MODEL_MISMATCH
    data = _usage_data(records) or {}
    if data.get("isByok") is True:
        return BYOK_ROUTED
    return AUTO_ROUTED if data.get("isAuto") is True else None


def _normal(arguments: Any) -> Any:
    """Arguments as the parser reads them (floats as Decimal, an absent value as {})."""
    return load_json(dump_json({} if arguments is None else arguments))


def _calls_match(turn: Turn, calls: Mapping[str, tuple[str, Any]]) -> bool:
    """Every parsed tool call was invoked, with the same name and arguments, and nothing else."""
    if calls.keys() != {c.call_id for c in turn.tool_calls}:
        return False
    try:
        for call in turn.tool_calls:
            name, arguments = calls[call.call_id]
            if call.bad_arguments is not None:
                same = dump_json(arguments) == call.bad_arguments
            else:
                same = _normal(arguments) == call.arguments
            if name != call.name or not same:
                return False
    except TurnError:
        return False
    return True


def _is_scrubbable(value: str) -> bool:
    """An absolute path of more than three characters; anything shorter or relative would erase
    ordinary text ("." or "/")."""
    return len(value) > 3 and (
        value.startswith(("/", "\\")) or value[1:3] == ":\\" or value[1:3] == ":/"
    )


def _paths_in(text: str, paths: list[str]) -> str:
    """``text`` without any of ``paths``, raw, repr-escaped, slash-flipped, in any case."""
    forms: set[str] = set()
    for path in paths:
        if path:
            escaped = repr(path)[1:-1]
            forms |= {path, escaped, path.replace("\\", "/"), path.replace("/", "\\")}
            forms |= {escaped.replace("\\", "/")}
    if not forms:
        return text
    pattern = "|".join(re.escape(f) for f in sorted(forms, key=len, reverse=True))
    # whole segments only: "/home/jan" is not replaced inside "/home/janet" or "/home/jan.doe";
    # a sentence's closing "." or "," after the path does not count as part of it
    whole = f"(?:{pattern})(?:(?<=[\\\\/])|(?!\\.?{_SEGMENT}))"
    return re.sub(whole, "<path>", text, flags=re.IGNORECASE)


def _home_free(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The records with the text of each ``session.error`` free of home directories: the runtime's
    error names local files (``redact.home_paths``). Every other event is kept as observed."""
    return [
        {**r, "data": {k: home_paths(v) if isinstance(v, str) else v for k, v in r["data"].items()}}
        if r["type"] == SESSION_ERROR
        else r
        for r in records
    ]


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
        self._cached: _Creds | None = None
        self._states: dict[str, _State] = {}
        self._teardowns: set[asyncio.Task[None]] = set()
        self._notes: list[str] = []  # release failures; close() raises them
        self._lock = threading.Lock()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._closed = False
        self._released = False

    @property
    def ruling(self) -> Path | None:
        return self._ruling

    @property
    def gate(self) -> GateResult:
        return self._gate

    # -------------------------------------------------------- synchronous side

    def _credentials(self) -> _Creds:
        """Redactor, token, runtime path and runtime environment, read once; None for a missing
        token, or for a runtime variable that is unset or not an existing regular file."""
        if self._cached is None:
            environ = os.environ if self._environ is None else self._environ
            runtime = environ.get(COPILOT_RUNTIME_VARIABLE) or None
            if runtime is not None and not Path(runtime).is_file():
                runtime = None
            self._cached = _Creds(
                Redactor.from_environ(environ),
                environ.get(_TOKEN_VARIABLE) or None,
                runtime,
                runtime_environment(environ),
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
        creds = self._credentials()
        redactor, token, runtime = creds.redactor, creds.token, creds.runtime
        if self._closed:
            return self._not_sent(PRE_SEND_FAILURE, "AdapterClosed: the adapter is closed", started)
        if token is None:
            return self._not_sent("KeyMissing", f"{_TOKEN_VARIABLE} is not set or empty", started)
        if runtime is None:
            return self._not_sent(
                "RuntimeMissing",
                f"{COPILOT_RUNTIME_VARIABLE} is not set to an existing file",
                started,
            )
        if not _DIGEST.fullmatch(invocation_digest) or not _DIGEST.fullmatch(reservation_id):
            return self._not_sent(
                "InvalidDigest", "the invocation digest or reservation id is not a name", started
            )
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
            request,
            invocation_digest,
            call_index,
            effort,
            started,
            loop.time() + self._overall_s,
            reservation_id,
        )
        environ = os.environ if self._environ is None else self._environ
        private = (str(Path(runtime).parent), *(environ.get(n, "") for n in _PROFILE_VARIABLES))
        options = ClientOptions(runtime, token, "", creds.env, private)
        future = asyncio.run_coroutine_threadsafe(self._exchange(call, options, redactor), loop)
        # the only teardown step on the reply's path is abort() after a timeout
        try:
            return future.result(timeout=self._overall_s + _ABORT_S + _OUTER_SLACK_S)
        except concurrent.futures.TimeoutError:
            future.cancel()
            loop.call_soon_threadsafe(self._release, invocation_digest)
            error_class, text = OVERALL_TIMEOUT, "the exchange outlasted its overall bound"
        except concurrent.futures.CancelledError:
            error_class, text = ADAPTER_CLOSED, "the adapter was closed during the call"
        return AdapterReply(
            "sent_unknown", None, None, None, error_class, None, started, self._clock(),
            message=text,
        )  # fmt: skip

    def close(self) -> None:
        """Release every exchange (concurrently, within one exchange's teardown budget), force-stop
        what is left, stop the loop and join its thread. Idempotent once released; a call after
        a failed release retries it. Release failures are raised, after everything else was
        released."""
        with self._lock:
            self._closed = True
            if self._released:
                return
            loop, thread = self._loop, self._thread
            if loop is None or thread is None:
                self._released = True
                return
        notes: list[str] = []
        shutdown = asyncio.run_coroutine_threadsafe(self._shutdown(), loop)
        try:
            notes += shutdown.result(timeout=_teardown_budget() + _CLOSE_SLACK_S)
        except concurrent.futures.TimeoutError:
            shutdown.cancel()
            notes.append("release exceeded its budget; clients force-stopped")
            force = asyncio.run_coroutine_threadsafe(self._force_all(), loop)
            try:
                notes += force.result(timeout=_FORCE_S + _CLOSE_SLACK_S)
            except concurrent.futures.TimeoutError:
                notes.append("force_stop did not finish")
        loop.call_soon_threadsafe(loop.stop)
        thread.join(timeout=_JOIN_S)
        if thread.is_alive():
            raise RuntimeError("; ".join([*notes, "the loop thread did not stop"]))
        loop.close()
        self._released = True
        if notes:
            raise RuntimeError("; ".join(notes))

    # -------------------------------------------------------- the loop side

    async def _shutdown(self) -> list[str]:
        for state in list(self._states.values()):
            for future in state.pending.values():
                future.cancel()
        await asyncio.sleep(0)
        for digest in list(self._states):
            self._release(digest)
        if self._teardowns:
            await asyncio.wait(set(self._teardowns), timeout=_teardown_budget() + 1)
        notes = await self._force_all()
        others = asyncio.all_tasks() - {asyncio.current_task()}
        for task in others:
            task.cancel()
        await asyncio.gather(*others, return_exceptions=True)
        notes, self._notes = [*self._notes, *notes], []
        return notes

    async def _force_all(self) -> list[str]:
        """force_stop every client whose release has not finished."""
        notes = []
        for state in list(self._states.values()):
            if (
                note := await _attempt("force_stop", state.client.force_stop(), _FORCE_S)
            ) is not None:
                notes.append(note)
        return notes

    def _release(self, digest: str) -> None:
        """Start the release of an exchange in the background (loop thread only). The state
        stays registered until its client is stopped."""
        state = self._states.get(digest)
        if state is None or state.releasing is not None:
            return
        if state.unsubscribe is not None:
            state.unsubscribe()
        for future in state.pending.values():
            future.cancel()
        task = asyncio.get_running_loop().create_task(self._drop(digest, state))
        state.releasing = task
        self._teardowns.add(task)
        task.add_done_callback(self._teardowns.discard)

    async def _drop(self, digest: str, state: _State) -> None:
        """Disconnect, stop, and on a failed stop force_stop. Failures go to ``self._notes``,
        which ``close()`` raises: the reply that ended the exchange has already been returned."""
        try:
            notes = [
                await _attempt(
                    "disconnect",
                    state.session.disconnect() if state.session else None,
                    _DISCONNECT_S,
                ),
                await _attempt("stop", state.client.stop(), _STOP_S),
            ]
            if notes[1] is not None:
                notes.append(await _attempt("force_stop", state.client.force_stop(), _FORCE_S))
            self._notes += [n for n in notes if n is not None]
        finally:
            if self._states.get(digest) is state:
                del self._states[digest]

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
            if getattr(invocation, "agent_id", None):
                raise ValueError("sub-agent tool calls are not served")
            if call_id in state.pending:
                raise ValueError("a tool call id was issued twice")
            future: asyncio.Future[str] = asyncio.get_running_loop().create_future()
            state.pending[call_id] = future
            state.calls[call_id] = (str(invocation.tool_name), invocation.arguments)
            self._post(state, _INVOKED)
            return await future

        return ToolDef(spec.name, spec.description, handler, dict(spec.parameters))

    async def _open(
        self, call: _Call, options: ClientOptions, system: str, deadline: float
    ) -> _State:
        home = Path.cwd() / ".copilot-home" / call.digest / call.reservation
        try:
            home.mkdir(parents=True, exist_ok=False)
        except FileExistsError:
            raise _Refuse("HomeExists", "HomeExists") from None
        client = self._factory(dataclasses.replace(options, home=str(home)))
        state = _State(client)
        self._states[call.digest] = state
        try:
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
        except BaseException:
            self._release(call.digest)
            raise
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
                    raise _Refuse("ExchangeExists", "this exchange already has a session")
                system, first_user = _plan_first(call.request)
                state = await self._open(call, options, system, call.deadline)
                answers, nudge = {}, first_user
            else:
                found = self._states.get(call.digest)
                if found is None or found.releasing is not None:
                    raise _Refuse("SessionMissing", "no session for this exchange; never resent")
                state = found
                answers, nudge = _plan_next(call.request, state)
            sent = True
            state.calls.clear()
            await self._deliver(state, answers, nudge, call.deadline)
            records, timeout = await self._collect(state, call.deadline)
            return await self._settle(call, state, records, timeout, redactor)
        except _Refuse as refusal:  # nothing was sent; a live exchange is left as it is
            return self._not_sent(refusal.error_class, refusal.message, call.started)
        except _ToolCallLost:
            return self._failed(call, TOOL_CALL_LOST, "a pending tool handler was cancelled")
        except TimeoutError:
            return self._failed(
                call,
                OVERALL_TIMEOUT if sent else PRE_SEND_FAILURE,
                "the exchange timed out" if sent else "OverallTimeout: the exchange timed out",
                sent=sent,
            )
        except Exception as error:  # noqa: BLE001 - released, and reported as a reply
            cls = ADAPTER_ERROR if sent else PRE_SEND_FAILURE
            scrubbed = _ABSOLUTE_PATH.sub("<path>", self._scrub(str(error), options))
            text = f"{cls}: {type(error).__name__}: {scrubbed}"
            return self._failed(call, cls, _snippet(redactor, text), sent=sent)

    def _scrub(self, text: str, options: ClientOptions) -> str:
        """``text`` without the runtime path, the exchange's home or the working directory."""
        values = [options.runtime, options.home, str(Path.cwd()), *options.private_paths]
        text = _paths_in(text, [v for v in values if _is_scrubbable(v)])
        return _WINDOWS_PATH.sub("<path>", text)

    def _failed(
        self, call: _Call, error_class: str, text: str, *, sent: bool = True
    ) -> AdapterReply:
        self._release(call.digest)
        if not sent:
            return self._not_sent(error_class, text, call.started)
        return AdapterReply(
            "sent_unknown", None, None, None, error_class, None, call.started, self._clock(),
            message=text,
        )  # fmt: skip

    async def _deliver(
        self, state: _State, answers: dict[str, str], nudge: str | None, deadline: float
    ) -> None:
        if any(future.done() for future in state.pending.values()):
            raise _ToolCallLost  # the SDK finished a handler: its result would go nowhere
        for call_id, text in answers.items():
            state.pending.pop(call_id).set_result(text)
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
        while not _boundary(records, state.calls):
            remaining = deadline - loop.time()
            if remaining <= 0:
                return records, OVERALL_TIMEOUT
            try:
                item = await asyncio.wait_for(state.queue.get(), min(self._idle_s, remaining))
            except TimeoutError:
                return records, OVERALL_TIMEOUT if remaining <= self._idle_s else IDLE_TIMEOUT
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
        body = dump_json(_home_free(records)).encode("utf-8")
        raw = redactor.bytes_(body)
        if timeout is not None:
            assert state.session is not None
            failure = await _attempt("abort", state.session.abort(), _ABORT_S)
            reply = self._timeout_reply(call, body, raw, timeout)
            self._release(call.digest)
            return self._with_note(reply, failure)
        outcome = parse("copilot", 200, body, {}, redactor)
        finished = self._clock()
        if isinstance(outcome, ProviderError):
            if outcome.error_class == "KeyReflected":
                raw = _REFLECTED_RAW
            elif outcome.error_class == "UnparsableReply":
                raw = _UNPARSABLE_RAW
            self._release(call.digest)
            return _reply_from_error(outcome, raw, 200, {}, call.started, finished)
        wrong = _routing_error(outcome, records, self._model.model)
        if wrong is None and not _calls_match(outcome, state.calls):
            wrong = TOOL_CALL_MISMATCH
        if wrong is None and state.pending.keys() == {c.call_id for c in outcome.tool_calls}:
            # the exchange goes on: the loop may answer the calls or nudge with a user message
            state.history = (
                *call.request.messages,
                Message("assistant", outcome.text, outcome.tool_calls),
            )
            return self._ok(call, outcome, raw, finished)
        self._release(call.digest)
        if wrong is None:
            return self._ok(call, outcome, raw, finished)
        message = f"the reply was refused: {wrong}"
        if outcome.usage == Usage() and outcome.billed_usd is None:
            # no counts and no charge: which charge was paid is unknown, as in the other paths
            return AdapterReply(
                "sent_unknown", None, raw, 200, wrong, None, call.started, finished,
                message=message,
            )  # fmt: skip
        return AdapterReply(
            "sent_usage", None, raw, 200, wrong, None, call.started, finished,
            outcome.usage, outcome.billed_usd,
            message=message,
        )  # fmt: skip

    @staticmethod
    def _with_note(reply: AdapterReply, note: str | None) -> AdapterReply:
        if note is None:
            return reply
        return dataclasses.replace(reply, message="; ".join(filter(None, [reply.message, note])))

    @staticmethod
    def _ok(call: _Call, turn: Turn, raw: bytes, finished: float) -> AdapterReply:
        return AdapterReply(
            "ok", turn, raw, 200, None, None, call.started, finished, turn.usage, turn.billed_usd
        )  # fmt: skip

    def _timeout_reply(self, call: _Call, body: bytes, raw: bytes, timeout: str) -> AdapterReply:
        if raw != body:  # a key is in the events so far: none of them is kept
            raw = _REFLECTED_RAW
        # read back as the parser reads a body: a charge written 100.0 is the integer 100
        records = cast(list[dict[str, Any]], load_json(body.decode("utf-8")))
        data = _usage_data(records)
        counts: Usage | None = None
        if data is not None:
            try:
                counts = _usage(data)
            except _BadReply:
                counts = None
        finished = self._clock()
        text = f"no further event within the {timeout} bound"
        # more than one usage event is more than one model call: which one was paid is unknown
        two_calls = sum(1 for r in records if r["type"] == USAGE) > 1
        if data is None or counts is None or counts == Usage() or two_calls:
            return AdapterReply(
                "sent_unknown", None, raw, None, timeout, None, call.started, finished,
                message=text,
            )  # fmt: skip
        return AdapterReply(
            "sent_usage", None, raw, None, timeout, None, call.started, finished,
            counts, _billed_usd(data), message=text,
        )  # fmt: skip


async def _attempt(name: str, step: Awaitable[None] | None, bound: float) -> str | None:
    """Run one release step (abort, disconnect, stop, force_stop) within its bound.

    Documented fail-open: teardown failures ride on reply.message into the call record when the
    step is on the reply's path (abort); the background release keeps them in the adapter's
    notes, which close() raises. The decided reply is never replaced by a release failure."""
    if step is None:
        return None
    try:
        await asyncio.wait_for(step, bound)
    except Exception as error:  # noqa: BLE001 - returned as a note, see above
        return f"{name} failed: {type(error).__name__}"
    return None


def _boundary(records: list[dict[str, Any]], calls: Mapping[str, tuple[str, Any]]) -> bool:
    """The call is complete: a session error, a session.idle or a second usage event (whatever
    was announced: a second model call is never part of this one); or usage and, for a tool
    turn, every announced handler invoked and its tool.execution_start seen."""
    kinds = [r["type"] for r in records]
    if SESSION_ERROR in kinds or "session.idle" in kinds or kinds.count(USAGE) > 1:
        return True
    data = _usage_data(records)
    if data is None:
        return False
    announced = data.get("numToolCalls")
    if isinstance(announced, int) and not isinstance(announced, bool) and announced > 0:
        starts = {r["data"].get("toolCallId") for r in records if r["type"] == TOOL_START}
        return len(calls) >= announced and starts >= calls.keys()
    # a tool turn that announces no count: parse names it, nothing else will come
    return data.get("finishReason") in _TOOL_FINISH
