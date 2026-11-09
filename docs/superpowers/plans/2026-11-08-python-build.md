# Credit OS in Python: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** make `Final-workflow-PY` the only Final Workflow product. It runs as Credit OS on colleagues' Windows work PCs from a network drive. Colleagues' runs execute on the owner's PC through the owner's Copilot seat.

**Architecture:** the plan works through phases 0, 1, B, 2, B5 and 3, spread across sub-sessions. Each sub-session owns a set of files on its own worktree and branch and runs subagent-driven development on its tasks. A **lead session coordinates**: it starts the sub-sessions, keeps the shared names, sets the merge order, relays the owner's go-aheads and keeps the record, and it writes no code. The server is the existing FastAPI/uvicorn app in `src/issuer_library`. The shared workspace is a folder on an SMB share, and coordination is by exclusive-create files.

**Tech Stack:** Python 3.13 (company Python 3.13.16 on work PCs), FastAPI 0.162.0, uvicorn 0.54.0, pydantic 2.14.1, github-copilot-sdk 1.0.28; pytest, Playwright (Chromium); `uv` 0.12.5.

**Spec:** [`docs/superpowers/specs/2026-11-08-python-build-design.md`](../specs/2026-11-08-python-build-design.md), approved by the owner on 2026-11-08. Executors read both documents. Where this plan says §N, it means a section of the spec.

## Global Constraints

- No Go and no Node work. `final-workflow` is frozen; it changes only by its README notice (Task 1.9), and the owner archives it.
- Only reusable code is taken from final-workflow; nothing is git-merged **(owner)**. Copies are byte-identical to a pinned commit, recorded in `tools/copied-from.txt`.
- Each PR has at most 800 changed lines, excluding lockfiles, fixtures and byte-identical copies. Fixtures are files under `tests/fixtures/`, `cases/`, `apps/issuer-library/web/testdata/`, and `apps/issuer-library/designs/*-answer-key.json`. `tools/pr_size.py` measures it.
- The app's visible name is **Credit OS**; "Library" stays the name of the screen that lists reports. Code folders `apps/issuer-library` and `src/issuer_library`, and the existing per-user settings folder, keep their names.
- Work-PC runtime: `C:\Program Files\Statestreet\Python313\pythonw.exe` with `-I -B -X utf8`. The package holds no `.exe`. The python.org embeddable runtime and the arm64 build are dropped.
- The shared workspace is on a network drive and addressed by its UNC path only. It is never inside the repository, and nothing from it is committed.
- Provider keys come only from the launching environment. The owner's runner reads `COPILOT_GITHUB_TOKEN` and `COPILOT_CLI_PATH`. No key reaches a colleague's PC.
- Paid runs happen only at named checkpoints, each with the owner's go-ahead stating config, modules and cap. There is no automatic paid retry. The Beta live checks use `sol-medium` **(owner)**. Colleagues' queued jobs accept only `copilot-*` configs **(owner)**.
- There is no overall spend limit **(owner)**; each job keeps its own USD `cap_usd`.
- Expected values are written by someone other than the code's author, before the code. A Go or Node test at the pinned commit is an answer key; its port keeps every expected value.
- Repo `AGENTS.md` (with the final-workflow lines added by Task 1.2) governs reviews and gates: `tools/quality_gate.py`, confidence-review, rewrite-tournament, one `VERIFICATION.md`. Never mutate historical live run directories.
- Every task brief and reviewer prompt includes these rules: no stub or fake value standing in for real behaviour; no catch-all that hides a failure unless the fail-open is documented and logged; the answer key is not edited by the implementer; every report ends with a `Not verified:` line.

## Review Focus

1. **A colleague's clock is off by a minute or two.** Expected: the runner shows as online as long as `runner.json` was written within 90 s, and a timestamp up to 300 s in the future also counts as fresh, not offline. Test in Task 3.1.
2. **A network blip leaves a half-written `start.claim`.** Expected: the runner refuses that job with a plain status, makes no provider call, and keeps serving the rest of the queue. Test in Task 3.2.
3. **The share is full or read-only when a colleague presses Start.** Expected: a plain error; no `start.claim` is left behind, so nothing is queued half-way. Test in Task 3.1.
4. **A job queued from an older Credit OS version is still waiting when the owner updates the runner.** Expected: the runner refuses it with "This run was queued from Credit OS <old>; review it again." rather than a misleading "inputs changed". Test in Task 3.2.
5. **A long UNC workspace path plus a long issuer name exceeds 259 characters.** Expected: the existing refusal fires on the runner before any spend, and the colleague sees it in the job's status. Test in Task 3.2.

---

## Sessions and coordination

### The lead session

- Starts each sub-session with a short brief: the task numbers it owns, the paths of this plan and the spec, its file ownership, and its base branch.
- Keeps **Shared names** (below). A sub-session that needs to change one asks the lead first, and the change lands in this plan before it lands in code.
- Sets the merge order, opens nothing itself, and merges only with the owner's word.
- Asks the owner each **Owner decision pending** question (below) when the task that needs it starts.
- Relays each paid go-ahead, quoting the owner's words.
- Writes the one `VERIFICATION.md` entry per phase checkpoint, keeps the ledger line per task (`agent=<name> fix-rounds=<n> gates-first-pass=<y|n|n/a>`), and runs the whole-branch review per sub-session branch (`mx-architect`, then `confidence-review` and `rewrite-tournament` on the branch diff).
- Writes no code (global rules §1).

### Sub-sessions

Every sub-session runs in its own worktree (`use_worktree: true`). It runs `superpowers:subagent-driven-development` on its tasks:
- The implementer is `mx-feature`, or `mx-scaffold` for mechanical, fully specified tasks.
- The per-task reviewer is `mx-precise`; `mx-adversary` also reviews tasks marked **sensitive**.
- A task gets at most two Sonnet fix rounds, then `mx-autonomous` writes a plan for a fresh `mx-feature`.

Each sub-session opens one PR per task group shown below, at most 800 lines each, and reports to the lead.

| Session | Phase | Tasks | Owns (only these files change) | Starts after | Runs alongside |
|---|---|---|---|---|---|
| S0 Network check | 0 | 0.1 | `apps/issuer-library/packaging/network_check.py` | plan approval | S1 |
| S1 Import | 1 | 1.1–1.3 | `tools/pr_size.py`, `tools/copied-from.txt`, every copied path, the both-side files, `AGENTS.md`, `.github/workflows/` | plan approval | S0 |
| S2 Launch and quit | 1 | 1.4 (**sensitive**) | `src/issuer_library/__main__.py`, `desktop.py`, new `launch.py`, new `quit.py`; the middleware class in `server.py` | S1's PRs merged | S3–S6 |
| S3 Runs | 1 | 1.5 (**sensitive**) | `src/issuer_library/jobs.py`, new `events.py`, new `notify.py` | S1 merged | S2, S4–S6 |
| S4 Library and store | 1 | 1.6 (**sensitive**) | `src/issuer_library/discovery.py`, `model.py`, `settings.py`; `Application` store and report methods in `server.py` | S1 merged | S2, S3, S5, S6 |
| S5 Browser suites | 1 | 1.7 | new `tests/test_issuer_library_*` browser files; `tests/issuer_library_browser.py` | S1 merged | S2–S4, S6 |
| S6 Carry-over | 1 | 1.8 | the carry-over branches' non-Go files; their ported tests | S1 merged; Plan 4 admission cases pass only after S4 | S2–S5 |
| S7 Name and freeze | 1 | 1.9, 1.10 | visible-name strings; final-workflow `README.md` | S2–S6 merged | — |
| SB2, SB3, SB4 | B | B.1–B.3 | per Beta plan, from its own Files lines | Phase 1 done | each other per their dependencies; S8 |
| S8 Package | 2 | 2.1–2.3 | `apps/issuer-library/packaging/*`, `settings.py` default-workspace source | Phase 1 done and Task 0.1 result in | SB2–SB4 |
| SB5 Release gate | B5 | B.4 | none (owner run) | SB2–SB4 and S8 merged | — |
| S9 Runner | 3 | 3.1, 3.2 (**sensitive**) | new `src/issuer_library/shared.py`, new `runner.py`; the shared-workspace branch in `jobs.py`; runner fields in `settings.py` | B.4 passed | S10 |
| S10 Queue screens and guide | 3 | 3.3, 3.4 | `apps/issuer-library/web/actions.js`, `views.js`, `screen.css`, `index.html`; `apps/issuer-library/COLLEAGUES.md` | B.4 passed | S9 |

`server.py` is touched by S2 (middleware), S3 (new routes), S4 (store) and S9 (new routes). Each touches only its named part. The later PR rebases on the earlier one, and the lead sets the order: S4, then S2, then S3.

Phase 2 may run alongside Phase B because their files are separate. Nothing reaches colleagues before Phase 3 **(owner: Beta before colleagues)**.

### Shared names

- `tools/copied-from.txt`: first line `source <40-hex final-workflow sha>`, then one repo-relative path per line, for files copied byte-identical.
- `src/issuer_library/version.py`: `def app_version() -> str`. It returns the text of the `VERSION` file beside the package root when present (written by the build as `<YYYY.MM.DD>-<12-hex sha>`), otherwise `"dev"`.
- `Application` run state (`src/issuer_library/server.py`, Tasks 1.4 and 1.5): `reviews: int` counts reviews in flight and changes only under `Application.lock` (S3's review path increments and decrements it; S2's quit reads it for "busy"; S3's workspace switch refuses while it is above 0). `quitting: bool` is set by S2's quit once the shutdown guard is claimed; S3's review and start paths refuse with 503 while it is true. (Added 2026-11-09, lead.)
- `Application.refreshing: threading.Lock` (Task 1.4): held for the whole of a discovery, in the periodic refresh and in the settings switch's discovery; quit acquires it to wait for a discovery in progress. S4 keeps it when it restructures discovery. (Added 2026-11-09, lead.)
- Launch session (Task 1.4): the session cookie is named `issuer-library-<port>`, as the Go answer key pins it; a port-free name such as `fw_session` would let one instance's cookie name serve another port's. (Ruling accepted by the lead, 2026-11-09.)
- **Shared-workspace files** (§7.2):
  - `shared.json` is `{"unc": "\\\\server\\share\\CreditOS\\workspace"}`.
  - `runner.json` holds the `Beat` fields below.
  - `intake/<id>/start.claim` is `{"requested_by": str, "requested_at": "<UTC ISO-8601, seconds, Z>", "review_id": str, "accepted": [str], "version": str}`.
  - `intake/<id>/taken` is `{"by": "runner" | "withdrawn", "who": str, "at": "<UTC ISO>"}`.
- **`src/issuer_library/shared.py`** (Task 3.1):
  - Constants: `MARKER = "shared.json"`, `HEARTBEAT = "runner.json"`, `STALE_AFTER = 90` and `FUTURE_TOLERANCE = 300` (seconds).
  - `@dataclass(frozen=True) class Beat: runner_id: str; user: str; version: str; accepting: bool; provider_ready: bool; active_job: str; updated_at: str`
  - `@dataclass(frozen=True) class StartRequest: requested_by: str; requested_at: str; review_id: str; accepted: tuple[str, ...]; version: str`
  - `def shared_unc(workspace: Path) -> str | None`
  - `def check_address(workspace: str, unc: str) -> None` raises `ValueError`.
  - `def write_beat(workspace: Path, beat: Beat) -> None`
  - `def read_beat(workspace: Path, now: datetime) -> Beat | None`
  - `def start_gate(beat: Beat | None, version: str) -> str`
  - `def request_start(folder: Path, request: StartRequest) -> None`
  - `def withdraw(folder: Path, who: str, now: datetime) -> bool`
  - `def take(folder: Path, runner_id: str, now: datetime) -> bool`
  - `def queued(workspace: Path) -> list[Path]`
  - `def queue_position(workspace: Path, job_id: str) -> int | None`
- **`src/issuer_library/runner.py`** (Task 3.2):
  - `def validate_intake(folder: Path, runner_version: str) -> str` returns `""` or a refusal message.
  - `class Runner` with `__init__(self, lib: Application, runner_id: str)`, `tick(self, now: datetime) -> None`, `enable(self, now: datetime) -> str` (`""` or a refusal message) and `run_forever(self, stop: threading.Event) -> None` (ticks every 15 s).
- **Settings** (`settings.Config`): `runner: bool = False`, `accept_colleague_jobs: bool = False` (Task 3.2), plus the default-workspace source (Task 2.2).
- **HTTP** (Tasks 3.2 and 3.3):
  - `GET /api/runner` returns `{"online": bool, "start_message": str, "accepting": bool, "version": str}`.
  - `POST /api/runs/withdraw` takes `{"id": str}` and returns 200 `{"state": "withdrawn"}` or 409 with a message.
  - `GET /api/runs/status` gains `"state": "queued"`, `"position": int` and `"requested_by": str`.

### Owner decisions pending (the lead asks each when its task starts)

1. Plan 3 Task 11b: where the pro forma tables appear in the report. The choices are (a) routes in `transaction-summary` on Primary runs (Plan 3's recommendation) or (c) kept out of the report as a known limitation (`plan-3-status.md`).
2. Plan 4 R-26: the fixed CP-1 chart-row format that the manifest writer selects from. Live CP-1 output shows the current rule selects nothing (`plan-4c-chart-row-evidence.md`).
3. Plan 4 Help wording (Task 14): a negative talk side is treated as missing; a quote with only bid or only ask has no price; runs tied on the latest reported date are all kept.
4. Each paid checkpoint: A-live, A-ab (optional), B-live, C1, C1n, C2, C1r, C3, RC-live (config `sol-medium`), and the Phase 3 real-share run (Copilot, cap named by the owner).
5. Phase 0: if the share check fails, whether to try the fallbacks in §6.4.

---

## Phase 0: network check

### Task 0.1: Network-path check package (S0)

**Files:**
- Create: `apps/issuer-library/packaging/network_check.py`
- Test: `tests/test_network_check.py`

**Interfaces:**
- Consumes: `download(url, sha, name)` and the PyPI wheel selection in `apps/issuer-library/packaging/runtime.py`.
- Produces: `artifacts/credit-os-network-check/` containing `lib/`, `check.py` and `Check.cmd`.

- [ ] **Step 1: Write the failing test.** `test_check_folder_has_no_executable_and_the_server_closure`: build into `tmp_path` with a fake `download` that returns local wheel zips. Assert:
  - no file ends in `.exe` or `.dll`;
  - `lib/pydantic_core/` exists;
  - `Check.cmd` contains `C:\Program Files\Statestreet\Python313\pythonw.exe` and ` -I -B -X utf8 `.
- [ ] **Step 2: Run** `uv run pytest tests/test_network_check.py -q`. Expected: FAIL (module missing).
- [ ] **Step 3: Implement** `build(target: Path) -> None` in `network_check.py`.
  - It unpacks the cp313 `win_amd64` / `none-any` wheels for `pydantic`, `pydantic-core`, `annotated-types`, `typing-extensions`, `typing-inspection`, `fastapi`, `starlette`, `annotated-doc`, `uvicorn`, `h11`, `click`, `anyio` and `idna`, at the `uv.lock` versions.
  - `check.py` inserts its own `lib` at `sys.path[0]`, imports `pydantic_core`, starts uvicorn on `127.0.0.1:0` with a one-route FastAPI app, and fetches `/health` with `urllib`.
  - It writes `%TEMP%\credit-os-network-check.txt` with: `pydantic_core.__file__`; import and first-response times in ms; `PASS` or the exception text.
- [ ] **Step 4: Run** the test. Expected: PASS. Then run `uv run python tools/quality_gate.py`. Expected: exit 0.
- [ ] **Step 5: Commit** `Phase 0: network-path check package for the work PC`.
- [ ] **Step 6 (owner, via the lead):**
  1. Build on the Mac with `uv run python apps/issuer-library/packaging/network_check.py artifacts/credit-os-network-check`.
  2. Copy the folder to the network drive, double-click `Check.cmd` on the work PC, and send the result file.
  3. The lead records the result in `VERIFICATION.md`.

  A `PASS` where `pydantic_core.__file__` starts with `\\` means Phase 2 follows §6.1 as designed. Anything else goes to Owner decision 5.

---

## Phase 1: catch-up and freeze

### Task 1.1: PR size and copy check (S1)

**Files:**
- Create: `tools/pr_size.py`, `tools/copied-from.txt` (empty until Task 1.2)
- Modify: `.gitignore` (add `.superpowers/`, the SDD stage folders)
- Test: `tests/test_pr_size.py`

**Interfaces:**
- Produces: `copied_mismatches(listing: Path, repo: Path) -> list[str]` (paths whose bytes differ from `git show <sha>:<path>`, or are missing) and `pr_lines(base: str, repo: Path) -> int`. Run as `python tools/pr_size.py --base origin/main`, which exits 1 if mismatches exist or the count exceeds 800.

- [ ] **Step 1: Write the failing tests** in a temporary git repo:
  - `test_identical_copy_is_not_counted`: a 900-line file listed and identical at the source sha gives `pr_lines == 0`, and the run exits 0.
  - `test_edited_copy_is_a_mismatch`: one changed byte puts the path in `copied_mismatches`, and the run exits 1.
  - `test_fixtures_and_lockfiles_are_not_counted`: changes under `tests/fixtures/`, `cases/`, `apps/issuer-library/web/testdata/`, `*-answer-key.json`, `uv.lock` give 0.
  - `test_801_counted_lines_fail`: exit 1.
- [ ] **Step 2: Run** `uv run pytest tests/test_pr_size.py -q`. Expected: FAIL.
- [ ] **Step 3: Implement** both functions with `subprocess` (`git diff --numstat <base>...HEAD`, `git show`). Standard library only.
- [ ] **Step 4: Run** the tests, then the quality gate. Expected: PASS, exit 0.
- [ ] **Step 5: Commit** `tools: PR size and copy check`.

### Task 1.2: Import final-workflow `main` (S1)

**Files:**
- Copy, byte-identical from pinned sha `<P>`:
  - every path that differs between `a313b50` and `<P>` and that this repo has not changed since `a313b50`;
  - every upstream rename and deletion (for example the PR 55 moves into `docs/archive/`, and `src/deploy_workflow/cpos_handoffs.py` deleted).
- Skip: `*.go`, `go.mod`, `*.cjs`, and Node-only tooling.
- Hand edit (counted): `AGENTS.md`, `pyproject.toml`, `uv.lock` (regenerated), `apps/issuer-library/validate.py`.
- Copy and then edit (counted for the edit only): `.github/workflows/quality-gate.yml`, `nightly-tests.yml`, `issuer-library-browser.yml`.

**Interfaces:**
- Consumes: `tools/pr_size.py`.
- Produces: `tools/copied-from.txt` with `source <P>`.

- [ ] **Step 1:** Pin `<P>` with `git fetch https://github.com/EricMG13/final-workflow main` and record the sha. Generate the path list with `comm -23 <(git diff --name-only a313b50 <P> | sort) <(git diff --name-only a313b50 HEAD | sort)`, minus the skipped patterns, and write it to `tools/copied-from.txt`.
- [ ] **Step 2:** Copy each listed path with `git checkout <P> -- <path>` and apply each upstream deletion and rename. Run `python tools/pr_size.py --base origin/main`. Expected: 0 mismatches.
- [ ] **Step 3:** Edit `AGENTS.md`: add final-workflow's three lines (quality gate, weekly full suite, `VERIFICATION.md` archive rule) verbatim, and repair the run-on line `retaining the simplest correct design.- Keep…`.
- [ ] **Step 4:** Edit `pyproject.toml`: keep the current pins and add any pin `<P>` added. Run `uv lock`, then `uv lock --check`. Expected: exit 0.
- [ ] **Step 5:** Edit `validate.py`:
  - keep the Python `quick`, `full` and `browser`;
  - add upstream's `suite` mode and new `PYTHON_TESTS` entries;
  - drop every `node` and `go` gate.
- [ ] **Step 6:** Edit the workflows: delete the `setup-go`, Go build and Node steps; keep the Python, Playwright and quality-gate steps.
- [ ] **Step 7: Run** `uv run python apps/issuer-library/validate.py quick` and `uv run python tools/quality_gate.py`. Expected: exit 0. Browser tests that fail because `web/` now expects server features not yet rebuilt are listed by name in the PR body as Phase 1 debt; nothing else may fail.
- [ ] **Step 8: Commit** `Import final-workflow <P>: reusable code, byte-identical`. Open PR 1-A.

### Task 1.3: Files changed on both sides (S1)

**Files (hand edits, counted):** `README.md`, `VERIFICATION.md` (take upstream's file and `docs/VERIFICATION-ARCHIVE.md`, then add this repo's Python-variant entries to the archive), `apps/issuer-library/README.md`, `examples/issuer-library/README.md`, `apps/issuer-library/designs/browser_check.py`, `designs/build.py`, `designs/fake_engine/bridge.py`, `apps/issuer-library/engine/store.py`.

Not ported: upstream changes to `packaging/runtime.py` and `smoke_test.py`, because Phase 2 replaces both.

- [ ] **Step 1:** For each file, apply `git diff a313b50 <P> -- <file>` onto this repo's version by hand. Keep the Python-server parts.
- [ ] **Step 2: Run** `uv run python apps/issuer-library/validate.py quick` and `uv run pytest tests/test_issuer_library_store.py -q`. Expected: exit 0, apart from the browser tests listed in PR 1-A. Run `python tools/pr_size.py --base origin/main`. Expected: at most 800, or split by file into PRs 1-B and 1-C.
- [ ] **Step 3: Commit** per file group. Open the PR(s).

### Task 1.4: Launch ticket, session, same-site, relaunch and quit (S2, **sensitive**)

**Files:**
- Create: `src/issuer_library/launch.py`, `src/issuer_library/quit.py`
- Modify: `src/issuer_library/__main__.py`, `desktop.py`, the middleware in `server.py`; in `server.py` also the `Application.__init__` lines declaring `session`, `reviews`, `quitting` and `refreshing`, `refreshing` taken around the existing discovery calls, and `Application.quit` answering 409 while `reviews > 0`; `client_of` in `tests/issuer_library_support.py` (sends the session cookie)
- Test: `tests/test_issuer_library_launch.py`, `tests/test_issuer_library_quit.py`

**Answer key:** these Go tests at `<P>`, each ported case for case with every expected value kept:
- `launch_test.go`: `TestEveryAppRequestNeedsTheSessionCookie`, `TestHeadRequestsOverLoopback`, `TestLaunchTicketIsExchangedOnceAndTheRedirectDropsIt`, `TestNoBrowserLaunchPrintsTheLinkOnStandardOutputOnly`, `TestOnlySameOriginOrUserInitiatedRequestsAreServed`, `TestRequestsWithoutThisLaunchsSessionAreRefused`, `TestSecretComparisonsAreConstantTime`, `TestTamperedTicketsAreRefusedWithoutSpendingTheRealOne`, `TestTheLaunchTicketExpires120SecondsAfterStart`, `TestTheSecretsAppearOnlyInTheCookie`.
- `launch_review_test.go`: `TestReviewConcurrentLaunchSpendsOnce`, `TestReviewGateCoversMethodsAndPaths`.
- `quit_test.go`: `TestAQuitRequestWaitsForADiscoveryInProgress`, `TestARelaunchThatGetsNoAnswerWithdrawsItsRequest`, `TestAStateFolderOtherUsersCanWriteIsRefused`, `TestOnlyAFreshWellFormedBusyAnswerIsShown`, `TestQuitClaimsTheShutdownGuardBeforeAStartCanBegin`, `TestQuitRequestIsAnsweredBusyWhileAReviewOrRunIsInFlight`, `TestRelaunchAsksAnIdleLibraryToQuitAndOpensAFreshLink`, `TestRelaunchIsToldARunKeepsTheLibraryBusy`, `TestRelaunchSidePlantedAnswersAndLinks`, `TestStaleOrInvalidQuitRequestsAreRemovedUnread`, `TestStartRacingAQuitRequestNeverOrphansAWorker`, `TestTheQuitRequestIsOwnerOnlyAndNamesOnlyTheProcess`, `TestTwoRelaunchesAtOnce`, `TestWindowsAccessListJudgement`.
- `go124_test.go`: `TestMkdirAllInCreatesNestedAndAcceptsExisting`, `TestMkdirAllInRefusesFilesAndEscapes`.
- Also every Go test in these files whose body changed between `a313b50` and `<P>` (`git diff a313b50 <P> -- apps/issuer-library/launch_test.go apps/issuer-library/quit_test.go`).

**Interfaces:**
- Produces:
  - `launch.Session(ticket_ttl: float = 120.0)` with `ticket() -> str`, `exchange(ticket: str) -> str | None` (returns the cookie value once), `valid(cookie: str) -> bool` (constant-time); created in `Application.__init__` after the first discovery, so the 120 s count from when the library is ready;
  - the cookie name `issuer-library-<port>` (Shared names);
  - `quit.ask_to_quit(state: Path, port: int) -> socket.socket`: the port's socket once the running instance has quit, otherwise an error carrying the Go key's busy or already-running text (the plan's earlier `request_quit(...) -> Literal[...]` could carry neither the busy counts nor the port; ruling accepted by the lead, 2026-11-09);
  - `Application.reviews`, `Application.quitting`, `Application.refreshing` (Shared names).
- Not applicable to S2: `go124_test.go`'s `mkdirAllIn` cases (a Go 1.24 stand-in for `os.Root.MkdirAll`, used by intake staging in `jobs.py`; S3 ports them if its staging needs the helper).
- Deferred to Task 1.5: ported cases that need S3's 503 guards in `review_run`/`start_run` or its A07 job adoption are marked `pytest.mark.skip(reason="deferred: needs Task 1.5 <guard|A07>; the later of 1-D2 and S3's PR un-skips")`; whichever of 1-D2 and S3's PR merges second un-skips them, and they pass there.
- `designs/browser_check.py` and `packaging/smoke_test.py` fetch a launch ticket (S2, after S1's PR 1-B brings its versions of both files).

- [ ] **Step 1:** Port the listed cases into the two test files. A case that cannot apply to the Python design (for example Go-only lock ordering) becomes `pytest.mark.skip(reason="not applicable: <why>")`, and the reason is copied into the PR body.
- [ ] **Step 2: Run** `uv run pytest tests/test_issuer_library_launch.py tests/test_issuer_library_quit.py -q`. Expected: the failures are the not-yet-built behaviour.
- [ ] **Step 3: Implement** until the ported cases pass. Use `secrets.compare_digest` for every secret comparison and `os.open(..., O_CREAT|O_EXCL)` for request files. On Windows, the state-folder check uses `icacls` output, as the Go `TestWindowsAccessListJudgement` table pins.
- [ ] **Step 4: Run** the two files, `tests/test_issuer_library_server.py`, the quality gate and `validate.py quick`. Expected: exit 0.
- [ ] **Step 5: Commit** per behaviour (ticket and session; same-site; relaunch and quit). Open PR 1-D.

### Task 1.5: Runs, events, resume, restart and notices (S3, **sensitive**)

**Files:**
- Create: `src/issuer_library/events.py` (event log to progress and JSON), `src/issuer_library/notify.py` (Windows notice)
- Modify: `src/issuer_library/jobs.py`; route lines in `server.py`
- Test: `tests/test_issuer_library_jobs.py`, new `tests/test_issuer_library_notify.py`

**Answer key:** at `<P>`:
- `jobs_test.go`: the 49 tests added since `a313b50` (list them with `comm -13` over `^func Test` names at `a313b50` and `<P>`), from `TestAFinishedRunNotifiesNativelyOnlyWhenNoTabWatches` through `TestWorkspaceSwitchIsRefusedWhileAReviewIsInFlight`, plus the tests whose bodies changed.
- `notify_test.go`: `TestFinishNoticeNamesTheStopReason`, `TestFinishNoticeTextUsesIssuerAndState`, `TestTabWatchingWaitsForAPollAfterTheFinish`, `TestToastEnvKeepsOnlyTheAllowedNames`, `TestToastScriptIsFixedAndReadsOnlyTheTwoVariables`.
- `main_test.go`: `TestRunRecordsItsErrorInTheLogBeforeClosingIt`.

**Interfaces:**
- Produces:
  - `GET /api/runs/events?id=<job>` returns `{"events": [...], "complete": bool}`;
  - `POST /api/runs/resume` takes `{"id": str}` and returns 200 with the new job's review payload;
  - `events.progress(folder: Path) -> dict | None`;
  - `notify.finish_notice(job: dict) -> tuple[str, str]` (title, body);
  - `notify.toast(title: str, body: str) -> None` (a no-op off Windows, logged).
- The resume cap comes from the stopped run's recorded `cap_usd`.

- [ ] **Step 1:** Port the listed cases. Not-applicable cases are handled as in Task 1.4.
- [ ] **Step 2: Run** `uv run pytest tests/test_issuer_library_jobs.py tests/test_issuer_library_notify.py -q`. Expected: the failures are the missing behaviour.
- [ ] **Step 3: Implement** until they pass. The notifier's child process gets only the two variables `TestToastEnvKeepsOnlyTheAllowedNames` allows; it never gets a provider key.
- [ ] **Step 4: Run** those files, the quality gate and `validate.py quick`. Expected: exit 0.
- [ ] **Step 5: Commit** per behaviour (events; resume; restart settle/adopt and start claim; review bounds and workspace switch; notices). Open PRs 1-E and 1-F, each at most 800 lines.

### Task 1.6: Library, store and report serving (S4, **sensitive**)

**Files:**
- Modify: `src/issuer_library/discovery.py`, `model.py`, `settings.py`; the `Application` store, report and catalogue methods in `server.py`
- Test: `tests/test_issuer_library_discovery.py`, `tests/test_issuer_library_server.py`, `tests/test_issuer_library_store.py`

**Answer key:** at `<P>`:
- `server_test.go`: `TestAFailedStoreIsNotCached`, `TestCatalogueRebuildAloneDoesNotRerunTheStore`, `TestConcurrentWorkspaceReadsShareOneStore`, `TestEmbeddedModelKeepsItsBytesAndSandbox`, `TestRefreshClearsTheWorkspaceCache`, `TestRefreshDiscoversWithoutHoldingTheCatalogueLock`, `TestReportPresentationSplicesBeforeTheFinalBodyTagInTheOriginalBytes`, `TestReviewEmbeddedGlyphReportOverHTTP`, `TestReviewLastBodyCloseBoundaries`, `TestReviewLastBodyCloseMatchesAnASCIILoweredOracle`, `TestSettingsAcceptOneLeadingByteOrderMark`, `TestStalledClientDoesNotHoldTheCatalogueLock`, `TestWorkspaceStoreRunsOnceUntilAFileChanges`, `TestWorkspaceSwitchDuringARefreshKeepsTheNewWorkspace`.
- `discovery_test.go`: `TestAPublishedModelAloneDoesNotRestoreARunsCompleteness`, `TestChangedModelMakesItsDeliveryUnavailable`, `TestDeclaredRunDeliveryIsListedOnce`, `TestDeliveryWithNeitherPageKeepsItsIssue`, `TestForeignRunDeliveryDoesNotSatisfyTheDeliveryCheckpoint`, `TestMetricMustBeAWholeNumberOfTheQuoteWithItsSignAndScale`, `TestModelDeliveryVerifiesAsAModelAndAReportKeepsItsKind`, `TestReviewRunDeliveryIdentityAdversarial`, `TestRunInternalDeliveryAcceptsTheLauncherRecordedIdentityOnly`, `TestRunInternalDeliveryMustMatchItsRunAndIssuer`, `TestSeedMetricsAllStated`, `TestStatedNumbersAdversarial`.
- Also the tests whose bodies changed in both files.
- Then the Plan 4 admission tests from `claude/plan-4c-library-manifest` @ `d877d8ce`: `TestManifestAcceptCases`, `TestManifestAdmitsAnswerKey`, `TestManifestOmittedFacilityCollectionsServedEmpty`, `TestManifestRejectCases`, `TestManifestTermErrorNamesSortedFirstKey`, `TestWriterKeyIsAdmittedWithItsChecklist`. These run against the answer keys that Task 1.8 copies, so this part starts after Task 1.8's Plan 4 PR.

**Interfaces:**
- Produces: the Forecast tab's data served at the path `<P>`'s `web/` requests (read in `web/actions.js` at `<P>`); `library.json` admission of `run.classification`, `run.private_side` and `run.facilities` (Shared names in `2026-11-08-run-expectations.md`).

- [ ] **Step 1:** Port the listed cases. Not-applicable cases are handled as in Task 1.4.
- [ ] **Step 2: Run** the three test files. Expected: the failures are the missing behaviour.
- [ ] **Step 3: Implement** until they pass. Reads stay bounded and refuse links (`O_NOFOLLOW` where the platform has it, otherwise a `lstat` check). No response is written while the catalogue lock is held.
- [ ] **Step 4: Run** the files, the quality gate and `validate.py quick`. Expected: exit 0.
- [ ] **Step 5: Commit**. Open PRs 1-G (store and report) and 1-H (discovery and admission).

### Task 1.7: Browser suites (S5)

**Files:**
- Create one test file per Node suite: `tests/test_issuer_library_workspace.py` (`library-workspace`), `_run_watch.py`, `_new_run.py` (extend the existing `test_issuer_library_app.py::NewRun` where it already covers a case), `_screening.py` (`screening` + `screening-dom`), `_run_activity.py`, `_context_embed.py`, `_escape_sinks.py`, `_draft_guard.py`, `_run_spend.py`.
- Extend: `test_issuer_library_screens.py` (`screens`), `test_issuer_library_css.py` (`screen-css`), `test_issuer_library_design.py` (`design`).
- Modify: `validate.py` `BROWSER_TESTS` and `PYTHON_TESTS`.

**Answer key:** the `test(...)` cases of each `*.test.cjs` at `<P>` (counts at `<P>`: library-workspace 32, run-watch 34, new-run 45, screens 40, design 94, screen-css 22, context-embed 21, run-activity 18, screening-dom 12, screening 5, escape-sinks 7, draft-guard 3, run-spend 3). Each case is ported with its expected values. A case already ported in this repo keeps its existing test.

**Interfaces:**
- Consumes: `tests/issuer_library_browser.py` (`open_app`, `Screen`, `serve`, `json_reply`, `held`, `until`).
- Method (as in `d9977b11`): the browser's own timers and layout replace jsdom stubs, and waits are for a condition, not a fixed time.

- [ ] **Step 1:** Port one suite per commit. After each, run `uv run pytest <file> -q -m browser`. Expected: PASS, or a failure naming a server feature from Tasks 1.4–1.6 (the lead tracks it until that task merges).
- [ ] **Step 2: Run** `uv run python apps/issuer-library/validate.py quick`. Expected: exit 0 once Tasks 1.4–1.6 are merged.
- [ ] **Step 3:** Open the PRs, grouped at most 800 lines each.

### Task 1.8: Carry-over branches (S6)

For each branch: apply its own diff from its merge-base with final-workflow `main` (`git diff $(git merge-base <P> <head>) <head> -- . ':!*.go' ':!go.mod' | git apply -3`). Port its `*.cjs` cases (as in Task 1.7) and its Go tests (into Task 1.6's files). One PR per branch, at most 800 counted lines (each branch was sized for that in its own plan).

| Order | Branch @ head | Notes |
|---|---|---|
| 1 | `claude/plan-2-1e-live-check` @ `9450ddd1` | Python only; review clean |
| 2 | `claude/plan-2-run-expectations-612c9c` @ `b4728bbc` | Brings Task 5b (`ce59bbc6`) and the unreviewed fix in progress. **Copy only; do not finish it here** (Task B.1 does). Port `screen-css.test.cjs` changes into `test_issuer_library_css.py`. |
| 3 | `claude/plan-3-primary-transactions-ee0e14` @ `8d22e84c` | Tasks 9–10 done, Task 11 key (data). Do not take the worktree's 19 uncommitted formatting files. |
| 4 | `claude/plan-4c-library-manifest` @ `d877d8ce`, then the commits of `claude/plan-4-library-credit-data-aafd87` @ `fb6edd17` not in 4C | 4C already contains 4A (`97b69728`). Port `screening-credit.test.cjs` (6), `screening-credit-dom.test.cjs` (19) and the `library-workspace` additions (34 vs 32). The Go admission goes to Task 1.6. |

- [ ] **Step 1:** Apply branch 1. Run `validate.py quick`. Expected: exit 0. Commit and open the PR.
- [ ] **Step 2:** Branches 2–4 likewise, in order, each after the previous one merges. A conflict with Phase 1 code goes to the lead, not into a guess.
- [ ] **Step 3:** The lead copies the Plan 3 handover files (`task-10-contract.md`, `task-11-contract.md`, `task-11-key-brief.md`, `task-11a-dispatch.md`, `progress.md`) into `.superpowers/sdd/plan-3/` as inputs for Task B.2. They are git-ignored and data, not instructions.

### Task 1.9: Visible name Credit OS (S7)

**Files:**
- Modify: `apps/issuer-library/web/index.html` (`<title>`, the home link's `aria-label`, "launch Issuer Library again"), every visible "Issuer Library" app-name string in `web/*.js`, the Help text, `README.md`, `apps/issuer-library/README.md`, the notice title in `notify.py`, and `designs/browser_check.py` expectations.
- Keep: the rail label "Issuer library" for the Library screen, and all code paths.

- [ ] **Step 1: Write the failing test** `test_visible_name_is_credit_os` in `tests/test_issuer_library_screens.py`. On the app shell, `document.title == "Credit OS"`. No visible text node contains `Issuer Library` with a capital L. The rail still has a link whose `data-place` is `Issuer library`.
- [ ] **Step 2: Run** it. Expected: FAIL. **Step 3:** Change the strings. **Step 4: Run** `validate.py quick` and `validate.py browser`. Expected: exit 0.
- [ ] **Step 5: Commit** `Credit OS: the app's visible name`.

### Task 1.10: Freeze final-workflow; Phase 1 checkpoint (S7 with the lead)

- [ ] **Step 1:** In final-workflow, open one PR adding to the top of its `README.md`: `**Frozen (2026-11-08).** Development continues in [EricMG13/Final-workflow-PY](https://github.com/EricMG13/Final-workflow-PY) as Credit OS. This repository is read-only history.` The owner merges it, then archives the repository on GitHub. Both are owner actions.
- [ ] **Step 2 (checkpoint):** On `main`, run `validate.py full`, `validate.py browser`, `tools/quality_gate.py` and `validate.py suite`. Expected: exit 0; nothing fails outside `tests/nightly-known-failures.txt`. The lead writes the Phase 1 entry in `VERIFICATION.md`, including each not-applicable Go case and its reason.

---

## Phase B: Beta V1 in Python

The Beta plans arrive with Task 1.2 in `docs/superpowers/plans/2026-11-08-*.md`. Their shared rules, owner decisions and shared names stand. Each runs in its own sub-session as written, with these changes.

### Task B.0: Retarget the Beta plans' Go and Node lines (lead's docs batch, `mx-scaffold`)

**Files:** `docs/superpowers/plans/2026-11-08-plan-2-run-expectations.md`, `-plan-4-library-credit-data.md`, `-plan-5-beta-release.md`.

| Where | From | To |
|---|---|---|
| Plans 2 and 4, Tech Stack | "Go, plain browser JavaScript; jsdom test-only" | "FastAPI server (`src/issuer_library`), plain browser JavaScript; pytest and Playwright" |
| Plan 2 Task 1 Files | `web/context-embed.test.cjs` | `tests/test_issuer_library_context_embed.py` |
| Plan 2 Task 6 Files, "Go side" | `jobs.go`, `jobs_test.go` | `src/issuer_library/jobs.py`, `tests/test_issuer_library_jobs.py`; "server side" |
| Plan 2 Task 7 Files | `web/new-run.test.cjs` | `tests/test_issuer_library_new_run.py` |
| Plan 4 Facts and Task 12 | `model.go`, `discovery.go:45-130, 261-296`, `discovery_test.go` | `src/issuer_library/model.py`, `discovery.py` (the admission functions), `tests/test_issuer_library_discovery.py` |
| Plan 4 Validation | `test_logic.cjs`, `test_dom.cjs` | `tests/test_issuer_library_screening.py` |
| Plan 5 step 4 | "the packaged app on Windows: `Smoke-test.ps1`" | "the Phase 2 package on the network drive, started by `Credit OS.cmd` on the work PC: `Smoke-test.ps1`" |
| All four | "Issuer Library" as the app name | "Credit OS" |

- [ ] **Step 1:** Make the edits, then run `grep -n -E '\.go\b|\.cjs|\bGo\b|jsdom' docs/superpowers/plans/2026-11-08-plan-[245]*.md`. Expected: no output.
- [ ] **Step 2: Commit** `Beta plans: retarget Go and Node lines to the Python server and pytest`.

### Task B.1: Plan 2 remainder (SB2)

Plan 2 from Task 5b on:
1. Finish the 5b fix round for its 2 Important findings. Start by reviewing the copied WIP `b4728bbc`, then reach a scoped re-review.
2. Checkpoint A: A-live, and A-ab (optional), each on the owner's go-ahead.
3. Tasks 6–8; Task 6 is on the Python server.
4. Checkpoint B (B-live, on the owner's go-ahead).

**Done when:** Plan 2's "Done when" holds and its checkpoints are recorded.

### Task B.2: Plan 3 remainder (SB3; depends on Plan 2's `live_check --case`, already copied by Task 1.8)

Plan 3:
1. C1 and C1n (already approved; the lead confirms the build sha with the owner before each Start).
2. Task 11a from `.superpowers/sdd/plan-3/task-11a-dispatch.md` against the frozen 80-case key.
3. Task 11b after Owner decision 1.
4. C2, C1r, C3.

**Done when:** Plan 3's "Done when" holds.

### Task B.3: Plan 4 remainder (SB4; after Plan 2 Task 6 and Plan 3 C2)

Plan 4:
1. The 4C whole-branch review, on the copied code.
2. The `bridge.start` call and its integration test.
3. R-26 after Owner decision 2.
4. The pro forma keys.
5. Task 13's remaining parts and Task 14 (with Owner decision 3).
6. Checkpoint D and D-live.

**Done when:** Plan 4's "Done when" holds.

### Task B.4: Beta release gate (SB5, after B.1–B.3 and Phase 2)

Plan 5 as retargeted by Task B.0. Its step 4 runs on the Phase 2 package.

**Done when:** Plan 5's "Done when" holds, including the owner's sign-off.

---

## Phase 2: work-PC package

### Task 2.1: Package build on the company Python (S8)

**Files:**
- Modify: `apps/issuer-library/packaging/build.py`, `packaging/runtime.py`, `packaging/smoke_test.py`, `packaging/Smoke-test.ps1`
- Create: `apps/issuer-library/packaging/start.py` (copied into each release), `src/issuer_library/version.py`
- Test: `tests/test_packaging.py`

**Interfaces:**
- Produces: `build(target: Path) -> Path`, which returns the release folder `target/app/<version>/`. It writes:
  - `target/Credit OS.cmd`, holding exactly one line naming `<version>`;
  - `target/default-workspace.json.example`, holding `{"workspace": "\\\\server\\share\\CreditOS\\workspace"}`.
- Produces: `app_version() -> str` (Shared names).
- The wheel list comes from `uv export --no-dev --no-emit-project --format requirements-txt` (no hand-kept `PINS`). Each wheel is cp313 `win_amd64` or `none-any`, and its SHA-256 is checked against PyPI's digest and the export's hash.

- [ ] **Step 1: Write the failing tests:**
  - `test_package_holds_no_executable`: no `.exe` or `.dll` anywhere under `target`.
  - `test_launcher_runs_company_python_on_this_release`: `Credit OS.cmd` contains `"C:\Program Files\Statestreet\Python313\pythonw.exe" -I -B -X utf8 "%~dp0app\<version>\start.py"`, and has a plain message when that file is missing.
  - `test_release_has_sdk_and_server_closure`: `lib/copilot/`, `lib/pydantic_core/`, `lib/fastapi/` and `lib/uvicorn/` exist.
  - `test_version_is_stamped_and_read`: the `VERSION` text matches `^\d{4}\.\d{2}\.\d{2}-[0-9a-f]{12}$`, and `app_version()` run from the release returns it.
  - `test_start_py_runs_isolated`: run `start.py --version` with `-I` from the release (host Python stands in for the company Python). The output equals `VERSION`.
- [ ] **Step 2: Run** `uv run pytest tests/test_packaging.py -q`. Expected: FAIL.
- [ ] **Step 3: Implement.** `start.py` puts `<release>/lib` and `<release>/src` at the front of `sys.path`, then calls `issuer_library.__main__.main()` with `--defaults <package root>/default-workspace.json`. Remove the embeddable download, the `._pth` file and arm64.
- [ ] **Step 4: Run** the tests, the quality gate and `validate.py quick`. Expected: exit 0.
- [ ] **Step 5: Commit**. Open PR 2-A.

### Task 2.2: Default workspace from the package (S8)

**Files:**
- Modify: `src/issuer_library/settings.py` (`load_config`), `__main__.py` (`--defaults`)
- Test: `tests/test_issuer_library_settings.py`

**Interfaces:** `load_config(loc: Locations, defaults: Path | None = None) -> tuple[Config, bool]`. The order is: managed policy (locked), then the per-user file, then `defaults` (not locked), then `Documents/FinalWorkflow`.

- [ ] **Step 1: Write the failing tests:**
  - `test_package_default_used_only_without_user_setting`: with no user file, `config.workspace` is the defaults value and `locked is False`. With a user file, the user's value wins.
  - `test_package_default_must_be_absolute`: a relative path raises `ValueError` naming the file.
  - `test_policy_still_wins_and_locks`.
- [ ] **Step 2: Run.** Expected: FAIL. **Step 3:** Implement. **Step 4: Run** with the gate. Expected: exit 0.
- [ ] **Step 5: Commit**. Add to PR 2-A if it stays at most 800 lines, otherwise open PR 2-B.

### Task 2.3: Library fallback (S8; only if Task 0.1 did not show `PASS` from `\\`)

**Files:** `apps/issuer-library/packaging/start.py`; test `tests/test_packaging.py::test_blocked_extension_falls_back_to_local_copy`.

- [ ] **Step 1: Write the failing test.** Make importing `pydantic_core` from the release raise `ImportError` once. Then `start.py` copies `lib/` to `<LOCALAPPDATA>/CreditOS/<version>/lib`, imports from there, and the second start reuses the copy without copying again.
- [ ] **Step 2–4:** Implement, then run the test with the gate. Expected: exit 0.
- [ ] **Step 5 (owner, via the lead):** run `Check.cmd`'s equivalent on the fallback folder. If it is blocked too, stop: Owner decision 5.

---

## Phase 3: colleagues' runs on the owner's PC

### Task 3.1: Shared workspace files (S9, **sensitive**)

**Files:**
- Create: `src/issuer_library/shared.py`
- Test: `tests/test_issuer_library_shared.py`

**Interfaces:** the `shared.py` entries in Shared names.

- [ ] **Step 1: Write the failing tests.** Expected values are written by a separate key-writer agent before the code, in `tests/fixtures/shared/expected.json`:
  - `test_take_is_exclusive`: two `take()` calls on one folder; exactly one returns `True`.
  - `test_withdraw_and_take_race_has_one_winner`: `withdraw()` then `take()`; `take` returns `False`, and `taken` says `"by": "withdrawn"`.
  - `test_queued_oldest_first_ties_by_id`: three claims (`requested_at` t2, t1, t1) give the order [t1 lower id, t1 higher id, t2]. Folders with `taken` are excluded.
  - `test_beat_fresh_window` (Review Focus 1). With `updated_at = T`:
    - `now = T + 89 s` gives a `Beat`;
    - `now = T + 91 s` gives `None`;
    - `now = T − 299 s` (writer clock ahead) gives a `Beat`;
    - `now = T − 301 s` gives `None`;
    - a missing or malformed file gives `None`.
  - `test_start_gate_messages`, exact strings:
    - `None` gives `"The runner is offline. You can still review runs and read reports; Start comes back when the runner is online."`;
    - `accepting=False` gives `"Colleague runs are switched off on the runner."`;
    - `provider_ready=False` gives `"The runner cannot reach its model provider right now."`;
    - version `"a"` versus `"b"` gives `"Restart Credit OS to update (runner a, yours b)."`;
    - all good gives `""`.
  - `test_request_start_on_unwritable_share_leaves_no_claim` (Review Focus 3): when the status write raises `OSError`, `start.claim` does not exist afterwards and the error propagates.
  - `test_drive_letter_refused`: `check_address("Z:\\CreditOS\\workspace", "\\\\srv\\share\\CreditOS\\workspace")` raises `ValueError` whose text contains the UNC path. A case-only difference in the UNC path passes.
  - `test_queue_position`: 1-based position among `queued()`, and `None` once taken.
- [ ] **Step 2: Run** `uv run pytest tests/test_issuer_library_shared.py -q`. Expected: FAIL.
- [ ] **Step 3: Implement.** Use exclusive create via `os.open(path, O_CREAT|O_EXCL|O_WRONLY)` and atomic replace via the existing `settings.save_json`. Timestamps are UTC with a `Z` suffix. `requested_by` comes from `os.environ.get("USERNAME") or getpass.getuser()`. Before `taken` exists, only the requester writes in the folder; `request_start` may remove its own `start.claim` on failure (§7.2).
- [ ] **Step 4: Run** the tests and the gate. Expected: exit 0.
- [ ] **Step 5: Commit**. Open PR 3-A.

### Task 3.2: Runner, pickup and the shared Start path (S9, **sensitive**)

**Files:**
- Create: `src/issuer_library/runner.py`
- Modify:
  - `src/issuer_library/jobs.py`: `start_run` queues in a shared workspace, and `job_view` shows `queued`, `position`, `requested_by` and `interrupted` when the runner is offline;
  - `settings.py`: `runner`, `accept_colleague_jobs`;
  - `__main__.py`: start the runner thread when `runner` is true;
  - `server.py`: `GET /api/runner`, `POST /api/runs/withdraw`.
- Test: `tests/test_issuer_library_runner.py`

**Interfaces:**
- Consumes: `shared.py`, `app_version()`, the existing worker start in `jobs.py` and the bridge's `review_id` recheck.
- Produces: the `runner.py` entries and HTTP in Shared names.

- [ ] **Step 1: Write the failing tests** (expected values from the key-writer, as in Task 3.1). Use a temporary folder as the share and a fake engine whose `start` records calls:
  - `test_one_job_at_a_time_oldest_first`: two queued jobs; one `tick` starts only the oldest; a second `tick` while it runs starts nothing.
  - `test_accepting_off_starts_nothing_and_beats_false`: `accept_colleague_jobs=False`; `tick` writes `runner.json` with `accepting: false`, and the engine records no start.
  - `test_non_copilot_config_refused`: a job with `config: "sol-medium"` ends `failed`, its message names Copilot, and there is no engine start.
  - `test_malformed_claim_refused_queue_continues` (Review Focus 2): a truncated `start.claim` ends `failed` with `"The Start request could not be read; review and start it again."`, and the next job still starts.
  - `test_older_version_refused_plainly` (Review Focus 4): a claim with `version: "2026.11.01-aaaaaaaaaaaa"` and runner version `"2026.11.20-bbbbbbbbbbbb"` gives the status message `"This run was queued from Credit OS 2026.11.01-aaaaaaaaaaaa; review it again."`, and no engine start.
  - `test_changed_inputs_after_review_refused`: after review, one byte of a source changes; the status is `failed`, and there is no provider call (the bridge's recheck).
  - `test_long_unc_path_refused_before_spend` (Review Focus 5): a workspace root of 200 characters plus a long issuer gives the bridge's path-length refusal in the status, and no engine start.
  - `test_second_runner_refused`: a fresh `runner.json` from another `runner_id` makes `enable()` return a message containing `"another runner"`.
  - `test_shared_start_queues_and_never_spawns`: `POST /api/runs/start` in a workspace with `shared.json` returns 202 with `{"state": "queued"}`, `start.claim` exists, and the colleague's engine `start` is never called. Without `shared.json`, the existing local start runs.
  - `test_start_disabled_when_runner_offline`: no `runner.json` gives 409 with the offline message, and no `start.claim`.
  - `test_runner_restart_settles_interrupted_job_without_rerun`: a job `taken` by an earlier runner, still `running` with no live worker, becomes `interrupted` on `tick`, with no engine start.
  - `test_withdraw_before_pickup_only`: withdraw returns 200 before `taken`, and 409 after the runner takes the job.
  - `test_shared_workspace_opened_by_drive_letter_is_refused`: a workspace setting of `Z:\...` whose `shared.json` names a UNC path is refused at load and at Settings save. The refusal appears in the app-problem banner and names the UNC path.
  - `test_runner_refuses_workspace_switch_while_worker_runs`: a Settings save that changes the workspace returns 409 while the runner's worker is active.
  - `test_recent_runs_show_requested_by`: `/api/runs/list` rows of shared jobs carry `requested_by`, from `start.claim`.
- [ ] **Step 2: Run** `uv run pytest tests/test_issuer_library_runner.py -q`. Expected: FAIL.
- [ ] **Step 3: Implement.**
  - `validate_intake` checks: the `job.json` shape; every source path resolves inside the folder; each source is at most `SOURCE_LIMIT`; module codes match `MODULE_CODE`; `cap_usd` is a positive `Decimal`; the config starts with `copilot-`; the claim's version equals the runner's.
  - After `take`, the runner writes `status.json` itself and never deletes `start.claim` (A08's release stays local-Start only).
  - `runner_id` is `f"{socket.gethostname()}:{os.getpid()}:{secrets.token_hex(4)}"`.
  - A copy whose workspace holds `shared.json` calls `check_address` when the workspace is loaded and when Settings is saved.
- [ ] **Step 4: Run** this file, `tests/test_issuer_library_jobs.py`, the gate and `validate.py quick`. Expected: exit 0.
- [ ] **Step 5: Commit**. Open PR 3-B (split runner from jobs/server changes if it exceeds 800 lines).

### Task 3.3: Queue on the screens (S10)

**Files:**
- Modify: `apps/issuer-library/web/actions.js`, `views.js`, `screen.css`
- Test: `tests/test_issuer_library_queue_screens.py` (browser)

**Interfaces:** consumes `GET /api/runner`, `POST /api/runs/withdraw` and the `queued` status (Shared names). The tests stub these routes with `json_reply`, so this task does not wait for Task 3.2.

- [ ] **Step 1: Write the failing tests:**
  - `test_start_disabled_shows_runner_message`: `/api/runner` returns `{"online": false, "start_message": "The runner is offline. …"}`. The Review step's Start button is disabled, and the message text is visible next to it.
  - `test_queued_run_shows_position_and_requester`: Run activity shows `Queued, position 2` and `Started by alex`.
  - `test_withdraw_button_until_pickup`: a Withdraw button appears for `queued`, posts `{"id": …}`, and the card shows `Withdrawn`. A `running` card has no Withdraw button.
  - `test_interrupted_when_runner_offline`: a `running` status with the runner offline shows `Interrupted: the runner went offline. Nothing restarts by itself.`
- [ ] **Step 2: Run.** Expected: FAIL. **Step 3:** Implement. **Step 4: Run** with `validate.py browser`. Expected: exit 0.
- [ ] **Step 5: Commit**. Open PR 3-C.

### Task 3.4: Colleague and owner guide; Phase 3 checkpoint (S10 with the lead)

**Files:** create `apps/issuer-library/COLLEAGUES.md`.

- [ ] **Step 1:** Write the colleague section:
  - open the network folder;
  - double-click `Credit OS.cmd`;
  - what Start does, and the four disabled messages from Task 3.1;
  - withdrawing a queued run;
  - where results appear;
  - who to ask.
- [ ] **Step 2:** Write the owner section:
  - share layout (§6.1);
  - permissions: colleagues read-only on `app\`, read and write on `workspace\`;
  - writing `shared.json`;
  - keeping the share path short;
  - copying the release locally for the runner;
  - setting `COPILOT_GITHUB_TOKEN` and `COPILOT_CLI_PATH` in the user environment;
  - runner mode, and the IT confirmation that must be recorded before turning on `accept_colleague_jobs`;
  - updating (new `app\<version>\`, one line in `Credit OS.cmd`).
- [ ] **Step 3:** Add a workspace guard to `validate.py quick`. `git ls-files` must contain no `intake/` path outside `cases/`/`tests/fixtures/`, no `runner.json` and no `shared.json`, and the package build must contain neither name.
- [ ] **Step 4 (checkpoint, owner go-ahead with a cap the owner names):**
  1. On the work PCs, a second Windows user queues one Copilot run.
  2. The owner's runner picks it up and runs it.
  3. Both copies show the result.
  4. Turning the runner off disables Start on the colleague's copy within 90 s.

  5. On the share, time one Refresh and one `/api/runs/list` from a colleague's copy. Set the screen poll interval from that measurement (§7.6): it is the measured refresh time times 10, rounded up to whole seconds, and never under 15 s. The value is recorded with its measurement.

  The lead writes the Phase 3 entry in `VERIFICATION.md`, labelled with its actual scope.

---

## Done when

Phase 1, Phase B (Plans 2–5 with the owner's sign-off), Phase 2 and Phase 3 each have their checkpoint recorded in `VERIFICATION.md`. Final-workflow carries the frozen notice. A colleague on a work PC can start a run from `Credit OS.cmd` on the network drive, and the owner's runner runs it through the owner's Copilot.
