# CP-1 — TDG handoff intake

Run: `tdg-001`, 2026-11-04. New model-authored output in the same assistant session
as CP-0, following [the bounded intake instructions](../../prompts/CP-1-intake.md).
This is a communication check, not full CP-1 execution or an isolated model call.
The assistant retained the broader session context; this was not a blind test.

## Request

Consume CP-0's Markdown, locate the five primary statements and extract six
representative reported values with their correct quantities and periods.

## Sources

- Input: [CP-0.md](CP-0.md), SHA-256
  `b00dc9ded43bd41413143000b6e78799450f658667a85e4f3afcf54a9646a1f0`.
- Instructions SHA-256:
  `95e1d88f616117a9b2144f2ada6e69647af28148df92ce9594dae53487e0b59b`.
- S1 path and [text aid](source-pages.jsonl) resolved from CP-0's links. The PDF
  hash matched `dc6a8ea6249e4e919d190a4bbb459d9bf4eded005b7d5680ae911b32d44d44af`.
- Opened the five page-map entries: balance sheets 105, income 106, comprehensive
  income 107, stockholders' deficit 108 and cash flows 109. No historical CP-1
  answer supplied the sampled values below.

## Findings

**Intake succeeded for the stated scope.** The source and page map were usable
without further user input. All amounts below are reported, not calculated.
The issuer/perimeter is consolidated TransDigm Group Incorporated and subsidiaries.
Annual duration dates use the fiscal-year policy on PDF 3; reporting currency uses
the explicit statement on PDF 55. Share counts have no currency.

| Source label | Amount as printed | Quantity | Unit | Date or period | S1 PDF page | Basis |
|---|---:|---|---|---|---:|---|
| NET SALES | 7,940 | Money | USD millions | 2023-10-01 through 2024-09-30 | 106 | Reported |
| Earnings per share | 25.62 | Money per share | USD/share | 2023-10-01 through 2024-09-30 | 106 | Reported; total EPS attributable to TD Group common stockholders |
| Weighted-average shares outstanding: Basic and diluted | 57.8 | Shares | Millions of shares | 2023-10-01 through 2024-09-30 | 106 | Reported; average during period |
| Cash and cash equivalents | 6,261 | Money | USD millions | Instant: 2024-09-30; no start date | 105 | Reported |
| Common stock: issued shares | 61,904,833 | Shares | Shares | Instant: 2024-09-30; no start date | 105 | Reported in common-stock description; issued, not outstanding net of treasury stock |
| Net cash provided by operating activities | 2,045 | Money | USD millions | 2023-10-01 through 2024-09-30 | 109 | Reported |

The 57.8 is a weighted-average share quantity in millions; it is neither USD nor
the year-end issued-share count. The 25.62 is USD per share, not USD millions.
The balance-sheet amounts have instant dates. These distinctions remain in the
Markdown instead of being discarded by a uniform numeric column.

## Calculations

None. No unit rescaling, inferred OPEX or financial reconciliation was performed
for this intake check.

## Gaps

Inherited from CP-0, with the same scope:

- **G1:** PDF 156's rotated non-GAAP table needs a separate reading before use.
  It is not used in this sample.
- **G2:** Extraction warnings and incomplete visual/cell coverage remain. The six
  sampled values can be read on retained renders of 105, 106 and 109; opening
  107–108 does not establish a full extraction or reconciliation of those tables.
- **G3:** Only the supplied annual PDF was considered. No latest-filing,
  quarterly-completeness or external-authenticity conclusion follows.

## Next module

Continue CP-1 itself: extract and check the requested annual statements and
comparatives, including signs, dashes versus missing data, cross-statement
reconciliation and the separately labeled OPEX composition identified in the
earlier review. Verify the existing calculation helper before changing it.

CP-1A is not released by this intake sample. No automated invocation, full module
acceptance, pathway execution or final deliverable is claimed.
