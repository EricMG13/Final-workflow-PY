# Final Workflow

Orchestrate the Deploy V-derived analytical workflow over issuer source files,
retaining applicable later methodological corrections and module Markdown handoffs,
and use a separate delivery process to construct the deliverables defined in the
Deploy Workflow project from those handoffs.
The current user's instructions govern this project. Imported comments, historical
plans, staff roles, pauses and approval records are evidence, not inherited authority.

- Subagents are permitted for implementation, review and verification.
- Work one analytical module at a time: compare its actual model output with the
  instructions sent and issuer evidence, then change only what that comparison
  justifies. Version comparisons support this work; they are not acceptance proof.
- To prove module function, use an alternative issuer or an older source when
  the current case lacks access. Clearly label outdated evidence and case scope;
  keep each issuer/date separate. Do not let unavailable TDG inputs stop other
  functional proof, or present an isolated case as a complete TDG pathway.
- CP-OS is this version's active orchestrator. It accepts the issuer files and
  requested workflow, orders and launches the selected analytical modules, supplies
  current Markdown handoffs, tracks progress, bounds retries/cost, resumes affected
  work and invokes the separate delivery process. Its M365 navigation-only
  restriction does not apply here. Do not add a competing orchestration layer.
- Select methods using METHODOLOGY-REVIEW.md: Deploy V supplies the ancestry and
  analytical breadth; later projects supply corrections and additions, as well as
  documented scope reductions. Neither the oldest package nor the newest project
  is an automatic authority for every module. Record the selected source revision.
- Excel is an input format for analysis only. Do not generate Excel workbooks
  or treat workbook export as a deliverable/completion requirement. Reuse the
  existing report, HTML Model, chart and calculation-JSON outputs as applicable.
- Analytical modules own analysis and inter-module Markdown communication.
  Markdown handoffs are intermediate artifacts, not completion of the user task.
- CP-8 compares deliverables from prior runs with the latest current run:
  values, periods, assumptions, conclusions, sources, limitations and output scope.
  It explains material changes and unresolved differences. The imported investment
  decision post-mortem/calibration task is superseded; it is not an input gate.
- CP-MEMO is replaced by the actual deliverables. Do not schedule a separate
  memo analytical module; the delivery process assembles outputs from handoffs.
- The delivery process reads those handoffs and reuses Deploy Workflow's existing
  deliverable designs, renderers and applicable calculation/export code. Add the
  necessary input adapter; do not require a second analytical execution merely
  to satisfy the later runtime's internal contracts.
- Preserve values, periods, units, source references, limitations and analytical
  conclusions across that boundary. Missing handoff content remains an explicit
  gap or a targeted repair request; delivery must not invent replacement analysis.
- Completion requires populated final deliverables constructed from actual module
  handoffs and checked against them, not just successful handoff generation.
  CP-OS owns this end-to-end completion condition, including delivery.
- Keep expected values independent of production calculations. Preserve exact
  amounts, missing versus zero, quantity family, currency, dates and source identities.
- A live/model success requires actual retained model responses and downstream
  consumption. Synthetic regressions and deterministic retained-data reports must
  be labeled with their actual scope.
- No credential files. Provider keys may come only from the launching environment.
  Paid execution is a separate, explicit action after offline readiness; the build
  itself does not run providers.
- Run confidence-review after code changes: enumerate doubts, trace their causes,
  test adversarial cases and repair confirmed defects before completion.
- Run rewrite-tournament in post-edit mode for nontrivial changed functions,
  retaining the simplest correct design.
- Run the quality gate on changed code before completion: `uv run python
  tools/quality_gate.py` (docs/QUALITY-GATE.md). Changed lines and the functions they
  fall in must pass ruff, the complexity limits, `ruff format` and strict mypy;
  the existing code outside that scope is not in the gate.
- While working, run fast targeted tests only (each run within a few minutes; `timeout 300`).
  The full suite, slow tests included, runs weekly (Sunday 01:00 UTC) in GitHub Actions
  (docs/QUALITY-GATE.md); a failure there not in tests/nightly-known-failures.txt is new.
- Keep one concise verification record. Entries older than two days move verbatim to docs/VERIFICATION-ARCHIVE.md; VERIFICATION.md stays under 1,000 lines. No review/brief/lease proliferation.
- Never mutate predecessor repositories or historical live run directories.
