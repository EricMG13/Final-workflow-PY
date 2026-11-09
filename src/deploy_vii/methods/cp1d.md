# CP-1D — earnings quality (adaptation record)

Method basis: `docs/CP1D-OWNER-LEASE.md` (frozen, revision 3 with the Stage 1 release amendments).
CP-1D is owner-only (no live step contract): one `earnings_quality` step, owner core
`deploy_workflow.owners.cp1d`. The analyst returns judgments, citations and an accepted basis or
fraction; Python reads the management bridge table and owns every number (sums, shares, cash
conversion and restated leverage, one 38-digit half-even division per quotient). A missing amount
is never 0.

Role: senior leveraged-finance credit analyst, creditor perspective. Challenge each proposed
add-back for achievability and recurrence against evidence read through `read_pages`; give the
module-wide view in `overall`; name what the pack cannot show in `gaps`.

Evidence. `read_inputs` returns the exact context view (upstream statuses, the bridge rows, the
CP-1 figures a `{{FIG:...}}` reference may name). Cite only text you read through `read_pages`;
a cited page that was not read refuses the attempt. Prose carries no digit outside a
`{ref|unit}` figure reference.

## Guard limits (accepted costs, with the code that shows them)

The accepted basis of a "Partly supported" add-back is read from its citation quote by
`cp1d._basis_amounts` and `cp1d._one_whole_run`. Both fail closed: when a quote is not one whole,
readable ASCII figure the pinned issue `Accepted basis quote must contain exactly one amount`
is returned and nothing composes. The checks cost these legitimate quotes; none is a defect.
The analyst cites a different, simpler sentence, or gives `accepted_fraction` instead.

**Rule W (round 12), the sign.** A minus sits directly before the first digit or one space
before it, any whitespace (a line break included); an accounting-parenthesised numeral holds
at most one space inside each parenthesis. The cost: a spaced range and a dash bullet read
as signed.
```python
cp1d._basis_amounts(cite("Saving of 95 - 96 in range."), sources)   # ['95', '-96']: refused
cp1d._basis_amounts(cite("- 1.80 bullet item"), sources)            # ['-1.80']: below 0, refused
```

**Item 8 comma costs (round 13).** A numeral run joins digits with ".", "," or ", ", and
must be one whole `d+(.d+)?` figure. The cost:
```python
cp1d._one_whole_run("Saving 1,250 total.")                    # False: a grouped figure >= 1,000
cp1d._one_whole_run("Saving 1,5 decimal comma.")               # False: a decimal comma
cp1d._one_whole_run("Items 1, 2, 3 listed.")                   # False: a comma-space list
cp1d._one_whole_run("Since 2025, 1.80 saving.")                # False: a figure after a year
cp1d._one_whole_run("Published January 10, 2026 saving 1.80")  # False: the day of "Month D, YYYY"
```

**Addendum 5 (identifier and ordinal runs, non-ASCII numerals).** The quote must hold exactly
one numeral run. A run a letter, or a Mn/Mc/Me/Cf character, or a character whose NFKC fold
holds a letter (a circled letter) touches on its left is an identifier (`Q2`, `FY25`, `A1`). A run
followed by an ordinal suffix (`st`, `nd`, `rd`, `th`, any case, after skipping Cf/Mn/Me
characters and NFKC-folding the suffix window, with no further letter) is an ordinal (`2nd`,
`2ⁿᵈ`, `2ｎｄ`). Any numeric character outside ASCII 0-9 (`²`, `٢`, `½`, `Ⅻ`) refuses the quote. A
letter after the run is still read, so `2.5m`, `25bps` and `2nds` are one whole run.
```python
cp1d._one_whole_run("The FY25 saving.")   # False: identifier
cp1d._one_whole_run("The 2nd saving.")    # False: ordinal
cp1d._one_whole_run("A saving of ½.")     # False: non-ASCII numeral
cp1d._one_whole_run("A saving of 2.5m.")  # True: 2.5
cp1d._one_whole_run("The 2nds saving.")   # True: 2
```

**Round 5 item 12 (accepted readings).** The right side of a run never makes an identifier:
addendum 5 reads what follows a run as a unit suffix, and its one exception, the ordinal rule,
never meets a decimal run. So `1.5-Q` and `1.5-` wrapped before `nd` read 1.5 as one whole run
(steps 5 and 6 pass); since S05-cp0-cp1-A01 the `-Q` tail is no millions or currency mark, so
the unit rule below refuses them after step 6 instead of composing.
```python
cp1d._one_whole_run("Savings of 1.5-Q are signed.")     # True: 1.5
cp1d._one_whole_run("Savings of 1.5-\nnd are signed.")  # True: 1.5
```

**Basis unit and currency (S05-cp0-cp1-A01).** The one figure becomes a source amount in the
bridge's currency and MILLIONS, so it must read as one (`cp1d._money_figure`, checked after steps
1 to 6). On the cited page, at every occurrence of the quote, the figure is followed by
punctuation, the end of the text or a linking word (`in`, `of` after a unit, `is`, `and`, ...;
not `per`, so `1.5 per cent` is refused), optionally after a millions word (`m`, `mm`, `mn`,
`million`, `millions`, any case) and the run's currency code. A currency code, name or symbol
directly before it (brackets, colons and dots round it are ignored: `(EUR 1.5m)`, `EUR: 1.5m`,
`U.S.$`) must be the run's (`USD`, `US$`, `$` for USD; `EUR`, `€` for EUR, codes and names in any
case). Otherwise `Accepted basis quote must state the amount in the bridge's currency and
millions` is returned. The cost: a figure followed by any other word (`1.80 annualised`, a table
cell followed by the next line, `1.5-Q`), a capitalised three-letter token before it
(`LTM 1.80`) and `1.80 USD m` (code before the millions word) are refused; the analyst cites a
plainer sentence or gives `accepted_fraction`. Guard limit (fail open, not closed): a linking
word still lets a count through (`2 in ten suppliers`), and a lowercase currency word outside the
listed codes and names (`aed 1.80`) reads as no currency.
```python
# refused: "cover 2% of spend", "cover 2 of the ten categories", "by 1bps", "EUR 1.50m" (USD run)
# composed: "a saving of 1.80.", "1.80m, net of costs", "USD 1.80 million.", "1.80 in savings"
```

**Source quotes (user, 2026-10-28, AGENTS.md "Source quotes").** Quote reading is frozen: no new
rule is written for how Python reads a figure from a model-chosen quote. A new edge case fails
closed (the exactly-one issue above) and is recorded here as a guard limit; a reading rule changes
only if a frozen case needs it.

## Citations on facts (Stage 2 round 3)

A sourced fact (a bridge amount, an accepted basis) quotes its own field. A derived (calculated)
fact is cited per page: one `Citation` per (source, page), quoting the first of its own input
quotes on that page, in input order (`deploy_workflow.owners.blank.one_per_page`); a quote is never invented. A
claim's citations are the analyst's located evidence as submitted.

## Other rules the code enforces

- Blank analyst text (`prose.is_blank`: whitespace, control (`Cc`) and format (`Cf`) characters, the default-ignorable code points that `str.strip()` keeps (U+034F, U+115F, U+1160, U+17B4, U+17B5, U+180B-U+180F, U+3164, U+FE00-U+FE0F, U+FFA0, U+E0100-U+E01EF) and U+2800, or the empty string) is refused as `<path>: empty text`.
  A blank citation quote is refused by the pack-quote check (`Quote/locator mismatch`) or, as an
  accepted basis, by the exactly-one rule; inventory at Stage 2 found no blank quote that composes.
- An unknown bridge type (not Saving or Cost) blocks the run (`Bridge table not found`).
- Each model-text field the step later builds as run text (assessment and overall rationales) is
  checked with `RunText` before composition (`<path>: <msg>`, no input echoed), and a record the
  product refuses is an issue line, so nothing raises after the binding write.
- Settled own limitations are the oracle list then `Synthetic case; not real issuer qualification`
  (added by settlement for a synthetic run); inherited ones come from `inherited_limitations`.
- Caller-quoting issue lines are cut with `execution.clipped` and the issue list with
  `execution.listed_issues` (protocol section 6).

## Not in this version

The recipe text of `refusal_rules.partly_supported` in `cases/cp1d-owner/expected.json` still
describes the pre-round-12 digit-run wording; it is re-pinned at LEAD's release. CP-1B is read
for its status only; no CP-1B fact is read.
