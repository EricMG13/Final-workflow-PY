"""Offline adversarial tests of the adapted cp-os loop; not live module proof."""

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from deploy_vii.contracts import Run
from deploy_workflow.model.adapter import AdapterReply
from deploy_workflow.model.handoff import HandoffExecutor, ModuleTools
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
