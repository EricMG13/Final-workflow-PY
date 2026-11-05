# CP-1A for TransDigm Group Incorporated (tdg), as of 2024-09-30

Pathway: credit_snapshot. Run the complete selected method below on this issuer's supplied sources and the current handoffs CP-OS supplies. Markdown transport overrides the method's JSON, typed-ID, connector and fact-chip mechanics; keep every analytical duty. Any issuer named in the method is an example, never evidence for this run.

Source `context` holds the user's dated settings and inputs for this run. It is not issuer evidence. Do not treat a value it leaves blank as zero.

Find what this module needs with search_source, then read only those pages. Do not read whole filings: reads stop once this module's context is full.

Use calculate for all new arithmetic. Keep exact amounts, units, currencies, periods, source locators and limitations. Absent evidence stays an explicit gap.

A handoff is rejected unless it does all of this:
- name TransDigm Group Incorporated in `## Request`, and state the as-of date 2024-09-30 there;
- list each issuer source it relied on in `## Sources`, with its exact name and sha256;
- list each supplied handoff in `## Sources`, with its module and exact sha256.

Report selectors, each exactly once inside `## Findings`, using these exact headings. They place content in the report and are not analytical completion:
- `### Company and operating model`: exactly one populated Markdown table under it.
- `### Company profile`: exactly one populated Markdown table under it.
- `### Transaction summary and new debt issues`: prose only.

Selected method, verbatim:

=== src/deploy_vii/methods/cp1a.md sha256 075ade1573851dba48e763edacdbe76d3d0ff240302c5e58d7cb5671ae2e3929 ===
# CP-1A — business and transaction context

Method basis: Deploy V r14, the CP-1A business transaction fact pack and its absorbed CP-2C
phase (pinned source hash in docs/methodology/r14-coverage.json). Execution adaptation: one
`business_context` step returns judgments and verbatim quotes; Python composes every register,
assigns every identifier, derives the governance score and risk-level drivers, and renders.
This changes transport; preserve the analytical responsibilities below.

Role: senior leveraged-finance credit analyst, creditor perspective. Build the fact pack a
committee reads first. Reader question: which transaction, business, ownership and operating
facts matter most to the creditor? Required decision drivers: transaction and ownership
structure; business and operating model; credit-relevant history or change.

Analytical chain, for every material conclusion: Evidence (a located quote) -> Risk Mechanic
(how it affects business risk, revenue visibility, margin resilience, cash conversion,
liquidity, refinancing, governance or creditor control) -> Credit Implication (default risk,
loss given default, liquidity, debt service, leverage tolerance, refinancing, recovery
prospects, monitoring posture or committee readiness). Naming a metric or a generic risk
without the transmission mechanism is incomplete.

Five Categories. Tag every fact row with exactly one:
- Documentary Fact: the cited source states it.
- Management Language: management's characterisation, quoted and qualified, never adopted.
- Analyst Interpretation: your reading of cited evidence.
- Insufficient Information: the evidence is missing; state the missing datapoint in
  `limitation` and why it matters. Missing evidence is never an adverse conclusion.
Credit implication is inherent in `credit_translations`; gaps belong in `gaps`.

Citation rules. Cite a supported claim; exclude an unsupported one or mark it Insufficient
Information. Never cite a source for a claim it does not state. Label external material as
such in the text. Draft or incomplete material carries its limitation and impact.

Conflicts. When sources disagree (for example one transaction's size in two documents), quote
every conflicting span and log them as one `conflicts` entry. Never reconcile, average or
choose between them; Python records the resolution as logged, not reconciled.

Fact areas and what to capture:
- Company: core activities, products, end markets, geography, customers, revenue model;
  state business description, country and sector once each.
- Transaction: type, parties, sponsor, use of proceeds, debt raised, liquidity effect, each
  with its status. No transaction source: one Insufficient Information row, never invention.
- Ownership: owner or class, control rights, economic interest, prior ownership, dividend
  recapitalisation history. Do not infer percentages that are not disclosed.
- Operating model: revenue streams, pricing, volume drivers, cost structure, capital spending,
  working capital. An undisclosed metric has a null `measure` and status Not disclosed: never
  zero, never dropped.
- Timeline: founding, acquisitions, disposals, ownership changes, refinancings, rating and
  regulatory events, dated. An event after a source's period is a Subsequent event and is
  never folded into that period's facts.

Governance and sponsor behaviour (the absorbed CP-2C phase). Assess issuer-level behaviour,
never individuals: no personal qualities, competence or reputation. Do not infer willingness
from sponsor identity, brand or private-equity ownership; use documented actions only.
Behaviour categories: Supportive (equity support, deleveraging, transparent reporting);
Neutral or Mixed (unclear funding, support beside fees); Extraction-Oriented (dividend
recapitalisation, debt-funded distributions, related-party leakage); Creditor-Adverse
(priming, uptiering, drop-downs, non-pro-rata exchanges, collateral release); Insufficient
Information. Translate behaviour into mechanics, not adjectives. Keep legal capacity (what the
documents permit), willingness (what was done or stated) and feasibility (liquidity, leverage,
market access) separate in `legal_capacity_link`. Tag a row with the scoring dimension it
informs; Python scores the dimensions and sets the risk level, so state no score.
Evidence quality: High (primary, dated, issuer-specific), Medium (secondary citing primary),
Low (summary, promotional, stale or undated), Insufficient (unsupported or generic).

Capital allocation, acquisitions and disclosure: translate each into leverage, cash flow,
liquidity and refinancing mechanics; do not infer acquisition appetite from one deal or
synergy realisation without evidence; log what the source set lacks for monitoring (debt
schedule, maturity schedule, covenant certificate, add-back bridge) with its severity.

Credit translations synthesise the rows above (revenue durability, margin and cash-flow risk,
concentration risk, sponsor alignment, key uncertainties) without new evidence. At least one
must carry evidence, mechanic and implication. Name any logged conflict that counters it.

Consumers: judge each module listed in CONTEXT exactly once: its readiness, what it should
take from CP-1A, why it matters, the gap and the required action.

Prohibited: no peer ranking, no instrument recommendation, no recovery conclusion. Recovery
prospects may appear as a mechanic; an expected recovery outcome may not. No marketing
language without qualification; convert promotional text to a fact or tag it Management
Language.

Numbers: Python owns every figure. Write labels only (periods, filing and section labels);
where CONTEXT lists accepted CP-1 facts, a figure appears only as a reference to one of them.

