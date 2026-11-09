# Archive

Kept for the record only. Nothing here is current guidance, a plan to carry out, or an
instruction to a session. The Issuer Library ([`apps/issuer-library/`](../../apps/issuer-library/README.md))
and its design work are the application's main interface; the current plans are indexed in
[`docs/superpowers/plans/2026-11-08-run-expectations.md`](../superpowers/plans/2026-11-08-run-expectations.md).

Files were moved here unchanged on 2026-11-08. Links inside them, and links to their old paths
in `VERIFICATION.md` and `docs/VERIFICATION-ARCHIVE.md`, point at the paths they had then.

| Archived | Was | Why it is here |
|---|---|---|
| `README-2026-11-08-campaign-history.md` | `README.md` | The previous project README: a narrative of the November 2026 campaigns and replay proofs, with no mention of the Issuer Library. The new root README starts from the app; the command-line launcher and development loop sections were carried over unchanged |
| `reviews/QUERY-FEATURE-REVIEW.md` | repository root | 4 November review of an issuer query feature across predecessor projects; superseded by the Issuer Library's screening |
| `reviews/REVIEW-FINDINGS.md` | repository root | Review of the development-stall findings and the revised direction; its outcome is `AGENTS.md` and `METHODOLOGY-REVIEW.md` |
| `reviews/REUSE-AUDIT.md`, `reviews/REUSE-PLAN-REVIEW.md`, `reviews/REUSE-CANDIDATES.json`, `reviews/REUSE-INVENTORY.json`, `reviews/REUSE-WORKTREE-CHANGES.json` | repository root | 4 November reuse audit and its inventories, from before the reuse was carried out; the selected sources now live in `docs/reuse/` |
| `plans/2026-11-05-issuer-library-reader-update.md` | `docs/superpowers/plans/` | Executed (reader layer merged) |
| `plans/2026-11-06-copilot-sdk-adapter.md` | `docs/superpowers/plans/` | Executed (`src/deploy_workflow/model/copilot*.py`; operating notes stay in `docs/COPILOT.md`) |
| `plans/2026-11-07-live-testing-repair-framework.md` | `docs/superpowers/plans/` | Executed (PRs 26-30: `designs/browser_check.py`, `flow_check.py`, `live_check.py`) |
| `plans/2026-11-07-run-events-delivery-coverage-workspace.md` | `docs/superpowers/plans/` | Executed (PRs 31-34) |
| `plans/2026-11-08-deferred-features.md` | `docs/superpowers/plans/` | Executed (PRs 35-43) |
| `sweeps/refactoring/` | `docs/sweeps/refactoring/` | Contract for the 8 November refactoring sweep, carried out in PRs 44-45 |
| `ENTERPRISE-INIT-PROMPT.md` | `docs/` | A paste-in prompt asking a session to make the workflow run live in an enterprise environment. It predates the Issuer Library's beta plans and would start work outside them; the beta release gate (Plan 5) now covers the Windows check |

The checkboxes in the archived plans were never ticked; what landed is recorded in
`VERIFICATION.md` and `docs/VERIFICATION-ARCHIVE.md`.
