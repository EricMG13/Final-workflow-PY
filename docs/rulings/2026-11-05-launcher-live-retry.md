# Retry of the CP-OS launch command's live test

lifts: live-provider-pause
by: user
date: 2026-11-05
configs: sol-medium

After the first attempt stopped in CP-0 at USD 0.28956660, the user was asked whether to match
cp-os's 3,000-character HTML pages and retry within the USD 12 total, and instructed
"Match it then retry".

Scope: one run of `test_live_launch_from_a_context_file_and_issuer_folder`. It runs CP-0, CP-1 and
CP-1A on OpenAI gpt-6.1-sol at medium effort, capped at USD 11.71, over the retained historical TDG
FY2024 public files, and retains its exchanges in `runs/cpos-launch-live-002`. Unknown charges stop
execution; an interrupted call is not resent.

The provider key comes from the launching environment only; no credential file is read. This run
proves the launch path for this dated case. It does not prove other configs, other issuers, the
full pathway preset or current credit conclusions.
