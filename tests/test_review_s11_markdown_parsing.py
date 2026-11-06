"""S11 review: the literal Markdown adapter retains or refuses every table and paragraph.

Synthetic handoffs; expected texts are written out literally, never derived from the adapter.
"""

import pytest

from deploy_workflow.handoff_delivery import fence_blocks, heading_text, table
from deploy_workflow.markdown_delivery import literal_module
from deploy_workflow.model_handoff_delivery import _literal_tables


def handoff(findings: str, *, title: str = "# CP-2 Acme", before: str = "") -> bytes:
    return (
        f"{before}{title}\n## Request\nAcme Corp.\n## Sources\nx\n## Findings\n{findings}"
        "## Calculations\nNone.\n## Gaps\nNone.\n## Next module\nDelivery.\n"
    ).encode()


def prose(module_id: str, raw: bytes) -> dict[str, list[str]]:
    module, _, meta = literal_module(module_id, raw)
    texts: dict[str, list[str]] = {}
    for table_ in module.tables:
        heading, kind = meta[table_.table_id]
        if kind == "prose":
            facts = {f.fact_id: f.text for f in module.facts}
            texts.setdefault(heading, []).extend(
                facts[fid] or "" for row in table_.rows for fid in row.fact_ids
            )
    return texts


def test_hash_number_paragraph_is_text_not_a_heading():
    raw = handoff(
        "### Key risks\n"
        "#1 risk is the 2027 maturity wall of USD 1,250 million.\n"
        "#2 risk is covenant headroom of 4%.\n"
    )
    expected = (
        "#1 risk is the 2027 maturity wall of USD 1,250 million. "
        "#2 risk is covenant headroom of 4%."
    )
    assert prose("CP-2", raw)["Key risks"] == [expected]
    assert heading_text("#1 risk") is None
    assert heading_text("### Key risks") == "Key risks"
    assert heading_text("#") == ""


def test_trailing_space_separator_table_is_parsed_not_dropped():
    raw = handoff("### Leverage\n| Metric | FY2025 |\n|---|---| \n| Net leverage | 6.4x |\n")
    module, _, meta = literal_module("CP-2", raw)
    (only,) = [t for t in module.tables if meta[t.table_id] == ("Leverage", "table")]
    facts = {f.fact_id: f for f in module.facts}
    assert [(r.label, [facts[i].text for i in r.fact_ids]) for r in only.rows] == [
        ("Net leverage", ["6.4x"])
    ]
    assert facts[only.rows[0].fact_ids[0]].citations[0].locator == "line 10"


def test_trailing_space_after_boundary_pipe_is_not_a_missing_pipe():
    headers, rows = table([(1, "| A | B | "), (2, "|---|---|"), (3, "| x | 0 |  ")])
    assert headers == ["A", "B"] and rows == [(3, "| x | 0 |  ", ["x", "0"])]


@pytest.mark.parametrize(
    "findings",
    [
        "### Liquidity\n| Item | Amount |\n| Cash | 0 |\n",
        "### Liquidity\n| Cash | 0 |\n",
        "### Gaps list\n| Gap | Effect |\n|---|---|\n| A | B |\n\n| C | D |\n",
    ],
)
def test_pipe_rows_outside_a_table_are_refused_not_dropped(findings):
    with pytest.raises(ValueError, match="model_handoff: pipe rows outside a table in CP-2"):
        literal_module("CP-2", handoff(findings))


def test_fenced_code_is_literal_prose_never_heading_or_table():
    raw = handoff(
        "### Liquidity view\n"
        "Liquidity is adequate.\n"
        "```text\n"
        "# interest cover computed as EBITDA / cash interest\n"
        "| not | a table |\n"
        "```\n"
        "Cash of USD 250 million covers maturities.\n"
        "| Metric | FY2024 |\n"
        "| --- | --- |\n"
        "| Cover | 4.0x |\n"
    )
    module, _, meta = literal_module("CP-2", raw)
    texts = prose("CP-2", raw)
    assert texts["Liquidity view"] == [
        "Liquidity is adequate.",
        "```text # interest cover computed as EBITDA / cash interest | not | a table | ```",
        "Cash of USD 250 million covers maturities.",
    ]
    assert "interest cover computed as EBITDA / cash interest" not in texts
    (cover,) = [t for t in module.tables if t.row_header == "Metric"]
    assert meta[cover.table_id] == ("Liquidity view", "table")
    assert cover.title == "Liquidity view — Metric"


def test_fence_blocks_number_each_block_and_unclosed_runs_to_end():
    lines = ["a", "```", "x", "```", "b", "~~~~py", "~~~", "y", "~~~~", "```", "z"]
    assert fence_blocks(lines) == [0, 1, 1, 1, 0, 2, 2, 2, 2, 3, 3]


def test_equal_headings_in_different_sections_stay_separate_prose():
    raw = (
        b"# CP-2 Acme\n## Request\nAcme Corp.\n## Sources\nx\n## Findings\n"
        b"### Limitations\nFindings caveat.\n## Calculations\nNone.\n## Gaps\n"
        b"### Limitations\nGap caveat.\n## Next module\nDelivery.\n"
    )
    module, _, meta = literal_module("CP-2", raw)
    tables = [t for t in module.tables if meta[t.table_id] == ("Limitations", "prose")]
    facts = {f.fact_id: f for f in module.facts}
    assert [[facts[r.fact_ids[0]].text for r in t.rows] for t in tables] == [
        ["Findings caveat."],
        ["Gap caveat."],
    ]
    assert [facts[t.rows[0].fact_ids[0]].citations[0].locator for t in tables] == [
        "line 8",
        "line 13",
    ]


def test_table_before_any_heading_is_titled_document_not_stopiteration():
    raw = handoff("", before="| Summary | Value |\n|---|---|\n| Net leverage | 6.4x |\n")
    module, _, meta = literal_module("CP-2", raw)
    (summary,) = [t for t in module.tables if t.row_header == "Summary"]
    assert meta[summary.table_id] == ("Document", "table")


def test_unknown_module_is_a_value_error():
    with pytest.raises(ValueError, match="markdown_module: unknown module CP-99"):
        literal_module("CP-99", handoff("Text.\n"))


def test_raw_table_titles_follow_section_headings_and_standalone_labels_only():
    raw = (
        b"# CP-1 Acme\n## Request\nAcme Corp.\n## Sources\nx\n## Findings\n"
        b"### Leverage register\n| Metric | FY2025 |\n|---|---|\n| Net leverage | 6.4x |\n"
        b"**Bridge (PDF 53):**\n| Row | FY2025 |\n|---|---|\n| EBITDA | 512 |\n"
        b"## Calculations\n**Note:** amounts in USD millions.\n"
        b"| Calc | Value |\n|---|---|\n| EBITDA | 512 |\n"
        b"## Gaps\n| Gap | Effect |\n|---|---|\n| No FY2026 guidance | Not supplied |\n"
        b"## Next module\nDelivery.\n"
    )
    _, _, tables, _ = _literal_tables("annual", raw, "0" * 64)
    assert [t.title for t in tables] == [
        "annual: Leverage register",
        "annual: Bridge (PDF 53):",
        "annual: Calculations",
        "annual: Gaps",
    ]
