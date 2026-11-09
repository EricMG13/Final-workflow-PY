"""R-SB2-1 answer key: a module's status comes from its own YAML fields, then CP-0's CONDITIONAL."""

import importlib.util
import shutil
import sys
from pathlib import Path

import pytest

from deploy_workflow import handoff_outcome

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests/fixtures/handoff-status-c1"
DESIGNS = ROOT / "apps/issuer-library/designs"
sys.path.insert(0, str(DESIGNS))
spec = importlib.util.spec_from_file_location("live_check", DESIGNS / "live_check.py")
live_check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(live_check)

CP4_ROW = "| CP-4 — legal and covenant package | CONDITIONAL — DO NOT RUN complete workflow | x |\n"


def handoff(*fields: str, body: str = "## Analysis\nText.\n") -> str:
    return "---\nmodule_id: CP-4\n" + "".join(f"{f}\n" for f in fields) + "---\n" + body


@pytest.mark.parametrize(
    ("module", "wanted"), [("CP-4", "limited"), ("CP-0", "unconfirmed"), ("CP-1", "limited")]
)
def test_retained_c1_through_actual_of(module: str, wanted: str) -> None:
    own = (FIXTURES / f"{module}.md").read_text()
    cp0 = (FIXTURES / "CP-0.md").read_text()
    assert handoff_outcome.actual_of(module, own, cp0)[0] == wanted


def test_retained_c1_through_live_check_outcome_faults(tmp_path: Path) -> None:
    for name in ("CP-0", "CP-1", "CP-4"):
        shutil.copy(FIXTURES / f"{name}.md", tmp_path / f"{name}.md")
    found, did = live_check.outcome_faults(
        {"CP-0": "ready", "CP-1": "ready", "CP-4": "limited"}, tmp_path
    )
    assert {m: d.split(" (")[0] for m, d in did.items()} == {
        "CP-0": "unconfirmed",
        "CP-1": "limited",
        "CP-4": "limited",
    }
    assert any(f.startswith("CP-0:") for f in found)
    assert any(f.startswith("CP-1:") for f in found)
    assert not any(f.startswith("CP-4:") for f in found)


CASES = {
    "a": (handoff("qa_status: Blocked", "review_status: Provisional"), "", "will_refuse"),
    "b": (handoff("committee_status: Committee Ready"), "", "ready"),
    "c": (
        handoff("committee_status: Committee Ready", "qa_status: Restricted"),
        "",
        "limited",
    ),
    "d": (handoff("committee_status: Requires More Work"), "", "unconfirmed"),
    "e": (None, CP4_ROW, "will_refuse"),
    "f": (handoff(), CP4_ROW, "unconfirmed"),
    "g": (handoff(body="This section is Provisional pending review.\n"), "", "unconfirmed"),
    "h": (handoff(body="Module Status: Blocked\n"), "", "will_refuse"),
    "i": (handoff(body="**Module Status:** Completed with Limitations\n"), "", "limited"),
    "k": (
        handoff("review_status: Provisional", body="Module Status: Completed\n"),
        "",
        "limited",
    ),
    "table-column-never-counts": (
        handoff(body="| x | Module Status |\n|---|---|\n| a | Blocked |\n"),
        "",
        "unconfirmed",
    ),
    "label-inside-prose-never-counts": (
        handoff(body="Note: the Module Status: Blocked line is not used here.\n"),
        "",
        "unconfirmed",
    ),
}


@pytest.mark.parametrize(("own", "cp0", "wanted"), CASES.values(), ids=CASES.keys())
def test_synthetic_status_cases(own: str | None, cp0: str, wanted: str) -> None:
    assert handoff_outcome.actual_of("CP-4", own, cp0)[0] == wanted


def test_c1_cp4_table_column_does_not_change_the_result() -> None:
    """(j) C1 CP-4 holds a "Module Status" table column; it stays limited and is not cited."""
    own = (FIXTURES / "CP-4.md").read_text()
    cp0 = (FIXTURES / "CP-0.md").read_text()
    got = handoff_outcome.actual_of("CP-4", own, cp0)
    assert got[0] == "limited"
    assert "Module Status" not in got[1]
