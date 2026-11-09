# Enterprise initialisation prompt

Paste everything below the line into a new Claude Code session opened in this repository inside
the enterprise environment. Before pasting, set the placeholders marked `<...>` and export the
credentials in the launching shell (never in a file).

---

## Task

Make Final Workflow run live in this enterprise environment, then prove it with complete live
test and repair runs. Read `AGENTS.md`, `README.md`, `docs/COPILOT.md`, `docs/QUALITY-GATE.md`,
`METHODOLOGY-REVIEW.md` and the newest entries of `VERIFICATION.md` first. `AGENTS.md` governs;
this prompt only adds the enterprise-specific work and the authorisations below.

## Authorisations (the user's, given in this prompt)

1. **Adapt the code to the environment.** You may change production code, launchers, tests and
   docs wherever the enterprise environment requires it: outbound proxy and TLS inspection
   (corporate CA bundle), egress allowlists, Windows or Linux paths, the Copilot runtime
   location, model ids and availability on the seat, pricing/AI-unit conversion, read-only or
   locked-down file systems, and internal mirrors for packages. Make the smallest change each
   observed failure justifies, keep it behind the existing interfaces, and keep a failing
   before-state and a passing after-state for each change. Do not add a competing
   orchestration layer; CP-OS stays the orchestrator.
2. **Paid live execution is lifted** for configs `<copilot-sol-medium copilot-opus-medium>`,
   for the campaign in this prompt only. Write the ruling yourself under `docs/rulings/`
   (`lifts: live-provider-pause`, `by: user`, `date: <today>`, `configs: ...`) quoting this
   authorisation. Lift `web-retrieval` the same way for the web phase (Phase 6) and name the
   hosts it covers.
3. **Budget:** shared ceiling USD `<TOTAL_CAP>` across the campaign, per-run caps as given in
   each phase. Unknown charges stop execution. Never raise a cap without asking me.
4. **Commit and push** verified work to the branch `<branch>`. Do not open a pull request unless
   asked.

## Constraints that do not change

- No credential files. `COPILOT_GITHUB_TOKEN` (and `OPENAI_API_KEY` etc. if a direct provider
  is used) come only from the launching environment. Never print, log, commit or write a key;
  confirm `model/redact.py` covers any new variable you introduce.
- Web retrieval is **Option 1**: the app's own fetcher (`research/webfetch.py`, driven by
  `url` rows in the research manifest and a `web-retrieval` ruling) stays in charge. Do not
  enable model-side web tools. Fetched pages remain recorded in `research/fetches.json`.
- Offline readiness first; the build itself never runs providers. Do not generate Excel
  workbooks. Never mutate predecessor repositories or historical run directories; every live
  run gets a new `runs/<id>` folder and its retained requests, responses, repairs and costs
  are kept, failed attempts included.
- A live success means actual retained model responses plus downstream consumption by the next
  module and by delivery. Label every result with its true scope (live, retained replay,
  synthetic, historical/outdated issuer). Keep issuers/dates separate. Missing handoff content
  stays an explicit gap or a targeted repair request; delivery never invents analysis.
- Expected values for checks are independent of production calculations.

## Phase 0: Environment survey (no spend)

1. Record OS, Python (needs 3.13), `uv` (pinned 0.12.5), proxy variables, CA bundle, and which
   hosts are reachable: the Copilot/GitHub endpoints, the model vendor endpoints, the package
   index, and the issuer hosts planned for Phase 6. Test with real requests, not assumptions.
2. `uv sync --locked` (use `--offline` or an internal mirror if required). Run
   `uv run python -m copilot download-runtime`; if it is blocked, obtain the runtime through the
   sanctioned internal route and set `COPILOT_CLI_PATH`. Do not bypass TLS verification or
   disable the proxy.
3. Fix install/network problems per authorisation 1. Re-run until clean.

## Phase 1: Offline readiness (no spend)

1. `timeout 300` fast targeted tests: `tests/model`, `tests/research`, `tests/test_cpos_*.py`,
   `tests/test_run_*.py`. Keep provider keys unset. Any environment-caused failure is repaired
   (authorisation 1); anything else is reported, not "fixed" by skipping tests.
2. `uv run python tools/quality_gate.py` on everything you changed.
3. Dry-run the launcher (no `--live`) on a historical case and confirm it prepares the run,
   prints the plan and makes no provider call.

## Phase 2: Seat check (small spend)

Run `uv run pytest tests/model/test_copilot_live.py -m live -q -s` with the token and runtime
set. Verify and write into `VERIFICATION.md` each item `docs/COPILOT.md` lists as *Not
verified*: pinned model ids, `numToolCalls` and event order, `copilotUsage.totalNanoAiu`
presence and the 1 AI unit = USD 0.01 conversion (a 100x error here is the main risk), whether
`max_output_tokens` is enforceable, stop/force-stop timing, concurrent custom tool calls, and
the runtime path and allowlisted environment on this OS. Repair adapter, pricing or model-id
mismatches; update `docs/COPILOT.md` to what is now verified.

## Phase 3: Smoke run (cap USD `<~5>`)

Reproduce the historical TDG FY2024 CP-0, CP-1, CP-1A live test through the launcher, as the
README describes (`tests/test_cpos_launch.py -m live` with `CPOS_LIVE_RULING`), on the Copilot
config in a new run folder. Compare the result with the retained `runs/cpos-launch-live-002`
reference in scope only (do not copy it). Review the actual answers against the filing.
Label it outdated historical evidence.

## Phase 4: Module-by-module live tests (cap USD `<per-module>`)

For each analytical module in the pathway preset, one at a time and in dependency order:

1. Launch it live with `--modules` narrowed to that module (dependencies kept), new run folder.
2. Compare the actual model output with the instructions sent and the issuer evidence: exact
   amounts, units, periods, currency, source references, missing versus zero, calculations.
3. If it fails, classify the cause (instruction, model answer, source access, calculation,
   handoff, or environment). Preserve the failed answer. Make the smallest justified change.
   Re-run only the affected module in a new run folder. Maximum **3 repair cycles per module**
   and the in-loop bounded repair of three drafts; after that, stop and report with evidence.
4. Where the current issuer lacks access, use an alternative issuer or an older source, labeled
   as outdated, kept separate by issuer/date. Do not let one unavailable input block other
   modules, and do not present an isolated case as a complete pathway.
5. Run confidence-review and rewrite-tournament (post-edit) on any non-trivial change, then the
   quality gate, before moving on.

## Phase 5: End-to-end pathway run (cap USD `<per-pathway>`)

1. Launch the full pathway through CP-OS from a context file and issuer folder, live, with
   delivery. Use a current issuer if the environment can supply the files, otherwise a
   historical one, labeled.
2. Completion requires populated final deliverables (report, HTML Model, charts, calculation
   JSON as applicable; CP-8 comparison against prior-run deliverables) constructed from the
   actual module handoffs and checked against them. Handoff generation alone is not completion.
3. Interrupt one run deliberately mid-pathway (after a module settles, before the next) and
   resume it in the same folder: confirm finished modules are rechecked, not resent, that
   retries stay bounded, and that a module interrupted mid-call is handled per the README
   (new run folder, never silently resent).
4. Repair observed failures as in Phase 4, then re-run the affected stage end to end.

## Phase 6: Live web retrieval (cap USD `<per-run>`)

1. Add `url` rows for a small set of public issuer pages to a research manifest; list the hosts
   and get them allowlisted on the enterprise egress. Write the `web-retrieval` ruling.
2. `webfetch.py` opens its own pinned TLS connections with `socket.create_connection`. If the
   enterprise requires an HTTP proxy or a corporate CA, adapt the fetcher (authorisation 1)
   **without weakening** its protections: manifest-host pinning, URL refusal rules,
   redirect checks, byte and time caps, IDNA handling, and the recorded fetch record. Run
   `tests/research` before and after; add a test for the proxy/CA path.
3. Run live: confirm the pages are fetched by the app, recorded in `research/fetches.json`,
   handed to the models as evidence, cited by source in the handoffs, and refused on resume if
   a page or the ruling changes. Test an adversarial case (redirect to a non-manifest host,
   oversized body, blocked host) and show it is refused.

## Phase 7: Close-out

1. Run `uv run python tools/quality_gate.py`; confirm the fast tests pass.
2. One concise entry in `VERIFICATION.md` (move entries older than two days to
   `docs/VERIFICATION-ARCHIVE.md`; keep the file under 1,000 lines): environment, config and
   seat, every run folder with its scope label, cost against each cap, repairs made and why,
   what each result proves and does not prove, and anything still unverified.
3. Update `README.md` and `docs/COPILOT.md` with the enterprise setup that actually worked
   (proxy, CA, runtime path, egress hosts).
4. Commit with clear messages and push to `<branch>`.

## Stop and ask me when

- A cap would be exceeded, a charge is unknown, or a cost differs from the AI-unit conversion
  by more than rounding.
- The only fix would weaken a security protection (TLS verification, host pinning, redaction)
  or needs a credential file.
- Compliance or policy blocks the Copilot runtime, the models, or an issuer host and the only
  route is outside this authorisation.
- Three repair cycles on one module have not resolved it.

## Final report format

State plainly, per phase: what ran, run folders and scope labels, cost, pass/fail with the
evidence, code changes made for the environment and why, and what remains unproven. Do not
describe a synthetic or replay result as a live success.
