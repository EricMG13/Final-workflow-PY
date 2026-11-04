# CP-0 — TDG historical peer-source admission

## Request

Admit three real candidate-peer financial reports for a FY2024 CP-1C loop.
Current host model, 2026-11-04, historical/outdated annual comparison. Ready with
Limitations; no native accepted source pack or November 2024 access backtest.
Acquisition/preflight occurred before `instructions.md` was locked.

## Sources

Existing checked borrower: `runs/tdg-002/CP-1-attempt-2.md`, actual TDG annual
financial handoff and retained original FY2024 PDF. Newly retained originals:

| Issuer / original primary source | SHA-256 / source period |
|---|---|
| Curtiss-Wright issuer-hosted 98-page 10-K | `f758203854c323ef4bdcda3650047920b1fa5433f8ab6562c702d3a1d6b94688`; December 31, 2024. |
| Moog issuer-hosted 98-page 10-K | `b20e9d309b1fd685953556b08d7007cce326ae48d76d9c1d8f4ecbdbdffd0bc4`; September 28, 2024. |
| HEICO issuer-hosted 152-page annual PDF | `523888d4a41351cd7af10556343ae12d5098a3fafaf9cfcde48f8ad0c5071af0`; October 31, 2024. |

Exact URLs/retrieval outcomes are in `sources/retrieval.json`; derivatives stay
beside originals. CW/Moog page text is pypdf output with 1-based page markers.
HEICO's first IR-format raw request returned 403, while its public annual PDF
download succeeded. That original has font/encoding extraction problems and
the local pypdf lacks its optional AES dependency. The retained `HEICO-pages.txt`
derivative is **unusable for financial extraction**, not accepted clean text.
No production parser was modified. Instead, exact public web captures of the
issuer's separate clean 145-page filing PDF are retained in
`HEICO-web-captures.json` / `HEICO-clean-lines.txt`. Selected statements visually
agree with the retained annual original. The two PDF versions have different
pagination; no hash equality or full-document equivalence is claimed.

## Findings

| Admission check | Actual result / downstream limit |
|---|---|
| Identities | Each original names its own consolidated issuer; TDG, HEICO, CW and Moog are kept separate. All are manufacturing groups, not the ARCC financial-company case. |
| Visual statement checks | CW original pp49/52; Moog pp40/45; HEICO original pp61/62/66 (printed 55/56/60) were rendered and viewed. Units, signs, columns and consolidated/parent distinction match selected text. This is not all-page visual assurance. |
| Source locators | CW pp49/51/52 and lease p62; Moog pp40/42/45–46/54/58; HEICO clean filing L2027–2098, L2297–2349, L3374–3378 and leases L3723–3736. Original HEICO visual pages match its selected clean statement values. |
| Fiscal comparability | Same named annual year, differing ending dates; Moog Note 1 says 52 weeks in FY2024 and FY2023. No calendar or quarterly restatement fabricated. Peer CW report was signed February 13, 2025; evidence was not all available at TDG's September close. |
| Financial distinctions | Borrowing versus finance-lease classification differs; Moog receivable sales affect CFO; advances/deferred revenue affect cash. These need explicit alignment before statistics. |
| Discovery authority | Public filing/IR discovery establishes inspectable candidates and facts. It does not turn model peer-selection judgment into a user-approved or exhaustive industry universe. |

## Calculations

No peer statistics or valuation. Source byte hashes and selected visual/text
agreement are admission checks, not analytical acceptance.

## Gaps

Full matched-period calendarization, complete primary-accounting normalization,
current data, price/market-cap/EV components and transaction multiples. Original
HEICO clean filing PDF bytes are not retained; original annual PDF and selected
clean indexed filing passages have the separate scope stated above.

## Next module

CP-1 must extract literal peer inputs and classification bridges, then CP-1C
must decide peer/metric comparability before calculating statistics. Never use
the garbled HEICO derivative, income attributable to parent as consolidated
income, or Moog's total CF cash as unrestricted balance-sheet cash.
