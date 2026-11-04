"""Units on pages read by OCR: the wiring and the gate (CP1H-R23.23, R23.23.1; T22 fix 1).

The wiring: a financial source whose coverage holds `OCR_MARK` for `page:N` puts
`(source_id, "page:N")` in the `ocr_pages` of the inputs the submit entry builds. The gate: a
located unit on such a page is not required (no extraction issue, no coverage); a unit on a page
with a text layer still is.
"""

from types import SimpleNamespace
from typing import Any, cast

import pytest
from test_line_locators import FIN, H_BS, H_IS, HEADER, NOT_EXTRACTED, ROWS, _issues, _with_spans

from deploy_vii.contracts import Coverage, Span
from deploy_vii.preparation import OCR_MARK, PreparedPack
from deploy_workflow import financial_workflow as fw
from deploy_workflow import unit_maps as um

MARK = f"{OCR_MARK} (tesseract 5.5.2); verify against the original"
UNCOVERED = "Uncovered extracted statement line: "


def test_the_submit_entry_hands_the_ocr_pages_to_the_expansion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pack = SimpleNamespace(
        sources=[
            SimpleNamespace(
                source_id="fin",
                status="ready",
                spans=[],
                coverage=[
                    SimpleNamespace(locator="page:1", limitation=None),
                    SimpleNamespace(locator="page:4", limitation=MARK),
                ],
            )
        ]
    )
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
    monkeypatch.setattr(fw, "seen_tables", lambda *a: [])
    monkeypatch.setattr(fw, "known_bindings", lambda *a: SimpleNamespace(sources={}))
    monkeypatch.setattr(fw, "_other_statement_rows", lambda *a: {})
    monkeypatch.setattr(fw, "expand", expand)
    fw.expand_unit_maps(cast(Any, store), cast(Any, binding), "{}", cast(Any, evidence))
    (inputs,) = taken
    assert inputs().ocr_pages == frozenset({("fin", "page:4")})
    assert inputs().ocr_header is fw._ocr_header


def _pack(*, ocr_first: bool) -> PreparedPack:
    """Two page units: page:1 a balance sheet, page:2 an income statement; page:1's coverage is
    OCR's when `ocr_first`."""
    spans = [
        Span(locator="page:1", text="\n".join([H_BS, HEADER, ROWS[0]])),
        Span(locator="page:2", text="\n".join([H_IS, HEADER, ROWS[1]])),
    ]
    coverage = (
        Coverage(locator="page:1", status="retained", limitation=MARK if ocr_first else None),
        Coverage(locator="page:2", status="retained"),
    )
    pack = _with_spans(spans)
    return pack.model_copy(
        update={
            "sources": tuple(
                s.model_copy(update={"coverage": coverage}) if s.source_id == FIN else s
                for s in pack.sources
            )
        }
    )


def test_the_gate_does_not_require_the_extraction_of_an_ocr_unit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, issues = _issues(monkeypatch, _pack(ocr_first=True), extract_all=False)
    assert f"{NOT_EXTRACTED}{FIN} page:2" in issues  # the text-layer unit is still required
    assert not [i for i in issues if "page:1" in i]


def test_the_gate_requires_the_extraction_of_both_units_without_ocr(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, issues = _issues(monkeypatch, _pack(ocr_first=False), extract_all=False)
    assert f"{NOT_EXTRACTED}{FIN} page:1, {FIN} page:2" in issues


def test_the_gate_asks_no_coverage_of_an_ocr_unit_and_still_asks_it_of_a_text_unit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, issues = _issues(monkeypatch, _pack(ocr_first=True))
    uncovered = [i for i in issues if i.startswith(UNCOVERED)]
    assert uncovered, issues
    assert all(f"{FIN} page:2 " in i for i in uncovered)
    _, both = _issues(monkeypatch, _pack(ocr_first=False))
    assert any(f"{FIN} page:1 " in i for i in both if i.startswith(UNCOVERED))
