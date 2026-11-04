# Statement rows of the golden HTML filings (CP1H-R18 answer key)

Method: DVII `extract_statement_lines` over each unit of `cases/statement-units` (fc93c39d), on a re-conversion that marks td/th boundaries and joins cells with ` | `, line-aligned with `convert_html` (asserted).
BGS is excluded (CP1H-R18 F1).
36 units, 1,130 rows.
A row's label is its own label cell (review H1); headers are not part of the key (review L1).
Ruling: CP1H-R18. `derive.py` documents the method; tests do not run it. Frozen: builders do not edit these files.
