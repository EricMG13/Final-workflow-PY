"""The rehearsal fake engine writes the frozen key pro forma findings; nothing else changes."""

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from deploy_workflow.owners.cpos_launch import (
    OPENING,
    PRO_FORMA,
    PRO_FORMA_ISSUES,
    pro_forma_issues,
)

ROOT = Path(__file__).resolve().parents[1]
KEY = ROOT / "tests/fixtures/primary-pro-forma/checker-cases.json"
CASES = {c["id"]: c for c in json.loads(KEY.read_text(encoding="utf-8"))["cases"]}

STUB = ["| Item | Value |", "| --- | --- |", "| Observed | 0 |", ""]
# What the fake wrote for a module with no pro forma paragraph before this change: the shared
# opening, one stub per routed heading, then the three closing sections.
PLAIN = "\n".join(
    [
        "# CP-3",
        "",
        "## Request",
        "Issuer as of 2014-06-30.",
        "",
        "## Sources",
        "",
        "- a.pdf 1111",
        "- CP-1 2222",
        "",
        "## Findings",
        "",
        "### Reader summary",
        "",
        "| Bottom line | Confidence | Main limitation |",
        "| --- | --- | --- |",
        "| A fake engine finding only. | Low | Fake data. |",
        "",
        "| Finding | Creditor impact | Confidence |",
        "| --- | --- | --- |",
        "| One item was observed. | None. | Low |",
        "",
        "### OPENING",
        "",
        "A fake engine view only.",
        "",
        "### Sources and uses",
        "",
        *STUB,
        "### A chart",
        "",
        "### Some prose",
        "",
        "A located finding.",
        "",
        "## Calculations",
        "",
        "None.",
        "",
        "## Gaps",
        "",
        "None.",
        "",
        "## Next module",
        "",
        "None.",
        "",
    ]
)


@pytest.fixture
def fake(monkeypatch: pytest.MonkeyPatch) -> Any:
    monkeypatch.setenv("CHECK_ROOT", str(ROOT))
    monkeypatch.delenv("FAKE_MALFORMED", raising=False)
    path = ROOT / "apps/issuer-library/designs/fake_engine/bridge.py"
    spec = importlib.util.spec_from_file_location("fake_bridge_under_test", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def plan(module: str, headings: tuple[tuple[str, str], ...]) -> dict[str, Any]:
    return {
        "run": {"issuer_name": "Issuer", "as_of": "2014-06-30"},
        "layout": {"routes": [{"module_id": module, "heading": h, "kind": k} for h, k in headings]},
    }


def context(module: str) -> dict[str, Any]:
    return {
        "module_id": module,
        "sources": {"a.pdf": "1111"},
        "handoffs": {"CP-1": {"sha256": "2222"}},
    }


def instructions_for(module: str, primary: bool) -> str:
    return "Method.\n\n" + (PRO_FORMA[module] if primary else "") + "\n\nEnd."


@pytest.mark.parametrize("module", ["CP-1A", "CP-1D", "CP-2"])
def test_primary_run_writes_an_accepted_answer(fake: Any, module: str) -> None:
    text = fake.handoff_markdown(
        context(module),
        plan(module, (("Sources and uses", "table"),)),
        instructions_for(module, True),
    )
    case = next(c for c in CASES.values() if c["module"] == module and c["expected"]["accepted"])
    assert case["findings"].strip() in text
    task: Any = SimpleNamespace(instructions=instructions_for(module, True).encode())
    findings = text[text.index("## Findings") : text.index("## Calculations")]
    assert pro_forma_issues(task, findings) == ()
    headings = [line for line in text.splitlines() if line.startswith("### ")]
    assert len(headings) == len(set(headings))


def test_a_routed_heading_the_key_holds_gets_no_second_stub(fake: Any) -> None:
    routes = (("Pro forma capitalisation", "table"), ("EBITDA ladder", "table"), ("Other", "table"))
    text = fake.handoff_markdown(
        context("CP-2"), plan("CP-2", routes), instructions_for("CP-2", True)
    )
    assert text.count("### Pro forma capitalisation") == 1
    assert text.count("### EBITDA ladder") == 1
    assert text.count("### Other") == 1
    assert text.count("| Observed | 0 |") == 1


def test_malformed_mode_writes_the_rejected_case(
    fake: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("FAKE_MALFORMED", "CP-2")
    text = fake.handoff_markdown(context("CP-2"), plan("CP-2", ()), instructions_for("CP-2", True))
    assert CASES["cap-no-cash-row"]["findings"].strip() in text
    task: Any = SimpleNamespace(instructions=instructions_for("CP-2", True).encode())
    findings = text[text.index("## Findings") : text.index("## Calculations")]
    issues = pro_forma_issues(task, findings)
    expected = {PRO_FORMA_ISSUES[c] for c in CASES["cap-no-cash-row"]["expected"]["issues"]}
    assert issues
    assert {next(p for p in expected if i.startswith(p)) for i in issues} == expected
    # Another module is not made malformed.
    other = fake.handoff_markdown(
        context("CP-1A"), plan("CP-1A", ()), instructions_for("CP-1A", True)
    )
    assert CASES["cp1a-sources-uses-valid-user-entered"]["findings"].strip() in other


@pytest.mark.parametrize("module", ["CP-2", "CP-3"])
def test_other_runs_and_modules_are_unchanged(
    fake: Any, monkeypatch: pytest.MonkeyPatch, module: str
) -> None:
    monkeypatch.setenv("FAKE_MALFORMED", "CP-2")
    routes = (("Sources and uses", "table"), ("A chart", "chart"), ("Some prose", "prose"))
    # Non-Primary CP-2 (no paragraph) and CP-3 (no paragraph at all) write the old text.
    text = fake.handoff_markdown(context(module), plan(module, routes), "Method.\n\nEnd.")
    assert text == PLAIN.replace("# CP-3", f"# {module}").replace("OPENING", OPENING[module])


DELIVERED = json.loads(
    (ROOT / "tests/fixtures/primary-pro-forma/delivered-block.json").read_text(encoding="utf-8")
)["pro-forma"]


def table_of(table: Any) -> dict[str, Any]:
    return {
        "header": [table.row_header, *table.columns],
        "rows": [[r.label, *(c.text for c in r.cells)] for r in table.rows],
    }


def test_fake_cp2_handoff_reaches_the_delivered_pro_forma_block_cell_for_cell(
    fake: Any, tmp_path: Path
) -> None:
    """The fake engine's Primary CP-2 handoff through the app's own layout and delivery functions
    (no server): the delivered capitalisation table and leverage tab are the frozen key's."""
    from test_cpos_pro_forma_delivery import CP2_RUN, deliver

    from deploy_vii.report_view import ReportView
    from deploy_workflow.owners.cpos_launch import _layout

    layout, _ = _layout(
        CP2_RUN, ("CP-2",), (), "cfg", run_type="primary", legal_documents="executed"
    )
    routes = tuple((r.heading, r.kind) for r in layout.routes if r.module_id == "CP-2")
    chosen = plan("CP-2", routes)
    chosen["run"]["issuer_name"] = CP2_RUN.issuer_name  # the run delivery checks the title against
    text = fake.handoff_markdown(context("CP-2"), chosen, instructions_for("CP-2", True))
    files = deliver(tmp_path, CP2_RUN, "CP-2", text, "primary")
    report = ReportView.model_validate_json(files["report-view.json"])
    block = next(b for b in report.blocks if b.block_id == "pro-forma")
    assert table_of(block) == DELIVERED["capitalisation"]
    assert len(block.tabs) == 1
    assert table_of(block.tabs[0]) == DELIVERED["leverage"]
