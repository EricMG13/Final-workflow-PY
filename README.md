# Final Workflow (Python variant)

This repository is the Python variant of `EricMG13/final-workflow`. The Issuer Library
server is FastAPI on uvicorn (`src/issuer_library`), and its browser checks use pytest with
Playwright. The original repository keeps the Go server and the Node test harness.

**The Issuer Library is the application.** It is a local browser app for finding dated issuer
runs, screening them, reading their module outputs and reports, and preparing and starting new
CP-OS runs. Everything else in this repository is the engine behind it, the design work for it,
or a record of how it was built.

```
Issuer source files → CP-OS runs the analytical modules → Markdown handoffs →
separate delivery process → reports shown in the Issuer Library
```

Excel files are analytical inputs only; no deliverable is an Excel workbook.

## Start here

| What | Where |
|---|---|
| The app: Windows launch, New run, workspace, local session, discovery contract, packaging | [`apps/issuer-library/README.md`](apps/issuer-library/README.md) |
| What the product is for, and its approved direction | [`apps/issuer-library/PRODUCT.md`](apps/issuer-library/PRODUCT.md) |
| Design system: colours, type, components | [`apps/issuer-library/DESIGN.md`](apps/issuer-library/DESIGN.md), [`DESIGN-SOURCES.md`](apps/issuer-library/DESIGN-SOURCES.md) |
| Screens and navigation | [`apps/issuer-library/INFORMATION-ARCHITECTURE.md`](apps/issuer-library/INFORMATION-ARCHITECTURE.md) |
| The approved Library screening design (reference for the app's Library screen) | [`examples/issuer-library/`](examples/issuer-library/README.md) |
| What is being built next, in order | [`docs/superpowers/plans/2026-11-08-run-expectations.md`](docs/superpowers/plans/2026-11-08-run-expectations.md) (index of Plans 1-5) |
| Project rules | [`AGENTS.md`](AGENTS.md) |
| Which method revision each module uses | [`METHODOLOGY-REVIEW.md`](METHODOLOGY-REVIEW.md) |
| Quality gate and test schedule | [`docs/QUALITY-GATE.md`](docs/QUALITY-GATE.md) |
| Verification record (recent; older entries in the archive) | [`VERIFICATION.md`](VERIFICATION.md), [`docs/VERIFICATION-ARCHIVE.md`](docs/VERIFICATION-ARCHIVE.md) |
| Superseded reviews, executed plans and the previous README | [`docs/archive/`](docs/archive/README.md) |

## Run the app from source

From the repository root, after `uv sync --locked`:

```bash
PYTHONPATH=src uv run python -m issuer_library --workspace "$PWD"
```

It opens the browser on the signed-in Library over this repository's `runs/` and `deliverables/`.
The server finds the engine beside itself, so no other variable is needed. The Windows
package needs neither: see the app README.

## Repository map

| Folder | Role |
|---|---|
| `apps/issuer-library/` | The app: Python server (`src/issuer_library`), `web/` frontend, `engine/` bridge to CP-OS, `designs/` browser and data-flow checks, `packaging/` |
| `examples/issuer-library/` | The approved screening design the app's Library follows |
| `src/deploy_workflow/` | CP-OS (`owners/cpos.py`, `owners/cpos_launch.py`), module owners, provider adapters, delivery |
| `src/deploy_vii/` | Deploy VII analytical code, inputs, report and Model renderers reused by delivery |
| `prompts/`, `docs/reuse/`, `docs/templates/`, `docs/rulings/` | Module instructions, selected method sources, the context form, and live-run rulings the code reads |
| `runs/`, `deliverables/`, `data/`, `cases/`, `handoffs/` | Retained evidence and fixtures. Read-only: never edited |
| `tests/`, `tools/` | Tests, the quality gate and the weekly suite |
| `docs/archive/` | Material kept for the record only; not current guidance |

## How a run works

CP-OS is the only orchestrator. It accepts the issuer files and the requested workflow, launches
the selected modules in dependency order, passes each its current Markdown handoffs, bounds
retries and spend, resumes affected work and invokes the separate delivery process. Delivery
rereads the handoffs and reuses the existing report designs; it never repeats the analysis or
invents missing content. Completion means populated deliverables built from the actual handoffs
and checked against them. A paid run is always an explicit, budgeted action; the build, tests and
browsing never call a provider.

The Issuer Library's New run drives the same launcher as the command line below.

## Start a run from a context file and issuer folder

Select the issuer files, the context file and the model. Without `--live` this only
prepares the run: it reads every file, writes the pinned manifest and module
instructions, prints the plan and makes no provider call.

```bash
PYTHONPATH=src .venv/bin/python -m deploy_workflow.owners.cpos_launch \
  --context path/to/context.json \
  --sources path/to/issuer-folder \
  --config sol-medium \
  --cap 25
```

Add `--live --ruling docs/rulings/<file>.md` to start the paid run; the ruling must
name the selected config, and the provider key must be in the launching environment.
CP-OS then runs the modules in order and publishes `deliveries/<id>/report.html`.

- **Context file:** a `context/1` file, such as one from
  [the context form](docs/templates/context-form.html). It sets the issuer, as-of date,
  case kind and pathway, and every module can read it as the source `context`.
- **Issuer folder:** read recursively. PDF, TXT, Markdown, XLSX, CSV, JSON and JSONL files
  are pinned as they are; HTML filings are pinned as their visible text in cp-os's
  3,000-character pages, headed by the filed document's name and hash. Other files and `_`-prefixed folders are listed as
  ignored, dotfiles are skipped, and an unreadable file stops the launch.
- **Model:** `--config` is `sol-medium`, `sol-high`, `opus-medium` or `deepseek-max`.
- **Cap:** a USD ceiling per run folder. Each call holds up to its worst-case price
  against the cap until it settles (USD 5.73 for `gpt-6.1-sol`), and a cap too small
  for one call of the largest module is refused before anything is sent.
- **Modules:** the pathway's preset by default. `--modules` narrows it, keeping
  dependencies, and must fill at least one report section.
- **Run folder:** `--out`, or `runs/<run id>`. A changed request, including a new file
  in the issuer folder or a new cap, needs a new folder. Relaunching the same request
  rechecks finished modules without resending them.

**Current limits:**

- The automated checks cover handoff structure, issuer/date/source/upstream anchors
  and report selectors. They hold no independent expected values, so a passing run has
  not had analytical review, and each report says so in its scope.
- It publishes the report only. The HTML Model, charts and calculation JSON need
  issuer-specific row selectors, which remain hand-written manifest work, as does CP-8.
- A module interrupted mid-call, or stopped by the cap, is never resent because its
  charge may be unknown. Finishing that request means a new run folder, which repeats
  and pays for the earlier modules.

- Reads stop once a module's context reaches about 700,000 bytes. The module is told to
  use what it has and record the rest as a gap, so a run over very large filings may not
  read all of them.

One paid test covers this path with historical TDG FY2024 files: CP-0, CP-1 and CP-1A
on `sol-medium`, retained in `runs/cpos-launch-live-002`. An ordinary test run skips it.
A rerun rechecks the retained answers and sends nothing. It passed at USD 0.93, and
[VERIFICATION.md](VERIFICATION.md) records the review of its answers against the filing.
The first attempt, [`runs/cpos-launch-live-001`](runs/cpos-launch-live-001), stopped
during CP-0 after USD 0.29; its reads of whole filings led to the read limit above.

```bash
CPOS_LIVE_RULING=docs/rulings/<file>.md PYTHONPATH=src:. .venv/bin/python -m pytest tests/test_cpos_launch.py -m live -q
```

## Development loop

Develop one bounded module result and its next handoff at a time:

1. **Fix the input.** Name the issuer files, requested scope, selected method
   revision and instructions. Retain the exact instruction file and source hashes.
2. **Run the model and retain its answer.** Keep the actual Markdown output and
   evidence used. State whether execution was a host session, provider call,
   retained-response replay or synthetic test. These prove different things.
3. **Check the answer.** Compare it with the instructions and issuer evidence.
   Check exact amounts, units, periods, source references, missingness and any
   calculations. Use expectations independent of production calculations.
4. **Repair only an observed failure.** Identify whether it is in the instructions,
   model answer, source access, calculation or handoff. Preserve the failed answer,
   make the smallest justified change and repeat the affected check.
5. **Consume the handoff.** The next module must open it and use its content,
   carrying limitations forward. A generated file alone does not pass this step.

Use the same six Markdown headings: Request, Sources, Findings, Calculations,
Gaps, Next module. Preserve module-specific analysis within them; the headings
are a common envelope, not a replacement for the methodology. A failed targeted
check triggers a targeted repair, not another repository or full rebuild.

Keep instructions in `prompts/`, actual run artifacts in `runs/<run>/`, and one concise running
record in [VERIFICATION.md](VERIFICATION.md).
