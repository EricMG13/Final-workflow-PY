# Library manifest fixtures (Plan 4 Task 12 answer key)

Hand-written on 2026-11-08 by an agent separate from the author of the admission code; the code's author may not edit them.
- `synthetic/`: fictional high-yield private-side run `synthetic-hy-001` (Northwind Fabrication Holdings is fictional). `workspace/` is copied as the workspace root; `library.json` is the manifest to admit.
- `synthetic/expected-served.json` and `retained-cp1/expected-served.json`: the subset `/api/catalogue` must serve (source keys namespaced `<run id>.<key>`); a key absent here must be absent or empty when served.
- `retained-cp1/library.json`: manifest for "retained model output (web-04cd..., TDG FY2024)". The test copies that run's CP-1.md and its context file byte-for-byte from the repository, then writes this manifest as the run's library.json.
- `reject-cases.json`: each item changes one JSON-pointer location in a fixture's library.json (RFC 6901; a pointer to a missing object member adds it); the whole manifest must be rejected ("Run metadata rejected:").
- `accept-cases.json`: same shape; each change must still be admitted.
- Every sha256 and quote is computed from the final files; do not edit a fixture file without recomputing them.
