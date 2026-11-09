"""Offline adversarial tests of the adapted cp-os loop; not live module proof."""

import json
import time
from dataclasses import replace
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from deploy_vii.contracts import Run
from deploy_workflow.model.adapter import AdapterReply
from deploy_workflow.model.handoff import REDACTION_FAILED, HandoffExecutor, ModuleTools
from deploy_workflow.model.turn import ToolCall, Turn, Usage
from deploy_workflow.owners.cpos import HandoffTask


def task() -> HandoffTask:
    return HandoffTask(
        Run(
            run_id="loop-test",
            issuer_id="TDG",
            issuer_name="TransDigm Group Incorporated",
            as_of=date(2024, 9, 30),
            case_kind="public",
            pathway="credit_snapshot",
            requested_modules=("CP-1", "CP-MODEL", "CP-1A", "CP-2"),
        ),
        "CP-2",
        b"Compare evidence and preserve gaps.",
        {"S1.txt": b"Revenue 100\nMissing cash"},
        {"CP-1": b"Revenue 100; cash unavailable"},
        1,
        (),
    )


GOOD = b"## Request\nTDG\n## Sources\nS1\n## Findings\n100\n## Calculations\nNone\n## Gaps\ncash unavailable\n## Next module\ndelivery\n"


def check(_task: HandoffTask, raw: bytes) -> tuple[str, ...]:
    return () if raw == GOOD else ("Expected source amount 100 and missing cash.",)


def turn(*calls: ToolCall, usage: Usage | None = None) -> AdapterReply:
    result = Turn(
        "",
        calls,
        usage or Usage(input_tokens=100, output_tokens=50),
        "tool_use" if calls else "end",
        "gpt-6.1-sol",
        "test",
        200,
    )
    return AdapterReply("ok", result, None, 200, None, None, 1, 2, result.usage)


class Adapter:
    config_id = "sol-medium"
    ruling = None

    def __init__(self, *replies: AdapterReply | Exception) -> None:
        self.replies = list(replies)
        self.requests = []

    def complete(self, request, **_identity):
        self.requests.append(request)
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply


def test_read_reject_edit_retains_exchange_and_current_handoff(tmp_path: Path) -> None:
    adapter = Adapter(
        turn(ToolCall("r", "read_pages", {"source_id": "S1.txt", "first": 1, "last": 1})),
        turn(ToolCall("w", "write_handoff", {"markdown": GOOD.decode().replace("100", "101")})),
        turn(ToolCall("e", "edit_handoff", {"edits": [{"old": "101", "new": "100"}]})),
    )
    loop = HandoffExecutor(tmp_path, adapter=adapter, cap_usd=Decimal(10), check=check)
    assert loop(task()) == GOOD
    assert "Revenue 100; cash unavailable" in adapter.requests[0].messages[1].text
    import json

    roles = json.loads(adapter.requests[0].messages[1].text)["module_roles"]
    assert "legal and covenant" in roles["CP-4"]
    assert "investment-committee" in roles["CP-6"]
    assert "prior and current deliverables" in roles["CP-8"]
    assert "CP-MEMO" not in roles
    assert "REJECTED" in adapter.requests[2].messages[-1].text
    assert len(list(tmp_path.rglob("*.request.json"))) == 3
    assert len(list(tmp_path.rglob("*.response.json"))) == 3
    assert len(list(tmp_path.rglob("*.tools.json"))) == 3
    assert loop.budget.spent > 0
    assert not loop.budget.unsettled
    with pytest.raises(ValueError, match="already_started"):
        loop(task())
    assert len(adapter.requests) == 3


def test_whole_filing_reads_stop_before_the_request_outgrows_the_budget_bound(
    tmp_path: Path,
) -> None:
    """runs/cpos-launch-live-001: parallel reads of whole filings stopped CP-0 with "1124866
    input-token bound is over the 1050000 supported", after paying for reads it never used."""
    filing = (
        "x" * 11_999 + "\n"
    ) * 200  # 200 pages of 12,000 characters, as a large text file reads.
    reads = [
        ToolCall(str(n), "read_pages", {"source_id": "S1.txt", "first": n + 1, "last": n + 8})
        for n in range(0, 192, 8)
    ]
    adapter = Adapter(
        turn(*reads[:8]),
        turn(*reads[8:16]),
        turn(*reads[16:24]),
        turn(ToolCall("w", "write_handoff", {"markdown": GOOD.decode()})),
    )
    loop = HandoffExecutor(tmp_path, adapter=adapter, cap_usd=Decimal(10), check=check)
    current = replace(task(), sources={"S1.txt": filing.encode()})
    assert loop(current) == GOOD
    assert max(p.stat().st_size for p in tmp_path.rglob("*.request.json")) < 1_050_000
    tools = [m.text for m in adapter.requests[-1].messages if m.role == "tool"]
    assert tools[0].startswith("<<<SOURCE id=S1.txt")
    assert "gap" in tools[-1] and tools[-1].startswith("ERROR")


def test_atomic_patch_allowlist_and_page_bounds(tmp_path: Path) -> None:
    module = ModuleTools(task(), tmp_path, check)
    assert module.call("__init__", {}).startswith("ERROR")
    assert module.call("read_pages", {"source_id": "S1.txt", "first": 2, "last": 2}).startswith(
        "ERROR"
    )
    assert module.call("read_pages", {"source_id": "S1.txt", "first": True, "last": 1}).startswith(
        "ERROR"
    )
    module.call("write_handoff", {"markdown": GOOD.decode().replace("100", "101")})
    draft = module.draft
    assert module.call(
        "edit_handoff", {"edits": [{"old": "101", "new": "100"}, {"old": "absent", "new": "x"}]}
    ).startswith("ERROR")
    assert module.draft == draft
    assert not module.accepted


def test_excel_input_preserves_formula_zero_and_cell_locators(tmp_path: Path) -> None:
    import io
    from dataclasses import replace

    from openpyxl import Workbook

    book = Workbook()
    sheet = book.active
    sheet.title = "Annual"
    sheet.append([0, None, "=A1+1", "USD millions"])
    buffer = io.BytesIO()
    book.save(buffer)
    module = ModuleTools(
        replace(task(), sources={"issuer.xlsx": buffer.getvalue()}), tmp_path, check
    )
    read = module.read_pages("issuer.xlsx", 1, 1)
    assert "Sheet Annual" in read and "A1=0" in read and "C1='=A1+1'" in read
    assert "D1='USD millions'" in read and "B1=" not in read
    assert not list(tmp_path.iterdir())  # Input parsing produces no workbook deliverable.


def _workbook(sheet_xml: str, dimension: str = "") -> bytes:
    """A minimal OOXML workbook written by hand, independent of the reader under test."""
    import io
    import zipfile

    main = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    rels = "http://schemas.openxmlformats.org/package/2006/relationships"
    office = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    parts = {
        "[Content_Types].xml": '<Types xmlns="http://schemas.openxmlformats.org/package/2006/'
        'content-types"><Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-'
        'officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/'
        'sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.'
        'worksheet+xml"/></Types>',
        "_rels/.rels": f'<Relationships xmlns="{rels}"><Relationship Id="r1" '
        f'Type="{office}/officeDocument" Target="xl/workbook.xml"/></Relationships>',
        "xl/workbook.xml": f'<workbook xmlns="{main}" xmlns:r="{office}"><sheets>'
        '<sheet name="Annual FY" sheetId="1" r:id="rId1"/></sheets></workbook>',
        "xl/_rels/workbook.xml.rels": f'<Relationships xmlns="{rels}"><Relationship Id="rId1" '
        f'Type="{office}/worksheet" Target="worksheets/sheet1.xml"/></Relationships>',
        "xl/worksheets/sheet1.xml": f'<worksheet xmlns="{main}">{dimension}'
        f"<sheetData>{sheet_xml}</sheetData></worksheet>",
    }
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, text in parts.items():
            archive.writestr(name, text)
    return buffer.getvalue()


def _read(tmp_path: Path, source_id: str, raw: bytes) -> str:
    module = ModuleTools(replace(task(), sources={source_id: raw}), tmp_path, check)
    return module.read_pages(source_id, 1, 1)


# Codex review of ac22d9d. Expected by hand: the stored lexeme 9007199254740993.25 is shown
# exactly (a float would give 9007199254740994.0); a formula with no stored value shows its
# cache as [absent], never 0; a non-General number format is shown with the cell.
def test_excel_amount_is_its_exact_stored_lexeme(tmp_path: Path) -> None:
    raw = _workbook(
        '<row r="1"><c r="A1"><v>9007199254740993.25</v></c><c r="B1"><f>A1*2</f></c></row>'
    )
    read = _read(tmp_path, "issuer.xlsx", raw)
    assert "Sheet Annual FY" in read
    assert "A1=9007199254740993.25 | B1='=A1*2' cache=[absent]" in read
    assert "9007199254740994" not in read


# Expected by hand: two stored cells at opposite corners of a sheet whose dimension claims all
# 17,179,869,184 cells are read as exactly those two cells, well within the test's time.
def test_excel_sparse_workbook_reads_only_stored_cells(tmp_path: Path) -> None:
    raw = _workbook(
        '<row r="1"><c r="A1"><v>1</v></c></row>'
        '<row r="1048576"><c r="XFD1048576"><v>2</v></c></row>',
        dimension='<dimension ref="A1:XFD1048576"/>',
    )
    started = time.monotonic()
    read = _read(tmp_path, "issuer.xlsx", raw)
    assert time.monotonic() - started < 5
    assert "date serials are retained without conversion.\nA1=1\nXFD1048576=2\n" in read


# Expected by hand: workbook bytes are a workbook under any source id, and bytes that only begin
# like a ZIP, or a ZIP that is not a workbook, are not.
def test_excel_is_detected_by_content_not_source_id(tmp_path: Path) -> None:
    import io
    import zipfile

    raw = _workbook('<row r="1"><c r="A1" t="inlineStr"><is><t>USD m</t></is></c></row>')
    assert "A1='USD m'" in _read(tmp_path, "S1", raw)
    assert "page=1>>>\nPK\x03\x04 is not a workbook\n<<<END>>>" in _read(
        tmp_path, "notes.xlsx", b"PK\x03\x04 is not a workbook"
    )
    other = io.BytesIO()
    with zipfile.ZipFile(other, "w") as archive:
        archive.writestr("word/document.xml", "<w/>")
    with pytest.raises(UnicodeDecodeError):
        _read(tmp_path, "S2", other.getvalue())


def test_heading_feedback_identifies_exact_repair(tmp_path: Path) -> None:
    module = ModuleTools(task(), tmp_path, check)
    response = module.call(
        "write_handoff", {"markdown": GOOD.decode().replace("## Findings", "## Extra\n## Findings")}
    )
    assert "## Request; ## Sources; ## Findings" in response
    assert "All subsections must use ### or deeper" in response
    assert "Extra" in response


def test_acceptance_is_terminal_within_same_turn(tmp_path: Path) -> None:
    adapter = Adapter(
        turn(
            ToolCall("a", "write_handoff", {"markdown": GOOD.decode()}),
            ToolCall("b", "write_handoff", {"markdown": "corrupt"}),
        )
    )
    loop = HandoffExecutor(tmp_path, adapter=adapter, cap_usd=Decimal(10), check=check)
    assert loop(task()) == GOOD
    assert len(list(tmp_path.rglob("*.draft.md"))) == 1


def test_explicit_retained_draft_repair_uses_existing_edit_tool(tmp_path: Path) -> None:
    from dataclasses import replace

    original = GOOD.replace(b"100", b"101")
    adapter = Adapter(
        turn(ToolCall("repair", "edit_handoff", {"edits": [{"old": "101", "new": "100"}]}))
    )
    loop = HandoffExecutor(tmp_path, adapter=adapter, cap_usd=Decimal(10), check=check)
    assert loop(replace(task(), draft=original, attempt=2)) == GOOD
    assert original == GOOD.replace(b"100", b"101")
    assert len(adapter.requests) == 1
    assert '"repair_draft"' in adapter.requests[0].messages[1].text


@pytest.mark.parametrize("reply", [RuntimeError("possibly sent"), turn(usage=Usage())])
def test_unknown_charge_stops_and_holds_budget(tmp_path: Path, reply) -> None:
    adapter = Adapter(reply)
    loop = HandoffExecutor(tmp_path, adapter=adapter, cap_usd=Decimal(10), check=check)
    with pytest.raises(RuntimeError):
        loop(task())
    assert len(adapter.requests) == 1
    assert loop.budget.stop_reason is not None
    assert loop.budget.spent > 0  # Budget conservatively charges the entire unknown hold.


def test_cap_refuses_before_send(tmp_path: Path) -> None:
    adapter = Adapter()
    loop = HandoffExecutor(tmp_path, adapter=adapter, cap_usd=Decimal("0.00001"), check=check)
    with pytest.raises(Exception, match="cap"):
        loop(task())
    assert not adapter.requests


def test_existing_calculation_kernel_preserves_missing_zero_and_exact_decimals(
    tmp_path: Path,
) -> None:
    import json

    module = ModuleTools(task(), tmp_path, check)
    assert json.loads(module.calculate("sum", ["0.1", "0.2"]))["value"] == "0.3"
    assert json.loads(module.calculate("sum", ["0", None]))["value"] is None
    assert json.loads(module.calculate("sum", ["0", "0"]))["value"] == "0"
    assert json.loads(module.calculate("ratio", ["1", "0"]))["value"] is None
    declined = json.loads(module.calculate("ratio", ["-6", "-36"]))
    assert declined["value"] is None
    assert declined["reason"] == "ZERO_OR_NEGATIVE_DENOMINATOR"
    assert json.loads(module.calculate("ratio", ["6", "36"]))["value"] == (
        "0.16666666666666666666666666666666666667"
    )
    assert module.calculate("sum", ["NaN"]).startswith("ERROR")
    assert module.calculate("sum", ["1e9999"]).startswith("ERROR")


def test_preconstructed_executor_reloads_prior_spend(tmp_path: Path) -> None:
    from dataclasses import replace

    one = HandoffExecutor(
        tmp_path,
        adapter=Adapter(turn(ToolCall("w", "write_handoff", {"markdown": GOOD.decode()}))),
        cap_usd=Decimal(10),
        check=check,
    )
    two = HandoffExecutor(
        tmp_path,
        adapter=Adapter(turn(ToolCall("w", "write_handoff", {"markdown": GOOD.decode()}))),
        cap_usd=Decimal(10),
        check=check,
    )
    one(task())
    prior = one.budget.spent
    two(replace(task(), instructions=b"Changed module instructions"))
    assert two.budget.spent == prior * 2


def test_governance_tool_retains_evidence_rows_and_unscorable_dimensions(tmp_path: Path) -> None:
    import json

    module = ModuleTools(task(), tmp_path, check)
    row = {
        "kind": "behaviour_flag",
        "topic": "Documented distribution",
        "documented_fact": "Source fact",
        "direction": "Extraction-Oriented",
        "behaviour_type": "distribution",
        "amount_funding_source": "Historical distribution; amount not supplied in this fixture",
        "legal_capacity_link": "Capacity not assessed",
        "dimension": "Shareholder extraction risk",
        "risk_mechanic": "Cash leaves issuer",
        "credit_implication": "Reduced buffer",
        "evidence_quality": "High",
        "category": "Documentary Fact",
        "citations": [{"source_id": "S1.txt", "locator": "page 1", "quote": "Source fact"}],
        "limitation": "Historical",
    }
    result = json.loads(module.score_governance([row]))
    assert result["composite"] == "Not Scorable"
    assert result["risk_level"] == "High"
    extraction = next(
        d for d in result["dimensions"] if d["dimension"] == "Shareholder extraction risk"
    )
    assert extraction["score"] == "5"
    assert extraction["deciding"][0]["citations"][0]["quote"] == "Source fact"
    invalid_topic = {**row, "kind": "governance_topic"}
    refused = module.score_governance([invalid_topic])
    assert refused.startswith("ERROR")
    assert "governance topic leaves" in refused
    assert "Extraction-Oriented is a behaviour category" in refused


def test_text_only_and_rejected_draft_limits(tmp_path: Path) -> None:
    for label, replies in [
        ("text", [turn()] * 3),
        ("draft", [turn(ToolCall("w", "write_handoff", {"markdown": "bad"}))] * 3),
    ]:
        adapter = Adapter(*replies)
        loop = HandoffExecutor(tmp_path / label, adapter=adapter, cap_usd=Decimal(10), check=check)
        with pytest.raises(RuntimeError, match="not accepted"):
            loop(task())
        assert len(adapter.requests) == 3


def test_search_source_snippet_keeps_its_place_after_a_length_changing_lowercase(
    tmp_path: Path,
) -> None:
    # U+0130 lowercases to two code points, so a match position found in the lowercased page is
    # not a position in the page; Turkish filings carry that letter. By hand: the match starts at
    # index 201 (200 letters and a space before it), so 80 characters before it are 79 letters and
    # the space, and the 14 after it and the rest of the page fit inside the 80 after.
    page = "İ" * 200 + " total revenue 1,234 million"
    source_task = replace(task(), sources={"S.txt": page.encode()})
    tools = ModuleTools(source_task, tmp_path, check)
    hit = tools.search_source("S.txt", "Total Revenue")
    assert hit == "page 1: …" + "İ" * 79 + " total revenue 1,234 million…"


def test_events_record_each_turn_and_rejection(tmp_path: Path) -> None:
    from deploy_workflow.run_events import EVENTS, read_events

    adapter = Adapter(
        turn(ToolCall("w", "write_handoff", {"markdown": GOOD.decode().replace("100", "101")})),
        turn(ToolCall("e", "edit_handoff", {"edits": [{"old": "101", "new": "100"}]})),
    )
    loop = HandoffExecutor(
        tmp_path / "live",
        adapter=adapter,
        cap_usd=Decimal(10),
        check=check,
        max_turns=7,
        events=tmp_path / "run",
    )
    assert loop(task()) == GOOD
    events = read_events(tmp_path / "run" / EVENTS)
    assert [e["event"] for e in events] == ["turn", "draft_rejected", "turn"]
    turns = [e for e in events if e["event"] == "turn"]
    assert [e["turn"] for e in turns] == [1, 2]
    assert {e["max_turns"] for e in turns} == {7}
    assert {e["module"] for e in events} == {"CP-2"}
    assert [e["writes_left"] for e in events if e["event"] == "draft_rejected"] == [2]
    assert all(e["cap_usd"] == "10" and Decimal(e["held_usd"]) > 0 for e in turns)
    assert Decimal(turns[0]["spent_usd"]) == 0 and Decimal(turns[1]["spent_usd"]) > 0


def test_a_refused_reservation_writes_no_turn_event(tmp_path: Path) -> None:
    from deploy_workflow.model.budget import BudgetExhausted
    from deploy_workflow.run_events import EVENTS

    loop = HandoffExecutor(
        tmp_path / "live",
        adapter=Adapter(),
        cap_usd=Decimal("0.000001"),
        check=check,
        events=tmp_path / "run",
    )
    with pytest.raises(BudgetExhausted):
        loop(task())
    assert not (tmp_path / "run" / EVENTS).exists()


def test_no_events_folder_writes_no_events(tmp_path: Path) -> None:
    adapter = Adapter(turn(ToolCall("w", "write_handoff", {"markdown": GOOD.decode()})))
    loop = HandoffExecutor(tmp_path, adapter=adapter, cap_usd=Decimal(10), check=check)
    assert loop(task()) == GOOD
    assert not list(tmp_path.rglob("events.jsonl"))


def test_a_turn_event_that_cannot_be_written_neither_holds_budget_nor_stops_the_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from types import SimpleNamespace

    from deploy_workflow import run_events
    from deploy_workflow.model.budget import Budget

    def full_disk(_fd: int) -> None:
        raise OSError(28, "No space left on device")

    monkeypatch.setattr(run_events, "os", SimpleNamespace(fsync=full_disk))
    adapter = Adapter(turn(ToolCall("w", "write_handoff", {"markdown": GOOD.decode()})))
    loop = HandoffExecutor(
        tmp_path / "live", adapter=adapter, cap_usd=Decimal(10), check=check, events=tmp_path
    )
    with pytest.warns(RuntimeWarning, match="run event not recorded: turn"):
        assert loop(task()) == GOOD
    assert len(adapter.requests) == 1
    assert not loop.budget.unsettled
    Budget(Decimal(10), tmp_path / "live").reserve(
        "call-next", Decimal("0.01"), config_id="sol-medium"
    )


def _boom(*_a, **_k):
    raise ArithmeticError("injected post-send fault")


@pytest.mark.parametrize("broken", ["redacted_turn", "price_usage"])
def test_a_post_reply_fault_settles_the_hold_as_unknown_and_records_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, broken: str
) -> None:
    """R15: redaction or pricing raising after a paid send must not leave the hold unsettled."""
    import json

    from deploy_workflow.model import handoff as handoff_module
    from deploy_workflow.model.budget import read_reservation_snapshot

    adapter = Adapter(turn(ToolCall("w", "write_handoff", {"markdown": GOOD.decode()})))
    loop = HandoffExecutor(tmp_path, adapter=adapter, cap_usd=Decimal(10), check=check)
    monkeypatch.setattr(handoff_module, broken, _boom)
    with pytest.raises(RuntimeError, match="cpos_live_stopped"):
        loop(task())
    (marker,) = read_reservation_snapshot(tmp_path)
    assert marker.status is not None  # settled, not left held
    assert loop.budget.spent == marker.usd > 0  # the whole hold counts, never zero
    (row,) = [json.loads(n) for n in (tmp_path / "calls.jsonl").read_text().splitlines()]
    assert row["cost_status"] == "unknown" and row["settled_usd"] is None
    assert "ArithmeticError: injected post-send fault" in row["error"]


def test_a_redactor_that_fails_on_an_adapter_error_still_settles_unknown(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from deploy_workflow.model.budget import read_reservation_snapshot

    adapter = Adapter(RuntimeError("socket gone"))
    loop = HandoffExecutor(tmp_path, adapter=adapter, cap_usd=Decimal(10), check=check)
    monkeypatch.setattr(loop.redactor, "exception", _boom)
    with pytest.raises(RuntimeError, match="cpos_live_stopped"):
        loop(task())
    (marker,) = read_reservation_snapshot(tmp_path)
    assert marker.status is not None
    assert loop.budget.spent == marker.usd > 0
    (row,) = [json.loads(n) for n in (tmp_path / "calls.jsonl").read_text().splitlines()]
    assert row["error"].startswith(REDACTION_FAILED) and row["cost_status"] == "unknown"


def test_a_pricing_fault_stop_is_one_line_and_the_trace_stays_in_the_record(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from deploy_workflow.model import handoff as handoff_module

    monkeypatch.setattr(handoff_module, "price_usage", _boom)
    adapter = Adapter(turn(ToolCall("w", "write_handoff", {"markdown": GOOD.decode()})))
    loop = HandoffExecutor(tmp_path, adapter=adapter, cap_usd=Decimal(10), check=check)
    with pytest.raises(RuntimeError) as caught:
        loop(task())
    message = str(caught.value)
    assert "\n" not in message and "Traceback" not in message
    assert message.endswith("unusable reply: ArithmeticError: injected post-send fault")
    (row,) = [json.loads(n) for n in (tmp_path / "calls.jsonl").read_text().splitlines()]
    assert "Traceback" in row["error"]


@pytest.mark.parametrize("kind", ["not_sent", "sent_known"])
def test_a_zero_cost_reply_with_a_pricing_fault_is_recorded_computed_and_stops(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: Any
) -> None:
    from deploy_workflow.model import handoff as handoff_module

    monkeypatch.setattr(handoff_module, "price_usage", _boom)
    reply = AdapterReply(kind, None, None, None, "Refused", None, 1, 2, message="refused")
    loop = HandoffExecutor(tmp_path, adapter=Adapter(reply), cap_usd=Decimal(10), check=check)
    with pytest.raises(RuntimeError, match="cpos_live_stopped"):
        loop(task())
    (row,) = [json.loads(n) for n in (tmp_path / "calls.jsonl").read_text().splitlines()]
    assert row["settled_usd"] == "0" and row["cost_status"] == "computed"
    assert loop.budget.spent == 0


def test_an_adapter_failure_keeps_its_message_beside_a_pricing_fault(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from deploy_workflow.model import handoff as handoff_module

    monkeypatch.setattr(handoff_module, "price_usage", _boom)
    adapter = Adapter(RuntimeError("socket gone after send"))
    loop = HandoffExecutor(tmp_path, adapter=adapter, cap_usd=Decimal(10), check=check)
    with pytest.raises(RuntimeError, match="cpos_live_stopped"):
        loop(task())
    (row,) = [json.loads(n) for n in (tmp_path / "calls.jsonl").read_text().splitlines()]
    assert "socket gone after send" in row["error"] and "injected post-send fault" in row["error"]


def test_a_post_reply_exception_whose_str_raises_still_settles_and_stops(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from deploy_workflow.model import handoff as handoff_module
    from deploy_workflow.model.budget import read_reservation_snapshot

    class Opaque(ArithmeticError):
        def __str__(self) -> str:
            raise ValueError("no text")

    def opaque(*_a: Any, **_k: Any) -> Any:
        raise Opaque

    monkeypatch.setattr(handoff_module, "price_usage", opaque)
    adapter = Adapter(turn(ToolCall("w", "write_handoff", {"markdown": GOOD.decode()})))
    loop = HandoffExecutor(tmp_path, adapter=adapter, cap_usd=Decimal(10), check=check)
    with pytest.raises(RuntimeError, match="cpos_live_stopped"):
        loop(task())
    (marker,) = read_reservation_snapshot(tmp_path)
    assert marker.status is not None and loop.budget.spent == marker.usd > 0
    (row,) = [json.loads(n) for n in (tmp_path / "calls.jsonl").read_text().splitlines()]
    assert row["cost_status"] == "unknown"
