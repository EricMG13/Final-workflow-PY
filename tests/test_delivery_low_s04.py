"""Synthetic regressions for S04 low findings (A04-A07, C08, C10): hand-written CP-1 handoffs
through the real CP-OS layout and markdown_files; no retained model response, no analytical run.
Expected values are written out from the handoff text, not computed by the code under test."""

import hashlib
import json
from pathlib import Path

import pytest

from deploy_vii.charts import _categories
from deploy_vii.contracts import Run, View
from deploy_vii.report_view import ReportView
from deploy_workflow.handoff_delivery import (
    DeliveryRequest,
    HandoffInput,
    hide_comments,
    physical_lines,
)
from deploy_workflow.markdown_delivery import literal_module, markdown_files
from deploy_workflow.model_handoff_delivery import _AnnualReader
from deploy_workflow.owners.cpos_launch import _layout

RUN = Run.model_validate_json(
    json.dumps(
        {
            "schema_version": "run/2",
            "run_id": "x",
            "issuer_id": "ACME",
            "issuer_name": "Acme Corp",
            "as_of": "2024-12-31",
            "method_version": "deploy-v-r14",
            "case_kind": "public",
            "pathway": "credit_snapshot",
            "requested_modules": ["CP-1"],
        }
    )
)
HEAD = "| Period | {cols} | Reporting unit | Basis and limitation |\n| --- | {sep} | --- | --- |\n"


def chart(heading, cols, rows, unit):
    out = f"### {heading}\n\n" + HEAD.format(
        cols=" | ".join(cols), sep=" | ".join("---" for _ in cols)
    )
    for period, *vals in rows:
        out += f"| {period} | " + " | ".join(vals) + f" | {unit} | basis |\n"
    return out + "\n"


def handoff(leverage=None, liq=None, unit_liq="US$m", extra=""):
    leverage = leverage or [("FY2023", "4.1", "3.9"), ("FY2024", "3.8", "3.5")]
    liq = liq or [("FY2023", "100", "200"), ("FY2024", "150", "Not supplied: undisclosed")]
    return (
        "# CP-1 Acme Corp\n\n## Request\nAcme Corp historical analysis.\n\n## Sources\nsrc.pdf\n\n"
        "## Findings\n\n"
        + chart("Chart data: leverage", ["Total debt / EBITDA", "Net debt / EBITDA"], leverage, "x")
        + chart("Chart data: interest cover", ["EBITDA / cash interest"], [("FY2024", "2.7")], "x")
        + chart("Chart data: liquidity", ["Cash", "Undrawn committed facilities"], liq, unit_liq)
        + chart("Chart data: debt maturities", ["Debt maturing"], [("2025", "50")], "US$m")
        + "### Financials and credit metrics\n\n"
        + "| Metric | FY2024 |\n| --- | ---: |\n| Revenue | 1 |\n\n"
        + extra
        + "## Calculations\nNone.\n\n## Gaps\nNone.\n\n## Next module\nDelivery.\n"
    )


def deliver(tmp_path: Path, text: str):
    raw = text.encode()
    layout, _ = _layout(RUN, ("CP-1",), (), "cfg")
    (tmp_path / "CP-1.md").write_bytes(raw)
    spec = HandoffInput(path="CP-1.md", sha256=hashlib.sha256(raw).hexdigest())
    files = markdown_files(
        DeliveryRequest(run=RUN, handoffs={"CP-1": spec}, layout=layout), tmp_path
    )
    report = ReportView.model_validate_json(files["report-view.json"])
    figures = {f.fig_id: f for b in report.blocks for f in b.figures}
    return files, figures, View.model_validate_json(files["view.json"])


@pytest.mark.parametrize(
    ("rows", "expected"),
    [
        # Hand-derived: the x axis runs oldest to newest whatever order the rows were written in.
        (
            [("FY2024", "3", "3"), ("FY2023", "4", "4"), ("FY2022", "5", "5")],
            ["FY2022", "FY2023", "FY2024"],
        ),
        (
            [("FY2022", "5", "5"), ("FY2023", "4", "4"), ("FY2024", "3", "3")],
            ["FY2022", "FY2023", "FY2024"],
        ),
        (
            [("FY2023", "4", "4"), ("FY2024", "3", "3"), ("FY2022", "5", "5")],
            ["FY2022", "FY2023", "FY2024"],
        ),
        # Quarters of one year sort by quarter; a label with no year keeps the authored order.
        ([("Q3 2024", "1", "1"), ("Q1 2024", "2", "2")], ["Q1 2024", "Q3 2024"]),
        ([("LTM", "1", "1"), ("FY2023", "2", "2")], ["LTM", "FY2023"]),
    ],
)
def test_chart_periods_run_oldest_first(tmp_path, rows, expected):
    _, figures, _ = deliver(tmp_path, handoff(leverage=rows))
    assert _categories(figures["S.1"].chart) == expected


def test_reordered_chart_keeps_each_value_with_its_period(tmp_path):
    # FY2024 Total debt/EBITDA is 3 and FY2023 is 4, as written.
    _, figures, _ = deliver(
        tmp_path, handoff(leverage=[("FY2024", "3", "9"), ("FY2023", "4", "8")])
    )
    got = {(m.series, m.label): m.value for m in figures["S.1"].chart.marks}
    assert (
        got[("Total debt / EBITDA", "FY2024")] == 3 and got[("Total debt / EBITDA", "FY2023")] == 4
    )
    assert got[("Net debt / EBITDA", "FY2024")] == 9 and got[("Net debt / EBITDA", "FY2023")] == 8


@pytest.mark.parametrize("separator", [" ", " ", "\x0c", "\x0b", "\x85", "\x1c", "\r"])
def test_line_citations_count_newlines_only(tmp_path, separator):
    # The prose line holds one separator; every later citation must still name the line a reader
    # finds by counting "\n" (with "\r\n" and a lone "\r" being one newline each).
    text = handoff(extra=f"Revenue rose{separator} strongly.\n\nLater paragraph.\n\n")
    _, _, view = deliver(tmp_path, text)
    physical = physical_lines(text)
    checked = 0
    for fact in next(m for m in view.modules if m.module_id == "CP-1").facts:
        for c in fact.citations:
            assert physical[int(c.locator.split()[-1]) - 1] == c.quote
            checked += 1
    assert checked > 10


def test_crlf_handoff_cites_the_same_lines(tmp_path):
    text = handoff(extra="Later paragraph.\n\n")
    _, _, lf = deliver(tmp_path, text)
    crlf = text.replace("\n", "\r\n")
    assert physical_lines(crlf) == physical_lines(text)
    _, _, got = deliver(tmp_path, crlf)

    def cites(v):
        return [c.locator for m in v.modules for f in m.facts for c in f.citations]

    assert cites(got) == cites(lf)


def test_physical_lines_edges():
    assert physical_lines("") == []
    assert physical_lines("a\n") == ["a"] and physical_lines("a\n\n") == ["a", ""]
    assert physical_lines("a b\r\nc\rd") == ["a b", "c", "d"]


def prose_texts(text: str) -> list[str]:
    module = literal_module("CP-1", text.encode())[0]
    return [f.text for f in module.facts if f.text]


def _doc(body: str) -> str:
    return (
        "# CP-1 Acme Corp\n## Request\nR.\n## Sources\nS.\n## Findings\n"
        + body
        + "\n## Calculations\nC.\n## Gaps\nG.\n## Next module\nN.\n"
    )


def test_multiline_html_comment_is_not_published():
    shown = prose_texts(_doc("Visible one.\n<!--\nDRAFT: internal 999\nmore\n-->\nVisible two.\n"))
    assert "Visible one." in shown and "Visible two." in shown
    assert not [t for t in shown if "DRAFT" in t or "more" == t or "-->" in t]


def test_single_line_and_nested_comments():
    shown = prose_texts(_doc("<!-- one line -->\nA.\n<!-- open <!-- inner -->\nB.\n"))
    # The comment ends at its first `-->` (HTML rule); the later `-->` text never appears alone.
    assert (
        "A." in shown
        and "B." in shown
        and not [t for t in shown if "inner" in t or "one line" in t]
    )


def test_comment_markers_inside_a_fence_stay_text():
    shown = prose_texts(_doc("```\n<!--\nkept\n```\nAfter.\n"))
    assert any("kept" in t for t in shown) and "After." in shown


def test_unterminated_html_comment_is_refused():
    with pytest.raises(ValueError, match="never closed"):
        literal_module("CP-1", _doc("Before.\n<!--\nhidden forever\n").encode())


TABLE = "| a | b |\n|---|---|\n| 1 | 2 |\n"


def _hidden(text: str) -> list[str]:
    return hide_comments(physical_lines(text), "m")


def test_a_comment_opened_mid_line_or_indented_hides_its_table_and_keeps_the_text_before_it():
    # Hand-derived: line 2 keeps "note " (text before the opener), lines 3-6 are inside the
    # comment through "-->", line 7 is outside again. Indented opener: only spaces before it, so
    # the opening line is blank. Back-to-back "<!-- x --> <!--" opens at the second marker.
    body = f"{TABLE}-->\ntext\n"
    assert _hidden(f"## A\nnote <!--\n{body}") == ["## A", "note ", "", "", "", "", "text"]
    assert _hidden(f"## A\n  <!--\n{body}") == ["## A", "", "", "", "", "", "text"]
    assert _hidden(f"## A\n<!-- x --> <!--\n{body}")[1:] == ["<!-- x --> ", "", "", "", "", "text"]


def test_comment_edge_cases_keep_their_old_meaning():
    # Nested openers end at the first "-->"; a closer with no opener is text; a comment closed on
    # its own line is single-line; markers in inline code and fences are text; a closer line that
    # opens another comment keeps hiding until the next closer.
    assert _hidden("a <!-- b <!-- c\nx\n--> y\nz\n") == ["a ", "", "", "z"]
    assert _hidden("only --> closer\n| 1 |\n") == ["only --> closer", "| 1 |"]
    assert _hidden("t <!-- c --> u\n| 1 |\n") == ["t <!-- c --> u", "| 1 |"]
    assert _hidden("`<!--` code\n| 1 |\n") == ["`<!--` code", "| 1 |"]
    assert _hidden("```\nq <!--\n| 1 |\n```\n") == ["```", "q <!--", "| 1 |", "```"]
    assert _hidden("<!-- a\nb --> <!-- c\nd\n-->\ne\n") == ["", "", "", "", "e"]


def test_a_mid_line_comment_never_closed_is_refused_naming_the_handoff():
    with pytest.raises(ValueError, match="m: the HTML comment opened on line 2 is never closed"):
        _hidden("## A\nnote <!--\n| hidden |\n")


def test_mid_line_comment_table_is_not_published_by_the_markdown_reader():
    shown = prose_texts(_doc("Before <!--\nDRAFT 999\n-->\nAfter.\n"))
    assert "Before" in " ".join(shown) and "After." in shown
    assert not [t for t in shown if "DRAFT" in t]


def test_reporting_unit_other_than_the_chart_unit_is_refused(tmp_path):
    with pytest.raises(ValueError, match="reported in EUR m, not US\\$m"):
        deliver(tmp_path, handoff(unit_liq="EUR m"))
    with pytest.raises(ValueError, match="reported in GBP m"):
        deliver(tmp_path, handoff(unit_liq="GBP m"))


def test_gap_in_another_unit_row_is_still_a_gap_and_matching_unit_publishes(tmp_path):
    # Hand-derived: FY2024 Undrawn is "Not supplied", so it stays a gap even in a EUR m row.
    rows = [("FY2023", "100", "200"), ("FY2024", "Not supplied: n/a", "Not supplied: n/a")]
    _, figures, _ = deliver(tmp_path, handoff(liq=rows))
    cash = {m.label: m.value for m in figures["S.3"].chart.marks if m.series == "Cash"}
    assert cash["FY2023"] == 100 and cash["FY2024"] is None


def test_table_route_into_a_chart_strip_block_is_refused(tmp_path):
    raw = handoff().encode()
    layout, _ = _layout(RUN, ("CP-1",), (), "cfg")
    routes = list(layout.routes)
    routes[0] = routes[0].model_copy(update={"kind": "table", "figure_id": None})
    layout = layout.model_copy(update={"routes": tuple(routes)})
    (tmp_path / "CP-1.md").write_bytes(raw)
    spec = HandoffInput(path="CP-1.md", sha256=hashlib.sha256(raw).hexdigest())
    with pytest.raises(ValueError, match="chart strip block takes only chart routes"):
        markdown_files(DeliveryRequest(run=RUN, handoffs={"CP-1": spec}, layout=layout), tmp_path)


@pytest.mark.parametrize(
    "cell", ["Not supplied: undisclosed", "Not supplied", "Not calculable: missing inputs", "—", ""]
)
def test_model_reader_treats_every_chart_gap_spelling_as_a_gap(cell):
    # Hand-derived: each spelling is an explicit gap (NOT_STATED, no value), never an error.
    raw = f"### T4.10 dashboard\n| Metric | FY2024 |\n|---|---|\n| Revenue | {cell} |\n".encode()
    spec = HandoffInput.model_validate_json(
        json.dumps({"path": "a.md", "sha256": hashlib.sha256(raw).hexdigest()})
    )
    from deploy_workflow.handoff_delivery import ModelDelivery

    layout = ModelDelivery.model_validate_json(
        json.dumps(
            {
                "periods": {
                    "FY2024": {
                        "start_date": "2024-01-01",
                        "end_date": "2024-12-31",
                        "balance_column": None,
                    }
                },
                "anchors": {"dashboard": "### T4.10 dashboard"},
                "rows": {"revenue": {"table": "dashboard", "label": "Revenue"}},
            }
        )
    )
    got = _AnnualReader(raw, spec, layout).read("revenue", "FY2024")
    assert got.value is None and got.reason == "NOT_STATED"


def test_model_reader_still_refuses_a_malformed_number():
    raw = b"### T4.10 dashboard\n| Metric | FY2024 |\n|---|---|\n| Revenue | 12x |\n"
    spec = HandoffInput.model_validate_json(
        json.dumps({"path": "a.md", "sha256": hashlib.sha256(raw).hexdigest()})
    )
    from deploy_workflow.handoff_delivery import ModelDelivery

    layout = ModelDelivery.model_validate_json(
        json.dumps(
            {
                "periods": {
                    "FY2024": {
                        "start_date": "2024-01-01",
                        "end_date": "2024-12-31",
                        "balance_column": None,
                    }
                },
                "anchors": {"dashboard": "### T4.10 dashboard"},
                "rows": {"revenue": {"table": "dashboard", "label": "Revenue"}},
            }
        )
    )
    with pytest.raises(ValueError, match="unsupported source spelling 12x"):
        _AnnualReader(raw, spec, layout).read("revenue", "FY2024")


# ---- review adversarial cases (second model); expected values written out from the text ----


@pytest.mark.parametrize(
    ("rows", "expected"),
    [
        # One granularity, one key per label: placed oldest first.
        (["2024-12-31", "2024-06-30", "2023-12-31"], ["2023-12-31", "2024-06-30", "2024-12-31"]),
        (["2024Q3", "2024Q1", "2023Q4"], ["2023Q4", "2024Q1", "2024Q3"]),
        (["H2 2024", "H1 2024", "H2 2023"], ["H2 2023", "H1 2024", "H2 2024"]),
        # The retained TDG CP-1 leverage labels (newest first as written).
        (
            ["FY2024 / 2024-09-30", "FY2023 / 2023-09-30"],
            ["FY2023 / 2023-09-30", "FY2024 / 2024-09-30"],
        ),
        # Cannot be placed: the authored order stays, never a partial sort.
        (["Dec 2024", "Jun 2024", "Dec 2023"], ["Dec 2024", "Jun 2024", "Dec 2023"]),
        (["H2 2024", "Q3 2024"], ["H2 2024", "Q3 2024"]),
        (["FY2024", "Q1 2024", "FY2023"], ["FY2024", "Q1 2024", "FY2023"]),
        (["FY2024", "CY2024"], ["FY2024", "CY2024"]),
        (["FY2024", "2023-12-31"], ["FY2024", "2023-12-31"]),
    ],
)
def test_chart_periods_are_placed_only_when_unambiguous(tmp_path, rows, expected):
    _, figures, _ = deliver(tmp_path, handoff(leverage=[(p, "1", "1") for p in rows]))
    assert _categories(figures["S.1"].chart) == expected


def test_the_table_twin_follows_the_marks_and_the_source_table_keeps_its_order(tmp_path):
    _, figures, view = deliver(
        tmp_path, handoff(leverage=[("FY2024", "3", "9"), ("FY2023", "4", "8")])
    )
    twin = [(r.label, r.cells[0].text) for r in figures["S.1"].chart.table_twin.rows]
    assert twin == [
        ("Total debt / EBITDA · FY2023", "4x"),
        ("Net debt / EBITDA · FY2023", "8x"),
        ("Total debt / EBITDA · FY2024", "3x"),
        ("Net debt / EBITDA · FY2024", "9x"),
    ]
    module = next(m for m in view.modules if m.module_id == "CP-1")
    typed = next(t for t in module.tables if t.table_id == "chart-model-chart-strip-S.1")
    assert [r.label for r in typed.rows] == [
        "Total debt / EBITDA · FY2024",
        "Net debt / EBITDA · FY2024",
        "Total debt / EBITDA · FY2023",
        "Net debt / EBITDA · FY2023",
    ]


def test_a_table_inside_a_multiline_comment_is_not_published_but_stays_in_the_source():
    text = _doc("<!--\n| Metric | FY2024 |\n| --- | --- |\n| Secret | 999 |\n-->\nVisible.\n")
    module, source, _ = literal_module("CP-1", text.encode())
    assert not [f for f in module.facts if f.text and ("999" in f.text or "Secret" in f.text)]
    assert not [t for t in module.tables if any(r.label == "Secret" for r in t.rows)]
    assert "Visible." in [f.text for f in module.facts]
    assert ("line 10", "| Secret | 999 |") in [(s.locator, s.text) for s in source.spans]


def test_a_chart_table_hidden_in_a_comment_is_not_charted(tmp_path):
    text = (
        handoff()
        .replace("### Chart data: leverage\n\n", "### Chart data: leverage\n\n<!--\n")
        .replace("### Chart data: interest cover", "-->\n### Chart data: interest cover")
    )
    with pytest.raises(
        ValueError, match="markdown_selector: expected one CP-1/Chart data: leverage"
    ):
        deliver(tmp_path, text)


def test_an_unterminated_comment_is_refused_by_every_table_reader():
    from deploy_workflow.model_handoff_delivery import _literal_tables

    raw = _doc("<!--\n| A | B |\n| --- | --- |\n| x | 1 |\n").encode()
    with pytest.raises(ValueError, match="CP-8: the HTML comment opened on line 7 is never closed"):
        _literal_tables("CP-8", raw, hashlib.sha256(raw).hexdigest())


def test_a_fence_inside_a_comment_does_not_open_a_fence():
    shown = prose_texts(_doc("<!--\n```\n-->\nShown.\n<!--\nsecret\n-->\nTail.\n"))
    assert "Shown." in shown and "Tail." in shown and not [t for t in shown if "secret" in t]


def test_a_comment_opened_inside_a_fence_is_code_and_its_closer_is_text():
    shown = prose_texts(_doc("```\n<!--\n```\nAfter -->\nTail.\n"))
    # One paragraph: the fenced lines as written, then the two plain lines joined.
    assert "``` <!-- ```" in shown and "After --> Tail." in shown


def test_a_number_with_a_blank_reporting_unit_is_refused_naming_the_cell(tmp_path):
    with pytest.raises(ValueError, match="FY2023 Cash is reported in no unit, not US\\$m"):
        deliver(tmp_path, handoff(unit_liq=""))


def test_a_model_gap_keeps_its_exact_spelling_in_the_source_reference():
    from deploy_workflow.handoff_delivery import ModelDelivery

    raw = (
        b"### T4.10 dashboard\n| Metric | FY2024 |\n|---|---|\n"
        b"| Revenue | Not supplied: undisclosed |\n"
    )
    spec = HandoffInput(path="a.md", sha256=hashlib.sha256(raw).hexdigest())
    layout = ModelDelivery.model_validate_json(
        json.dumps(
            {
                "periods": {
                    "FY2024": {
                        "start_date": "2024-01-01",
                        "end_date": "2024-12-31",
                        "balance_column": None,
                    }
                },
                "anchors": {"dashboard": "### T4.10 dashboard"},
                "rows": {"revenue": {"table": "dashboard", "label": "Revenue"}},
            }
        )
    )
    got = _AnnualReader(raw, spec, layout).read("revenue", "FY2024")
    assert (got.value, got.reason) == (None, "NOT_STATED")
    assert [(s.source_locator, s.cell_text) for s in got.sources] == [
        ("line 4", "Not supplied: undisclosed")
    ]
