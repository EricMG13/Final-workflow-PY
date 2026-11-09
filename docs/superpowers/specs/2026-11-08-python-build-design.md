# Final Workflow in Python: one product, usable by colleagues at work

Design, 2026-11-08. Status: **approved by the owner on 2026-11-08**.

Marked **(owner)**: decided by the owner. Marked **(call)**: the designer's call, open to the owner's
correction when reading. Everything else is a fact verified on 2026-11-08, with its source.

## 1. Intent

The owner (sole developer) wants colleagues to use Credit OS on their own Windows work PCs
from a shared folder, with no install and no IT exception. Colleagues read reports and start runs
themselves inside the app, without asking the owner. Only the owner's GitHub Copilot seat does LLM
work. **(owner)**

**Name (owner):** the app is called **Credit OS**, not Issuer Library. **(call)** Everything a user
sees says Credit OS: the launcher file, page title, Help, README, Windows notices and the colleague
guide. "Library" stays the name of the screen that lists reports. Code folders and package names
(`apps/issuer-library`, `src/issuer_library`) and the existing per-user settings folder stay as they
are, so nothing moves and no one's settings are lost.

All further development moves to `EricMG13/Final-workflow-PY`. The owner's words: "stop any Go
related work and move all applicable work to the python version". `EricMG13/final-workflow` (Go
server) becomes a frozen predecessor. **(owner)**

Why Python: the work PCs' application-control product blocks unsigned executables (go.exe is
blocked as "Not Signed"); signed `python.exe`, `node.exe`, PowerShell, cmd and GitHub-signed
`copilot.exe` run, and compiled Python extensions (`.pyd`) load
(github.com/EricMG13/issuer-library-work-deployment-prompt, `CHECKS.md`, `CHECKS-2.md`, `CHECKS-3.md`).

## 2. Goals, non-goals, anti-goals

**Goals**
1. `Final-workflow-PY` holds everything of value from final-workflow `main` and from the stopped
   sessions' pushed branches, with every Go and Node piece rebuilt in Python or pytest/Playwright.
2. The Beta V1 plans (2–5) finish in Python **before** colleagues get the app. **(owner)**
3. A colleague opens the app by double-clicking a file on the network drive. Nothing is installed,
   nothing asks for admin rights, and the shared folder holds no program file. **(owner, runtime)**
4. A colleague reviews a run offline on their own PC and presses Start; the owner's copy of the app
   runs it through the owner's Copilot, one job at a time, oldest first, each job under its own USD
   cap; everyone sees the result in the shared workspace. **(owner)**

**Non-goals**
- An overall spend limit on colleagues' runs. **(owner: no overall limit)** Each job keeps its own cap.
- A server, database, web host or cloud service. Each person runs a loopback-only local copy.
- Provider keys or tokens on colleagues' PCs, now or later.
- New analysis, new modules or a second analytical execution for delivery (repo `AGENTS.md`).
- Excel output (repo `AGENTS.md`).
- Any further Go or Node work.

**Anti-goals** (it would be a failure even if it ran)
- A colleague's job spends money while the owner's runner is offline or after the owner switched
  colleague jobs off, or a paid run restarts by itself after an interruption.
- A job spends on inputs other than the ones its reviewer saw (inputs changed after review).
- Colleagues' issuer material ends up in the public GitHub repository.
- Anyone who can write the shared workspace can change the code that runs with the owner's token.
- Two people's runs overwrite or hide each other.

## 3. Constraints

**Work PCs** (verified on the owner's work PC, 2026-11-08):
- Every colleague's PC has the company Python at `C:\Program Files\Statestreet\Python313\python.exe`
  and `pythonw.exe` (3.13.16, no app packages installed). **(owner: "Yes, all of them")**
- The company pip index returned 503 on every request; nothing can be installed from it.
- Copilot CLI 1.0.105 (the runtime `github-copilot-sdk==1.0.28` pins, protocol 3) is cached by gh
  2.94.0 at `%LOCALAPPDATA%\GitHub CLI\copilot\copilot.exe`; the owner set `COPILOT_CLI_PATH` to it.
  `COPILOT_GITHUB_TOKEN` must be in the owner's launching environment; the app passes it explicitly
  and ignores the gh login. The SDK is pure Python (`py3-none-any`, Python >= 3.11; needs
  python-dateutil, pydantic >= 2.11, httpx) and is not in the Windows package today.
- Not yet tested: whether `pydantic_core`'s compiled `.pyd` loads **from a network path**. It loads
  from the company's own install folder.

**Shared folder**: a mapped network drive (SMB), not a SharePoint/OneDrive-synced library. **(owner)**

**Repository**
- `Final-workflow-PY` stays **public**. **(owner)** It already holds `runs/`, `deliverables/` and
  `data/`; that existing material is unchanged by this design.
- `final-workflow` gets a README notice pointing to `Final-workflow-PY`, then is archived on GitHub
  (read-only). **(owner)** Every stopped session's work is now pushed, so nothing blocks the archive.
- The repo's `AGENTS.md`, with the final-workflow lines copied in (§5.1), and the owner's global rules govern
  models, reviews and gates: `tools/quality_gate.py`, `validate.py` modes, confidence-review,
  rewrite-tournament, one `VERIFICATION.md`.
- Each PR has at most 800 changed lines, excluding fixtures, lockfiles and files copied byte-identical
  from a pinned final-workflow commit (§5.1).
- Paid execution is a separate, explicit owner go-ahead at a named checkpoint. The build runs no provider.
- The Beta live checks (A-live, A-ab, B-live, C1–C3, RC-live) stay on `sol-medium` (OpenAI), as the
  Beta plans say. **(owner)** Copilot is used only for colleagues' runs in Phase 3.
- Never mutate historical live run directories. final-workflow changes only by the owner-approved
  notice and archive above.

## 4. Order of work

| Phase | Delivers | Visible to colleagues |
|---|---|---|
| 0. Pre-flight (owner, 2 minutes, before Phase 1 starts) | The network-path `.pyd` check (§6.4) | No |
| 1. Catch-up and freeze | Reusable final-workflow code copied; Go server features rebuilt in Python; Node suites ported; pushed carry-over branches copied; final-workflow frozen | No |
| B. Beta V1 in Python | Plans 2, 3, 4 finished on the Python server, each with its checkpoint | No |
| 2. Work-PC package | The shared-folder package on the company Python | No (owner only) |
| B5. Beta release gate | Plan 5's gate, with its Windows step run on the Phase 2 package | No |
| 3. Colleagues' runs | Shared workspace, queue, runner, heartbeat, colleague guide | Yes, after the owner switches colleague jobs on |

**(call)** Plan 5 moves after Phase 2, because its gate requires the packaged app on Windows and the
only package that runs on a work PC is Phase 2's. This keeps the owner's order: Beta before colleagues.

## 5. Phase 1: catch-up and freeze

### 5.1 Copy the reusable code from final-workflow

No git merge. **(owner: "just take the re-usable code")** Files are copied verbatim from one pinned
final-workflow commit (`main` was at `dd3dfa18` on 2026-11-08; the builder pins the tip at the time
and records it), as the repo's earlier "Sync final-workflow main" commits did. final-workflow's
history stays in the frozen repository.

- **Taken as is**: everything the Python repo never changed, which is most of it: `src/deploy_workflow`,
  `src/deploy_vii`, the Python `tests/`, `cases/`, `tools/`, `.github/workflows`, docs (methods,
  rulings, plans), and in `apps/issuer-library/` the `engine/`, `web/` and `designs/` files.
  Files final-workflow deleted or moved (for example PR 55's archive of superseded material) are
  deleted or moved here too.
- **Not taken**: Go files, `go.mod`, `*.cjs` suites and Node-only tooling. Their behaviour is rebuilt
  in §5.2.
- **Changed on both sides** (the `apps/issuer-library/` files the Python port edited, `README.md`,
  `VERIFICATION.md`, `pyproject.toml`, `AGENTS.md`): keep the Python repo's version and apply
  final-workflow's change by hand. `AGENTS.md` gains the final-workflow lines on
  `tools/quality_gate.py`, the weekly full suite and the `VERIFICATION.md` archive rule;
  `pyproject.toml` keeps the server pins and adds any new upstream pin.
- Carry-over branches (§9) come after `main`'s copy: each branch's own changes (from its merge-base
  with final-workflow `main`, Go and Node excluded) are applied, one PR per branch.

**PR size (call):** the copy lands in import PRs split by area. Lines copied byte-identical from the
pinned commit do not count toward the 800-line cap; that code was reviewed in its own final-workflow
PRs. A small check compares every copied file with `git show <sha>:<path>` and fails on any
difference. Hand edits to files changed on both sides, and all new code, count as usual.

### 5.2 Rebuild the Go server's features in Python

final-workflow `main` added 41 Go commits since `a313b50` (about +1.6k production, +4.9k test lines)
and +5.7k lines of Node suites. The Go and Node tests are the behaviour specification: each case is
ported to pytest (server) or pytest + Playwright (browser) first, run against the Python server, and
code changes only where a ported case fails. A case that does not apply to the Python design (for
example a Go-specific lock ordering) is recorded as not applicable with its reason, not dropped silently.

Features to rebuild (from the Go commit log, `a313b50..dd3dfa18 -- apps/issuer-library/*.go`):
- **Launch**: a one-time launch ticket that expires, then a session cookie; same-site requests refused.
- **Relaunch and quit**: a relaunch can ask an idle library to quit; the Quit and Start-versus-quit races.
- **Runs**: resume a stopped run as a new reviewed job, copying only its listed sources, with the cap
  taken from the stopped run's record; Run activity record and card; run progress and stop reason
  from the CP-OS event log; the run event log served as JSON; the Forecast tab serving the published
  model and why it was built.
- **Windows notices**: one native notice when a run finishes with no tab open; no provider keys in the
  notifier's child process.
- **Workspace store**: reruns only when a workspace file changes; Refresh does not wait for it.
- **S18 security and robustness fixes**: A01/C01 slow review delivers its response; A02/C06 report
  adapter injected at `</body>` in the original bytes; A03 metric equals a whole number of its quote
  (with exponents, parentheses, slash dates, `-$`); A04/C05 Recent runs by write time, never cutting an
  active job; A06/C04 deliveries attached only on matching identity; A07 settle or adopt a running job
  after a restart; A08/C02 release the start claim when no worker started; A09 one leading UTF-8 BOM
  in settings; C07 no response written under the catalogue lock; C08 no workspace switch during a
  review; C09 a declared delivery listed once; C10 `run()`'s error in `library.log`; C11 discovery
  without the catalogue lock; C12 each upload streamed into its file and hash; malformed
  `workflow.json` discarded; bounded, unlinked reads of manifests and delivery identities; read errors
  by type and reason; completion needs a report.

Node suites to port: `library-workspace`, `run-watch`, `screens`, `new-run`, `screening-dom`,
`screening`, `run-activity`, `context-embed`, `escape-sinks`, `draft-guard`, `run-spend`,
`screen-css`, `design`.

### 5.3 Carry-over branches

Every stopped session's branch is accounted for in the table in §9.

### 5.4 Freeze final-workflow

After Phase 1's copy lands: a README notice on final-workflow `main` (one PR, owner merges) naming
`Final-workflow-PY` as the product and final-workflow as frozen. Then archive on GitHub; all
stopped sessions' work is pushed. **(owner)**

## 6. Phase 2: the work-PC package

### 6.1 What the package is

One folder on the network drive. It holds Python source, pure-Python wheels unpacked, the web front
end, the engine files and one compiled extension (`pydantic_core`, `cp313-win_amd64`). **It holds no
`.exe`.** The python.org embeddable runtime leaves the work package. **(owner: runtime; call: drop
the embeddable runtime and arm64)**

```
\\<server>\<share>\CreditOS\
  Credit OS.cmd               starts the company pythonw.exe on app\<version>\start.py
  app\<version>\              one folder per release, read-only for colleagues
    start.py                  puts lib\ and src\ on sys.path, runs issuer_library
    lib\  src\  web\  engine\
  workspace\                  the shared workspace (Phase 3); outside the repository
```

- The launcher runs `C:\Program Files\Statestreet\Python313\pythonw.exe -I -B -X utf8
  "%~dp0app\<version>\start.py"`. `-I` ignores `PYTHONPATH` and user site-packages, so `start.py`
  adds its own `lib\` and `src\` explicitly. If the company Python is missing, the launcher says so in
  plain words.
- One package for everyone, including the Copilot SDK and its dependencies (pure Python). Colleagues'
  copies never call it: they have no token.
- **Updates (call):** the owner copies a new `app\<version>\` and changes the one version line in
  `Credit OS.cmd`. Running copies keep their version until restarted; nothing overwrites a file
  a colleague has open (Windows locks a loaded `.pyd`).
- Versions match `uv.lock`; the build verifies each wheel's SHA-256 as `packaging/runtime.py` does now.

### 6.2 Who writes what

- Colleagues: read-only on `app\`; read and write on `workspace\`. The owner sets these share
  permissions (colleague guide, §7.8).
- **The owner's runner never runs from the shared `app\` folder (call).** The owner copies the same
  release to a local folder on the work PC and starts it with the same launcher on the company
  `pythonw.exe`, so nobody who can write the share can change the code that holds the owner's token.
  The token and `COPILOT_CLI_PATH` come from the owner's user environment; the workspace comes from
  the owner's own settings.

### 6.3 Per-user state

Settings, logs and the per-user port stay in each user's `%LOCALAPPDATA%`, as now. **(call)** The
package carries a default workspace (a plain file beside the launcher, holding the shared workspace's
UNC path), read only when the user has no saved setting, so a colleague does not type it. It does not
lock the setting: the owner can switch between the shared workspace and a local one. The existing
`%ProgramData%` policy file stays IT's lock and is not used for this.

### 6.4 Pre-flight check (Phase 0)

Before Phase 1 starts (it takes 2 minutes), the owner runs, on the work PC, the company `pythonw.exe`
against a test package placed on the network drive: it imports `pydantic_core` from the network path
and serves the app on loopback. Start-up time from the share is measured at the same time. pydantic
sits under the server and the engine's offline review, so this decides whether Phase 2 works as
designed. Fallbacks, in order **(call)**:
1. The share works: as designed.
2. Blocked from the share: on first start `start.py` copies `app\<version>\lib\` to
   `%LOCALAPPDATA%\CreditOS\<version>\` and loads it from there (no admin rights, nothing
   registered). The same check is run on that folder.
3. Blocked there too: stop and bring it to the owner before any Phase 2 work. The candidate is the
   company SSCPACK Python 3.12 with its installed pydantic 2.13.4 (the model tests passed on 3.12.14
   with SSCPACK's versions), which needs the app to support 3.12 and SSCPACK on every PC.

Phase 1 and the Beta plans go ahead whatever the result: the owner uses them on the owner's own
machines, and only Phase 2 depends on it.

### 6.5 Owner's runner environment

`COPILOT_GITHUB_TOKEN` and `COPILOT_CLI_PATH` come only from the owner's launching environment.
`Smoke-test.ps1` is updated for the new package and run by the owner on the work PC.

## 7. Phase 3: colleagues' runs on the owner's PC

### 7.1 Roles

- **Colleague copy**: reads the shared workspace, reviews runs offline, queues reviewed runs, shows
  queue position, progress and results. Never runs a worker, never needs a token.
- **Runner**: the owner's copy with runner mode on. It also is a normal copy for the owner, and the
  owner's own Starts in the shared workspace go through the same queue (one code path).
- A workspace is **shared** when it holds a marker file `shared.json` (written once by the owner). In
  a shared workspace Start always queues. Outside one (the owner's local or development workspace)
  Start runs a worker locally, as today. **(call)**

### 7.2 Shared workspace files

The existing layout already is a queue: `intake/<job-id>/` holds `context.json`, `sources/`,
`job.json`, `review.json`, `start.claim` and `status.json`; job ids are `web-<32 hex>`, so copies
never collide. Phase 3 adds:

| File | Written by | Purpose |
|---|---|---|
| `shared.json` | owner, once | Marks the workspace as shared |
| `runner.json` | runner only, every ~15 s, by atomic replace | Heartbeat: runner id, user, app version, `accepting`, `provider_ready`, active job, `updated_at` (UTC) |
| `intake/<id>/start.claim` | the requester's copy, exclusive create | The Start request: `requested_by` (Windows user name, display only), `requested_at`, `review_id`, accepted limitation ids (Plan 2's receipt) |
| `intake/<id>/taken` | runner **or** requester, exclusive create; first wins | `{"by": "runner", ...}` = picked up; `{"by": "withdrawn", ...}` = the requester withdrew it before pickup |

**Handover rule (call).** Until `taken` exists, only the requester's copy writes in `intake/<id>/`.
After the runner creates `taken`, only the runner and its worker write there (status, Start receipt,
the recomputed review's temporary folder), and only they ever write `runs/` and `deliverables/`. The
requester never deletes anything after Start. A failed start on the runner is recorded in
`status.json`, not by removing `start.claim` (A08's release stays a local-Start rule). Exclusive create
(atomic on SMB) settles the two races: double pickup and pickup versus withdrawal.

**Workspace identity (call).** A shared workspace is addressed by its UNC path only, which
`shared.json` records. A copy that opens a shared workspace by a drive letter refuses it, with a
message giving the UNC path. So `job.json` carries the same path on every PC, the path stays inside
the review binding (`review_id`), and the runner resolves the same folder.

### 7.3 Job lifecycle

1. **Review** on the requester's PC, offline, as today.
2. **Start**: allowed only if the runner is online, `accepting` is true, the heartbeat's
   `provider_ready` is true (a colleague's own review records `false`, having no token) and the
   runner's app version equals the requester's. Otherwise Start is disabled with a plain message
   ("The runner is offline", "Colleague runs are switched off", "Restart Credit OS to update").
   Nothing is queued while the runner is offline. **(owner: offline message; call: version rule)**
3. **Queued**: Run activity shows the position. The requester may withdraw it until pickup.
4. **Pickup**: the runner takes the oldest `requested_at` (ties by job id), one job at a time, by
   creating `taken`. It re-validates the folder as untrusted input (`job.json` shape, paths inside the
   folder, sizes, module codes, positive cap, and a `copilot-*` config only, because the owner's
   Copilot seat is the only LLM account colleagues' runs may use **(owner)**) and recomputes the review; the existing bridge refuses
   to start when the recomputed `review_id` differs from the approved one. A refusal makes no
   provider call and the status says why.
5. **Running**: the existing worker, cap, ledger and status files, now under the runner.
6. **Finished, stopped or failed**: everyone sees the run in Recent runs and the Library; the
   requester's copy gives the existing Windows notice.

### 7.4 Heartbeat and offline

- A copy treats the runner as **offline** when `runner.json` is missing or its `updated_at` is more
  than 90 s old by the copy's own clock (domain-joined PCs keep time within seconds). **(call)**
- Offline: Start disabled with the message; reading, reviewing and the Library still work. Jobs
  already queued wait for the runner's return. **(owner)**
- **Mid-run drop**: the job shows as interrupted. When the runner returns it settles the job by the
  existing A07 rule and never restarts paid work by itself; a rerun is a new reviewed job (the
  existing resume feature) that someone starts. **(owner, existing rule)**
- **Second runner**: runner mode refuses to switch on while a fresh `runner.json` belongs to another
  runner id. Exclusive `taken` already prevents a job running twice. **(call)**

### 7.5 Switching colleague jobs on

Runner mode has one setting, **off by default**: accept queued jobs from this shared workspace. The
owner switches it on only after recording IT/compliance confirmation that issuer text may leave
through the owner's Copilot account. With it off, the runner still writes the heartbeat with
`accepting: false`, so colleagues see why Start is disabled. **(call)**

### 7.6 Multi-writer behaviour

- **Recent runs and discovery** show everyone's runs, with `requested_by`. Ordering stays by write time
  (A04).
- **Workspace switch**: refused during a review (C08) and, on the runner, while its worker runs.
- **Refresh cost**: N copies poll the share. The store reruns only when a file changes (already
  rebuilt in §5.2); the builder measures one refresh against a workspace with the repo's current run
  count and sets the poll interval from that measurement.
- **Path length**: UNC paths are long; the bridge's existing 259-character refusal applies before any
  spend. The colleague guide tells the owner to keep the share path short.

### 7.7 Security

- Trust boundary: anyone who can write `workspace\` can queue jobs that spend the owner's Copilot up to
  the cap they enter. The share's permissions are the access control; `requested_by` is a label, not
  authentication.
- The runner treats every intake folder as untrusted input (§7.3 step 4) and runs from local code
  (§6.2).
- The token never leaves the runner's environment; the worker and notifier children get no keys
  beyond what the existing code passes.
- The shared workspace is outside the repository. A check in `validate.py` (or the quality gate)
  fails if the package build or a commit includes files from a workspace (`intake/`, `runner.json`,
  `shared.json`).

### 7.8 Colleague setup guide

One page, `apps/issuer-library/COLLEAGUES.md` **(call: file name)**: open the network folder,
double-click `Credit OS.cmd`, what Start does and when it is disabled, where results appear, who
to ask. A second section for the owner: share layout and permissions, writing `shared.json`, runner
mode, the IT confirmation switch, updating to a new version.

## 8. Verification

- Per task: the affected tests and `tools/quality_gate.py`; per phase: `validate.py full` and
  `validate.py browser`; the full suite runs weekly in CI (repo `AGENTS.md`).
- Phase 3's queue and runner have their own tests with a temporary folder standing in for the share:
  double pickup, pickup versus withdrawal, stale heartbeat, second runner, version mismatch, changed
  inputs after review, runner offline at Start, interrupted run. Expected values are written by
  someone other than the code's author.
- Real-share proof is the owner's: the Phase 0 check, the Phase 2 smoke test, and one Phase 3 run
  where a second Windows user queues a job and the owner's runner runs it, with a cap the owner names
  at that go-ahead.
- Each live or paid check names its scope (issuer, date, synthetic or public proxy) in one
  `VERIFICATION.md` entry.

## 9. Carry-over accounting

Fetched from github.com/EricMG13/final-workflow on 2026-11-08; nothing copied from any worktree.

| Branch @ head | What it holds | Plan |
|---|---|---|
| `claude/plan-2-1e-live-check` @ `9450ddd1` | Frozen live cases, `live_check --case`, back-test; review clean; Python only | Copy in Phase 1 |
| `claude/plan-2-run-expectations-612c9c` @ `b4728bbc` | Task 5b single-run walk (`ce59bbc6`, 2 Important review findings); `b4728bbc` is the unreviewed fix in progress with a 390-px Library overflow fix; one `.cjs` | Copy in Phase 1, porting the `.cjs`; Phase B finishes the 5b fix round and review, then Tasks 6–8 (Task 6 rebuilt on the Python server), Checkpoints A and B (A-live, A-ab, B-live need the owner's go-ahead) |
| `claude/plan-3-primary-transactions-ee0e14` @ `8d22e84c` | Task 9 Mattress Firm 2014 public proxy case and frozen key (done); Task 10 CP-4 Provisional review and checker, 54-case key, gates green at `f3ca0c05` (done); Task 11 contract and frozen 80-case pro forma key (data only); no Go | Copy in Phase 1; Phase B does Task 11a (code), Task 11b (report routes, after the owner's placement answer) and live checks C1/C1n/C2/C1r/C3. The git-ignored Task 10/11 contracts, 11a brief and ledger come from the Plan 3 handover notes as inputs |
| Plan 3 worktree leftovers | 19 uncommitted files: 18 are exactly `ruff format` of HEAD, and `cp1d.md` reformats comment spacing inside a method file | **Not carried**: formatting only, and reformatting a method file would change module instructions |
| `claude/plan-4a-library-admission` @ `97b69728` | Go admission of credit fields, screening logic and answer keys | Answer keys and screening code copied; Go admission rebuilt in `discovery.py`/`model.py` from its ported Go tests |
| `claude/plan-4-library-credit-data-aafd87` @ `fb6edd17` | Library credit/market screen UI, Help, README | Web files copied; serving side rebuilt; Node suites ported |
| `claude/plan-4c-library-manifest` @ `d877d8ce` | `engine/library_manifest.py` and its pytest; a Go admission test against its key; case-folded issuer grouping (R-29) | Copied together with 4B's later commits; Go test ported; its whole-branch review (stopped before findings) runs in Phase B |
| Plan 4 not done | `bridge.start` call and integration test (waits on Plan 2 Task 6); chart-row format R-26; pro forma keys; Checkpoints D and D-live | Phase B |
| `claude/beta-v1-coordination-1d6fe4` (local), `claude/beta-v1-shared-names` @ `821f6f2e` | Nothing beyond `main` | No action |
| Plan 3 and 4 status notes (`plan-3-status.md`, `plan-4-status.md`, `plan-4c-chart-row-evidence.md`, `plan-3-handover/`) | Handover notes in the stopped sessions' notes folder | Read as data when the Phase B tasks are written; open owner calls in them go to the plan |

## 10. Left to the builder

Task split and PR boundaries within the 800-line cap; which ported Go cases are not applicable and
why; poll intervals (from measurement); the exact `runner.json` and `start.claim` fields beyond those
named; how Run activity draws queue position; wording of messages within the plain-language rule;
the build script's structure.

## 11. Items for the owner outside this design

Pre-existing, reported, not fixed here: `tests/model` has 3 failures on Python 3.12 and 3.13 caused
by a missing ruling `docs/rulings/2026-11-02-model-testing-live.md`. An earlier proposal of one
standing ruling file for the Copilot configs, instead of per-run rulings, is the owner's to take up.
