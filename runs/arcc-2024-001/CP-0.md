# CP-0 — ARCC historical source admission

## Request

Admit the selected Ares Capital Corporation FY2024 financial and July 2029
note sources under `instructions.md`. Ready with limitations for this case.
Actual current host-model work on 2026-11-04, with session context; no provider
run or native source-pack qualification. Historical balances are 2024-12-31.

## Sources

- `sources/ARCC-FY2024-10K.pdf`: original issuer-hosted 320-page PDF,
  SHA-256 `4483569e723b1a0c479d1ce45bcf64e11f6c82c98754bce1aa317641eb81e170`.
  `annual-pages.txt` is a pypdf derivative, with 1-based PDF page markers.
- `sources/base-lines.txt`: full indexed SEC Exhibit 4.1, May 13, 2024 base
  indenture, 1,706 indexed lines; `sources/supplement-lines.txt`: full indexed
  SEC Exhibit 4.2, same-date first supplement, 525 lines. Exact tool captures
  remain in `legal-web-captures.json`; original legal HTML byte requests were
  refused with HTTP403. No access bypass was attempted.

## Findings

| Check | Source / admission result |
|---|---|
| Issuer identity | Annual cover names Ares Capital Corporation, not Ares Management or an unrelated REIT; the base L6 and supplement L16 name that same issuer. |
| Selected contract identity | Annual PDF p104, Exhibits 4.22–24, identifies the base, first supplement and 5.950% July 2029 note form; the actual source filenames/accessions were resolved from those references. |
| Executed state | Base L4 marks execution version; L1686–1705 and supplement L324–339 contain execution statements and named `/s/` blocks for Company and Trustee. No cryptographic or enforceability opinion. |
| Series and priority | Supplement 1.01(a) / L73 designates these notes Senior Securities; other series and subsidiary obligations have distinct terms. |
| Period and publication | 2024-12-31 financial snapshot, annual audit report dated February 5, 2025 (PDF p112). Retrieval/execution in November 2026 is not a 2024 point-in-time access backtest. |
| Visual/source agreement | Retained PDF p65 visually confirms July 2029 principal 850 and coverage per unit 1,962 plus its definition; p274 visually confirms principal versus carrying columns, coverage 196% and minimum 150%. These two page images were viewed, not all 320. |
| Legal text integrity | Every index retained, 744 matching base overlaps, 359 matching supplement overlaps. A shorter boundary truncation at base L815 is preserved in raw captures; the complete matching-prefix line is used in reconstruction. No unresolved differing source line. |
| Authority and scope | The two executed agreements and annual report support the selected coverage review. Other facility instruments, subsequent amendments, certificates and actual borrowing requests are not admitted as complete. |

## Calculations

No capacity calculation. File hashes, index coverage and matching-prefix
truncation checks are source-admission checks only.

## Gaps

Original legal HTML bytes/visual assurance; full agreement/amendment and
compliance-certificate set; present-day source update. A restricted historical
source pack cannot establish all-contract or current compliance.

## Next module

CP-1 must extract the actual published coverage presentation and its definition,
principal versus carrying amounts and dated subsequent events. CP-4 then reads
base plus supplement for the selected series; neither may assume EBITDA is this
test's numerator or the 850 note amount is the group's entire denominator.
