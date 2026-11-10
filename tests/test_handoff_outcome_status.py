"""R-SB2-1 answer key: a module's status comes from its own YAML fields, then CP-0's CONDITIONAL."""

import importlib.util
import json
import shutil
import sys
import time
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


C1N = ROOT / "tests/fixtures/handoff-status-c1n"
C1N_CP4_LINE7 = (
    "**Module Status: Blocked. CP-4 Blocked. No executed governing document available.** "
    "The supplied set contains no governing credit agreement, indenture, offering memorandum, "
    "financing draft or lender presentation. The acquisition agreement is not a governing "
    "financing document. The provisional-review override therefore does not clear the "
    "documentary gate. This handoff records the gate decision and bounded reported "
    "capital-structure facts, not a completed covenant interpretation."
)


def _own(module: str, body: str = "## Analysis\nText.\n") -> str:
    return f"---\nmodule_id: {module}\n---\n{body}"


def test_1e_r_c1n_cp4_fixture_will_refuse() -> None:
    own = (C1N / "CP-4.md").read_text()
    cp0 = (C1N / "CP-0.md").read_text()
    assert handoff_outcome.actual_of("CP-4", own, cp0)[0] == "will_refuse"


def test_1e_r_c1n_line7_will_refuse() -> None:
    assert (C1N / "CP-4.md").read_text().splitlines()[6] == C1N_CP4_LINE7
    assert handoff_outcome.actual_of("CP-4", handoff(body=C1N_CP4_LINE7 + "\n"), "")[0] == (
        "will_refuse"
    )


def test_1e_s_completed_with_limitations_then_text() -> None:
    body = "Module Status: Completed with Limitations. See §3.\n"
    assert handoff_outcome.actual_of("CP-4", handoff(body=body), "")[0] == "limited"


def test_1e_t_blocked_comma_text_unconfirmed() -> None:
    body = "Module Status: Blocked, see below\n"
    assert handoff_outcome.actual_of("CP-4", handoff(body=body), "")[0] == "unconfirmed"


def test_1e_u_c1n_cp0_row_fourth_cell_limited() -> None:
    cp0 = (C1N / "CP-0.md").read_text()
    assert handoff_outcome.actual_of("CP-1", _own("CP-1"), cp0)[0] == "limited"


def test_1e_v_blocked_in_fourth_cell_will_refuse() -> None:
    cp0 = "| CP-1 — figures | READY | x | BLOCKED: no statements |\n"
    assert handoff_outcome.actual_of("CP-1", _own("CP-1"), cp0)[0] == "will_refuse"


def test_1e_w_other_modules_row_does_not_set_cp1() -> None:
    cp0 = "| CP-4 — legal | x | BLOCKED |\n"
    assert handoff_outcome.actual_of("CP-1", _own("CP-1"), cp0)[0] == "unconfirmed"


@pytest.mark.parametrize(
    "first_cell",
    [
        "CP-4",
        "CP-4 — legal",
        "CP-4 – legal",
        "CP-4 - legal",
        "CP-4: Legal",
        "cp-4",
        "**CP-4**",
    ],
    ids=lambda c: f"1j-is-row-{c}",
)
def test_1j_is_the_row_blocked_will_refuse(first_cell: str) -> None:
    cp0 = f"| {first_cell} | BLOCKED |\n"
    assert handoff_outcome.actual_of("CP-4", None, cp0)[0] == "will_refuse"


NOT_CP4_CELLS = ["CP-4.1", "CP-4a", "CP-40", "CP-4-1", "CP-4 (draft)"]


NO_STATUS_OWN = "# CP-4\nbody\n"


@pytest.mark.parametrize("first_cell", NOT_CP4_CELLS, ids=lambda c: f"1j-not-row-blocked-{c}")
def test_1j_not_the_row_blocked_then_real_row_ready(first_cell: str) -> None:
    cp0 = f"| {first_cell} | BLOCKED |\n| CP-4 | READY |\n"
    assert handoff_outcome.actual_of("CP-4", NO_STATUS_OWN, cp0)[0] == "ready"


@pytest.mark.parametrize("first_cell", NOT_CP4_CELLS, ids=lambda c: f"1j-not-row-ready-{c}")
def test_1j_not_the_row_ready_alone_is_not_reached(first_cell: str) -> None:
    cp0 = f"| {first_cell} | READY |\n"
    assert handoff_outcome.actual_of("CP-4", None, cp0)[0] == "not_reached"


@pytest.mark.parametrize("first_cell", NOT_CP4_CELLS, ids=lambda c: f"1j-not-row-ready-own-{c}")
def test_1j_not_the_row_ready_alone_with_own_is_unconfirmed(first_cell: str) -> None:
    cp0 = f"| {first_cell} | READY |\n"
    assert handoff_outcome.actual_of("CP-4", NO_STATUS_OWN, cp0)[0] == "unconfirmed"


def test_1j_lead_probe_cp4_1_blocked_then_cp4_ready() -> None:
    # The lead's probe expected "ready" for own=None; corrected by the lead (R-SB2-1j
    # amendment): with no own handoff only BLOCKED/CONDITIONAL count (R-SB2-1 rule 3).
    cp0 = "| CP-4.1 | BLOCKED |\n| CP-4 | READY |\n"
    assert handoff_outcome.actual_of("CP-4", None, cp0)[0] == "not_reached"


def test_1j_lead_probe_cp4_1_blocked_then_cp4_ready_with_own_handoff() -> None:
    cp0 = "| CP-4.1 | BLOCKED |\n| CP-4 | READY |\n"
    assert handoff_outcome.actual_of("CP-4", NO_STATUS_OWN, cp0)[0] == "ready"


CASES_1J2 = [  # (module, own?, cp0, expected): the lead probe_1j_rows.py, verbatim
    # (module, own?, cp0, expected)
    ("CP-1", False, "| CP-1A | BLOCKED |\n", "not_reached"),
    ("CP-1", False, "| CP-1D | BLOCKED |\n", "not_reached"),
    ("CP-1", False, "| CP-10 | BLOCKED |\n", "not_reached"),
    ("CP-1", True, "| CP-10 | BLOCKED |\n| CP-1 | READY |\n", "ready"),
    ("CP-1", True, "| CP-1 — financial-data foundation | READY |\n", "ready"),
    ("CP-1", False, "| CP-1: Financial data | BLOCKED |\n", "will_refuse"),
    ("CP-4", False, "| CP-4 - label | BLOCKED |\n", "will_refuse"),
    ("CP-4", False, "| CP-4-1 | BLOCKED |\n", "not_reached"),
    ("CP-4", False, "| CP-4:label | BLOCKED |\n", "will_refuse"),
    ("CP-4", False, "| CP-4 : label | BLOCKED |\n", "will_refuse"),
    ("CP-4", False, "| CP-4—label | BLOCKED |\n", "not_reached"),  # ruling: not a match
    ("CP-4", False, "| `CP-4` | BLOCKED |\n", "will_refuse"),
    ("CP-4", False, "| **`CP-4`** — Legal | CONDITIONAL |\n", "will_refuse"),
    ("CP-4", False, "| cp-4 — legal | BLOCKED |\n", "will_refuse"),
    ("CP-4", True, "| cp-4.1 | READY |\n", "unconfirmed"),
    # list markers (ruling: stripped)
    ("CP-4", False, "| - CP-4.1 | BLOCKED |\n", "not_reached"),
    ("CP-4", False, "| 1. CP-4.1 | BLOCKED |\n", "not_reached"),
    ("CP-4", False, "| - CP-4 | BLOCKED |\n", "will_refuse"),
    ("CP-4", True, "| - CP-4 | READY |\n", "ready"),
    # leading empty cell / id in later cell
    ("CP-4", False, "|  | CP-4 | BLOCKED |\n", "will_refuse"),
    ("CP-4", False, "| Legal | CP-4 | BLOCKED |\n", "will_refuse"),
    # disagreeing rows: worst wins
    ("CP-4", True, "| CP-4 | READY |\n| CP-4 — again | BLOCKED |\n", "will_refuse"),
    ("CP-4", True, "| CP-4 | BLOCKED |\n| CP-4 | READY |\n", "will_refuse"),
    ("CP-4", False, "| CP-4 | READY |\n| CP-4 | CONDITIONAL |\n", "will_refuse"),
    # false-ready without own: READY row never counts
    ("CP-4", False, "| CP-4 | READY |\n", "not_reached"),
    ("CP-4", False, "| CP-4 | READY_WITH_LIMITATIONS |\n", "not_reached"),
    ("CP-4", False, "| CP-4.1 | BLOCKED |\nCP-4 is READY\n", "not_reached"),
    # other module row not read as prose
    ("CP-4", False, "| CP-4.1 | see CP-4 BLOCKED |\n", "not_reached"),
]


@pytest.mark.parametrize(
    ("module", "has_own", "cp0", "wanted"),
    CASES_1J2,
    ids=[f"1j2-{i:02d}-{m}-{'own' if o else 'noown'}" for i, (m, o, _, _) in enumerate(CASES_1J2)],
)
def test_1j2_row_markup_list_markers_id_prefixes(
    module: str, has_own: bool, cp0: str, wanted: str
) -> None:
    own = f"# {module}\nbody\n" if has_own else None
    assert handoff_outcome.actual_of(module, own, cp0)[0] == wanted


# --- Handoff-outcome batch: R-SB2-1g, 1i, 1k and the reader Lows (ids prefixed b1-) ---
NO_STATUS = "# CP-4\nbody\n"
CASES_B1 = [  # (module, own, cp0, expected): values from the rulings
    # R-SB2-1g: a row is ranked by the class it resolves to
    ("CP-1", NO_STATUS, "| CP-1 | READY_WITH_LIMITATIONS | CONDITIONAL |\n", "limited"),
    ("CP-1", None, "| CP-1 | READY_WITH_LIMITATIONS | CONDITIONAL |\n", "will_refuse"),
    ("CP-1", NO_STATUS, "| CP-1 | READY | CONDITIONAL |\n", "ready"),
    ("CP-1", NO_STATUS, "| CP-1 | CONDITIONAL |\n", "unconfirmed"),
    # R-SB2-1i: prose and row both read, worst class wins
    ("CP-4", NO_STATUS, "CP-4 BLOCKED: no indenture.\n\n| CP-4 | READY |\n", "will_refuse"),
    ("CP-4", NO_STATUS, "CP-4 READY.\n\n| CP-4 | BLOCKED |\n", "will_refuse"),
    ("CP-4", NO_STATUS, "CP-4 READY_WITH_LIMITATIONS.\n\n| CP-4 | READY |\n", "limited"),
    # R-SB2-1k: status, colon, then the id (same exact-id boundary as 1j)
    ("CP-4", None, "Blocked: CP-4.\n", "will_refuse"),
    ("CP-1", None, "BLOCKED: CP-1, CP-4 and CP-5.\n", "will_refuse"),
    ("CP-4", None, "BLOCKED: CP-1, CP-4 and CP-5.\n", "will_refuse"),
    ("CP-5", None, "BLOCKED: CP-1, CP-4 and CP-5.\n", "will_refuse"),
    ("CP-4", None, "Blocked: CP-4.1.\n", "not_reached"),
    ("CP-4", NO_STATUS, "READY_WITH_LIMITATIONS: CP-4\n", "limited"),
    # Lows
    ("CP-4", "Module Status: `Blocked`. See below.\n", "", "will_refuse"),
    ("CP-4", "> ```\nModule Status: Blocked\n> ```\n", "", "will_refuse"),
    ("CP-4", "---\nqa_status: ok\n```\n---\nModule Status: Blocked\n", "", "will_refuse"),
    ("CP-4", "Note Module Status: Blocked\n", "", "unconfirmed"),
    ("CP-4", "Module Status: Blocked\r\n", "", "will_refuse"),
]
IDS_B1 = [
    "b1-1g-limited-over-conditional",
    "b1-1g-no-own-will-refuse",
    "b1-1g-ready-conditional-ignored",
    "b1-1g-conditional-own-unconfirmed",
    "b1-1i-prose-blocked-row-ready",
    "b1-1i-prose-ready-row-blocked",
    "b1-1i-prose-limited-row-ready",
    "b1-1k-blocked-colon-id",
    "b1-1k-list-cp1",
    "b1-1k-list-cp4",
    "b1-1k-list-cp5",
    "b1-1k-id-boundary",
    "b1-1k-limited-colon-id",
    "b1-low-backtick-value-then-text",
    "b1-low-blockquote-fence",
    "b1-low-front-matter-fence",
    "b1-low-u2028-not-a-line-break",
    "b1-low-crlf",
]


@pytest.mark.parametrize(("module", "own", "cp0", "wanted"), CASES_B1, ids=IDS_B1)
def test_b1_batch_cases(module: str, own: str | None, cp0: str, wanted: str) -> None:
    assert handoff_outcome.actual_of(module, own, cp0)[0] == wanted


@pytest.mark.parametrize(
    ("own", "wanted"),
    [
        ("Module Status: Completed" + " x" * 500000, "unconfirmed"),
        ("- " * 500000 + "Module Status: Blocked", "will_refuse"),
    ],
    ids=["b1-low-long-line-text", "b1-low-long-list-markers"],
)
def test_b1_long_lines_finish_within_2s(own: str, wanted: str) -> None:
    start = time.monotonic()
    got = handoff_outcome.actual_of("CP-4", own, "")[0]
    assert time.monotonic() - start < 2
    assert got == wanted


@pytest.mark.parametrize(
    ("own", "wanted"),
    [
        ("# CP-4\nModule Status: Completed\n\nNot blocked: CP-4 has its indenture.\n", "ready"),
        (
            (
                "# CP-4\nModule Status: Completed\n\n"
                "Previously blocked: CP-4 lacked inputs; resolved.\n"
            ),
            "ready",
        ),
        ("# CP-4\nModule Status: Completed\n\nCP-4 blocked earlier\n", "ready"),
        ("# CP-4\nbody\n\nNot blocked: CP-4.\n", "unconfirmed"),
    ],
    ids=[
        "b1f1-not-blocked-colon-id",
        "b1f1-previously-blocked-colon-id",
        "b1f1-id-then-status-control",
        "b1f1-no-status-colon-id-prose",
    ],
)
def test_b1f1_own_handoff_prose_status_colon_id_never_counts(own: str, wanted: str) -> None:
    assert handoff_outcome.actual_of("CP-4", own, "")[0] == wanted


OWN4 = "# CP-4\nbody\n"
OWN1 = "# CP-1\nbody\n"
B1K2_CASES = [
    ("CP-4", None, "Blocked: CP-4, CP-5.\n", "will_refuse", "list-cp4"),
    ("CP-5", None, "Blocked: CP-4, CP-5.\n", "will_refuse", "list-cp5"),
    ("CP-4", None, "Blocked: CP-4 because CP-1 data is missing\n", "will_refuse", "because-cp4"),
    ("CP-1", None, "Blocked: CP-4 because CP-1 data is missing\n", "not_reached", "because-cp1"),
    ("CP-4", None, "CP-4 BLOCKED: CP-1 covenant data missing.\n", "will_refuse", "reason-cp4"),
    ("CP-1", OWN1, "CP-4 BLOCKED: CP-1 covenant data missing.\n", "unconfirmed", "reason-cp1-own"),
    ("CP-1", None, "CP-4 BLOCKED: CP-1 covenant data missing.\n", "not_reached", "reason-cp1"),
    ("CP-4", None, "- Blocked: CP-4\n", "will_refuse", "bullet"),
    ("CP-4", None, "**Blocked:** CP-4\n", "will_refuse", "bold"),
]
for _neg in ("Not blocked: CP-4.", "No longer blocked: CP-4.", "Unblocked: CP-4."):
    B1K2_CASES.append(("CP-4", None, _neg + "\n", "not_reached", "neg-" + _neg.split(":")[0]))
    B1K2_CASES.append(("CP-4", OWN4, _neg + "\n", "unconfirmed", "neg-own-" + _neg.split(":")[0]))
for _m in ("CP-4", "CP-5", "CP-6", "CP-7"):
    B1K2_CASES.append(
        (_m, None, "Blocked: CP-4 & CP-5 / CP-6 and CP-7.\n", "will_refuse", "sep-" + _m)
    )


@pytest.mark.parametrize(
    ("module", "own", "cp0", "wanted"),
    [c[:4] for c in B1K2_CASES],
    ids=["b1k2-" + c[4].replace(" ", "-") for c in B1K2_CASES],
)
def test_b1k2_cp0_status_line_start_not_negated_id_list(
    module: str, own: str | None, cp0: str, wanted: str
) -> None:
    assert handoff_outcome.actual_of(module, own, cp0)[0] == wanted


RF_BQ_CASES = [
    (
        "rf-bq-fence-hides-blocked",
        "> ```\n> Module Status: Blocked\n> ```\n",
        "| CP-4 | READY |\n",
        "ready",
    ),
    (
        "rf-bq-fence-hides-completed",
        "> ```\n> Module Status: Completed\n> ```\n",
        "| CP-4 | BLOCKED |\n",
        "will_refuse",
    ),
    ("rf-bq-fence-exits", "> ```\nModule Status: Blocked\n> ```\n", "", "will_refuse"),
    ("rf-bq-status-outside-fence", "> Module Status: Blocked\n", "", "will_refuse"),
]
RF_CASES = [
    ("rf-1k-id-lower", "CP-4", None, "blocked: cp-4\n", "will_refuse"),
    ("rf-1k-heading", "CP-4", None, "## Blocked: CP-4\n", "will_refuse"),
    (
        "rf-1i-second-prose-mention",
        "CP-4",
        OWN4,
        "CP-4 READY for review.\nLater: CP-4 BLOCKED by covenant gap.\n",
        "will_refuse",
    ),
    (
        "rf-1l-cp0-ready-then-blocked",
        "CP-4",
        OWN4,
        "CP-4 READY for review.\nCP-4 BLOCKED by covenant gap.\n",
        "will_refuse",
    ),
    (
        "rf-1l-cp0-blocked-then-ready",
        "CP-4",
        OWN4,
        "CP-4 BLOCKED by covenant gap.\nCP-4 READY for review.\n",
        "will_refuse",
    ),
    ("rf-1l-cp0-two-ready", "CP-4", OWN4, "CP-4 READY for review.\nCP-4 READY again.\n", "ready"),
    (
        "rf-1l-own-ready-then-blocked",
        "CP-4",
        "# CP-4\nCP-4 READY for review.\nCP-4 BLOCKED by covenant gap.\n",
        "",
        "will_refuse",
    ),
    (
        "rf-1l-own-blocked-then-ready",
        "CP-4",
        "# CP-4\nCP-4 BLOCKED by covenant gap.\nCP-4 READY for review.\n",
        "",
        "will_refuse",
    ),
    (
        "rf-1l-own-two-ready",
        "CP-4",
        "# CP-4\nCP-4 READY for review.\nCP-4 READY again.\n",
        "",
        "ready",
    ),
    ("rf-1m-period", "CP-5", None, "Ready: CP-5. Blocked: CP-6.\n", "not_reached"),
    ("rf-1m-period-cp6", "CP-6", None, "Ready: CP-5. Blocked: CP-6.\n", "not_reached"),
    ("rf-1m-semicolon", "CP-5", None, "Ready: CP-5; Blocked: CP-6.\n", "not_reached"),
    ("rf-1m-semicolon-cp6", "CP-6", None, "Ready: CP-5; Blocked: CP-6.\n", "not_reached"),
    ("rf-1m-newline", "CP-5", None, "Ready: CP-5\nBlocked: CP-6\n", "not_reached"),
    ("rf-1m-newline-cp6", "CP-6", None, "Ready: CP-5\nBlocked: CP-6\n", "will_refuse"),
    ("rf-1n-fenced-colon", "CP-4", None, "```\nBlocked: CP-4\n```\n", "not_reached"),
    ("rf-1n-fenced-row", "CP-4", None, "```\n| CP-4 | BLOCKED |\n```\n", "not_reached"),
    ("rf-1n-fenced-prose", "CP-4", None, "```\nCP-4 BLOCKED\n```\n", "not_reached"),
    ("rf-1n-outside-fence-counts", "CP-4", None, "```\nx\n```\nBlocked: CP-4\n", "will_refuse"),
    ("rf1-item-number", "CP-4", None, "Item 3. Blocked: CP-4\n", "not_reached"),
    ("rf1-eg", "CP-4", None, "See the note e.g. Blocked: CP-4\n", "not_reached"),
    ("rf1-sentence", "CP-4", None, "The matter is not resolved. Blocked: CP-4\n", "not_reached"),
    (
        "rf1-negated-semicolon",
        "CP-4",
        None,
        "Nothing is blocked; Blocked: CP-4 was the old note\n",
        "not_reached",
    ),
    ("rf1-draft-v-ready", "CP-4", "# CP-4\nbody\n", "Draft v. Ready: CP-4\n", "unconfirmed"),
    ("rf1-line-start-guard", "CP-4", None, "Blocked: CP-4\n", "will_refuse"),
    (
        "rf1-m2-cp0-two-statuses",
        "CP-4",
        "# CP-4\nbody\n",
        "CP-4 READY for drafting but BLOCKED for filing\n",
        "will_refuse",
    ),
    (
        "rf1-m2-own-two-statuses",
        "CP-4",
        "# CP-4\nCP-4 READY for drafting, BLOCKED for filing",
        "",
        "will_refuse",
    ),
    (
        "rf1-m2-no-own-two-statuses",
        "CP-4",
        None,
        "CP-4 READY for drafting but BLOCKED for filing\n",
        "will_refuse",
    ),
    *[(c[0], "CP-4", c[1], c[2], c[3]) for c in RF_BQ_CASES],
]


@pytest.mark.parametrize(
    ("module", "own", "cp0", "wanted"),
    [c[1:] for c in RF_CASES],
    ids=[c[0] for c in RF_CASES],
)
def test_rf_final_status_reader_batch(module: str, own: str | None, cp0: str, wanted: str) -> None:
    assert handoff_outcome.actual_of(module, own, cp0)[0] == wanted


RF_LINEAR_INPUTS = {
    "spaces": "x." + " " * 1_000_000 + "x",
    "numbered": "x" + ". 1" * 333_000,
}


@pytest.mark.parametrize("name", list(RF_LINEAR_INPUTS))
def test_rf1_cp0_reader_is_linear_at_one_megabyte(name: str) -> None:
    text = RF_LINEAR_INPUTS[name]
    start = time.perf_counter()
    handoff_outcome.actual_of("CP-4", "# CP-4\nbody\n", text)
    assert time.perf_counter() - start < 1.0


RF2_OWN = "# CP-4\nbody\n"
RF2_CASES = [
    (
        "rf2-ready-then-blocked",
        RF2_OWN,
        "CP-4 READY for review, then CP-4 BLOCKED by covenant gap\n",
        "will_refuse",
    ),
    (
        "rf2-ellipsis",
        RF2_OWN,
        "CP-4 READY for review … CP-4 BLOCKED by covenant gap.\n",
        "will_refuse",
    ),
    ("rf2-update-colon", RF2_OWN, "CP-4 update: CP-4 BLOCKED by covenant gap\n", "will_refuse"),
    ("rf2-mention-right-after-mention", RF2_OWN, "CP-4 CP-4 BLOCKED\n", "will_refuse"),
    ("rf2-no-own-mention-right-after-mention", None, "CP-4 CP-4 BLOCKED\n", "will_refuse"),
    (
        "rf2-own-handoff",
        "# CP-4\nCP-4 READY for review, then CP-4 BLOCKED by covenant gap\n",
        "",
        "will_refuse",
    ),
]
for _n in (68, 69, 70, 71, 72):
    _edge = "will_refuse" if _n <= 70 else "unconfirmed"
    RF2_CASES += [
        (f"rf2-cp0-spaces-{_n}", RF2_OWN, "CP-4" + " " * _n + "BLOCKED\n", _edge),
        (f"rf2-cp0-letters-{_n}", RF2_OWN, "CP-4 " + "x" * (_n - 2) + " BLOCKED\n", _edge),
        (f"rf2-own-spaces-{_n}", "# CP-4\nCP-4" + " " * _n + "BLOCKED\n", "", _edge),
    ]


@pytest.mark.parametrize(
    ("own", "cp0", "wanted"), [c[1:] for c in RF2_CASES], ids=[c[0] for c in RF2_CASES]
)
def test_rf2_second_same_id_mention_in_window(own: str | None, cp0: str, wanted: str) -> None:
    assert handoff_outcome.actual_of("CP-4", own, cp0)[0] == wanted
