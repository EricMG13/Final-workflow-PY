"""The note guard on a line note table, and the wiring of ``expand_unit_maps`` (CP1H-R23, R23.24.2).

Answer key (read, never written): ``r1_line_source_second_header.py``, ``r3_wiring_mutants.py``
and ``r5_note_rows_edges.py`` of ``review-probes/t23-fix1/``. On a ``line:K-E`` table that prints
a note column every ``footnote_marker`` row goes to the model, with no second header needed. The
wiring test calls ``fw.expand_unit_maps`` with the store, source context and table reads isolated
(as ``tests/test_ocr_units.py`` does), and asserts the ``UnitInputs`` that ``expand`` receives.
"""

from types import SimpleNamespace
from typing import Any, cast

import pytest
from test_note_reference_guard_tables import _expand, _pack

from deploy_vii.contracts import Span
from deploy_vii.statement_extract import extract_statement_lines
from deploy_workflow import financial_workflow as fw
from deploy_workflow import unit_maps as um
from deploy_workflow.html_text import convert_html
from deploy_workflow.statement_lines import line_table


def _tr(*cells: str) -> str:
    return "<tr>" + "".join(f"<td>{cell}</td>" for cell in cells) + "</tr>"


@pytest.mark.parametrize(
    "second",
    [
        pytest.param(_tr("", "Level 1", "Level 2", "Level 3"), id="level-1-2-3"),
        pytest.param(_tr("", "GBP m", "GBP m", "GBP m"), id="gbp-m"),
    ],
)
def test_a_dropped_note_on_a_line_note_table_goes_to_the_model_whatever_its_second_header(
    second: str,
) -> None:
    html = (
        "<html><body><p>Annual report</p><p>Group financial statements</p>"
        "<p>Consolidated Statement of Financial Position</p><table>"
        + _tr("", "Note", "December 31, 2025", "December 31, 2024")
        + _tr("Receivables", "4", "350.0", "300.0")
        + _tr("Cash", "", "500.0", "400.0")
        + _tr("Total assets", "", "850.0", "700.0")
        + second
        + _tr("Goodwill", "12", "450", "670")
        + "</table></body></html>"
    ).encode()
    lines = convert_html(html).text.splitlines()
    spans = [Span(locator=f"line:{i}", text=text) for i, text in enumerate(lines, 1)]
    first = next(i for i, text in enumerate(lines, 1) if text.startswith("Consolidated"))
    assert first > 1
    table = line_table(dict(enumerate(spans, 1)), f"line:{first}-{len(lines)}", "html")
    pack = _pack("html", spans)
    assert _expand(pack, table, "BS", "Goodwill") == []


def _l(label: str, *values: str) -> str:
    return label.ljust(30) + "".join(v.rjust(12) for v in values)


def test_the_submit_entry_hands_the_note_pages_and_note_rows_to_the_expansion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    text = "\n".join(
        [
            _l("", "Note", "2025", "2024"),
            _l("Revenue", "4", "1,200", "1,000"),
            _l("Group", "2025", "2024", "2023"),
            _l("Goodwill", "12", "450", "670"),
            _l("Other", "8", "(1,500)", "900"),
        ]
    )
    table = extract_statement_lines(text, "page:1", "fin")
    assert [(r.line_no, "footnote_marker" in r.flags) for r in table.lines] == [
        (2, True),
        (3, False),
        (4, True),
        (5, True),
    ]
    source = SimpleNamespace(
        source_id="fin",
        status="ready",
        spans=[Span(locator="page:1", text=text)],
        coverage=[],
    )
    pack = SimpleNamespace(sources=[source])
    financial = SimpleNamespace(source_id="fin", classification="financial")
    context = SimpleNamespace(sources=[financial])
    store = SimpleNamespace(pack=lambda: pack)
    binding = SimpleNamespace(step_id="financials", ticket_id="t")
    evidence = SimpleNamespace(seen=lambda: (), extracted=())
    taken: list[Any] = []

    def expand(payload: str, *, extracted: Any, inputs: Any) -> um.Expansion:
        taken.append(inputs)
        return um.Expansion(payload, ())

    # the store, the source context and the table reads are isolated; the wiring is the real one
    monkeypatch.setattr(fw, "_source_context", lambda *a: context)
    monkeypatch.setattr(fw, "LineTools", lambda *a, **k: None)
    monkeypatch.setattr(fw, "seen_tables", lambda *a: [table])
    monkeypatch.setattr(fw, "known_bindings", lambda *a: SimpleNamespace(sources={}))
    monkeypatch.setattr(fw, "_other_statement_rows", lambda *a: {})
    monkeypatch.setattr(fw, "expand", expand)
    fw.expand_unit_maps(cast(Any, store), cast(Any, binding), "{}", cast(Any, evidence))
    (inputs,) = taken
    built = inputs()
    assert built.note_pages == frozenset({("fin", "page:1")})  # page:1 is not a located unit
    assert built.located == frozenset()  # page:1 is not a located statement unit
    assert built.note_rows == {("fin", "page:1"): frozenset({4, 5})}
