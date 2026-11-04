"""Bounded source-fragment candidates for CP-1 statement labels."""

from pathlib import Path

from deploy_vii.contracts import Span
from deploy_vii.live.tools import extracted_body
from deploy_vii.statement_extract import extract_statement_lines
from deploy_workflow.statement_lines import line_table

FIXTURES = Path(__file__).parents[1] / "cases" / "cp1-chain" / "fixtures"


def _table(name: str):
    return extract_statement_lines((FIXTURES / name).read_text(), "page:1", "issuer")


def test_all_caps_row_prefix_remains_an_exact_candidate_part() -> None:
    table = _table("allcaps-wrapped-prefix.txt")
    row = table.lines[0]

    assert row.label == "REPLACEMENT COMPONENTS"
    assert [(part.line_no, part.text) for part in row.label_candidates] == [
        (5, "SERVICE REVENUE FROM"),
        (6, "REPLACEMENT COMPONENTS"),
    ]


def test_ambiguous_caption_and_digit_continuation_are_exposed_without_automatic_merge() -> None:
    ambiguous = _table("ambiguous-caption-row-refusal.txt")
    assert ambiguous.lines[0].label == "Reconciliation"
    assert [(part.line_no, part.text) for part in ambiguous.lines[0].label_candidates] == [
        (3, "OTHER OPERATING ADJUSTMENTS"),
        (4, "Reconciliation"),
    ]

    digits = _table("digit-bearing-continuation.txt")
    row = digits.lines[0]
    assert row.label == "and model 4 service plans"
    assert [(part.line_no, part.text) for part in row.label_candidates] == [
        (4, "Revenue from product family 2"),
        (5, "and model 4 service plans"),
    ]


def test_candidate_parts_do_not_cross_blank_or_previous_data_row() -> None:
    table = _table("blank-table-boundary.txt")
    row = table.lines[0]
    assert [(part.line_no, part.text) for part in row.label_candidates] == [(5, "Other income")]


def test_source_bound_colon_heading_remains_a_candidate_part() -> None:
    text = """STATEMENT OF OPERATIONS
2025       2024
Weighted-average shares outstanding:
Basic and diluted                  100         90
"""
    table = extract_statement_lines(text, "page:106", "issuer")
    assert [(part.line_no, part.text) for part in table.lines[0].label_candidates] == [
        (3, "Weighted-average shares outstanding:"),
        (4, "Basic and diluted"),
    ]
    assert (
        '[{"line_no":3,"text":"Weighted-average shares outstanding:"},'
        '{"line_no":4,"text":"Basic and diluted"}]'
    ) in extracted_body(table)


def test_label_candidates_stop_at_the_actual_period_header_and_statement_title() -> None:
    import test_financial_workflow as g1

    table = extract_statement_lines(
        g1.MANIFEST["sources"][1]["pages"][1]["text"], "page:2", "financial"
    )
    first = table.lines[0]

    assert first.label == "Revenue"
    assert [(part.line_no, part.text) for part in first.label_candidates] == [(5, "Revenue")]


def test_independent_html_rows_expose_only_their_own_label_fragment() -> None:
    text = (
        "STATEMENT OF OPERATIONS",
        "2025       2024",
        "Revenue                         10          9",
        "Other income                     5          4",
        "Total revenue                   15         13",
    )
    spans = {index: Span(locator=f"line:{index}", text=line) for index, line in enumerate(text, 1)}

    table = line_table(spans, "line:1-5", "issuer")

    assert [
        (line.label, [(part.line_no, part.text) for part in line.label_candidates])
        for line in table.lines
    ] == [(line.label, [(line.line_no, line.label)]) for line in table.lines]
