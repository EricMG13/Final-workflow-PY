# CP-0 — TDG executed legal-source admission

## Request

Admit one historical governing document for CP-4. **Ready with limitations for
the selected indenture review.** This is a 2026-11-04 host-model source check,
following acquisition and the frozen `CP-4-instructions.md`; not a full source
pack, current legal status, independent signature verification or native runtime.

## Sources

The retained FY2024 10-K's Exhibit 4.12 row incorporates the September 19, 2024
indenture for the 6.000% Senior Secured Notes due 2033, filed with the September
20 Form 8-K. Its EDGAR accession/document path matches the actual retrieved
[SEC exhibit](https://www.sec.gov/Archives/edgar/data/1260221/000119312524222468/d887611dex41.htm).
The HTTP scheme in the old index was upgraded to HTTPS; the document path did
not change. Acquisition was preflight, before the analytical brief was frozen.

Direct raw-byte request returned HTTP403, retained in `legal-source/retrieval.json`.
The public web tool successfully read the body. `legal-source/web-captures.json`
retains twenty exact tool responses; `legal-source/source-lines.txt` reconstructs
all indexed lines **0–2876**, with no missing index or disagreeing overlap.
This is complete indexed text, **not original HTML bytes or a visual audit**.
Hashes/retrieval checks are recorded in `CP-4-verification.json`.

## Findings

| Source admission field | Actual evidence / implication |
|---|---|
| Document state | Title marks execution version; dated 2024-09-19, names the issue; L2236 onward carries execution statement and named signature blocks. Filed execution-version primary evidence; no cryptographic/legal enforceability assurance. |
| Entity roles | L225: TransDigm Inc. is Company/issuer; TransDigm Group Incorporated is Holdings; named Guarantors; BNY Mellon roles distinguish Trustee/US collateral agent and UK collateral agent. Do not collapse borrower, parent or agent into one entity. |
| Scope | This notes indenture governs the named issue; its definitions reference other facilities. It is not the A/R agreement or the operative credit agreement. |
| Date / base | Document date September 19, 2024; financial foundation September 30 annual balances/flows remain separate. Later amendments, releases and designations have not been exhaustively checked. |
| Law | Section 11.06 / L2054 names New York law for the indenture, notes and guarantees; no interpretation of enforceability supplied here. |
| Missing dependent documents | Definition at L562 identifies a 2019 first-lien ICA with later joinders, including September 19, 2024. ICA/security-agreement bodies, current usage/certificates and full entity collateral/value map are not supplied by this admission. |

The text supports actual clause review, including conditions and definitions.
It does not establish present covenant capacity, complete security perfection,
priority enforcement control or issuer financial-metric equivalence. Missing
dependent documents are specific limitations, not a reason to ignore the actual
governing clauses that are available.

## Calculations

No financial calculation. Text-index coverage and overlapping-text identities
are deterministic source-admission checks. Tool captures preserve their actual
formatting; source fractions and math markup must not become different numbers.

## Gaps

Original HTML bytes/visual comparison, a complete later amendment/joinder chain,
operative ICA/security text, certificates/usage and financial/legal definition
bridges remain open. The annual CP-1 source and quantity/perimeter limitations
still apply. This is source admission, not CP-4, full CP-0 or final delivery.

## Next module

CP-4 should read the actual admitted clauses, keep roles/definitions/conditions
and cite section plus retained line. It must not use the indenture's A/R
description to certify the separate facility's extension, substitute reported
financial ratios, turn unknown usage into zero or infer current enforcement
control from an unexamined ICA. Delivery follows actual analytical handoffs.
