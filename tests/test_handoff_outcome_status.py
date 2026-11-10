"""R-SB2-1 answer key: a module's status comes from its own YAML fields, then CP-0's CONDITIONAL."""

import importlib.util
import json
import shutil
import sys
from pathlib import Path
from types import SimpleNamespace

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
    assert not any(f.startswith("CP-0:") for f in found)
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
    "l": (handoff(body="Module Status: **Blocked**\n"), "", "will_refuse"),
    "m": (handoff(body="`Module Status: Blocked`\n"), "", "will_refuse"),
    "n": (handoff(body="- Module Status: Blocked.\n"), "", "will_refuse"),
    "o": (handoff(body="**Module Status**: Completed with Limitations\n"), "", "limited"),
    "p": (handoff(body="| Module Status | Blocked |\n"), "", "unconfirmed"),
    "q": (handoff(body="Module Status: Blocked pending review\n"), "", "unconfirmed"),
    "r": (handoff(body="Module Status: completed with limitations\n"), "", "limited"),
    "s": (handoff(body="Module Status: `Blocked`.\n"), "", "will_refuse"),
    "t": (handoff(body="- `Module Status: Blocked` \n"), "", "will_refuse"),
    "u": (handoff(body="**Module Status:** `Completed`.\n"), "", "ready"),
    "v": (handoff(body="***Module Status:*** Blocked\n"), "", "will_refuse"),
    "w": (handoff(body="> Module Status: Blocked\n"), "", "will_refuse"),
    "x": (handoff(body="module status: Blocked\n"), "", "will_refuse"),
    "y": (handoff(body="| module status | Blocked |\n"), "", "unconfirmed"),
    "z": (handoff(body="> Module Status: Blocked pending review\n"), "", "unconfirmed"),
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


def test_case_outcomes_reports_cp0_not_testable(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    modules = ["CP-0", "CP-4"]
    intake = tmp_path / "intake/x"
    intake.mkdir(parents=True)
    review = {"modules": modules, "expectations": [{"scope": "CP-4", "outcome": "limited"}]}
    (intake / "review.json").write_text(json.dumps(review))
    run = tmp_path / "runs/web-x"
    run.mkdir(parents=True)
    for name in modules:
        shutil.copy(FIXTURES / f"{name}.md", run / f"{name}.md")
    expected = {
        "ordered_modules": modules,
        "counted_total": 0,
        "modules": {"CP-4": [{"outcome": "limited"}]},
    }
    notes: list[tuple[bool, str]] = []

    class Notes:
        def note(self, ok: bool, what: str, fault: bool = True, kind: str = "check") -> None:
            notes.append((ok, what))

    monkeypatch.setattr(live_check, "required_outputs", lambda *a, **k: [])
    args = SimpleNamespace(case_data={"expected-outcomes": expected})
    live_check.case_outcomes(Notes(), args, tmp_path, {})
    assert not any("CP-0:" in what for _, what in notes)
    assert "CP-0: not testable (states no status of its own)\n" in capsys.readouterr().out
    ok, what = notes[-1]
    assert ok is True
    assert what.startswith("forecast confirmed equal for the 1 testable modules")


@pytest.mark.parametrize("body", ["Module Status: Blocked\n", "module status: Blocked\n"])
def test_explanation_quotes_the_status_value_as_written(body: str) -> None:
    got = handoff_outcome.actual_of("CP-4", handoff(body=body), "")
    assert got[0] == "will_refuse"
    assert "Blocked" in got[1]


def _hand(body: str = "", fm: str = "") -> str:
    return "---\nmodule_id: CP-4\n" + fm + "---\n" + body


@pytest.mark.parametrize(
    ("own", "wanted"),
    [
        (_hand("```\nModule Status: Blocked\n```\n"), "unconfirmed"),
        (_hand("", "Module Status: Blocked\n"), "will_refuse"),
        (_hand("", 'qa_status: "Blocked"\n'), "will_refuse"),
        (_hand("", "qa_status: 'Restricted'\n"), "limited"),
        (_hand("", "qa_status: blocked\n"), "will_refuse"),
        (_hand("", "committee_status: committee ready\n"), "ready"),
        (_hand("", "qa_status: Blocked # was\n"), "will_refuse"),
        ("﻿" + _hand("", "qa_status: Blocked\n"), "will_refuse"),
        (_hand("| Module Status: Blocked |\n"), "unconfirmed"),
    ],
    ids=[
        "fence",
        "fm-label",
        "dq",
        "sq",
        "lower",
        "committee-lower",
        "comment",
        "bom",
        "table-row",
    ],
)
def test_r_sb2_1d_fences_front_matter_value_forms_bom(own: str, wanted: str) -> None:
    assert handoff_outcome.actual_of("CP-4", own, "")[0] == wanted


READY_ROW = "| CP-4 | READY |\n"
CASES_1H = {
    "1h-inline-triple-wrapped": ("```Module Status: Blocked```\n", READY_ROW, "will_refuse"),
    "1h-inline-triple-earlier": (
        "```CP-4 inline note```\nModule Status: Blocked\n",
        READY_ROW,
        "will_refuse",
    ),
    "1h-tilde-hides-completed": ("~~~\nModule Status: Completed\n~~~\n", "", "unconfirmed"),
    "1h-tilde-backtick-tilde": (
        "~~~\n```\n~~~\nModule Status: Blocked\n",
        READY_ROW,
        "will_refuse",
    ),
    "1h-four-backtick-holds-three": (
        "````\n```\nModule Status: Completed\n````\n",
        "",
        "unconfirmed",
    ),
    "1h-unclosed-fence": ("```\nModule Status: Completed\n", "", "unconfirmed"),
    "1h-four-space-not-fence": (
        "    ```\nModule Status: Blocked\n    ```\n",
        READY_ROW,
        "will_refuse",
    ),
    "1h-own-fenced-ready": ("```\nCP-4 READY\n```\n", "", "unconfirmed"),
    "1h-info-string-backtick": ("```py`\nModule Status: Blocked\n", READY_ROW, "will_refuse"),
    "1h-closing-line-trailing-text": (
        "```\n``` x\nModule Status: Blocked\n",
        "",
        "unconfirmed",
    ),
    "1h-three-space-opens-fence": (
        "   ```\nModule Status: Blocked\n```\n",
        "",
        "unconfirmed",
    ),
}


@pytest.mark.parametrize(("own", "cp0", "wanted"), CASES_1H.values(), ids=CASES_1H.keys())
def test_r_sb2_1h_fences_per_commonmark(own: str, cp0: str, wanted: str) -> None:
    assert handoff_outcome.actual_of("CP-4", own, cp0)[0] == wanted
