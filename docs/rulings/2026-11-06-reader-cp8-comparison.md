# CP-8 comparison of the reader-layer live run against the prior launcher run

lifts: live-provider-pause
by: user
date: 2026-11-06
configs: sol-medium

The user instructed, in order: "run test using gpt to check if design update";
"Approve, USD 12 cap"; "proceed with tests"; then, after the retained run
`runs/web-04cd5a5d02ea7d1dea714a8a6632cd21` was reported, "Yes, run CP-8".

Scope: one bounded CP-8 deliverable comparison through CP-OS (`run_live_comparison`)
on sol-medium, prior = `runs/cpos-launch-live-002` delivery `ce11d9e8…`, current =
`runs/web-04cd5a5d02ea7d1dea714a8a6632cd21` delivery `278856a3…`, both TransDigm as
of 2024-09-30. Cap USD 12, one outer attempt, repairs inside the loop. The key comes
only from the launching environment; no credential file. No predecessor or
historical live directory is mutated; the new run directory is
`runs/cpos-tdg-reader-comparison-001`.
