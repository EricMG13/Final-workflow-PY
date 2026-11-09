# Issuer Library example

A local, read-only screening directory. Open `index.html` directly in a browser.
Rebuild from this directory with `../../.venv/bin/python build.py`.

This screening now lives in the app's Library (`apps/issuer-library`). This example stays
as the approved reference and its tests keep running.

## Design and implementation plan

Approved direction: one local directory of issuer runs, searchable by identity,
sector and credit metrics, with completeness and links to the existing reports.
Audience: analysts finding a dated case and deciding which evidence to open.
Style: the deliverables' Direction C shell, using their actual `tokens.css`,
`app.css`, State Street logo and seven Red Hat font faces. The navy rail, white
navigator, compact headings, square report blocks, status colours and right-aligned
Mono figures share the report design system. `style.css` supplies only the library
composition and responsive overrides; it defines no separate colour palette.

Work is executed inline; no analytical execution or provider calls.

- [x] Pin curated real-run metadata and exact source excerpts in `catalog.json`.
  Preserve each issuer, date, metric definition, currency and missing value.
- [x] `build.py` verifies all source pins and report bundles, then embeds the
  catalogue, local fonts, CSS and scripts into `index.html`. All links remain
  relative to this example directory. Historical files are read only.
- [x] `logic.js` provides pure filtering and sorting; `app.js`, `style.css` and
  `template.html` implement accessible controls, run details and report history.
- [x] Add a separate fictional dataset to demonstrate numeric completeness.
  Real-run workflow completeness remains unassessed; no score follows from
  file presence, module counts or successful hashing.
- [x] Check source/hash failures, relative paths, null/zero numeric filtering,
  incompatible metric bases, simulated keyboard operation and report links. Browser layout checks remain open.
- [x] Perform confidence review and post-edit rewrite tournament inline; record
  the result in the project's existing `VERIFICATION.md`.

## Data scope

The real catalogue is a curated snapshot, not automatic discovery or CP-OS
integration. New runs need explicit catalogue entries. Its source excerpts are
verified against pinned handoffs on rebuild; the page records its build time.
Financial periods and case evidence dates are distinct. Issuer tags transferred
from another handoff name that source explicitly; unestablished tags stay unknown.

The fictional dataset exists only to exercise screening controls. Its completion
score is completed requirements divided by total required checkpoints, including
sources, analysis, checks, downstream use and delivery. No illustrative issuer
has an actual report link. Completion describes workflow progress, not credit
quality; real scoring needs a scope-specific, verified checklist.

## Files and checks

`catalog.json` is the reviewed input snapshot; `index.html` is generated output.
`test_build.py` verifies admission and transport boundaries.
`tests/test_issuer_library_example.py` checks numeric filtering, unknowns,
definitions, sorting, illustrative scores and the page's controls in a real browser.
No network access, package installation or local server is needed to use the page.

## Verification scope

The Python admission tests and the headless Chromium checks of the screening
logic and page controls pass. Headless Chromium executes the page's scripts and
layout but is not a visual acceptance: responsive rendering and opening reports
from the double-clicked file remain unverified. The file opens directly for the user.

The catalogue's numeric mappings are curated and checked against handoff rows.
The builder validates pinned source text and literal value presence; it is not
a general financial parser or an automatic verification of period/definition
semantics. Sector tags retain their specific source. Unknown tags stay unclassified.
Rebuilding checks the snapshot; the already-open page does not monitor file changes.

Run from the project root:

```sh
.venv/bin/python examples/issuer-library/build.py
.venv/bin/python -m unittest discover -s examples/issuer-library -p test_build.py
.venv/bin/pytest -m browser tests/test_issuer_library_example.py
.venv/bin/ruff check examples/issuer-library/build.py examples/issuer-library/test_build.py
```

The browser checks drive the generated page in headless Chromium through Playwright, a
dev dependency that is not part of the HTML runtime. Run `uv run playwright install
chromium` once, or set `ISSUER_LIBRARY_CHROMIUM` to an installed Chromium executable.
