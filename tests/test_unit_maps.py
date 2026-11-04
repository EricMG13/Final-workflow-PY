"""The model maps statement units; Python composes the lines before the gate (CP1H-R23, T21b).

Answer keys (read, never written):
- the three SHC payloads of ``cases/statement-coverage/`` and the T21a helpers of
  ``tests/test_statement_compose.py`` that build each unit's column map and row map from a
  payload's own judgment fields; the frozen counts are 236 / 363 / 274 (R23.10);
- R23.10's Uncovered sets: none for run3-seq7; 10-Q line 74 and 75 and 10-K line 258 and 259
  (the rows the extractor flags ``label_ends_numeric``) for both seq6 cases;
- R23.13: a row flagged only ``footnote_marker`` is composed, any other flag leaves it to the
  model;
- R23.16: the expansion runs at the submit entry, before the binding; the composed submission is
  the payload from then on; notes reach the model and are not journaled issues.
"""

import hashlib
import json
import re
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest
import test_cp1_coverage_gate as gate
import test_financial_workflow as g1
import test_o2_done_when as o2
import test_statement_compose as comp

from deploy_vii.cp1_workflow import FinancialSubmission
from deploy_vii.execution import Execution
from deploy_vii.financial_contracts import StatementLine
from deploy_vii.live.schema import strict_schema
from deploy_vii.live.submission import STEPS
from deploy_vii.preparation import OCR_MARK, load_pack
from deploy_vii.statement_extract import ExtractedTable, extract_statement_lines
from deploy_workflow import financial_workflow as fw
from deploy_workflow import owner_workflow as ow
from deploy_workflow import statement_compose as sc
from deploy_workflow.model.loop import ToolLoop
from deploy_workflow.prompts.tools import model_schema, offered_schema
from deploy_workflow.unit_maps import (
    FinancialMapSubmission,
    UnitInputs,
    expand,
)

SPECS = [(m, s) for m, o in ow.OWNER_SPECS.items() for s in o.steps]


def _spec(step_id: str) -> ow.StepSpec:
    return next(s for _, s in SPECS if s.step_id == step_id)


# ---- (a) expansion through the real gate, SHC -----------------------------------------------


def _row_entries(item: dict[str, Any]) -> list[dict[str, Any]]:
    """The unit's row map, from the lines T21a composed: each carries the row's four judgment
    fields and cites the row's locator."""
    table: ExtractedTable = item["unit"]["table"]
    number = {row.locator: row.line_no for row in table.lines}
    seen: dict[int, dict[str, Any]] = {}
    for line in item["composition"].lines:
        row = number[line.value.citations[0].locator]
        seen[row] = {
            "row": row,
            "line_id": line.line_id,
            "item_id": line.item_id,
            "line_kind": line.line_kind,
            "sign_convention": line.sign_convention,
        }
    return list(seen.values())


def _map_payload(payload: dict[str, Any], composed: list[dict[str, Any]]) -> dict[str, Any]:
    """The payload with every line the composer composes removed (the lines of the rows it leaves
    to the model stay), plus the unit maps built from the same judgment fields."""
    maps = []
    for book in payload["financial"]["books"]:
        own = [c for c in composed if c["book"]["book_id"] == book["book_id"]]
        left = {
            (c["unit"]["source_id"], r.locator) for c in own for r in c["composition"].left_to_model
        }
        book["statement_lines"] = [
            line
            for line in book["statement_lines"]
            if any((c["source_id"], c["locator"]) in left for c in line["value"]["citations"])
        ]
        maps += [
            {
                "source_id": c["unit"]["source_id"],
                "locator": c["unit"]["locator"],
                "book_id": book["book_id"],
                "statement": c["unit"]["kind"],
                "columns": c["columns"],
                "rows": _row_entries(c),
            }
            for c in own
        ]
    return {**payload, "unit_maps": maps}


@pytest.fixture
def replay(tmp_path: Path, request: pytest.FixtureRequest) -> gate.Replay:
    run, submission, stored, _ = request.param
    return gate.Replay(tmp_path, run, submission, stored)


@pytest.mark.parametrize("replay", comp.CASES, indirect=True)
def test_the_expanded_payload_has_t21as_lines_and_exactly_the_uncovered_rows_of_r23_10(
    replay: gate.Replay, request: pytest.FixtureRequest
) -> None:
    expected = request.node.callspec.params["replay"][3]
    submission = request.node.callspec.params["replay"][1]
    payload = comp._payload(replay)
    composed = comp._compose_payload(payload, replay.tables())
    mapped = _map_payload(payload, composed)
    kept = {b["book_id"]: len(b["statement_lines"]) for b in mapped["financial"]["books"]}
    kept_priority = {
        b["book_id"]: max((line["display_priority"] for line in b["statement_lines"]), default=0)
        for b in mapped["financial"]["books"]
    }
    result = fw.expand_unit_maps(
        replay.history, ow._fin(replay.binding), json.dumps(mapped), replay.evidence
    )
    expanded = json.loads(result.payload)
    assert "unit_maps" not in expanded
    parsed = FinancialSubmission.model_validate_json(result.payload)  # else the gate returns early
    total = 0
    for book in parsed.financial.books:
        got = book.statement_lines[kept[book.book_id] :]
        own = [c for c in composed if c["book"]["book_id"] == book.book_id]
        position = 0
        offset = kept_priority[book.book_id]
        for item in own:  # a unit's priority is its offset plus the row's position in the unit
            rows = item["unit"]["table"].lines
            top = offset
            for line in item["composition"].lines:
                theirs = got[position]
                position += 1
                cited = line.value.citations[0].locator
                at = next(i for i, row in enumerate(rows, 1) if row.locator == cited)
                assert theirs.display_priority == offset + at
                same = line.model_copy(update={"display_priority": theirs.display_priority})
                assert same == theirs
                top = max(top, theirs.display_priority)
            offset = top
        assert position == len(got)  # the book holds no line T21a did not compose
        total += len(got)
    assert total == expected
    issues = replay.issues(result.payload)
    uncovered = set()
    for issue in gate._uncovered(issues):
        found = re.match(rf"{gate.PREFIX}(\S+) (\S+) line (\d+)", issue)
        assert found, issue
        uncovered.add((found[1], found[2], int(found[3])))
    assert uncovered == comp.UNCOVERED[submission]
    assert not [i for i in issues if gate.UNMEASURED in i or gate.NOT_EXTRACTED in i]
    assert not [n for n in result.notes if "not extracted" in n or "malformed" in n]


# ---- (b) through submit_review ---------------------------------------------------------------


def _skeleton(unit_maps: list[dict[str, Any]], periods: list[str]) -> str:
    """A financials payload that is not a whole `FinancialSubmission`: the gate then leaves the
    shape to the core (``_evidence_issues``), so the submit runs to the journal over the real
    extraction without a 36 KB payload."""
    manifest_periods = [
        {key: value for key, value in period.items() if key != "reported"}
        for period in g1.MANIFEST["periods"]
    ]
    period_records = {period["period_id"]: period for period in manifest_periods}
    for alias, period in zip(periods, manifest_periods[1:], strict=False):
        period_records.setdefault(alias, {**period, "period_id": alias})
    book = {
        "book_id": "b1",
        "periods": [period_records[p] for p in periods],
        "statement_lines": [],
    }
    return json.dumps({"financial": {"books": [book]}, "unit_maps": unit_maps})


def _revenue_map(columns: list[str | None], rows: tuple[int, ...]) -> dict[str, Any]:
    return {
        "source_id": "financial",
        "locator": "line:22-46",
        "book_id": "b1",
        "statement": "IS",
        "columns": columns,
        "rows": [
            {
                "row": row,
                "line_id": f"r{row}",
                "item_id": f"other:r{row}",
                "line_kind": "detail",
                "sign_convention": "signed",
            }
            for row in rows
        ],
    }


Q5 = ["p-q1", "p-q2", "p-q3", "p-q4", "p-fy"]


def _extract(workflow: ow.OwnerWorkflow, units: tuple[str, ...]) -> None:
    for unit in units:
        done = workflow.invoke("extract_statements", {"source_id": "financial", "locators": [unit]})
        assert done["status"] == "ok", done


def test_owner_submit_expands_a_map_payload_before_the_binding(tmp_path: Path) -> None:
    workflow, run_dir = o2.at_financials(tmp_path)
    _extract(workflow, o2.UNITS)
    binding, spec = workflow.binding, workflow.spec
    sent = _skeleton([_revenue_map(cast(Any, Q5), (24, 25))], Q5)
    outcome = workflow.submit_review(sent)
    assert outcome["status"] == "invalid", outcome  # past the gate: the skeleton is not a review
    *shown, last = outcome["notes"]  # the unit's other rows are left to the model
    assert shown and all(n.startswith("unit_maps[0] financial line:22-46") for n in shown)
    assert re.fullmatch(r"and \d+ more notes", last)  # a unit shows at most 12 notes
    record = workflow._submissions[-1]
    store = Execution(run_dir / "execution")
    raw = ow._raw(store, record.binding.payload_sha256)
    assert raw != sent
    assert hashlib.sha256(raw.encode()).hexdigest() == record.binding.payload_sha256
    document = json.loads(raw)
    assert "unit_maps" not in document
    sha = next(s.sha256 for s in load_pack(run_dir / "pack").sources if s.source_id == "financial")
    lines = document["financial"]["books"][0]["statement_lines"]
    assert len(lines) == 2 * 5  # two rows, five columns
    revenue = [line for line in lines if line["line_id"] == "r24"]
    assert [line["period_id"] for line in revenue] == Q5
    assert [Decimal(str(line["value"]["amount"])) for line in revenue] == [30, 30, 30, 30, 120]
    for line in lines:
        (cite,) = line["value"]["citations"]
        assert cite["source_sha256"] == sha and cite["source_id"] == "financial"
        assert cite["locator"] in ("line:24", "line:25")
        StatementLine.model_validate_json(json.dumps(line))
    # the stored payload is `_fill`'s output over the composed payload
    assert ow._raw(store, record.stored_payload_sha256) == ow._fill(store, binding, raw)[0]
    assert spec.schema is FinancialSubmission


def test_owner_submit_stores_a_payload_without_maps_byte_identical(tmp_path: Path) -> None:
    workflow, run_dir = o2.at_financials(tmp_path)
    sent = '{ "financial" : {"books": [ ] } ,\n "definition": {} }'
    outcome = workflow.submit_review(sent)
    assert outcome["status"] == "refused"
    record = workflow._submissions[-1]
    assert ow._raw(Execution(run_dir / "execution"), record.binding.payload_sha256) == sent
    assert "notes" not in outcome


def test_owner_refusal_shows_the_notes_but_does_not_journal_them(tmp_path: Path) -> None:
    workflow, run_dir = o2.at_financials(tmp_path)
    _extract(workflow, o2.UNITS[:2])  # the balance sheet unit is not extracted
    binding, spec, evidence = workflow.binding, workflow.spec, workflow._epoch_calls[-1]
    unextracted = {**_revenue_map(cast(Any, Q5), (24,)), "locator": "line:82-131"}
    elsewhere = {**_revenue_map(cast(Any, Q5), (24,)), "book_id": "nope"}
    outcome = workflow.submit_review(_skeleton([unextracted, elsewhere], Q5))
    assert outcome["status"] == "refused", outcome
    notes = outcome["notes"]
    assert any("line:82-131" in n and "not extracted in this epoch" in n for n in notes)
    assert any("no book nope" in n for n in notes)
    assert "Financials must extract every located statement unit" in " ".join(outcome["issues"])
    assert not [i for i in outcome["issues"] if "unit_maps" in i]
    record = workflow._submissions[-1]
    assert record.issues == tuple(outcome["issues"])  # the journal holds the gate's issues only
    store = Execution(run_dir / "execution")
    stored = ow._raw(store, record.stored_payload_sha256)
    assert ow._gate(store, binding, spec, stored, evidence.source_evidence) == record.issues
    for note in notes:
        assert all(note not in issue for issue in record.issues)


def test_g1_submit_expands_a_map_payload_before_the_binding(tmp_path: Path) -> None:
    workflow, _ = g1.before_financials(tmp_path)
    g1.financial_reads(workflow)
    page = g1.MANIFEST["sources"][1]["pages"][1]
    table = extract_statement_lines(page["text"], "page:2", "financial")
    width = len(table.lines[0].values)
    rows = [r for r in table.lines if not r.flags and len(r.values) == width][:2]
    assert len(rows) == 2
    columns: list[str | None] = ["q1-2025", *([None] * (width - 1))]
    unit = {
        "source_id": "financial",
        "locator": "page:2",
        "book_id": "b1",
        "statement": "IS",
        "columns": columns,
        "rows": [
            {
                "row": r.line_no,
                "line_id": f"r{r.line_no}",
                "item_id": f"other:r{r.line_no}",
                "line_kind": "detail",
                "sign_convention": "signed",
            }
            for r in rows
        ],
    }
    outcome = workflow.submit_review(_skeleton([unit], ["q1-2025"]))
    assert outcome["status"] == "invalid", outcome
    record = workflow._submissions[-1]
    store = Execution(tmp_path / "store")
    raw = fw._audit(store, "payloads", record.binding.payload_sha256).read_text("utf-8")
    document = json.loads(raw)
    assert "unit_maps" not in document
    lines = document["financial"]["books"][0]["statement_lines"]
    assert [Decimal(str(line["value"]["amount"])) for line in lines] == [r.values[0] for r in rows]
    assert {line["value"]["citations"][0]["source_sha256"] for line in lines} == {
        g1.MANIFEST["sources"][1]["sha256"]
    }
    stored = fw._audit(store, "payloads", record.stored_payload_sha256).read_text("utf-8")
    assert stored == fw._filled(store, workflow._binding, raw)[0]


# ---- the model sees the notes after the issues -----------------------------------------------


def _shown(result: dict[str, Any]) -> dict[str, Any]:
    class Workflow:
        def submit_review(self, payload: str) -> dict[str, Any]:
            return result

    loop = object.__new__(ToolLoop)
    loop._workflow = cast(Any, Workflow())
    content, _, _ = loop._call(cast(Any, SimpleNamespace(arguments={})), "submit_review")
    shown: dict[str, Any] = json.loads(content)
    return shown


def _outcome(**extra: Any) -> dict[str, Any]:
    return {
        "status": "refused",
        "issues": ["gate issue"],
        "step_id": "financials",
        "next_step": "financials",
        "refusal": None,
        **extra,
    }


def test_the_tool_result_appends_the_notes_after_the_gates_issues() -> None:
    shown = _shown(_outcome(notes=["unit_maps[0] x: left to you"]))
    keys = list(shown)
    assert shown["issues"] == ["gate issue"] and shown["notes"] == ["unit_maps[0] x: left to you"]
    assert keys.index("notes") > keys.index("issues")


def test_the_tool_result_is_unchanged_without_notes() -> None:
    assert list(_shown(_outcome())) == ["status", "issues", "step_id", "next_step", "refusal"]


# ---- (c) the schema --------------------------------------------------------------------------


def test_the_offered_financials_schema_has_unit_maps_and_the_canonical_one_does_not() -> None:
    spec = _spec("financials")
    offered = offered_schema(spec)
    assert "unit_maps" in offered["properties"] and "unit_maps" in offered["required"]
    assert model_schema(spec) is FinancialMapSubmission
    assert spec.schema is FinancialSubmission
    assert fw.SCHEMAS["financials"] is FinancialSubmission
    assert "unit_maps" not in strict_schema(FinancialSubmission)["properties"]
    assert set(FinancialMapSubmission.model_fields) - {"unit_maps"} == set(
        FinancialSubmission.model_fields
    )


@pytest.mark.parametrize("module_id,spec", SPECS, ids=[f"{m}-{s.step_id}" for m, s in SPECS])
def test_every_other_steps_offered_schema_is_unchanged(module_id: str, spec: ow.StepSpec) -> None:
    if spec.step_id == "financials":
        return
    live = STEPS.get(spec.step_id)
    expected = spec.schema if spec.step_id == "source_readiness" or live is None else live.schema
    assert model_schema(spec) is expected
    assert "unit_maps" not in json.dumps(offered_schema(spec))


# ---- (d) a mistake composes nothing for its unit ---------------------------------------------

TABLE_56, SHA_56 = comp._page("CZR", 56)
OWN = {"line_id": "own", "display_priority": 7}


def _entry(**change: Any) -> dict[str, Any]:
    return {
        "source_id": TABLE_56.source_id,
        "locator": TABLE_56.locator,
        "book_id": "b1",
        "statement": "BS",
        "columns": ["fy2024", "fy2023"],
        "rows": [
            {
                "row": r.line_no,
                "line_id": f"l{r.line_no}",
                "item_id": f"other:r{r.line_no}",
                "line_kind": "detail",
                "sign_convention": "signed",
            }
            for r in TABLE_56.lines[:2]
        ],
        **change,
    }


def _printed(*ids: str) -> Any:
    """A table's own printed header as `UnitInputs.ocr_header` reads it: one period id per column
    (CP1H-R23.27.1: every unit's map is verified against it)."""
    return lambda _table, _book: tuple(frozenset({i}) for i in ids)


PRINTED = _printed("fy2024", "fy2023")


def _document(maps: object, lines: list[dict[str, Any]] | None = None) -> str:
    book = {
        "book_id": "b1",
        "periods": [{"period_id": "fy2024"}, {"period_id": "fy2023"}],
        "statement_lines": [OWN] if lines is None else lines,
    }
    return json.dumps({"financial": {"books": [book]}, "unit_maps": maps})


def _expand(
    maps: object,
    *,
    tables: list[ExtractedTable] | None = None,
    extracted: bool = True,
    printed: Any = PRINTED,
) -> tuple[Any, list[str]]:
    """The expanded document and the notes, then "called" once if the inputs were read."""
    units = [TABLE_56] if tables is None else tables
    calls: list[str] = []

    def inputs() -> UnitInputs:
        calls.append("called")
        located = frozenset((t.source_id, t.locator) for t in units)
        return UnitInputs(units, {TABLE_56.source_id: SHA_56}, ocr_header=printed, located=located)

    keys = {(t.source_id, t.locator) for t in units} if extracted else set()
    result = expand(_document(maps), extracted=keys, inputs=inputs)
    return json.loads(result.payload), [*result.notes, *calls]


def test_a_valid_map_appends_its_lines_after_the_models_own_with_the_next_priorities() -> None:
    document, notes = _expand([_entry()])
    *shown, called = notes  # the unit's other rows are left to the model, then the call
    assert called == "called"
    assert shown and all("(not_in_row_map)" in n or n.startswith("and ") for n in shown)
    assert "unit_maps" not in document
    lines = document["financial"]["books"][0]["statement_lines"]
    assert lines[0] == OWN and len(lines) == 1 + 2 * 2
    assert [line["display_priority"] for line in lines[1:]] == [8, 8, 9, 9]
    for line in lines[1:]:
        StatementLine.model_validate_json(json.dumps(line))


def test_the_next_unit_of_a_book_continues_after_the_previous_ones_priorities() -> None:
    second = replace(TABLE_56, locator="page:99")
    document, _ = _expand([_entry(), _entry(locator="page:99")], tables=[TABLE_56, second])
    lines = document["financial"]["books"][0]["statement_lines"]
    assert [line["display_priority"] for line in lines[1:]] == [8, 8, 9, 9, 10, 10, 11, 11]


REPEATED = _entry()["rows"] + _entry()["rows"][:1]


@pytest.mark.parametrize(
    "maps,extracted,fragment,asked",
    [
        pytest.param([_entry(statement="XX")], True, "unit_maps[0] is malformed", False, id="bad"),
        pytest.param(["rows"], True, "unit_maps[0] is malformed", False, id="not-a-map"),
        pytest.param([_entry(book_id="nope")], True, "no book nope", False, id="unknown-book"),
        pytest.param([_entry()], False, "not extracted in this epoch", False, id="unextracted"),
        pytest.param([_entry(rows=REPEATED)], True, "mapped more than once", True, id="repeats"),
    ],
)
def test_a_mistaken_map_composes_nothing_leaves_the_payload_lines_and_gives_a_note(
    maps: object, extracted: bool, fragment: str, asked: bool
) -> None:
    document, notes = _expand(maps, extracted=extracted)
    assert document["financial"]["books"][0]["statement_lines"] == [OWN]
    assert "unit_maps" not in document
    assert any(fragment in n for n in notes), notes
    assert ("called" in notes) is asked  # the inputs are read only for a unit that can compose


def test_a_failed_check_composes_nothing_and_the_note_names_check_column_and_both_sums() -> None:
    table, _sha, row_map = comp._czr()
    assets = next(r for r in table.lines if r.label == "Total assets")
    bumped = comp._bumped(table, assets, 0)
    entries = [
        {
            "row": n,
            "line_id": j.line_id,
            "item_id": j.item_id,
            "line_kind": j.line_kind,
            "sign_convention": j.sign_convention,
        }
        for n, j in row_map.items()
    ]
    document, notes = _expand([_entry(rows=entries)], tables=[bumped])
    assert document["financial"]["books"][0]["statement_lines"] == [OWN]
    printed = assets.values[0]
    note = next(n for n in notes if sc.BS_LIABILITIES_PLUS_EQUITY in n)
    assert "column 0" in note and "fy2024" in note
    assert f"{(printed or 0) + 1} != {printed}" in note


def test_a_row_left_to_the_model_and_an_undeclared_column_are_notes() -> None:
    flagged = replace(TABLE_56.lines[0], flags=("label_ends_numeric",))
    table = replace(TABLE_56, lines=(flagged, *TABLE_56.lines[1:]))
    document, notes = _expand(
        [_entry(columns=["fy2024", "fy2099"])], tables=[table], printed=_printed("fy2024", "fy2099")
    )
    lines = document["financial"]["books"][0]["statement_lines"]
    assert len(lines) == 1 + 1  # the second row, in fy2024 only
    left = next(n for n in notes if f"row {flagged.line_no} " in n)
    assert "left to you (flagged): label_ends_numeric" in left and flagged.label in left
    assert any("fy2099" in n and "does not declare" in n for n in notes)


# ---- the payloads that are not expanded -----------------------------------------------------


def test_a_payload_without_unit_maps_is_returned_byte_identical() -> None:
    for text in ('{ "financial" : {"books": [ ] } }', "[1, 2]", "not json", '{"a": 1.50}'):
        result = expand(text, extracted=set(), inputs=lambda: pytest.fail("no map to compose"))
        assert (result.payload, result.notes) == (text, ())


@pytest.mark.parametrize("empty", [None, []])
def test_an_empty_unit_maps_is_dropped_and_a_non_list_is_left_with_a_note(empty: object) -> None:
    text = json.dumps({"financial": {"books": []}, "unit_maps": empty})
    dropped = expand(text, extracted=set(), inputs=lambda: pytest.fail("no map to compose"))
    assert json.loads(dropped.payload) == {"financial": {"books": []}} and dropped.notes == ()
    odd = json.dumps({"unit_maps": {"x": 1}})
    kept = expand(odd, extracted=set(), inputs=lambda: pytest.fail("no map to compose"))
    assert kept.payload == odd and kept.notes == ("unit_maps is not a list; nothing composed",)


# ---- (e) R23.13: footnote_marker is informational ---------------------------------------------


@pytest.mark.parametrize(
    "flags,composed",
    [
        ((), True),
        (("footnote_marker",), True),
        (("label_ends_numeric",), False),
        (("more_values_than_header_years",), False),
        (("footnote_marker", "label_ends_numeric"), False),
    ],
)
def test_only_a_footnote_marker_flag_leaves_a_row_composable(
    flags: tuple[Any, ...], composed: bool
) -> None:
    row = replace(TABLE_56.lines[0], flags=flags)
    table = replace(TABLE_56, lines=(row, *TABLE_56.lines[1:]))
    judged = {row.line_no: comp._judge(row)}
    result = comp._compose(table, SHA_56, "BS", ["fy2024", "fy2023"], judged)
    made = [line for line in result.lines if line.value.citations[0].locator == row.locator]
    assert bool(made) is composed
    if not composed:
        (left,) = [r for r in result.left_to_model if r.line_no == row.line_no]
        assert (left.reason, left.detail) == (sc.FLAGGED, ", ".join(flags))


# ---- model-controlled shapes fail closed (CP1H-R23.20) ---------------------------------------


def _expand_book(**change: Any) -> tuple[dict[str, Any], tuple[str, ...]]:
    book = {
        "book_id": "b1",
        "periods": [{"period_id": "fy2024"}, {"period_id": "fy2023"}],
        "statement_lines": [],
        **change,
    }
    text = json.dumps({"financial": {"books": [book]}, "unit_maps": [_entry()]})
    keys = {(TABLE_56.source_id, TABLE_56.locator)}
    result = expand(
        text,
        extracted=keys,
        inputs=lambda: UnitInputs(
            [TABLE_56], {TABLE_56.source_id: SHA_56}, ocr_header=PRINTED, located=frozenset(keys)
        ),
    )
    return json.loads(result.payload)["financial"]["books"][0], result.notes


@pytest.mark.parametrize("bad", [["fy2024"], {"x": 1}], ids=["list", "object"])
def test_a_period_id_that_is_not_a_string_is_undeclared_and_does_not_crash(bad: object) -> None:
    book, notes = _expand_book(periods=[{"period_id": bad}, {"period_id": "fy2023"}])
    assert [line["period_id"] for line in book["statement_lines"]] == ["fy2023", "fy2023"]
    assert any("column 0" in n and "does not declare" in n for n in notes), notes


@pytest.mark.parametrize("held", ["garbage", 7, {"a": 1}], ids=["string", "number", "object"])
def test_a_statement_lines_that_is_not_a_list_is_kept_and_nothing_is_composed(held: object) -> None:
    book, notes = _expand_book(statement_lines=held)
    assert book["statement_lines"] == held
    assert any("statement_lines is not a list" in n and "nothing composed" in n for n in notes)


# ---- units on OCR pages (CP1H-R23.23) ---------------------------------------------------------


@pytest.mark.parametrize("on_ocr_page", [True, False])
def test_the_expansion_passes_ocr_for_a_unit_on_an_ocr_page_only(
    monkeypatch: pytest.MonkeyPatch, on_ocr_page: bool
) -> None:
    key = (TABLE_56.source_id, TABLE_56.locator)
    asked: list[Any] = []
    real = sc.compose_unit

    def spy(*args: Any, **kwargs: Any) -> sc.Composition:
        asked.append(kwargs.get("ocr"))
        return real(*args, **kwargs)

    monkeypatch.setattr(sc, "compose_unit", spy)
    ocr_pages = frozenset({key}) if on_ocr_page else frozenset({("other-source", "page:1")})
    expand(
        _document([_entry()]),
        extracted={key},
        inputs=lambda: UnitInputs(
            [TABLE_56],
            {TABLE_56.source_id: SHA_56},
            ocr_pages=ocr_pages,
            ocr_header=PRINTED,
            located=frozenset({key}),
        ),
    )
    assert asked == [on_ocr_page]


def test_the_ocr_pages_are_the_financial_pages_whose_coverage_starts_with_the_ocr_mark() -> None:
    def cover(locator: str, limitation: str | None) -> SimpleNamespace:
        return SimpleNamespace(locator=locator, limitation=limitation)

    mark = f"{OCR_MARK} (tesseract 5.5.2); verify against the original"
    pack = SimpleNamespace(
        sources=[
            SimpleNamespace(
                source_id="fin",
                coverage=[cover("page:1", None), cover("page:2", mark), cover("page:3", "No")],
            ),
            SimpleNamespace(source_id="other", coverage=[cover("page:9", mark)]),
        ]
    )
    assert fw._ocr_pages(pack, ("fin",)) == {("fin", "page:2")}
