# Offline Issuer Library

A local application for preparing issuer runs, launching the existing CP-OS
workflow, screening dated results and reading deliverables in one interface.
The library reads historical evidence; New run writes fresh intake, execution and
delivery folders. Candidate output remains explicitly qualified.

## Windows: double-click launch

1. Extract the entire Windows ZIP and keep `Issuer Library.cmd` beside its `engine` and
   `web` folders. Choose the appropriate Windows ZIP (amd64 for Intel/AMD, arm64 for
   Windows on ARM).
2. Double-click **Issuer Library.cmd**. It starts the bundled Python runtime without a
   console window, opens the default browser and runs only on `127.0.0.1`. No Python
   installation, Node, downloads or internet are needed.
3. In **Settings** on the left rail, enter the full folder containing `runs/` and
   `deliverables/`, then choose **Save and reload**. The default is the Windows
   Documents known folder plus `FinalWorkflow`; existing folders are not moved.
4. The rail reaches every part of the one app: Issuer library, Research workspace,
   Reports, Run activity, New run, Search (`/`), Settings and Help. Choose a run
   in the library to read its overview, modules, calendar, reports and evidence. A report
   opens inside the app beside that navigation; its **Built from** list opens the
   module outputs it used, and a module output links to the deliverables that used it.
   Discovery runs every 30 seconds; when it finds a change the app offers **Reload**.
   **Download original HTML** saves the standalone report.
5. **Quit library** in Settings stops the service. Closing a tab leaves it running.
   Launching the package again reopens the same per-user instance. Quitting or
   changing workspace is refused while a model run is active.

The Windows packages are pilot builds, not signed enterprise releases. Windows
execution, browser rendering and enterprise rollout still need Windows acceptance.
IT can sign the launcher script and the bundled runtime, or wrap the launcher in its
own signed shortcut, and distribute the package using its normal software deployment
process. No firewall opening or Windows service is needed.

## New run: context, issuer folder, review, Start

New run follows `src/deploy_workflow/owners/cpos_launch.py`, the same launcher as its
command line, and stays inside the app: moving elsewhere and back keeps what you entered.

1. Complete the Run context form or load a saved `context.json`. It sets the issuer,
   workflow and dates. Optional sections stay available in disclosures.
2. Choose the issuer folder (up to 500 files, 64 MiB each and 512 MiB in total). Choose
   a model and a maximum USD spend. **Advanced** narrows the modules (their dependencies
   are added) and sets the turns allowed per module. Office's `~$` lock files, beside a
   document someone has open, and Windows files such as `Thumbs.db` are listed as unread.
3. **Validate and review run** runs the launcher's offline preparation, with no provider
   call. Review shows the modules in order, the model and effort, the spend ceiling, what
   one call holds while in flight, the file hashes, the files no module can read, the
   report sections this run fills and those it does not. A refusal writes nothing. A run
   needs about 140 characters of path below the workspace folder; where Windows long paths
   are off, review refuses a workspace too deep for that, before any spend.
4. Approve it, then choose **Start run**. The application starts one CP-OS worker.
   Duplicate Start requests cannot create another execution. Changed files, context,
   instructions, workflow code or review invalidate the approval.
5. Follow the module in progress, the last accepted module and recorded spend. Recent runs stay listed after
   reopening the page. The progress step is headed by the run's issuer, workflow, date and id. Recent runs
   lists every run in the workspace with its workflow, module, state and spend; opening
   a row shows its progress. A rejected module stops the run: its work is kept and no automatic
   paid retry is made. A finished run opens on its deliverables. Automated checks cover
   structure, anchors and report selectors only: review the handoffs against the sources
   before relying on a report. The launcher publishes the report; it does not publish an
   HTML Model, charts or calculation JSON.

Preparing and validating inputs works offline. Live model execution requires its
configured provider connection and credentials in the **launching environment**:
`OPENAI_API_KEY`, `ANTHROPIC_API_KEY` or `OPENROUTER_API_KEY`. The application never
asks for or stores provider keys in a file. IT should provide those environment
variables through its approved launch mechanism; restart the app after changes.
Missing configuration keeps Start disabled. The build and tests never run providers.

CP-OS keeps ordering, retention, resume, budget and delivery, as for the command line.
Delivery rereads the module handoffs and reuses the report renderer, and is hash-checked.
No separate CP-MEMO execution is added.

Drafts live under `<workspace>/intake/<run-id>`. Execution, including response records,
handoffs and the verified delivery, lives under `runs/<run-id>`. The app creates these
standard parent folders in a new writable workspace. Existing run destinations are not
overwritten. A stopped web run shows the handoffs it accepted and publishes no report. It
is not resumed from the app; the command line can resume the run folder.
A crash/interruption is retained and does not trigger an automatic paid restart.

The Windows package contains pinned Python 3.13.15 and its dependency wheels,
verified against upstream SHA-256 digests at build time. It needs no Python/pip
installation or launch-time downloads. `Smoke-test.ps1` checks packaged imports,
Windows locking, the workspace read and offline context review; it never starts a model run. Run it
on the target Windows host as part of acceptance. Native Windows execution and
paid model success have not been demonstrated on this macOS build host.

## Standard locations and enterprise configuration

- Install: IT may place the package in `%ProgramFiles%\FinalWorkflow\IssuerLibrary`.
  The package writes nothing beside itself (bytecode caching is off) and can run from a
  read-only location.
- Managed configuration: `%ProgramData%\FinalWorkflow\IssuerLibrary\settings.json`.
  If present, it takes precedence and locks workspace changes in the UI/CLI.
- Per-user state: `%LOCALAPPDATA%\FinalWorkflow\IssuerLibrary\settings.json`,
  `index.json` and `library.log` (rotated on launch above 1 MiB).
- Business data: an approved workspace with `data/`, `runs/` and `deliverables/`.
  Windows Known Folder APIs resolve Documents, LocalAppData and ProgramData,
  including folder redirection. No user-specific absolute path is embedded.

Example managed configuration (IT must provision this actual folder and permissions):

```json
{"workspace": "D:\\Research\\FinalWorkflow"}
```

A UNC path is also supported when available. Offline use requires the data to be
locally available: disconnected network shares and cloud placeholders cannot be
read. A moved workspace needs one configuration update. Store the canonical files
in the workspace, not in the index; the index is disposable and rebuilt on launch.
Per-user state must not be redirected to a shared index used by multiple users.

Only enumerated files under the selected workspace can be served. Pinned files
are rechecked when opened. Reports run in an opaque sandbox with external network
access disabled. Only this local application can embed the report; its renderer,
sections and evidence inspector remain available. The embedded view adds a scoped
Deploy VII presentation adapter: the evidence panel opens on demand, laptop reading
uses one column, and narrative citations use Red Hat Text. Hash verification uses
the retained original bytes before that presentation is added. Downloads and
standalone originals remain byte-for-byte unchanged. Legacy self-contained
reports work here. Deliveries that require external scripts/assets need packaging
adaptation; network assets are never silently fetched.

## Discovery and metadata contract

Every immediate subfolder of `runs/` appears, even without structured metadata.
Retained Markdown, text, PDF, HTML, JSON, CSV and XLSX files are listed recursively.
Hidden files and symlinks are not enumerated. Each file must be a regular file at
most 64 MiB; each run is limited to 5,000 listed files. Discovery notices expose
invalid/partial manifests and missing/changed evidence instead of hiding the case.

Every immediate subfolder of `deliverables/` and of a run's `deliveries/` is checked using its existing
`delivery.json` file hashes and `view.json` issuer/run identity. A report is linked
to a run through an explicit matching identity or a checked legacy mapping. Other
deliveries get their own revision row. A shared issuer, folder timestamp or filename
does not establish a run relationship or the latest approved revision.

The embedded legacy adapter retains the existing example's seven curated cases.
It applies only when the exact source hashes and quoted lines match the workspace.
It is not a general financial parser. Additional unstructured runs are discovered
with unknown summary fields. No fictional screening dataset is shipped in the UI.

For new structured metadata, the producer can publish `runs/<run-id>/library.json`
with schema `issuer-library-run/1`. See `run-manifest.example.json`: it is explicitly
fictional and will be rejected until replaced with real hashes and excerpts.
The CP-OS app adapter emits context-labelled metadata for new app runs. Screening
metrics and a verified completeness checklist remain unassessed until supplied. Write the manifest atomically after its
referenced handoffs exist; incomplete writes remain visible as discovery notices.

- `run.id` must equal its folder name. `issuer`, `name` and `identity_source` are
  required. Non-unknown sector requires `sector_source`. Dates are ISO calendar dates.
- Source keys contain letters, digits, underscore or hyphen. Each source contains
  `path` (workspace-relative, forward slashes), `sha256`, 1-based `line` and exact
  `quote`. Paths must stay within `runs/`, `data/` or `deliverables/`.
- `metrics` supports `revenue`, `ebitda`, `leverage`, `coverage`, `cash`, `cashflow`.
  Each supplied metric has a decimal-string `value`, `unit`, `period`, `basis` and
  source key. Units must carry currency/scale where applicable, e.g. `USD m`.
  Keep unavailable values null, distinct from zero. Evidence checks establish
  literal transport, not an independent financial interpretation of the row.
  Optional `provenance` is the producer's explicit `cited`, `calculated` or
  `synthetic` classification. Omit it when unknown: the interface shows
  **Not classified** beside the source link. A verified source alone does not
  establish provenance type, and the library never infers it from the value,
  basis or reference name.
- `artifacts` can name explicit workspace-relative delivery folders, labels,
  relationship (`direct` or `related`) and state. The library verifies the actual
  delivery and issuer before enabling a link. The delivery's own status is retained;
  a legacy `superseded` flag remains excluded from primary links.
- `checklist` defaults to null, giving **Not assessed**. To report a score, provide
  `scope` and unique `requirements` with `id`, `stage`, `done`, `evidence` (source
  keys). Required stages: `sources`, `analysis`, `verification`, `downstream`,
  `delivery`. Every done checkpoint must have verified evidence. The score is the
  integer percentage of done/required checkpoints; optional tasks should not be in
  the denominator. This is the producer's scoped assessment, not library approval.
  Report availability and hashes alone never imply analytical completion. A claimed
  delivery checkpoint also requires an available direct report bundle; a missing or
  changed bundle withholds the score rather than preserving stale completion.

## Development and reproducible packaging

The server is Python: `src/issuer_library`, a FastAPI application served by uvicorn on
loopback only. Build and tests need Python 3.13 and uv 0.12.5; no compiler or Node.
Windows runtime dependencies are bundled.

```sh
uv sync --locked
uv run pytest tests/test_issuer_library_discovery.py tests/test_issuer_library_server.py tests/test_issuer_library_jobs.py tests/test_issuer_library_store.py
PYTHONPATH=src uv run python -m issuer_library --workspace /absolute/workspace --no-browser
uv run python apps/issuer-library/packaging/smoke_test.py
uv run python apps/issuer-library/packaging/build.py
```

The smoke test starts the repository's server over loopback and checks launch, retained
reports, the workspace store, a second launch, settings, an offline review, the Start gate,
periodic discovery, quit and restart. With a package folder as its argument it runs the
same checks against that package's runtime, on Windows. The runtime packager downloads
official Python and the pinned PyPI wheels, FastAPI and uvicorn among them, into a
verified cache; rebuilds reuse that cache. No provider execution occurs. Outputs go to
`artifacts/issuer-library` at the repository root. Each package holds the launcher
script, the `web/` front end and the `engine/` folder with the pinned runtime, the engine
scripts and the `src/` packages; `python313._pth` puts `..\src` on the isolated
interpreter's path. Packaging copies the deliverables' actual design tokens, styles, brand
image and licensed fonts, plus the verified legacy adapter. Screening logic extends the
existing example with exact decimal comparison. Frontend composition lives in `web/`.
Windows amd64/arm64 packages are produced; macOS and Linux development runs the server
from the repository. No issuer runs, uploaded PDFs, provider credentials or complete
reports enter the ZIP. A clearly fictional context is included only for the explicit
offline smoke test.

`--state-dir` provides an isolated state directory for tests. `--port` overrides
the stable per-user loopback port if another application occupies it. A running
instance must be quit before changing command-line workspace settings.

Browser checks run the front end in headless Chromium through Playwright, a dev
dependency: run `uv run playwright install chromium` once, or set
`ISSUER_LIBRARY_CHROMIUM` to an installed Chromium executable. `designs/build.py`
writes their fixture from the curated retained runs and fails if a curated pin goes
stale; the tests build it themselves:

```sh
uv run pytest -m browser tests/test_issuer_library_app.py tests/test_issuer_library_design.py tests/test_issuer_library_example.py tests/test_issuer_library_reader.py tests/test_issuer_library_screens.py
```

`validate.py quick | full | browser | suite` runs these gates in one command with provider keys
removed. `browser` serves the repository with a fake provider through `designs/browser_check.py`.
It needs `FW_PYTHON` and, for a Chromium that Playwright did not download,
`ISSUER_LIBRARY_CHROMIUM`.

These checks execute the page's scripts in a real browser with synthetic API replies,
but do not establish visual layout or Windows launcher acceptance. See the single
repository `VERIFICATION.md` record for actual scope.

The server finds the engine beside itself: `apps/issuer-library/engine` in the
repository, `engine/` in a package. Only an offline check sets `ISSUER_LIBRARY_ENGINE_ROOT`,
to serve a fake engine. The CP-OS worker runs under the same interpreter as
the server. Do not turn the loopback application into a remotely exposed multi-user
service.

## How the one app is put together

`web/` is the whole front end. `boot.js` reads `/api/catalogue` and `/api/workspace`, then
loads `views.js`, `actions.js` and `screen.js`. If the store cannot be read the app still
opens, states the problem and keeps Settings and Help reachable.

The server discovers runs and deliveries into the catalogue, serves pinned files and the
front end, and runs the New run API; `engine/bridge.py` reviews and starts a run in its own
process. `/api/workspace` imports `engine/store.py`, which parses every retained handoff, at
the run root or in a run's delivery, for the runs the catalogue discovered; there is one
parser. Labels come from the catalogue and the launcher's
`workflow.json`, with hand-written reading labels for the curated runs. `engine/catalog.json`
pins curated visuals to exact files: a pin that no longer matches is dropped and listed under
Settings, and that output falls back to its plain sections. A handoff the parser refuses
stays readable as one flagged block. A file that cannot be read hides its run, also listed.

Reports are served by the server under the same sandbox as before and traced to run files
by SHA-256; a handoff with no matching run file is named. All resources are local. No new
analysis is performed, and missing observations are never plotted as zero. See DESIGN.md for
the screens, and the single repository `VERIFICATION.md` for what has actually been checked.
