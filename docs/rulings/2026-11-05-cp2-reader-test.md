# Live test of CP-2's reader standard

lifts: live-provider-pause
by: user
date: 2026-11-05
configs: sol-medium

CP-2's launcher instructions gained the user's Microsoft 365 Copilot custom instruction, Deploy
V's reader-facing rules and a required `### Credit view` opening. Asked whether to commit, the
user instructed "test first".

Scope: one CP-OS run of CP-2 on OpenAI gpt-6.1-sol at medium effort, capped at USD 8, over the
historical TDG FY2024 public files as of 2024-09-30. CP-0, CP-1 and CP-1A are the accepted
handoffs of `runs/cpos-launch-live-002`, copied and pinned as retained, so only CP-2 calls the
provider. Exchanges are retained in `runs/cpos-launch-cp2-reader-001`; live-002 is read, never
written. Unknown charges stop execution; an interrupted call is not resent.

The provider key comes from the launching environment only; no credential file is read. This run
shows how the new instructions read for one dated case. It does not prove other modules, issuers
or configs, or current credit conclusions.
