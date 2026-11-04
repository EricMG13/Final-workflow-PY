# CP-0 — retained interim source pack

Run source readiness in the current host session for the four raw TDG HTML
filings listed in `source-preparation/manifest.json`. The parser/text outputs
are reading aids, not issuer evidence or financial acceptance. Reuse the
Deploy V-derived source-readiness instructions in `prompts/CP-0.md` and later
`src/deploy_vii/methods/cp0.md` with these scope amendments.

Verify raw/text/metadata/unit-definition hashes. Establish issuer, document
type, accounting/consolidation basis, exact periods, unit families, status and
versions from actual content. Separate calendar dates and issuer week labels.
Inspect the primary statement/notes locations and context metadata. Do not
normalize or calculate financial amounts in CP-0. Do not assume every quarter
has an equal calendar duration because its heading says thirteen weeks.

For the next CP-1 increment prioritize the December 28, 2024 quarterly filing:
all primary statement rows and comparable columns; cash/debt/facility facts;
subsequent distribution and cash movements. Record text line and inline fact
locators, and whether table position preserves each column. Inspect the March,
June and September sources for identity/period readiness; this does not certify
their complete content. The existing annual PDF remains a distinct source.

Keep compound USD/share units sourced from original unit XML, amounts/shares
from their own units, and dimensional facts separate from consolidated facts.
Text extraction is not visual verification. Flag any issue that restricts the
next consumer, with an action. No credential or provider operation.

Write the six common headings: Request, Sources, Findings, Calculations, Gaps,
Next module. Calculations is not applicable to CP-0. Explicitly state execution
scope, permitted CP-1 work and incomplete coverage. Retain short exact excerpts
so readiness claims can be checked. A consumer must actually open and use this
handoff; a saved Markdown file alone does not close the loop.
