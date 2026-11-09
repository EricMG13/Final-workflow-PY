# Library credit screening answer key

Written 2026-11-08 by an agent separate from the author of the screening code. All issuers are fictional.
Follows `.superpowers/sdd/2026-11-08-plan-4-library-credit-data/task-13-filter-spec.md` (binding).

- `rating-scale.json`: rating scale and placement answer key (committed earlier, Task 13a).
- `screening-catalogue.json`: 18 served-shape catalogue rows (`real`) plus `sources`; sha256 values are a fixed placeholder, no file is read.
- `filter-cases.json`: filters, expected sorted ids and per-group `{recorded, hidden}` coverage, derived by hand from the spec.
- `sort-cases.json`: expected full ordered ids for `net_leverage` and `rating` sorts, both directions.
- Judgment calls are recorded in each case's `why`; implementers must not edit these files.
