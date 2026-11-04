"""CP1H-R22, R23 (T21c): the CP-3 prompt states how the model maps statement units and what the
financials gate then enforces.

The model maps every ``extract_statements`` unit in ``unit_maps`` and Python writes those lines
(``unit_maps.expand``). ``financial_workflow._evidence_issues`` refuses a financials object that
leaves an extracted row or a declared period column uncovered, except a null column of a unit
another unit's lines supply (``_null_column``, R23.16). The statement follows the contract and its
letter index in every composed ``financials`` message, before ``Rules:``.
"""

__all__ = ["COVERAGE_RULE_ID", "COVERAGE_STATEMENT"]

COVERAGE_RULE_ID = "financials.coverage"
COVERAGE_STATEMENT = (
    "Map every statement unit `extract_statements` returns in `unit_maps`; Python then writes "
    "its statement lines from the extracted text. For each unit give its `source_id` and "
    "`locator`, the `book_id`, the `statement` (BS, IS or CFS; comprehensive income is IS), "
    "`columns` with one period_id from that book per printed column, or null when the book "
    "declares no period for it or another unit already gives that period, and `rows` with "
    "each extracted row's number and its `line_id` (used once in its book), `item_id`, "
    "`line_kind` and `sign_convention` (total liabilities and equity is "
    "`other:total_liabilities_and_equity`). For the qualified path set `profile` to "
    "`typed-source/1`. Then supply exactly one `row_label_selections` entry for every mapped "
    "row: `row` is the extracted row's physical `line_no`, and `part_line_numbers` selects the "
    "ordered contiguous exact fragments shown in that row's `label_candidates`, including its "
    "amount-bearing line. Python joins only those printed fragments with single spaces; do not "
    "supply reconstructed label text or select a section caption as a row prefix. Supply exactly "
    "one `row_dimensions` entry per mapped row, with a `quantity` kind (`monetary`, "
    "`currency_per_share`, or `shares`), source-supported scale and citations to the statement's "
    "printed unit context. A per-share label must use `currency_per_share`; a weighted-average "
    "share count must use `shares`; ordinary statement amounts use `monetary`. Balance-sheet "
    "columns bind only to `PERIOD_END` periods with no start date. Flow columns must match the "
    "printed duration and exact end date; cite source fiscal policy for annual period starts. "
    "Comprehensive income uses the transport statement `IS` only with distinct `other:ci_*` "
    "line and item IDs and its own page/unit. Do not write lines for the rows you map. Write a "
    "`statement_lines` entry only for a row Python leaves to you (the submit result's notes "
    "name each one): the row's statement, its label verbatim, each mapped column's amount (a "
    "printed dash is 0), citing the row's own locator (on a line source, `line:N` with N the "
    "row's number in the extract), citing each selected fragment and the amount-bearing line. "
    "A row left uncovered "
    "is refused as an `Uncovered extracted statement line` with its reason."
)
