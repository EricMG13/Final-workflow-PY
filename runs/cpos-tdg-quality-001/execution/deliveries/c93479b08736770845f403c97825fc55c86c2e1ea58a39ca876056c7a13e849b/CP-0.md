# CP-0 — TDG retained interim source readiness

## Request

Prepare the four retained HTML filings for financial analysis, prioritizing the
December 28, 2024 Form 10-Q and its comparative columns. Execution is the current
host model with local tools and existing preparation code, with conversation
context available. No provider/API or imported readiness runtime was invoked.
The supplied pack is historical and does not establish current 2026 conditions.

Result: **ready with limitations for the next CP-1 increment**. The primary
statements, cash/debt notes and period metadata can be read. Full content/visual
coverage of all four filings and full module-workbook sufficiency remain open.

## Sources

`source-preparation/manifest.json` pins all four raw sources, extracted text and
inline metadata. All twelve raw/text/metadata hashes matched on this run. The
raw HTML files are issuer evidence; generated text and inline JSON are reading
aids. Paths below are relative to the project root under
`data/public-corpus/v1/TDG/`; corresponding `.txt`/`.xbrl.json` aids are in this
run's `source-preparation/` directory.

| Source | Raw filename | Raw SHA-256 |
|---|---|---|
| H1 | TDG_2024-03-30_10-Q_0001260221-24-000046_tdg-20240330.htm | 7e902c48d87067b4ea96c388ab2ca460c9c1c3c2e2960da09629377a7b359b0d |
| H2 | TDG_2024-06-29_10-Q_0001260221-24-000069_tdg-20240629.htm | 74876b8874a3a396efd700114b280f45fcfcd3f11ceae31adee98c93bfacbf03 |
| H3 | TDG_2024-09-30_10-K_0001260221-24-000083_tdg-20240930.htm | fe8e1ae9f3fa8c44445b21396c0423153ae9cf80ef6e8c908574d84a63e14121 |
| H4 | TDG_2024-12-28_10-Q_0001260221-25-000014_tdg-20241228.htm | 9bdfd29ebc3c57b72d506e7dff2a2ca2e3179035deb4941dcd026523a5b8595a |

Method: Deploy V-derived source readiness, amended for actual source coverage
and the current Markdown transport as in `METHODOLOGY-REVIEW.md`;
`src/deploy_vii/methods/cp0.md` records the later adaptation's pinned reference
`bd71346301b373afa72655916a4c1b42bf4c9823`. Exact current method/instruction
hashes are recorded in the verification record. The existing annual PDF is a
separate retained presentation of FY2024; H3 is not byte-identical to it.

## Findings

### Identity, authority, accounting and periods

All four covers identify **TransDigm Group Incorporated**, SEC file 001-32833,
and the inline contexts identify CIK 0001260221. Each cover says either Form
10-Q or Form 10-K and names the reporting date. These are retained filings;
external retrieval, authenticity and completeness against SEC exhibits were
not checked again. Filename dates were not used as the identity oracle.

H4 text line 197 defines the Company as TransDigm Group Incorporated and its
subsidiaries, identifies unaudited interim information, U.S. GAAP annual
accounts, the audited September comparison balance, normal recurring management
adjustments and prior-year reclassifications described as immaterial. It says
the interim results are not necessarily indicative of the full year. These
statements support consolidated interim analysis, not a new audit opinion.

| Source | Located cover and statement scope | Exact undimensioned duration examples |
|---|---|---|
| H1 | Cover line 4: “For the quarterly period ended March 30, 2024”; income heading lines 78 onward; cash flows lines 171 onward | Quarter 2023-12-31–2024-03-30; YTD 2023-10-01–2024-03-30; comparative quarter 2023-01-01–2023-04-01. |
| H2 | Cover line 4: “For the quarterly period ended June 29, 2024”; income lines 75 onward; cash flows lines 186 onward | Quarter 2024-03-31–2024-06-29; YTD 2023-10-01–2024-06-29; comparative quarter 2023-04-02–2023-07-01. |
| H3 | Cover line 4: “For the fiscal year ended September 30, 2024”; primary statements lines 898–1060 | Annual 2023-10-01–2024-09-30 and comparative annual contexts. A context alone does not establish a complete separately reported quarterly statement. |
| H4 | Cover line 4: “For the quarterly period ended December 28, 2024”; income heading: “Thirteen Week Periods Ended” | Current c-1: 2024-10-01–2024-12-28; prior c-5: 2023-10-01–2023-12-30. Balances c-3: 2024-12-28; c-4: 2024-09-30. |

Retain issuer week labels and exact source context dates together. Do not
replace the current quarter's source start with an assumed Sunday, force an
equal calendar duration, or treat a balance instant as a flow window. Later
earnings comparability must consider these actual periods.

### H4 statement and note map for CP-1

| Content | Text-aid lines / source locator basis |
|---|---|
| Balance sheet and two instant columns | 40–76; source title “CONDENSED CONSOLIDATED BALANCE SHEETS”; inline fact ID plus its instant context controls each figure. |
| Income and two quarterly columns | 76–98; respective c-1/c-5 duration contexts distinguish current/prior figures. |
| Comprehensive income | 98–110. |
| Changes in stockholders' deficit | 110–150; preserve shares versus USD and total versus parent equity. |
| Cash-flow statement and supplemental payments | 150–196; quarter flows, with September opening cash. |
| Basis / consolidation | 197 onward, Note 1. |
| Earnings per share | 261–274, Note 4; original compound units control USD/share. |
| Repurchases, inventory, intangibles | 274 onward, Notes 5–7. |
| Debt, securitization, covenants and subsequent events | Locate by the actual note headings in H4, retaining inline/text locators before use. This readiness pass does not interpret those contracts or certify availability. |

Money is displayed in millions except stated exceptions. Shares and per-share
data are different quantity families: H4 line 40 says “Amounts in millions,
except share amounts”; line 76 says “Amounts in millions, except per share
amounts”. Inline scale/unit metadata must be retained, not guessed from the
displayed number or element ID.

### Preparation, versions and consumer readiness

The existing preparation retained 336/373/477/241 contexts and
1,141/1,256/1,928/974 inline facts for H1–H4. All source text/metadata remains
available. The earlier raw-HTML audit in VERIFICATION.md checked fact/context
attributes; this run verified the retained hashes and inspected the named
content. Counts do not establish full review or visual fidelity.

The known parser limitation remains: compound USD/share units appear as empty
tuples in its JSON. `source-preparation/raw-unit-definitions.json` retains the
original numerator/denominator XML. Do not infer a unit from `usdPerShare` or
treat EPS as a USD amount. Dimensional contexts include segments, equity
members and other subpopulations; only a confirmed consolidated statement
context can supply a consolidated total.

CP-1 may extract H4's primary statements, reported non-GAAP reconciliations and
cash/debt narrative with source-based definitions and bounded checks. CP-1B
must wait for that financial handoff and an actual date-compatibility check.
CP-2D may then update historical liquidity facts from those validated outputs;
no missing covenant certificate, cash restriction or forward plan is supplied
by merely preparing H4. Peer, market, legal and decision-history modules retain
their own unmet source requirements. Source navigation/CP-PARSE phase is
exercised here for these HTMLs; full alias coverage is not established by it.

## Calculations

Not applicable to CP-0. Hash and metadata checks establish source identities
and extraction scope; no financial amount was normalized or calculated here.

## Gaps

| ID | Affected work | Required action |
|---|---|---|
| G1 | H1/H2/H3 have identity/period and statement-location checks, not complete source-content review | Read the required source sections when those scopes enter CP-1; no full-pack certification. |
| G2 | HTML text extraction is not visual verification; long source paragraphs and nested tables can hide column/footnote distinctions | CP-1 must tie each selected figure to its inline fact, context, unit and table row; inspect the original table if ambiguous. |
| G3 | Compound-unit parser limitation affects EPS | Use original retained unit XML; keep USD/share separate from amounts and share counts. |
| G4 | Exact interim date windows differ from naïve calendar-quarter/equal-duration assumptions | Preserve both dates and issuer labels; test downstream comparability rather than altering source periods. |
| G5 | External authenticity/version/exhibit completeness and broader source requirements remain unchecked | Preserve provenance and scope; obtain the specific needed evidence for its consumer. |
| G6 | Full normalized financial tables, quarter/annual reconciliation and complete deliverables are downstream work | Complete CP-1 and actual downstream consumption; CP-0 readiness does not accept those outputs. |

## Next module

CP-1: open this handoff, verify H4 and its aids from the manifest, and use the
statement map and exact c-1/c-5/c-3/c-4 periods. Extract both quarterly columns,
all primary-statement rows and definitions, then reconcile independently.
Carry G1–G6, especially date/compound-unit restrictions. Keep this H4 extension
distinct from the checked FY2024 annual financial handoff and its limitations.
