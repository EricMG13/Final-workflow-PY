# GitHub Copilot SDK Adapter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. The owner chose subagent-driven execution (2026-11-06).

**Goal:** Let a CP-OS live module exchange be answered by GitHub Copilot (Claude and GPT through the user's Copilot seat on a Windows PC) behind the existing `ModelAdapter` seam, with the handoff loop, budget, redaction, call log and handoff checks unchanged.

**Architecture:** A `copilot` provider with two configurations (`copilot-sol-medium`, `copilot-opus-medium`). `CopilotAdapter` runs one isolated Copilot SDK session (`mode="empty"`, no built-in tools) per module exchange and answers each `complete()` with exactly one model call: the session's events for that call are the raw body, `providers.parse("copilot", ...)` turns them into the `Turn` the loop already prices, redacts and records. The loop keeps executing tools: the SDK's tool handlers block on a future that the next `complete()` resolves with the loop's tool results. Copilot bills per token; the runtime's reported `cost` is the billed charge.

**Tech Stack:** Python 3.13 · `github-copilot-sdk==1.0.28` (MIT; pins Copilot CLI runtime 1.0.105; depends on `pydantic>=2.11` already locked at 2.14.1, `python-dateutil`, `httpx`) · existing `deploy_workflow.model` package.

**Spec:** the **Design** section of this file. Design decisions were taken by the controller on 2026-11-06 after the owner's answers: shared issuer-library platform launches runs, the run executes on the owner's Windows PC, Claude and GPT through Copilot, version rules ignored, SDK added.

**SDK source of truth:** the published wheel, unpacked at
`/private/tmp/claude-501/-Users-ericguei-Documents-final-workflow--claude-worktrees-adversarial-reviewer-ux-ui-d73bdd/ccd0316f-4413-42e1-88f5-3c1f104abb06/scratchpad/sdk-1.0.28/w/copilot/` (read-only; `client.py`, `session.py`, `tools.py`, `_mode.py`, `generated/session_events.py`, `generated/rpc.py`). After Task 1 the same files are importable from the locked environment (`uv run python -c "import copilot, inspect; print(inspect.getsourcefile(copilot))"`). GitHub `main` is newer than 1.0.28: never read it for this plan.

## Design (the spec this plan implements)

1. **Provider and configurations.** `Provider` gains `"copilot"`. `CONFIG_PROVIDERS`, `CONFIG_MODELS`, `MODEL_EFFORTS`, `PRICES`, `model_testing.configs.CONFIGS`, `adapter.KEY_VARIABLES`, `record._PROVIDERS`, `providers.INCLUSIVITY`, `run_pathway.BYTES_PER_TOKEN_LOWER_BOUND` each gain the copilot entries below. Configurations: `copilot-sol-medium` = (`"copilot"`, model `"gpt-6.1-sol"`, effort `"medium"`); `copilot-opus-medium` = (`"copilot"`, model `"claude-opus-5.5"`, effort `"medium"`). Both have `roles=frozenset()` in `CONFIGS` (no model-testing stage plans them). The Copilot model ids are pinned from GitHub's naming (`ModelInfo.id` examples such as `"claude-sonnet-4.5"`) and are **unverified until the first run on the seat**: the adapter refuses before sending when `list_models()` does not list the id (Design 6).
2. **Prices** (GitHub "Models and pricing", fetched 2026-11-06, USD per 1M tokens, 1 AI credit = $0.01): `copilot-sol-medium` input 2.00, cached read 0.10, cache write 2.50, output 10.00, long context above 272 000 input tokens at 4.00 / 0.20 / 5.00 / 15.00, `max_input_tokens=272_000`, `long_context_after=272_000`, `max_context_tokens=1_050_000`, `reservation_context_tokens=1_050_000`. `copilot-opus-medium` input 4.00, cached read 0.20, cache write held at 8 (the Anthropic 1-hour write rate; Copilot lists 5.00 but the runtime's cache TTL is unverified and the copilot table only sizes holds), output 20.00 (no 5 m / 1 h split). Both copilot entries carry `reservation_output_tokens=128_000`: the runtime does not enforce `max_output_tokens`, so `request_reservation_usd` (and the loop's reservation function) price output at `max(max_output, price.reservation_output_tokens)` when that field is set; 128 000 is both models' documented output maximum (`cases/pilot-fixes/limits.json`). `COPILOT_PRICES_AS_OF = date(2026, 11, 6)`.
3. **Charge.** `INCLUSIVITY["copilot"] = Inclusivity(None, None, True)`: the charge is the `assistant.usage` event's `copilotUsage.totalNanoAiu`, a non-negative integer-valued JSON number of nano-AI-units, as `Turn.billed_usd = Decimal(<its digits>) * Decimal("1E-9") * Decimal("0.01")` (1 AI unit = 1 AI credit = $0.01; confirmed on the seat by Task 5's factor check). The experimental `cost` field is ignored. A missing, negative, non-integer-valued or non-numeric `totalNanoAiu` leaves `billed_usd` `None` (an unknown charge, never a guess). `computed_usd("copilot", ...)` returns `None`; `price_usage` returns `_UNKNOWN` for a live copilot call with no `billed_usd`, as it does for openrouter. Reservations use the table (Design 2). A token count the runtime does not state is `None`, never 0.
4. **Raw body and parse.** The raw body of one call is the JSON array of the session events observed for that call, each `{"type": <SessionEventType value>, "data": <event.data.to_dict()>}` (camelCase wire keys), serialised with `dump_json`. `providers.parse("copilot", status, body, headers, redactor)` dispatches to `copilot.parse_events(text, seen, cut_as_turn) -> Turn` (raising `providers._BadReply` on shape errors) so key-reflection guards, `UnparsableReply` and the record's archive re-check (`record._PROVIDERS`) work unchanged. A body that is not a JSON array of such objects is `_BadReply`. Mapping:
   - exactly one `assistant.usage` event, else `_BadReply`; `inputTokens`→`input_tokens`, `cacheReadTokens`→`cached_read_tokens`, `cacheWriteTokens`→`cache_write_tokens`, `outputTokens`→`output_tokens`, `reasoningTokens`→`reasoning_tokens` (absent → `None`); `model`→`reported_model`; `copilotUsage.totalNanoAiu`→`billed_usd` per Design 3 (absent, negative, non-integer-valued or non-numeric → `None`); `apiCallId`, else `providerCallId`, → `request_id`; `finishReason` `"stop"` or `"end_turn"`→`"end"`, `"tool_calls"` or `"tool_use"`→`"tool_use"`, `"length"` or `"max_tokens"`→`"max_tokens"` (both the OpenAI and the Anthropic `/v1/messages` words, since Copilot relays each model's vocabulary; Task 5's seat check records the word each model reports), anything else or absent →`"other"`; a `"length"` finish with no tool call is `ProviderError(SENT_CHARGE_USAGE if usage else SENT_CHARGE_UNKNOWN, "ReplyCut", ...)` with the usage, billed, model and request id, exactly as the other mappers apply CP1H-R16, unless `cut_as_turn` is true (then the `max_tokens` turn); a `"length"` finish with tool calls is a `max_tokens` turn carrying them; tool calls under any other non-`tool_use` stop are `_BadReply("tool calls without finishReason tool_calls")`;
   - `text` = the `content` of every `assistant.message` event joined with `""` (none → `""`);
   - `tool_calls` = every `tool.execution_start` event in order: `toolCallId`→`call_id`, `toolName`→`name`, `arguments`→`arguments` when it is a JSON object, `{}` when absent or `null` (the runtime omits arguments for a no-parameter tool such as `list_sources`; the OpenAI mapper maps empty arguments the same way), else `arguments={}` and `bad_arguments=<its JSON text>`; a duplicate `toolCallId` is `_BadReply`; a start carrying a non-null `parentToolCallId` (a sub-agent call, impossible in `mode="empty"`) is `_BadReply`; when the usage event carries `numToolCalls`, the count must equal it, else `_BadReply("tool count ...")`; when `finishReason` is `"tool_calls"` and `numToolCalls` is absent, `_BadReply("tool count unknown")`;
   - the whole decoded body object is appended to `seen` as `_parse_openai` does, so an escaped key anywhere in it (reasoning, tool titles) is caught;
  - a usage event that states no count at all makes a `session.error` `SENT_CHARGE_UNKNOWN`, as `_usage_error` does;
  - a `session.error` event anywhere → `ProviderError(SENT_CHARGE_USAGE if a usage event is present else SENT_CHARGE_UNKNOWN, "SessionError", <redacted snippet of errorType + message>, statusCode)` returned from `parse` (not raised), with the usage event's counts in `ProviderError.usage` when present;
   - `http_status` = 200; `provider_blocks = ()`; stop reason `"tool_use"` with zero tool calls is `_BadReply`.
5. **Adapter.** `deploy_workflow/model/copilot.py: CopilotAdapter(model: ModelSpec, ruling: Path, *, environ: Mapping[str, str] | None = None, clock=time.time, rulings_root: Path | None = None, client_factory: ClientFactory = real_client)` implements `ModelAdapter`. Construction runs `check_live_gate` first, before any environment read (as `LiveAdapter`). On the first `complete` only it reads `COPILOT_GITHUB_TOKEN` (`KEY_VARIABLES["copilot"]`) and `COPILOT_CLI_PATH`; a missing or empty token → `not_sent` `KeyMissing` ("COPILOT_GITHUB_TOKEN is not set or empty"); a missing variable or a path that is not an existing regular file → `not_sent` `RuntimeMissing` (message names the variable only, never the path). `effort_for(model)` refusals → `not_sent` with the error's class name. The adapter never reads `~/.copilot`: `base_directory` is `<cwd>/.copilot-home/<invocation_digest>` created by the adapter.
6. **Client and session.** `real_client` builds `CopilotClient(connection=RuntimeConnection.for_stdio(path=runtime), github_token=key, use_logged_in_user=False, mode="empty", base_directory=home, log_level="none", env=<allowlist>)` where the allowlist copies from the adapter's `environ` mapping only: `PATH`, `HOME`, `USERPROFILE`, `TMPDIR`, `TEMP`, `TMP`, `SYSTEMROOT`, `SYSTEMDRIVE`, `COMSPEC`, `PATHEXT`, `WINDIR`, `USERNAME`, `APPDATA`, `LOCALAPPDATA`, `PROGRAMDATA`, `LANG`, every `LC_*`, `SSL_CERT_FILE`, `SSL_CERT_DIR`, `REQUESTS_CA_BUNDLE`, `NODE_EXTRA_CA_CERTS`, `HTTP_PROXY`, `HTTPS_PROXY`, `NO_PROXY` and their lower-case forms (never a provider key, never `GH_TOKEN`/`GITHUB_TOKEN`; the token travels only through `github_token`). `ClientOptions.token` has `repr=False`. The home directory is `<cwd>/.copilot-home/<invocation_digest>/<reservation_id>` created with `exist_ok=False` (a refused first call never blocks a retry); an existing home is `not_sent` `HomeExists`; `.copilot-home/` is git-ignored. Before the first session the adapter calls `list_models()`: the pinned model id must be listed, else `not_sent` `ModelUnavailable`; when that model's `supported_reasoning_efforts` is a list, it must contain the effort, else `not_sent` `EffortUnavailable`. Sessions: `create_session(model=spec.model, reasoning_effort=effort, system_message={"mode": "replace", "content": <system text>}, tools=<one Tool per request.tools>, available_tools=ToolSet().add_custom("*"), on_permission_request=<reject every request>, streaming=False, session_id=invocation_digest)`. Each `Tool` has `name`, `description`, `parameters=dict(spec.parameters)`, `skip_permission=True`, and the adapter's handler. The system text is the request's `system` messages joined by `"\n\n"`; the first `send` carries the request's single `user` message text (more than one user message in the first request → `not_sent` `HistoryMismatch`). `max_output_tokens` is checked by `effort_for`'s neighbour `_check` semantics (1..`MAX_OUTPUT_TOKENS`) but cannot be enforced on the runtime; the plan records this under Not verified.
7. **One `complete`, one model call.** State per `invocation_digest`: the session, the history the adapter has seen (the redacted `TurnRequest.messages` tuple of the last request plus the assistant/tool messages it produced), and the pending tool futures keyed by `tool_call_id`. `call_index == 0`: create the session, `send`. `call_index > 0` with no state → `not_sent` `SessionMissing` (CP-OS resumes from retained responses; never resend). Otherwise the request's messages must begin with the adapter's history as a prefix (field-wise equality of `role`, `text`, `tool_calls`, `tool_call_id`), else `not_sent` `HistoryMismatch`; the tail is zero or more `tool` messages followed by at most one `user` message. Every pending future must receive exactly one tool message by `tool_call_id` and no tool message may name an unknown id (`not_sent` `ToolResultMismatch`); then the user message, if any, is `send`-ed. A tool handler records `(tool_call_id, tool_name, arguments)` for the current call, awaits its future and returns the loop's result string unchanged (the loop has already redacted it).
8. **Call boundary and timeouts.** The call's events are every event delivered after `send`/resolution until the boundary: an `assistant.usage` event has arrived and (its `numToolCalls` > 0 → that many handler invocations AND that many `tool.execution_start` events have been recorded; otherwise → a `session.idle` event has arrived); or a `session.idle`, a second `assistant.usage` or a `session.error` event has arrived whatever was announced (a second model call inside one `complete` is never billed as the first: the parser refuses two usage events as `UnparsableReply`, and a timeout reply over a body with two usage events is `sent_unknown`). A handler invocation records `(tool_call_id, tool_name, arguments)`; a difference from the `tool.execution_start` event with that id is `sent_usage` `ToolCallMismatch`. Events with a non-empty `agent_id` are ignored. No event for `transport.IDLE_S` seconds → `abort()`, outcome `IdleTimeout`; `transport.OVERALL_S` from the call's start → `abort()`, outcome `OverallTimeout`; either is `sent_usage` with the usage when a usage event was seen, else `sent_unknown`; the raw body is the events so far. The session is kept after an `"end"`/`"max_tokens"`/`"other"` turn (the loop may send a nudge as the next user message); it is disconnected and the state dropped after an error or a timeout, on `close()`, and when a later request for the same digest cannot continue it. A refusal (`not_sent`) never tears down a live session. Teardown never sits on the reply's path: `_drop` runs as a tracked background task that `close()` awaits. The boundary for a tool turn also requires that a `tool.execution_start` event has arrived for every invoked handler (the start events are the parser's tool-call source), not only the invocations. `AdapterReply` fields follow `LiveAdapter.complete`: `started`/`finished` from `clock`, `http_status` 200 for a parsed body, `raw = redactor.bytes_(body)`, `_REFLECTED_RAW` / `_UNPARSABLE_RAW` on `KeyReflected` / `UnparsableReply`. After `parse`, a turn whose `reported_model != spec.model`, or whose usage event has `isByok` or `isAuto` true, is `sent_usage` `ModelMismatch` / `ByokRouted` / `AutoRouted` with the turn's usage and billed cost; the body is still archived.
9. **Threads.** `complete` is synchronous. The adapter owns one thread running an asyncio loop (`asyncio.new_event_loop`, `run_forever`) and submits coroutines with `asyncio.run_coroutine_threadsafe`; the outer `.result()` bound is `overall_s` plus every teardown bound that can sit on the path. Teardown of a state (`abort` 5 s, `disconnect` 5 s, `stop` at least 30 s, the SDK's own shutdown budget, then `force_stop` on failure; `ClientLike` gains `force_stop()`) runs as a tracked background task and the state stays registered until `stop` finishes. `close()` drops every kept state concurrently, waits at most one state's teardown budget, force-stops whatever is left, stops the loop and joins the thread; it is idempotent and a second call after a timed-out first call retries the release. Resolving a tool result for a future that is already done (the SDK cancelled the handler) is `sent_unknown` `ToolCallLost`, never a silent skip. `__del__` is not relied on. The adapter is used by one `HandoffExecutor` at a time.
10. **Redaction.** `redact.KEY_ENV_NAMES` gains `"COPILOT_GITHUB_TOKEN"`, `"GH_TOKEN"`, `"GITHUB_TOKEN"`; `KEY_PATTERN` also matches GitHub token shapes `gh[pousr]_[A-Za-z0-9]{36,}` and `github_pat_[A-Za-z0-9_]{22,}` with the same boundary rule. Error messages never carry the token, the runtime path, a prompt or an answer.
11. **Wiring.** `owners/cpos.py` and `owners/cpos_launch.py` build `CopilotAdapter` when `CONFIGS[config].provider == "copilot"`, else `LiveAdapter`; the live-mode checks that test `isinstance(execute.adapter, LiveAdapter)` accept either. `COPILOT_GITHUB_TOKEN` is the key variable `cpos_launch` reports for copilot configs through `KEY_VARIABLES`.
12. **Not built.** No CLI (`copilot -p`) fallback, no headless TCP server, no BYOK, no streaming, no compaction, no MCP, no runtime download by the code (`COPILOT_CLI_PATH` must point at an installed runtime), no Windows-specific code.

## Global Constraints

- Python `>=3.13,<3.14`; `uv` `==0.12.5`; `uv lock --check` passes; `ruff check`, `ruff format --check` and `mypy` (strict) report nothing in new or changed files (28 pre-existing mypy errors elsewhere stay as they are).
- No credential file; keys only from the environment mapping passed in, read on the first `complete`. The build, import, tests and replays never start the Copilot runtime or any provider.
- Money is `Decimal` from JSON digits (`turn.load_json`); never `float`. A count the runtime does not state is `None`, never 0.
- No stub or fake value standing in for real behaviour in `src/`; no catch-all that hides a failure. Tests use fakes injected through `client_factory`; the real client is built only by `real_client`.
- Every task report ends with a `Not verified:` line.
- Commit messages end with `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`.
- The 800-changed-line gate: Tasks 1–3 go in one PR from this branch; Tasks 4–5 in a second PR stacked on it.

## Review Focus

1. A `tool.execution_start` whose `arguments` is a JSON string or list, not an object: the turn carries `bad_arguments` and the loop answers "ERROR: malformed tool arguments" (Task 3 test `test_non_object_arguments_are_bad_arguments`).
2. The runtime reports `cost` as `0` or omits it: the charge is `0` only when stated; absent is unknown, never priced from the table live (Task 2 test `test_copilot_live_charge_is_billed_only`, Task 3 test `test_usage_without_cost_has_no_billed_usd`).
3. A tool result arrives for a `tool_call_id` the runtime never issued, or one issued call gets no result: the adapter refuses before sending anything (Task 4 test `test_tool_result_mismatch_is_not_sent`).
4. The loop stops mid-exchange (budget overrun, acceptance) while handlers are still awaiting: `close()` cancels the futures and disconnects without hanging (Task 4 test `test_close_releases_blocked_handlers`).
5. A GitHub token appears inside an event's text (the model echoes the environment): the record's raw body is `_REFLECTED_RAW` and the token never reaches `calls.jsonl` (Task 4 test `test_token_echoed_in_events_is_withheld`).

---

### Task 1: Dependency and redaction

**Files:**
- Modify: `pyproject.toml` (dependencies), `uv.lock`
- Modify: `src/deploy_workflow/model/redact.py:18-24`
- Test: `tests/model/test_redact.py`

**Interfaces:**
- Produces: `KEY_ENV_NAMES` containing the three GitHub variables; `KEY_PATTERN` matching GitHub token shapes.

- [ ] **Step 1: Write the failing tests** in `tests/model/test_redact.py`:

```python
@pytest.mark.parametrize(
    "token",
    [
        "ghp_" + "A" * 36,
        "gho_" + "b1" * 18,
        "github_pat_" + "x" * 22 + "_" + "y" * 40,
    ],
)
def test_github_token_shapes_are_redacted(token: str) -> None:
    assert Redactor().text(f"Authorization: Bearer {token}.") == "Authorization: Bearer [redacted]."


def test_github_token_inside_a_word_is_not_a_token() -> None:
    assert Redactor().text("xghp_" + "A" * 36) == "xghp_" + "A" * 36


def test_copilot_variables_are_exact_values() -> None:
    environ = {"COPILOT_GITHUB_TOKEN": "tok-one", "GH_TOKEN": "tok-two", "GITHUB_TOKEN": "tok-3"}
    redactor = Redactor.from_environ(environ)
    assert redactor.text("tok-one tok-two tok-3") == "[redacted] [redacted] [redacted]"
```

- [ ] **Step 2: Run them**: `uv run pytest tests/model/test_redact.py -q`. Expected: the three new tests FAIL.
- [ ] **Step 3: Add the dependency**: in `pyproject.toml` `dependencies` append `"github-copilot-sdk==1.0.28"`; run `uv lock` then `uv sync --locked`. Check: `uv run python -c "import copilot; from copilot import CopilotClient, RuntimeConnection, Tool, ToolSet"` exits 0 and `uv run python -c "from copilot._cli_version import CLI_VERSION; print(CLI_VERSION)"` prints `1.0.105`.
- [ ] **Step 4: Extend `KEY_ENV_NAMES` and `KEY_PATTERN`** in `redact.py` per Design 10. The pattern keeps its left boundary group and adds the two GitHub alternatives inside the existing capture group; `_KEY_PATTERN_BYTES` follows automatically.
- [ ] **Step 5: Run** `uv run pytest tests/model/test_redact.py tests/model/test_record.py -q`. Expected: all PASS.
- [ ] **Step 6: Gates**: `uv run ruff check <changed files> && uv run ruff format --check <changed files> && uv run mypy <changed src files> && uv lock --check` (the repo has pre-existing ruff failures in untouched files; gates run over the task's changed files). Expected: exit 0 each.
- [ ] **Step 7: Commit** `feat(copilot): lock github-copilot-sdk 1.0.28 and redact GitHub tokens`.

### Task 2: Provider tables, prices and configurations

**Files:**
- Modify: `src/deploy_workflow/model/turn.py:15-45`, `src/deploy_workflow/model/providers.py:73-78,133-142`, `src/deploy_workflow/model/pricing.py:38,125-165,279-312`, `src/deploy_workflow/model/adapter.py:61-65`, `src/deploy_workflow/model/record.py:65`, `src/deploy_workflow/model_testing/configs.py:37-55`, `src/deploy_workflow/run_pathway.py` (`BYTES_PER_TOKEN_LOWER_BOUND`)
- Test: `tests/model/test_pricing.py`, `tests/model/test_providers.py`, `tests/test_model_testing_configs.py`

**Interfaces:**
- Produces: `Provider` includes `"copilot"`; `CONFIG_PROVIDERS["copilot-sol-medium"] == CONFIG_PROVIDERS["copilot-opus-medium"] == "copilot"`; `CONFIG_MODELS` maps them to `"gpt-6.1-sol"` and `"claude-opus-5.5"`; `MODEL_EFFORTS["claude-opus-5.5"] == frozenset({"medium"})`; `PRICES` has both; `INCLUSIVITY["copilot"]`; `KEY_VARIABLES["copilot"] == "COPILOT_GITHUB_TOKEN"`; `record._PROVIDERS` includes `"copilot"`; `COPILOT_PRICES_AS_OF`.

- [ ] **Step 1: Write the failing tests**:

```python
# tests/model/test_pricing.py
def test_copilot_table_rates() -> None:
    sol, opus = price_of("copilot-sol-medium"), price_of("copilot-opus-medium")
    assert (sol.input, sol.cached_read, sol.cache_write, sol.output) == (
        Decimal("2.00"), Decimal("0.10"), Decimal("2.50"), Decimal("10.00"))
    assert (sol.long_context_after, sol.long_input, sol.long_output) == (272_000, Decimal(4), Decimal(15))
    assert (opus.input, opus.cached_read, opus.cache_write, opus.output) == (
        Decimal(4), Decimal("0.20"), Decimal(8), Decimal(20))
    assert sol.reservation_output_tokens == opus.reservation_output_tokens == 128_000
    assert COPILOT_PRICES_AS_OF == date(2026, 11, 6)


def test_copilot_hold_prices_output_at_the_model_maximum() -> None:
    held = request_reservation_usd(price_of("copilot-opus-medium"), 1000, 32_000)
    assert held == request_reservation_usd(price_of("copilot-opus-medium"), 1000, 128_000)
    assert request_reservation_usd(price_of("opus-medium"), 1000, 32_000) < held


def test_copilot_live_charge_is_billed_only() -> None:
    usage = Usage(input_tokens=1000, cached_read_tokens=0, output_tokens=10)
    assert price_usage("copilot-sol-medium", usage).cost_status == "unknown"
    priced = price_usage("copilot-sol-medium", usage, Decimal("0.0021"))
    assert (priced.usd, priced.cost_status) == (Decimal("0.0021"), "billed")
    assert price_usage("copilot-sol-medium", usage, Decimal("0.0021"), offline=True).cost_status == "unknown"


# tests/model/test_providers.py
def test_copilot_configs_admit_medium_only() -> None:
    assert effort_for(ModelSpec("copilot-opus-medium", "copilot", "claude-opus-5.5", "medium")) == "medium"
    with pytest.raises(UnknownEffort):
        effort_for(ModelSpec("copilot-opus-medium", "copilot", "claude-opus-5.5", "high"))
    with pytest.raises(UnknownEffort):
        effort_for(ModelSpec("copilot-sol-medium", "copilot", "claude-opus-5.5", "medium"))


def test_copilot_cannot_be_built_as_an_https_request() -> None:
    spec = ModelSpec("copilot-sol-medium", "copilot", "gpt-6.1-sol", "medium")
    with pytest.raises(ProviderConfigError):
        build(spec, TurnRequest((Message("user", "hi"),), (), 100, "medium"), "tok")
```

Update `test_table_is_the_four_configs_dated` (now six configurations; the copilot two dated by `COPILOT_PRICES_AS_OF`) and the `tests/test_model_testing_configs.py` tests that enumerate configurations so the copilot entries are expected with `roles == frozenset()`.

- [ ] **Step 2: Run** `uv run pytest tests/model/test_pricing.py tests/model/test_providers.py tests/test_model_testing_configs.py -q`. Expected: new tests FAIL (`NoPrice`, `KeyError`, or `UnknownEffort` not raised).
- [ ] **Step 3: Add the entries** per Design 1–3: `build()` raises `ProviderConfigError("copilot is not an https provider")` for `spec.provider == "copilot"` before any URL is chosen; `computed_usd` returns `None` for `"copilot"`; `price_usage` treats `"copilot"` like `"openrouter"` live. `BYTES_PER_TOKEN_LOWER_BOUND["copilot"]` = the smaller of the openai and anthropic entries.
- [ ] **Step 4: Run** the three test files again. Expected: PASS. Then `uv run pytest tests/model tests/test_model_testing_configs.py tests/test_run_pathway.py -q`. Expected: PASS.
- [ ] **Step 5: Gates** as Task 1 Step 6 over the changed files.
- [ ] **Step 6: Commit** `feat(copilot): copilot provider, two configurations and their prices`.

### Task 3: Event parsing

**Files:**
- Create: `src/deploy_workflow/model/copilot.py` (parsing half)
- Modify: `src/deploy_workflow/model/providers.py:636-644` (dispatch)
- Test: `tests/model/test_copilot_parse.py`

**Interfaces:**
- Consumes: Task 2 tables; `providers._BadReply`, `ProviderError`, `ErrorKind`, `Turn`, `Usage`, `ToolCall`, `turn.load_json`.
- Produces: `copilot.parse_events(text: str, seen: list[Any], cut_as_turn: bool) -> Turn | ProviderError` and `providers.parse("copilot", 200, body, {}, redactor)` returning that result through `_guard_decoded`; `copilot.event_record(event) -> dict[str, Any]` = `{"type": event.type.value, "data": event.data.to_dict()}`; `copilot.SESSION_ERROR = "session.error"` and the other event-type string constants used by Task 4.

- [ ] **Step 1: Write the failing tests** in `tests/model/test_copilot_parse.py`, building bodies as JSON arrays of `{"type", "data"}` dicts (camelCase keys) and calling `parse("copilot", 200, body, {}, Redactor())`:
  - `test_text_turn`: usage `{"model": "gpt-6.1-sol", "inputTokens": 12, "cacheReadTokens": 4, "cacheWriteTokens": 0, "outputTokens": 7, "reasoningTokens": 2, "copilotUsage": {"totalNanoAiu": 12300000}, "cost": 0.5, "finishReason": "stop", "apiCallId": "api-1"}` + message `content: "done"` + idle → `Turn("done", (), Usage(12, 4, 0, 7, 2 as mapped), "end", "gpt-6.1-sol", "api-1", 200, billed_usd=Decimal("0.000123"))`.
  - `test_tool_turn`: `finishReason: "tool_calls"`, `numToolCalls: 2`, two `tool.execution_start` events (`toolCallId`, `toolName`, `arguments` objects) → `stop_reason == "tool_use"`, two `ToolCall`s in order, `text == ""`.
  - `test_non_object_arguments_are_bad_arguments`: `arguments: "[1,2]"` → `ToolCall(..., {}, bad_arguments='"[1,2]"')`.
  - `test_tool_count_mismatch_is_unparsable`: `numToolCalls: 1` with two starts → `ProviderError.error_class == "UnparsableReply"`, kind `SENT_CHARGE_UNKNOWN`.
  - `test_tool_calls_without_count_are_unparsable`: `finishReason: "tool_calls"`, no `numToolCalls` → `UnparsableReply`.
  - `test_usage_without_cost_has_no_billed_usd`: no `copilotUsage` → `billed_usd is None` even with `cost` present; `totalNanoAiu: 0` → `Decimal(0)`; `totalNanoAiu: 12300000.5`, `-1` and `"12300000"` → `None`.
  - `test_key_split_across_messages_is_reflected`: a token split across two `assistant.message` contents (`"ghp_" + "A" * 20` then `"A" * 16`) → `KeyReflected` (the joined text goes into `seen`; adopt `.superpowers/sdd/2026-11-06-copilot-sdk-adapter/probes/task2_archive_copilot_body.py` as the answer key).
  - `test_two_usage_events_are_unparsable`, `test_no_usage_is_unparsable`, `test_not_a_list_is_unparsable` (`b"{}"`).
  - `test_session_error_with_usage_is_sent_usage`: error event `{"errorType": "provider", "message": "upstream 503", "statusCode": 503}` after a usage → `ProviderError(SENT_CHARGE_USAGE, "SessionError", ..., 503)` with `usage.output_tokens` equal to the usage event's; without a usage → `SENT_CHARGE_UNKNOWN`.
  - `test_length_without_calls_is_reply_cut` (`error_class == "ReplyCut"`, kind `SENT_CHARGE_USAGE`, usage counts carried; with `cut_as_turn=True` a `max_tokens` turn), `test_length_with_calls_is_a_max_tokens_turn`, `test_calls_under_stop_are_unparsable`, `test_unknown_finish_reason_is_other`, `test_non_string_content_is_unparsable`.
  - `test_key_in_event_text_is_reflected`: a message `content` containing `"ghp_" + "A" * 36` → `error_class == "KeyReflected"`.
  - `test_nano_aiu_keeps_its_digits`: `"totalNanoAiu": 123456789012345678` → `billed_usd == Decimal("1234567.89012345678")` exactly (no float round trip; synthetic-body scope: the SDK types the field as float, so a live value is exact only below 2**53).
  - `test_duplicate_tool_call_id_is_unparsable`, `test_absent_arguments_are_empty` (`arguments` omitted and `null` → `{}` with `bad_arguments is None`), `test_sub_agent_start_is_unparsable` (`parentToolCallId: "p1"`), `test_anthropic_finish_words` (`end_turn`→end, `tool_use` with count→tool_use, `max_tokens`→ReplyCut without calls), `test_usage_without_counts_makes_error_unknown`.
  - `test_real_sdk_events_round_trip`: build real `copilot.generated.session_events.SessionEvent` objects (usage, message, idle) with the SDK's `from_dict`, pass them through `event_record` and `dump_json`, and `parse` the result to the same `Turn` as `test_text_turn` (adopt `probes/task3_sdk_event_record.py` as the answer key).
- [ ] **Step 2: Run** `uv run pytest tests/model/test_copilot_parse.py -q`. Expected: FAIL (`parse` has no copilot branch; module missing).
- [ ] **Step 3: Implement** `parse_events` in `copilot.py` per Design 4 and the dispatch `elif provider == "copilot": result = parse_events(text, seen, cut_as_turn)` in `providers.parse`. Every string decoded from the body is appended to `seen` the way `_parse_openai` does (so `_guard_decoded` sees it). Import `copilot` lazily inside `parse` or at module top without importing the SDK: `copilot.py`'s parsing half imports nothing from the `copilot` package.
- [ ] **Step 4: Run** the test file and `uv run pytest tests/model -q`. Expected: PASS (the record archive re-check loops over `"copilot"` without raising on openai/anthropic bodies: `tests/model/test_record.py` stays green).
- [ ] **Step 5: Gates** over `copilot.py`, `providers.py` and the test.
- [ ] **Step 6: Commit** `feat(copilot): parse a call's session events into a turn`.

### Task 4: The adapter

**Files:**
- Modify: `src/deploy_workflow/model/copilot.py` (adapter half), `src/deploy_workflow/model/adapter.py` (export nothing new; `KEY_VARIABLES` from Task 2)
- Test: `tests/model/test_copilot_adapter.py`

**Interfaces:**
- Consumes: Task 3 `parse` and `event_record`; `adapter.check_live_gate`, `AdapterReply`, `_REFLECTED_RAW`, `_UNPARSABLE_RAW`, `_reply_from_error`; `providers.effort_for`; `transport.IDLE_S`, `OVERALL_S`; `redact.Redactor.from_environ`; `turn.dump_json`.
- Produces: `CopilotAdapter` (Design 5–9), `ClientFactory = Callable[[ClientOptions], ClientLike]`, `ClientOptions(runtime: str, token: str, home: str)` frozen dataclass, protocols `ClientLike` (`async start()`, `async list_models() -> list[Any]`, `async create_session(**options) -> SessionLike`, `async stop()`) and `SessionLike` (`on(handler) -> Callable[[], None]`, `async send(text: str) -> str`, `async abort()`, `async disconnect()`), `real_client(options: ClientOptions) -> ClientLike` (imports the SDK inside the function), `CopilotAdapter.close()`.

- [ ] **Step 1: Write the fake** at the top of `tests/model/test_copilot_adapter.py`: `FakeClient(script: list[Step])` where a `Step` is one of `Emit(event_dict)`, `Invoke(tool_call_id, tool_name, arguments)` (calls the registered `Tool.handler` in a task and keeps the returned result), `Idle()`; `FakeClient.create_session(**options)` records `options`; `FakeSession.send(text)` records the text and plays the next script segment up to the next `Await` marker; events are real `copilot.generated.session_events.SessionEvent` instances built with `SessionEvent.from_dict`-style constructors from the wheel (the fake imports the SDK; the adapter under test does not need the real runtime). `list_models()` returns dicts shaped like `ModelInfo.to_dict()` with `id` and `supportedReasoningEfforts`.
- [ ] **Step 2: Write the failing tests** (ruling fixture as in `tests/model/test_adapter.py::live_ruling`, `RULING_TEXT` naming `copilot-sol-medium`; `SPEC = ModelSpec("copilot-sol-medium", "copilot", "gpt-6.1-sol", "medium")`; `environ={"COPILOT_GITHUB_TOKEN": "ghp_" + "A" * 36, "COPILOT_CLI_PATH": str(tmp_runtime_file)}`):
  - `test_gate_runs_before_environment`: constructing with a ruling not naming the config raises `LivePauseInForce` and `client_factory` is never called.
  - `test_missing_token_is_not_sent`, `test_missing_runtime_is_not_sent` (`error_class` `KeyMissing` / `RuntimeMissing`; message names the variable; no session created).
  - `test_model_not_listed_is_not_sent` (`ModelUnavailable`), `test_effort_not_supported_is_not_sent` (`EffortUnavailable`).
  - `test_first_call_creates_an_empty_mode_session_with_the_tools`: `create_session` options contain `model == "gpt-6.1-sol"`, `reasoning_effort == "medium"`, `system_message == {"mode": "replace", "content": "<system text>"}`, `streaming is False`, `available_tools` lists `custom:*`, one `Tool` per `request.tools` with `skip_permission`; client options are `ClientOptions(runtime, token, home)` with `home` under cwd and named by the digest; `send` was given the user text.
  - `test_text_reply_is_ok`: script emits usage + message + idle → reply kind `"ok"`, `turn.text`, `billed_usd`, `raw` equals `redactor.bytes_(dump_json([...events...]))`, `http_status == 200`; the session was disconnected.
  - `test_tool_calls_block_until_the_next_complete`: script: usage(`numToolCalls: 1`, `tool_calls`), `Invoke("c1", "read_pages", {...})`, `Await`, then usage(stop) + message + idle. First `complete` returns `tool_use` with `ToolCall("c1", "read_pages", {...})` while the handler is still blocked; second `complete` with history + `Message("tool", "PAGE TEXT", tool_call_id="c1")` returns the text turn, and the fake saw the handler return `"PAGE TEXT"`.
  - `test_user_nudge_after_tool_results_is_sent`: tail `tool` message then `user` message → `send` called with the nudge text once.
  - `test_history_mismatch_is_not_sent`, `test_call_index_without_session_is_not_sent` (`SessionMissing`), `test_tool_result_mismatch_is_not_sent` (unknown id, and a missing id).
  - `test_idle_timeout_after_usage_is_sent_usage`: fake clock advances past `IDLE_S` with no further event → `IdleTimeout`, kind `sent_usage`, `usage` set, `abort` called; `test_overall_timeout_before_usage_is_sent_unknown`.
  - `test_session_error_is_reported` (kind from Task 3's parse; session disconnected).
  - `test_model_mismatch_is_sent_usage` (`reported_model` differs → `ModelMismatch`), `test_byok_is_refused` (`isByok: true` → `ByokRouted`).
  - `test_token_echoed_in_events_is_withheld`: message content contains the token value → `raw == _REFLECTED_RAW`, `error_class == "KeyReflected"`.
  - `test_close_releases_blocked_handlers`: after a `tool_use` reply, `close()` returns within 2 s, the handler's task finished with a cancelled future, `disconnect`/`stop` were called; a second `close()` is a no-op.
  - `test_agent_events_are_ignored`: an event with `agent_id` set is neither in the body nor counted.
- [ ] **Step 3: Run** `uv run pytest tests/model/test_copilot_adapter.py -q`. Expected: FAIL (`CopilotAdapter` undefined).
- [ ] **Step 4: Implement** `CopilotAdapter`, `ClientOptions`, the protocols and `real_client` per Design 5–9. The permission handler returns the SDK's reject result for every request (shape from `generated/rpc.py` `PermissionDecisionKind`; pick the deny kind and document it in a comment with the file path). Handlers are `Tool.handler` callables taking a `ToolInvocation` and returning `str`. The waiting loop lives in one coroutine per call that reads from an `asyncio.Queue` fed by the `on()` handler.
- [ ] **Step 5: Run** the test file, then `uv run pytest tests/model -q`. Expected: PASS.
- [ ] **Step 6: Gates** over `copilot.py` and the test; `mypy` strict must accept the SDK types (`py.typed` ships in the wheel).
- [ ] **Step 7: Commit** `feat(copilot): CopilotAdapter bridges SDK tool handlers to the handoff loop`.

### Task 5: CP-OS wiring, seat check and record

**Files:**
- Modify: `src/deploy_workflow/owners/cpos.py:248-262,440-470,565-580,690-712`, `src/deploy_workflow/owners/cpos_launch.py:650-705`
- Create: `tests/model/test_copilot_live.py`, `docs/COPILOT.md`
- Modify: `VERIFICATION.md`, `tests/test_owner_cpos.py` or `tests/test_cpos_launch.py` (whichever covers adapter selection); `src/deploy_workflow/model/record.py` (`_error_response` infers `sent_unknown` for the adapter's error classes `IdleTimeout`, `OverallTimeout`, `ToolCallLost`, `AdapterClosed`, `AdapterError`, so `export_recording` never raises on a copilot record; test in `tests/model/test_record.py`); `src/deploy_workflow/model/copilot_adapter.py` (`_Creds` fields `token` and `env` get `repr=False`; home path and env allowlist per Design 6)
- Test: `tests/test_cpos_launch.py`, `tests/test_owner_cpos.py`

**Interfaces:**
- Consumes: `CopilotAdapter`, `CONFIGS`, `KEY_VARIABLES`.
- Produces: `cpos.run_live(..., config="copilot-sol-medium")` and the `cpos_launch` entry build a `CopilotAdapter`; live-mode checks accept it.

- [ ] **Step 1: Write the failing tests**: `test_copilot_config_selects_the_copilot_adapter` (patch `HandoffExecutor` or inspect the executor built for `config="copilot-opus-medium"` with a passing ruling: `isinstance(executor.adapter, CopilotAdapter)`, and `client_factory` is never called because no `complete` ran); `test_live_mode_check_accepts_copilot_adapter` for the `cpos_execution_mode` guard; `test_launcher_reports_copilot_key_variable` (`COPILOT_GITHUB_TOKEN` named for a copilot config).
- [ ] **Step 2: Run** `uv run pytest tests/test_owner_cpos.py tests/test_cpos_launch.py -q -k copilot`. Expected: FAIL.
- [ ] **Step 3: Implement** Design 11 with one helper `live_adapter_for(...)` and, wherever a `CopilotAdapter` is built, `close()` it in a `finally` after the executor finishes (it holds the runtime process and the kept sessions). Replace the Task 2 launcher refusal for copilot configs with the real wiring. Then the rest of Design 11 with that helper `live_adapter_for(selected: ModelConfig, ruling, environ, rulings_root) -> LiveAdapter | CopilotAdapter` in `owners/cpos.py`, used by both `cpos.py` sites and `cpos_launch.py`.
- [ ] **Step 4: Write** `tests/model/test_copilot_live.py`, marked `@pytest.mark.live`, skipped unless `COPILOT_GITHUB_TOKEN` and `COPILOT_CLI_PATH` are both set: builds `real_client(ClientOptions(...))`, asserts `list_models()` contains `"gpt-6.1-sol"` and `"claude-opus-5.5"` with `"medium"` supported, then runs one `CopilotAdapter.complete` with a ruling under a temporary rulings root, a one-line system text, the user text `"Call the tool echo with text 'ok', then reply with the tool's result only."` and one tool `echo(text: string)`; asserts the first reply is `tool_use` with one call, the second (tool result `"ok"`) is `ok` with `"ok"` in the text, `reported_model == "gpt-6.1-sol"`, and for each reply `billed_usd` lies between 0.25× and 4× of `(input_tokens * 2.00 + output_tokens * 10.00) / 1_000_000` from the reply's own usage (a unit error in the nano-AIU conversion is a 100× miss). This is the seat verification the owner runs at work; it is paid and never runs in CI.
- [ ] **Step 5: Write** `docs/COPILOT.md` (under 80 lines): the enterprise policy path (AI controls → Copilot → Features & clients → Clients → Copilot CLI), the seat and model enablement, compliance note (prompts carry issuer text), `uv sync --locked`, `uv run python -m copilot download-runtime` once, `COPILOT_CLI_PATH` to the runtime executable it prints, `COPILOT_GITHUB_TOKEN` from a fine-grained token (`use_logged_in_user=False`: the CLI login is never used), the ruling file lifting the pause for `copilot-sol-medium` / `copilot-opus-medium`, the seat check command `uv run pytest tests/model/test_copilot_live.py -m live -q`, and the Not verified list from this plan.
- [ ] **Step 6: Record** in `VERIFICATION.md` one entry `## 2026-11-06 — GitHub Copilot SDK adapter`: the dependency decision (stdlib cannot speak the runtime's JSON-RPC in a few lines; no pinned dependency does; `github-copilot-sdk==1.0.28`, MIT, runtime 1.0.105), the tests run with counts, gates, and `Not verified:` the pinned model ids, `numToolCalls` and event order on a real seat, `cost` presence, `max_output_tokens` not enforceable, Windows runtime path handling.
- [ ] **Step 7: Run** `uv run pytest -q` (whole suite; the live test is skipped) and the gates over changed files. Expected: PASS / exit 0.
- [ ] **Step 8: Commit** `feat(copilot): CP-OS selects CopilotAdapter for copilot configurations; seat check and setup page`.

---

## Self-review (controller, 2026-11-06)

- Spec coverage: Design 1–3 → Task 2; 4 → Task 3; 5–9 → Task 4; 10 → Task 1; 11 → Task 5; 12 is a non-goal list. Review Focus 1 → Task 3, 2 → Tasks 2 and 3, 3–5 → Task 4.
- Names used across tasks: `parse_events`, `event_record`, `CopilotAdapter`, `ClientOptions`, `ClientLike`, `SessionLike`, `real_client`, `close`, `live_adapter_for`, `COPILOT_PRICES_AS_OF`, error classes `KeyMissing`, `RuntimeMissing`, `ModelUnavailable`, `EffortUnavailable`, `HistoryMismatch`, `SessionMissing`, `ToolResultMismatch`, `IdleTimeout`, `OverallTimeout`, `SessionError`, `ModelMismatch`, `ByokRouted`, `AutoRouted`.
- Proportion: the plan fixes interfaces and tests; bodies are left to the implementer except the event mapping table, which is the spec.
