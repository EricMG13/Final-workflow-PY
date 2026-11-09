# Manifest writer fixtures (Plan 4C answer key)

Written 2026-11-08 by an agent separate from the writer's author; the code's author may not edit them. Synthetic issuers (Northwind, Harbor Lane) are fictional.
- `synthetic/` (`synthetic-hy-001`): high-yield private-side run; context and CP-1 are byte copies of `../synthetic/`; receipt, one delivery folder (with `view.json` listed in `delivery.json`), all checklist items done.
- `retained/` (`web-04cd...`, TDG FY2024): retained model output; only `expectations.json` is hand-written, `copy.json` lists the byte-for-byte copies from `runs/` (the `inputs/ec0a...` file becomes `context.json`) the test must make into a temp workspace first.
- `edge/` (`synthetic-edge-001`): interim `h1-2025`; LTM row chosen, `Not supplied` net leverage, two LTM cover rows (no metric), `1,250` cash with a negative undrawn (no metric), empty-id deal term and empty rating skipped, quote on a facility with no deal term, no receipt, no delivery; CP-1A is requested but has no handoff (item not done).
- `missing-expectations/`: no `expectations.json`; `expected-error.txt` holds `expectations.json`, which the `ManifestError` message must name.
- Compare `expected-library.json` as parsed JSON (key order is the spec's order but not binding); sources are compared in full, including the quote's leading spaces and trailing commas.
- `workspace/` is the workspace root. Every sha256, line and quote was computed from the final bytes and checked by a throwaway script.
- `run.issuer` is always `identity.issuer_id` (R-25; `tdg` for retained). Choices where the spec is silent: the line of a `delivery.json` or receipt hash is the whole line with its indentation; `receipt_report` and delivery evidence order follows the checklist; the chosen delivery's report hash is the `delivery.json` value (it equals the file's real hash in every case).
