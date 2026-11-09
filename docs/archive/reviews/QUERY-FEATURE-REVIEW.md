# Query feature: credit and Deploy project review

Reviewed 4 November 2026. Local working-tree/source review; no predecessor repository or historical run was modified. No provider, database, deployment or browser session was started.

The broad issuer query feature is designed but is not implemented end to end in the inspected projects. Three different capabilities must be distinguished: the original Credit OS issuer-chat prototype, CAOS Book's structured filtering/sorting, and the proposed assistant over reusable issuer analysis. Deploy's source-search tools are another useful component, but do not provide that assistant.

## Product direction clarified after the review

The user confirmed a conversational issuer-research product backed by a knowledge graph derived from module outputs, with optional web research. Completed analyses enter the reusable corpus only through explicit addition to a research library; extraction into the graph follows automatically. The requested interface resembles familiar conversational assistants, with a chat composer at the bottom.

The following is the proposed design for that direction, not an implementation claim or authorization for paid execution.

**Local-first requirement, subsequently confirmed.** The application and its storage must run locally and remain usable offline; module/provider AI calls are permitted network operations. The previously requested optional web research necessarily requires connectivity and must be explicitly enabled. Library browsing, stored conversations, graph traversal, deterministic comparisons and viewing existing outputs must not require a cloud service. New provider-generated answers require connectivity unless a separately configured local model is used. Given this constraint, the revised storage recommendation is embedded SQLite plus retained local handoff files: graph entities/edges, provenance, publication/history and conversations in SQLite; local FTS5 narrative indexing; exact decimal text with application Decimal calculations and numeric comparisons rather than floating-point or lexicographic ranking. Semantic retrieval can be added with a local index. This supersedes PostgreSQL as the preferred starting recommendation for this local application; the physical engine remains a proposal pending design agreement. No source deletion or database migration is implied.

**Experience.** A central conversation is the primary workspace. A collapsible left sidebar offers New chat, private conversation history and Research library. A persistent, multiline bottom composer has Send/Stop and a visible Library / Library + web selector. Start with Library selected. Users ask questions and follow up in ordinary language; they do not have to select database tools or query syntax. On narrow screens the sidebar becomes a drawer and the composer remains usable without covering the latest answer.

Answers can contain cited prose, exact comparison tables, charts and relationship views. Evidence details open on demand. Research reports use applicable existing delivery renderers. Graph exploration is an answer format available when relevant; a graph dashboard does not replace the conversation. Show concise progress, actual coverage, dates and cost/limit status without exposing hidden model reasoning. Missing inputs, partial coverage, unavailable web access and interrupted queries get explicit states.

**Knowledge.** Explicit Add to library binds the selected run/handoff revisions, issuer, date, method revision, completion/scope status and source identities. Indexing never silently upgrades a historical or partial analytical case into a complete current assessment. Preserve module Markdown as the analytical authority. Derive dated entities, exact observations, directed relationships, arguments and coverage records with statement/table locators. Include narratives as well as registers. Newer published runs supersede current views while retaining explicit historical access; withdrawals invalidate dependent current results. Never modify original handoffs during indexing.

**Query execution.** Use one controlled tool layer for eligible graph traversal, narrative retrieval, exact filtering/ranking/calculation and optional web search. A bounded model loop selects tools and synthesizes cited answers. The host enforces identities, source mode, exact arithmetic, allowed operations, limits and publication. Web findings carry URLs and retrieval dates and stay distinct from module analysis. Query conclusions remain labelled inferences; neither conversational reasoning nor saving a finding overwrites module facts. Conversations remain private; selected knowledge requires explicit publication to become reusable.

**Approach choice.** Narrative retrieval alone is simpler but cannot establish complete numeric rankings or typed relationships. A graph alone captures relationships but misses much of the analytical explanation. The recommended approach combines a versioned knowledge graph, structured exact queries and narrative retrieval, with web as an optional tool. Select the physical database after checking the chosen host's storage and deployment needs; this design does not pretend the database has been selected or installed. CP-OS remains the analytical orchestrator, and delivery consumes existing handoffs without rerunning analysis.

**First proof.** Explicitly add real dated handoffs, inspect their extracted observations/relationships, ask one exact comparison and one qualitative follow-up, and consume the cited results in the actual conversation UI. Verify exclusions, missing versus zero, period/basis mismatches, private/withdrawn premises, graph direction, failed indexing, web-mode separation and budget stops. Query-generated populated outputs must agree with their supporting handoffs. Offline fixtures and retained-data checks must be labelled separately from separately authorized live model/web proof. Code changes require confidence-review and, for nontrivial functions, rewrite-tournament without subagents.

## Project coverage

Searches covered local first-party source and documentation under `/Users/ericguei/Documents`, excluding dependencies and generated build trees. Relevant source files were then inspected directly. Git revisions identify orientation only: several working trees contain changes, so these are not claims about clean commits or deployed versions.

| Project / local HEAD where available | Query-related implementation and relevance |
|---|---|
| Credit Operating System, including nested `caos` and Modular OS | Actual `/api/chat/issuer` endpoint and issuer-chat UI exist. Browser context is explicitly mock ATLF run #2641. Module RAG retrieves source documents; neither path is the later Book-based cross-issuer assistant. |
| Modular OS; Co-Pilot Agents (`9f42094`) | Analytical prompts, issuer/source discovery, research and handoff conventions. No general issuer-query service located. |
| COAS-V3 (`e0dbcbf`) | Workspace/config scaffolding in inspected app/lib files; no query implementation located. |
| Deploy V (`c4d2e35`); Deploy V Development | Analytical ancestry and Markdown contracts; no general query implementation located. |
| Deploy VI (`5c491b7`); Deploy VI evidence | Analytical/runtime/report work and retained evidence; no general query implementation located. |
| DEPLOY VII (`be92508`); lowercase `deploy-vii` (`f49845d`) | Uppercase project supplies analytical/runtime components. Lowercase directory is essentially initialization/instructions. No general query implementation located. |
| Deploy Workflow (`9f925b2b`) | Module execution, bounded source-pack search, research and deliverable components; no retained-analysis query assistant located. |
| deploy workflow Codex (`2e3966d`) | Parallel analytical/handoff implementation; no general query implementation located. |
| Deploy Workflow Sessions | Searched session trees for feature-specific references; no additional query implementation identified. Their design/data examples are not live query proof. |
| `caos-v2` (`b5a3932f`); `caos-gitleaks` (`4807cb0a`); `caos-workbench` (`79c7f3e`) | All three retain `/query` as a forward to `/book/`. No dedicated Query section in their route inventories. |
| `caos-firebase` (`9e6ca9f0`) | Same route forward. October 11 research proposes typed issuer facts, controlled database tools and an optional web lane; proposals are not implementation. |
| `caos-databricks` (`dfff264c`) | Most complete query design and five implementation plans. Current tree has substantial Book implementation, but still forwards `/query` to Book and lacks the planned query/knowledge packages. |
| `caos-databricks-streamlit` (`98faaef`) | Read-only Directory/Analysis/Model/Book viewer; its documented scope has no model worker or query commands. |
| `caos test` (`433c02e`); `caos-v2-train` | Prototype/local material. `caos test` search filters a predefined client-side result list; this is not analytical query execution. No broader assistant located. |
| `cp-os` (`e67bf0c`) | Source search and issuer-linked CP-DR research briefs exist. Research questions feed modules; this is not a cross-run query conversation. |
| `final-workflow` | Actual module handoffs, source/model tooling and bounded handoff-to-report delivery exist. No reusable issuer knowledge index, publication boundary or query conversation service located. |
| lowercase `deploy` | No substantive project files found in the inspected directory. |

Supplementary feature-specific searches in Agent Files, Loan Compare, Loan Scorecard, RBOT OS, WIP, updated and Documents/Codex found no additional matches. This inventory does not cover inaccessible/cloud-only projects, archive contents, deleted branches or every historical commit.

## Findings and implications

### 1. The existing issuer chat is a prototype, not reusable analytical grounding

[IssuerChat.tsx](</Users/ericguei/Documents/Credit Operating System/caos/frontend/src/components/deepdive/IssuerChat.tsx:15>) builds context from imported demonstration data and explicitly says “all figures mock.” It prepends that context to browser-held conversation turns and sends them through `askIssuer`. The [backend](</Users/ericguei/Documents/Credit Operating System/caos/backend/api/routes/chat.py:47>) authenticates the user, rate-limits requests and forwards the supplied messages to the configured model.

The request has no case/run/artifact identity for the server to resolve and authorize. Citation instructions are prompt text; the response is plain reply text without host-validated evidence references. Browser history uses one fixed ATLF storage key. These are confirmed source properties, not a demonstrated production exploit or deployment finding.

Reuse the interaction idea if helpful. A production query feature needs server-resolved eligible analysis, current authorization, validated provenance, private ownership and explicit spending limits. Simply replacing mock data with real browser context would leave those contracts unresolved.

### 2. The October query handoff understates the Book implementation now on disk

The [October 17 discovery](</Users/ericguei/Documents/caos-databricks/docs/issuer-query-discovery-2026-10-17.md>) describes a four-case, membership-scoped Book and missing publication/grant APIs. That description is stale relative to the inspected current tree:

- [Book commands](</Users/ericguei/Documents/caos-databricks/caos/api/commands/book.py:1>) implement Add/Withdraw, completed-run checks and snapshot-bound publication.
- [Migration 0051](</Users/ericguei/Documents/caos-databricks/caos/store/0051_book_entries.sql:1>) defines stored entries, agency ratings, classifications, exact metric strings, historical identity and withdrawal restrictions.
- [Book reads](</Users/ericguei/Documents/caos-databricks/caos/api/reads/book.py:1>) select the latest live entry and history. The wire bounds are 1,000 issuers and 100 historical entries, with explicit truncation.
- [`entry_run`](</Users/ericguei/Documents/caos-databricks/caos/store/book.py:240>) and Book-grant tests exist. [Book filtering](</Users/ericguei/Documents/caos-databricks/frontend/src/sections/book/filter.ts:1>) compares decimal strings exactly, keeps null separate, and scopes money comparisons by currency.

This is implementation evidence, not a fresh test pass, migration or deployed-access proof. Refresh the query plans against these real interfaces; do not build a second Book. Conversely, Book filtering is not evidence that natural-language reasoning, graph capture or query execution exists.

### 3. The most developed query design still has no corresponding runtime

The [design](</Users/ericguei/Documents/caos-databricks/docs/superpowers/specs/2026-10-17-issuer-query-graph-design.md>) and [handoff](</Users/ericguei/Documents/caos-databricks/docs/issuer-query-claude-handoff-2026-10-17.md>) cover:

- Completed runs explicitly added to Book; latest live entry by default and explicit history.
- Typed observations, relationships, arguments, narratives and capture coverage.
- Exact host rankings; grounded inference kept distinct from stated facts.
- Private conversations, selected explicit publication and transitive withdrawal/supersession handling.
- Finite cost/work limits and budgeted continuation.
- Cited charts, profiles, graph views and research reports; optional separate web research.

These are useful design requirements. However, the proposed `caos/query`, `caos/knowledge`, query store/API modules, QuerySection and query-runtime tests are absent. [Routes](</Users/ericguei/Documents/caos-databricks/frontend/src/app/routes.json:21>) still forward `/query` to Book. No retained model query response plus downstream query-result consumption was established.

The five plans are a starting point for adaptation, not executable acceptance proof. Their own approval text authorizes planning rather than implementation/deletion.

### 4. Knowledge capture and comparison semantics are the main missing work

The earlier [Firebase proposal](</Users/ericguei/Documents/caos-firebase/docs/research/2026-10-11-firebase-features-review.md:90>) starts with an `issuer_facts` read model and controlled ranking tools. The later Databricks design correctly broadens this to narratives and relationships. A metric-only index cannot explain operating exposures; semantic retrieval alone cannot prove a ranking over all eligible issuers.

Capture must preserve issuer/legal perimeter, exact value, missingness, units/currency, period, scenario, metric definition, method revision, source identity and statement locator. Ratings need agency/scale; leverage needs its debt/EBITDA basis. Names alone cannot establish entity identity. Repeated downstream summaries cannot count as independent corroboration.

The current Book list is bounded. A future assistant cannot rank its first 1,000 returned issuers and claim “all issuers” when the response is partial. It needs complete authorized enumeration or an explicit incomplete-coverage result. The same distinction applies to failed capture, unindexed entries and incomparable observations.

### 5. Final Workflow needs an adapter, not wholesale adoption of CAOS runtime contracts

The CAOS capture plans assume canonical records, route nodes, database Book entries and the existing model factory. Final Workflow's selected boundary is actual module Markdown handoffs, CP-OS orchestration and separate delivery. Its [current adapter](src/deploy_workflow/handoff_delivery.py:279) is deliberately limited to CP-1/CP-1A/CP-2 and a five-section report; it is not a general query-result exporter.

For this project, an eligible-analysis manifest should bind the selected handoff bytes, issuer/date, actual execution scope, selected method revision, evidence and limitations. A query projection can index those handoffs without a second analytical execution. It must not relabel every retained file as accepted or every bounded case as a completed issuer assessment.

Adapt the older module map to [METHODOLOGY-REVIEW.md](METHODOLOGY-REVIEW.md) and current instructions: CP-OS owns end-to-end orchestration; CP-8 compares prior/current deliverables; no separate CP-MEMO analytical module; no Excel output requirement. The historical graph-map descriptions of CP-OS navigation, CP-8 calibration and workbook/memo exports are not current authority here.

## Implementation sequence supported by the review

1. Refresh the October design's dependency inventory and select the target runtime explicitly. Record which product decisions carry into Final Workflow; historical approval does not authorize source deletion, paid calls or migration here.
2. Define eligible run/handoff publication and immutable provenance. Reuse existing Book contracts where running CAOS; adapt checked handoffs where running Final Workflow. Preserve private, partial and historical boundaries.
3. Prove deterministic extraction and exact filter/rank/compare tools on a small real handoff corpus. Include missing/zero, mixed definitions/currencies, agency ratings, duplicate lineage, stale entries and truncated populations. Keep expected results independent of production calculations.
4. Add the bounded conversational loop, private results and citations. Ground narrative inference in identified premises; publish selected knowledge only through an explicit action. Integrate with the selected host's existing accounting rather than assuming CAOS APIs exist in Deploy.
5. Render query tables/charts/research outputs through applicable existing designs and export code. Check populated outputs against the handoffs. Queries that reveal missing analysis should request a targeted module repair through CP-OS, not invent it.
6. Add relationship exploration and optional web research within the same provenance/mode rules. A separate graph database is not required to establish the first working query path. Source-retention cutover needs its own explicit scope and proof; the October 24-hour deletion proposal is not an instruction to delete current evidence.

The first useful vertical slice is one exact, cited comparison over real eligible handoffs, followed by one grounded qualitative question, both with visible coverage. A chat mockup, passing parser fixtures or successful handoff indexing alone would not complete it.

## Verification record and limits

Performed: project inventory; feature-specific searches; direct source/document inspection; local HEAD/status orientation; JSON assertions confirming `/query -> /book/` and absence of a Query section in five CAOS route inventories; explicit existence checks for the proposed Databricks query/knowledge implementation paths. Those static assertions passed. Current Book code was checked against the older discovery claims, revealing the dependency drift above.

Only this review document was added. No application code changed, so code-change confidence-review and rewrite-tournament gates were not triggered. No synthetic query result was presented as live/model success.

Not verified: application test suites; database migrations or concurrent authorization/accounting; deployed behavior; query extraction precision/recall; actual provider answers or cost; source deletion/backups; browser accessibility/performance; cloud-only projects or archived history. No end-to-end query feature is claimed proven by this review.
