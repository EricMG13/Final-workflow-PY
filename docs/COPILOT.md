# Running the models through GitHub Copilot

`copilot-sol-medium` (`gpt-6.1-sol`) and `copilot-opus-medium` (`claude-opus-5.5`) call the
models through the GitHub Copilot SDK (`github-copilot-sdk==1.0.28`, runtime 1.0.105) instead of
a provider's HTTP API. CP-OS builds `CopilotAdapter` for these configurations and closes it
(runtime process and kept sessions) when the run ends.

## 1. Enterprise policy (an administrator does this once)

- AI controls -> Copilot -> Features & clients -> Configure features & clients -> Clients ->
  Copilot CLI: set it to **Enabled everywhere**, or **Let organizations decide** and enable it
  for the organization that holds your seat.
- Enable the two models at the enterprise level; the runtime lists only enabled models.
- Get compliance sign-off first: every prompt carries issuer text (filings, covenants, figures)
  that leaves this machine for GitHub and the model vendor.

## 2. This machine

```
uv sync --locked
uv run python -m copilot download-runtime
```

The second command is run once. It prints the cached runtime path; set `COPILOT_CLI_PATH` to the
runtime executable it prints (on Windows, the `.exe`). Set `COPILOT_GITHUB_TOKEN` from a
fine-grained token for your seat, in the launching environment only (no credential file). The CLI
login is never used (`use_logged_in_user=False`), so a logged-in `gh` or Copilot CLI does nothing here.

## 3. The ruling

Live runs stay refused until a ruling file under `docs/rulings/` names the configuration. Write
the file yourself, with these lines:

```
lifts: live-provider-pause
by: user
date: YYYY-MM-DD
configs: copilot-sol-medium copilot-opus-medium
```

## 4. Seat check (paid; run before the first real run)

```
uv run pytest tests/model/test_copilot_live.py -m live -q -s
```

It skips unless `COPILOT_GITHUB_TOKEN` and `COPILOT_CLI_PATH` are both set, and it never runs
in the normal suite or CI. It lists the models, runs one tool exchange through the real
adapter and prints each reply's `finishReason` and its `billed_usd` against the price of the
reply's own tokens (a unit error in the AI-unit conversion would be a 100x miss).

## 5. A run

```
uv run python -m deploy_workflow.owners.cpos_launch --context ... --sources ... \
  --config copilot-sol-medium --cap 50 --live --ruling docs/rulings/<file>.md
```

Without `--live` nothing is sent. The launcher reports `COPILOT_GITHUB_TOKEN` as the key variable.
Each exchange creates one working directory, `.copilot-home/<invocation>/<reservation>` (git-ignored),
at its first call, named after that call's reservation; later calls of the exchange reuse it.

## Session settings and exchange lifetime

- Each session is created with `large_output={"enabled": False}` and
  `infinite_sessions={"enabled": False}` (SDK 1.0.28 `create_session` options). The SDK defaults
  would replace a tool result over 50 KB with a temp-file reference the model cannot open (the
  session offers only `custom:*` tools), and compact the context in the background with model
  calls whose charge is outside `assistant.usage`, so neither reserved nor settled.
- An exchange (one module, or one tool-loop step) holds one runtime process. It is released
  when the module or step ends (`CopilotAdapter.end_exchange`, called by the handoff executor
  and the tool loop), when a call fails or is refused, and at the latest by `close()`.
- A release detaches the session and stops the runtime first, and only then cancels the tool
  handlers still waiting, so no cancelled handler can turn into a tool failure the runtime
  answers with a further, unrecorded model call. (With SDK 1.0.28 a cancelled handler raises
  `CancelledError`, which the SDK's `except Exception` does not turn into an error result
  either.) `close()` force-stops every runtime whose release has not finished concurrently.
- A failed call is not retried: it ends its exchange (the turn is aborted), and the session
  cannot take the same request again. `CopilotAdapter.resends` is False, so the tool loop stops
  on the call's own class (IdleTimeout, a 5xx `session.error`) with the hold counted as unknown,
  instead of spending the run's one retry on a call that could only be refused.
- A later call of an exchange that asks for another reasoning effort than the session was
  created with is refused before anything is sent (`EffortMismatch`).
- A reply whose usage event carries `copilotUsage.totalNanoAiu` settles from that charge even
  when the reply is refused for its shape (`UnparsableReply`), a `session.error` or a timeout
  reports no token counts.

## Not verified

- The pinned model ids `gpt-6.1-sol` and `claude-opus-5.5` on a real seat.
- `numToolCalls` and the event order on a real seat.
- `copilotUsage.totalNanoAiu` is present, and 1 AI unit = $0.01 holds.
- `max_output_tokens` is not enforceable on the runtime (holds cover it; the output is not capped).
- The Windows runtime path and whether the allowlisted environment is enough there.
- `stop()` and `force_stop()` timing on a real runtime.
- The runtime dispatches a turn's custom tool calls concurrently (the seat check now exercises two calls in one turn).
- That `large_output` and `infinite_sessions` set to disabled are honoured by runtime 1.0.105
  (the options are sent; their runtime effect is from the SDK docstrings, not observed).
