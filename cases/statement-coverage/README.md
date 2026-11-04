# Statement coverage answer key

Frozen answer key for the CP-1 financials coverage gate, ruling CP1H-R20, task T16.

## Sources

- Run 3 (`artifacts/model-testing/cp1h-live-3/pilot-sol-high-earnings_update-4/execution/owner-run-audit`, `submissions/` and `payloads/`): the three `shc-seq*` files.
- Run 4 (`artifacts/model-testing/cp1h-live-4/pilot-sol-medium-earnings_update-5/execution/owner-run-audit`): the two `shc-run4-*` files.

## Files and sha256

Each sha256 equals the file's original content-addressed name.

| File | sha256 |
| :--- | :--- |
| shc-seq7-submission.json | 1b081243ec7946292fb00d6a5c645fc96d99a2a4e64e7d195011660e3c02710d |
| shc-seq7-stored.json | 50560157288307de91edaa12764b02fcd5d18f48669965bf63e5d0def5cb98cc |
| shc-seq6-submission.json | 76f47321c0d9c9840c335dc5a2c17998b966e1909d9b219262a6819f7181f9b5 |
| shc-run4-seq6-submission.json | 4bdaf20ee146ea596e8036349bfbaa0fa5b7d8e433197883a2d00621e1adf78d |
| shc-run4-seq6-stored.json | 912f35116257501f7f16cb2b1a85e7cdabdbc84a6da05ec0cd1279869ab82790 |

## Expected results

- Before T16 (1b8644c3), each submission gives exactly 215 "Uncovered extracted statement line" issues.
- After T16:
  - seq 7 gives exactly 25, all at locator line:82-114 of the SHC 10-Q source.
  - seq 6 gives 215, because no citation quote holds its row label.
  - run-4 seq 6 gives 177.
- Neither "Financials must extract every located statement unit" nor "Statement extraction is unmeasured" appears for seq 7 or run-4 seq 6.

The expected counts came from the coverage pre-flight's probes (`work/build/cp1h/preflight-coverage.md`) and are re-derived by an independent oracle reviewer. Builders do not edit this directory.
