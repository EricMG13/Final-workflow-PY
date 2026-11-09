# Plan 5: Beta V1 Release

> **For agentic workers:** Steps use checkbox (`- [ ]`) syntax. Subagents are permitted for
> implementation, review and verification (`AGENTS.md`); expected values are never written by the
> agent that writes the code they check. Split on 2026-11-08 from the combined plan revised after
> its adversarial review.

**Goal:** decide release readiness for the first beta on the `main` commit to be released.

**Depends on:** Plans 1-4 merged, each with its checkpoint recorded in `VERIFICATION.md`.

**Shared rules:** the index, [`2026-11-08-run-expectations.md`](2026-11-08-run-expectations.md), holds the owner decisions, global constraints, the live-check method, the required outputs and the review record. They apply here unchanged. Review Focus numbers and task numbers are kept from the combined plan, so cross-references still resolve.

## Release gate

Run once after Plan 4's Checkpoint D, on the `main` commit to be released:

1. Plans 1-4 merged, and each plan's checkpoint recorded in `VERIFICATION.md`.
2. `validate.py full`, `validate.py browser` and `validate.py suite`. No failure beyond
   `tests/nightly-known-failures.txt`. While GitHub Actions starts no jobs, these local runs stand
   in for CI, and the record says so.
3. **RC-live:** if code changed after C3, one more whole-pathway run on the release candidate
   (Credit Snapshot, TDG FY2024, cap USD 30), with every required output checked.
4. The packaged app on Windows: the owner runs `Smoke-test.ps1`, then opens the app in Edge, creates a
   run up to the Review step, opens a live run's report and the Library filters.
5. Help and README describe exactly what the beta does, including known limitations: the HTML Model
   and `calculation.json` are not published by app runs; Primary terms are Provisional before
   closing; metrics are Not recorded for older runs.
6. Owner sign-off.

## Done when

The release gate has passed on the released `main` commit, including the Windows smoke test and the
owner's sign-off.
