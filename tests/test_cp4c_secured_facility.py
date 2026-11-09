"""S09-A04 remainder: CP-4C selects CP-1's secured facility by its T4.18 secured status, not by
the id `term-loan`. Exactly one secured facility at the quarter period is that one; none or more
than one is an issue naming the count (a repairable validator issue and an empty view, never a
raise). Expected values are hand-derived from the rows each test writes.

Base rows (cp1_facts): at q4-2025 the row `term-loan` is SECURED and SENIOR; q3-2025 holds an
UNSECURED row; a FY alias row at fy-2025 is SECURED. T4.14 states q3-2025, q4-2025 and fy-2025,
so the quarter period is q4-2025 (the alias ends the same day).
"""

import importlib
from pathlib import Path
from typing import Any

import pytest

from deploy_vii.contracts import Fact
from deploy_workflow.owners import cp4c

conn: Any = importlib.import_module("test_connect_cp4c")
stage1: Any = importlib.import_module("test_method_cp4c")

Q4 = "q4-2025"


def _row(row: str, facility: str, secured: str, seniority: str = "SENIOR") -> tuple[Fact, ...]:
    """A T4.18 row at q4-2025 under its own fact ids."""
    return tuple(
        conn._text("T4.18", row, field, value, Q4)
        for field, value in (
            ("facility_id", facility),
            ("period_id", Q4),
            ("secured_status", secured),
            ("seniority", seniority),
        )
    )


def _without_current_row(facts: tuple[Fact, ...]) -> tuple[Fact, ...]:
    return tuple(f for f in facts if not (f.table_id == "T4.18" and f.row_id == "term-loan"))


def _upstream(tmp_path: Path, cp1: tuple[Fact, ...], cp4: tuple[Fact, ...] | None = None) -> Any:
    store, _, attempt = conn.seed(tmp_path, cp1=cp1, cp4=cp4)
    return store, attempt, cp4c.cp4c_upstream(store=store, attempt=attempt)


def _renamed(facts: tuple[Fact, ...], old: str, new: str) -> tuple[Fact, ...]:
    return tuple(f.model_copy(update={"text": new}) if f.text == old else f for f in facts)


def test_one_secured_facility_with_another_id_is_the_selected_one(tmp_path: Path) -> None:
    # The q4-2025 row is renamed 'senior-notes'; it is the only SECURED row at q4-2025.
    base = conn.cp1_facts()
    cp1 = tuple(
        f.model_copy(update={"text": "senior-notes"})
        if (f.table_id, f.row_id, f.field) == ("T4.18", "term-loan", "facility_id")
        else f
        for f in base
    )
    cp4 = _renamed(stage1._cp4("positive").facts, "term-loan", "senior-notes")
    _, _, upstream = _upstream(tmp_path, cp1, cp4)
    head = upstream.cp1
    assert head.facility_issue is None
    assert head.facility_id == "senior-notes"
    assert (head.secured_status.text, head.seniority.text) == ("SECURED", "SENIOR")
    assert cp4c.cp4_issue(upstream.cp4, head.facility_id) is None


def test_the_default_term_loan_is_still_selected(tmp_path: Path) -> None:
    _, _, upstream = _upstream(tmp_path, conn.cp1_facts())
    assert (upstream.cp1.facility_id, upstream.cp1.facility_issue) == ("term-loan", None)


ZERO = (
    "CP-4C: CP-1 T4.18 shows 0 secured facilities at q4-2025, not exactly one, so no secured "
    "facility can be selected"
)
TWO = (
    "CP-4C: CP-1 T4.18 shows 2 secured facilities at q4-2025 (term-loan, revolver), not exactly "
    "one, so no secured facility can be selected"
)


def test_no_secured_facility_is_an_issue_naming_the_count(tmp_path: Path) -> None:
    # The q4-2025 row is removed; the q3-2025 row is UNSECURED and the alias row is at fy-2025.
    _, _, upstream = _upstream(tmp_path, _without_current_row(conn.cp1_facts()))
    assert upstream.cp1.facility_issue == ZERO


def test_an_unsecured_row_at_the_quarter_is_not_secured(tmp_path: Path) -> None:
    cp1 = _without_current_row(conn.cp1_facts()) + _row("term-loan", "term-loan", "UNSECURED")
    _, _, upstream = _upstream(tmp_path, cp1)
    assert upstream.cp1.facility_issue == ZERO


def test_two_secured_facilities_are_an_issue_naming_the_count_and_ids(tmp_path: Path) -> None:
    cp1 = conn.cp1_facts() + _row("revolver", "revolver", "SECURED")
    _, _, upstream = _upstream(tmp_path, cp1)
    assert upstream.cp1.facility_issue == TWO


def test_an_unsecured_second_facility_does_not_change_the_selection(tmp_path: Path) -> None:
    cp1 = conn.cp1_facts() + _row("notes", "notes", "UNSECURED", "SUBORDINATED")
    _, _, upstream = _upstream(tmp_path, cp1)
    assert (upstream.cp1.facility_id, upstream.cp1.facility_issue) == ("term-loan", None)


@pytest.mark.parametrize("two", [False, True])
def test_the_validator_and_the_view_refuse_with_the_issue_and_never_raise(
    tmp_path: Path, two: bool
) -> None:
    cp1 = _without_current_row(conn.cp1_facts())
    if two:  # revolver then term-loan, both SECURED at q4-2025, in head order
        cp1 += _row("revolver", "revolver", "SECURED") + _row("term-loan", "term-loan", "SECURED")
    want = TWO.replace("term-loan, revolver", "revolver, term-loan") if two else ZERO
    store, _, upstream = _upstream(tmp_path, cp1)
    pack = store.pack()
    got = cp4c.content_issues(cp4c._inputs(pack, conn._submission(), upstream))
    assert got == (want,)
    block = cp4c.context_block(pack=pack, upstream=upstream)
    assert block["context_issue"] == want
    assert set(block) == {"upstream", "context_issue", "inherited_limitations"}


def test_a_paid_response_over_no_secured_facility_settles_rejected_not_pending(
    tmp_path: Path,
) -> None:
    # The retained step is validated by the journal: the issue is journaled and the attempt ends
    # rejected, where a raise would leave the step pending on every resume.
    store, _, attempt = conn.seed(tmp_path, cp1=_without_current_row(conn.cp1_facts()))
    conn._submit(store, attempt, conn.json.dumps(conn._payload("positive")))
    done = conn._finished(store, attempt)
    assert done.status != "pending"
    assert done.issues == (ZERO,)


def test_a_valid_head_composes_unchanged(tmp_path: Path) -> None:
    store, _, attempt = conn.seed(tmp_path)
    inputs = cp4c._inputs(
        store.pack(), conn._submission(), cp4c.cp4c_upstream(store=store, attempt=attempt)
    )
    assert cp4c.content_issues(inputs) == ()


def test_a_single_secured_row_without_a_facility_id_is_an_issue_not_a_raise(
    tmp_path: Path,
) -> None:
    cp1 = tuple(
        f
        for f in conn.cp1_facts()
        if (f.table_id, f.row_id, f.field) != ("T4.18", "term-loan", "facility_id")
    )
    _, _, upstream = _upstream(tmp_path, cp1)
    assert upstream.cp1.facility_issue == (
        "CP-4C: the one secured CP-1 T4.18 row at q4-2025 states no facility id or no terms"
    )


# --- review of ruling A04 (second model): adversarial heads, expected values read by hand ---


def test_a_secured_status_that_is_not_known_is_not_counted(tmp_path: Path) -> None:
    # The q4-2025 term-loan row states its secured status as missing: no row is known SECURED.
    cp1 = tuple(
        Fact(
            fact_id=f.fact_id,
            label=f.label,
            table_id=f.table_id,
            row_id=f.row_id,
            field=f.field,
            period=f.period,
            status="missing",
            limitation="not stated",
        )
        if (f.table_id, f.row_id, f.field) == ("T4.18", "term-loan", "secured_status")
        else f
        for f in conn.cp1_facts()
    )
    _, _, upstream = _upstream(tmp_path, cp1)
    assert upstream.cp1.facility_issue == ZERO


def test_a_secured_row_at_an_earlier_quarter_only_is_not_selected(tmp_path: Path) -> None:
    # The q4-2025 row is removed and a SECURED revolver row is added at q3-2025 (not the quarter).
    revolver = tuple(
        conn._text("T4.18", "revolver-q3", field, value, "q3-2025")
        for field, value in (
            ("facility_id", "revolver"),
            ("period_id", "q3-2025"),
            ("secured_status", "SECURED"),
            ("seniority", "SENIOR"),
        )
    )
    _, _, upstream = _upstream(tmp_path, _without_current_row(conn.cp1_facts()) + revolver)
    assert upstream.cp1.facility_issue == ZERO


def test_a_secured_alias_row_of_another_facility_does_not_change_the_selection(
    tmp_path: Path,
) -> None:
    # A revolver row at the fy-2025 alias is SECURED; at q4-2025 only term-loan is SECURED.
    revolver = tuple(
        conn._text("T4.18", "revolver-fy", field, value, "fy-2025")
        for field, value in (
            ("facility_id", "revolver"),
            ("period_id", "fy-2025"),
            ("secured_status", "SECURED"),
            ("seniority", "SENIOR"),
        )
    )
    _, _, upstream = _upstream(tmp_path, conn.cp1_facts() + revolver)
    assert (upstream.cp1.facility_id, upstream.cp1.facility_issue) == ("term-loan", None)


def test_two_secured_rows_of_one_facility_are_counted_not_merged(tmp_path: Path) -> None:
    cp1 = conn.cp1_facts() + _row("term-loan-2", "term-loan", "SECURED")
    _, _, upstream = _upstream(tmp_path, cp1)
    assert upstream.cp1.facility_issue == TWO.replace("term-loan, revolver", "term-loan, term-loan")


def test_the_alias_of_a_newly_selected_facility_must_agree(tmp_path: Path) -> None:
    # The only SECURED q4-2025 row is renamed 'senior-notes' and its fy-2025 alias (also renamed)
    # is UNSECURED: the alias check reads the selected id, not term-loan, and refuses with a typed
    # facility issue (hand-written below), no longer a ValueError.
    renamed = _renamed(conn.cp1_facts(alias=("UNSECURED", "SENIOR")), "term-loan", "senior-notes")
    _, _, upstream = _upstream(tmp_path, renamed)
    assert upstream.cp1.facility_issue == (
        "CP-4C: senior-notes secured_status differs between its q4-2025 row and its fy-2025 alias"
    )


def test_an_unreadable_alias_or_period_is_refused_by_validator_and_view(tmp_path: Path) -> None:
    # Ruling: the two former raises settle like the count issue. Alias disagreement: the validator
    # returns exactly the one issue line (no raise) and the view offers nothing but that line.
    cp1 = conn.cp1_facts(alias=("SECURED", "SUBORDINATED"))
    store, _, upstream = _upstream(tmp_path, cp1)
    line = "CP-4C: term-loan seniority differs between its q4-2025 row and its fy-2025 alias"
    assert upstream.cp1.facility_issue == line
    pack = store.pack()
    assert cp4c.validate_restructuring(
        pack=pack, submission=conn._submission(), upstream=upstream
    ) == (line,)
    block = cp4c.context_block(pack=pack, upstream=upstream)
    assert block["context_issue"] == line
    assert set(block) == {"upstream", "context_issue", "inherited_limitations"}
    # No T4.14 period at all: the same shape with its own line.
    bare = tuple(f for f in conn.cp1_facts() if f.table_id != "T4.14")
    _, _, none = _upstream(tmp_path / "none", bare)
    assert none.cp1.facility_issue == "CP-4C: CP-1 states no T4.14 period"
    # Two QUARTER periods ending on the same latest day: no single current period (2025-12-31).
    twin = tuple(f for f in conn.cp1_facts() if f.table_id != "T4.14") + conn._t414(
        (
            ("q3-2025", "QUARTER", "2025-09-30"),
            ("q4-2025", "QUARTER", "2025-12-31"),
            ("q4b-2025", "QUARTER", "2025-12-31"),
        )
    )
    _, _, two = _upstream(tmp_path / "two", twin)
    assert two.cp1.facility_issue == "CP-4C: CP-1 has no single current T4.18 period at 2025-12-31"


def test_a_rejected_attempt_has_one_repair_and_then_no_further_begin(tmp_path: Path) -> None:
    # Spend bound: attempt 0 and its one repair are both rejected with the issue; a third begin is
    # refused, so a CP-1 without one secured facility costs at most two model responses.
    store, _, attempt = conn.seed(tmp_path, cp1=_without_current_row(conn.cp1_facts()))
    payload = conn.json.dumps(conn._payload("positive"))
    conn._submit(store, attempt, payload)
    repair = store.begin(cp4c.MODULE_ID)
    assert (repair.number, repair.repair_issues) == (1, (ZERO,))
    conn._submit(store, repair, payload)
    assert conn._finished(store, repair).issues == (ZERO,)
    with pytest.raises(ValueError, match="one repair has been consumed"):
        store.begin(cp4c.MODULE_ID)


# --- second-model review of the typed CP-1 faults: every former raise path, end to end ---
# Each line is hand-written from the rows below: the facility is term-loan, its quarter row is
# q4-2025 (SECURED, SENIOR), the alias is fy-2025, and the latest T4.14 end is 2025-12-31.


def _missing(fact: Fact) -> Fact:
    return fact.model_copy(update={"text": None, "status": "missing", "limitation": "not stated"})


_BASE = conn.cp1_facts()
_NO_T414 = tuple(f for f in _BASE if f.table_id != "T4.14")
FAULTS = [
    # The alias row states no seniority at all (`theirs is None`), not a different one.
    (
        tuple(f for f in _BASE if f.fact_id != "cp1-T4.18-term-loan-fy-seniority"),
        "CP-4C: term-loan seniority differs between its q4-2025 row and its fy-2025 alias",
    ),
    (
        conn.cp1_facts(alias=("UNSECURED", "SUBORDINATED")),  # both differ: the first term named
        "CP-4C: term-loan secured_status differs between its q4-2025 row and its fy-2025 alias",
    ),
    # T4.14 rows whose end dates are all unsettled state no period.
    (
        tuple(_missing(f) if (f.table_id, f.field) == ("T4.14", "end_date") else f for f in _BASE),
        "CP-4C: CP-1 states no T4.14 period",
    ),
    # Two FY periods and no quarter on the latest day: the FY fallback is not single either.
    (
        _NO_T414
        + conn._t414(
            (
                ("q3-2025", "QUARTER", "2025-09-30"),
                ("fy-2025", "FY", "2025-12-31"),
                ("fyb-2025", "FY", "2025-12-31"),
            )
        ),
        "CP-4C: CP-1 has no single current T4.18 period at 2025-12-31",
    ),
]


@pytest.mark.parametrize("cp1,line", FAULTS)
def test_each_former_raise_is_one_line_in_validator_view_and_settled_attempt(
    cp1: tuple[Fact, ...], line: str, tmp_path: Path
) -> None:
    store, attempt, upstream = _upstream(tmp_path, cp1)
    assert upstream.cp1.facility_issue == line
    assert upstream.cp1.facility_id == ""
    pack = store.pack()
    assert cp4c.validate_restructuring(
        pack=pack, submission=conn._submission(), upstream=upstream
    ) == (line,)
    _, body = cp4c.view(store, attempt)  # the view serialises, never raises
    assert conn.json.loads(body)["context_issue"] == line
    # The attempt settles rejected with exactly that issue and its one repair carries it.
    conn._submit(store, attempt, conn.json.dumps(conn._payload("positive")))
    assert conn._finished(store, attempt).issues == (line,)
    repair = store.begin(cp4c.MODULE_ID)
    assert (repair.number, repair.repair_issues) == (1, (line,))


def test_a_single_fy_period_without_a_quarter_is_still_read(tmp_path: Path) -> None:
    # Not a fault: the latest end holds one FY period and no quarter, so fy-2025 is the period
    # and its SECURED row (the alias rows of cp1_facts) is the facility; no issue.
    t414 = conn._t414((("q3-2025", "QUARTER", "2025-09-30"), ("fy-2025", "FY", "2025-12-31")))
    _, _, upstream = _upstream(tmp_path, _NO_T414 + t414)
    assert upstream.cp1.facility_issue is None
    cp1 = upstream.cp1
    assert (cp1.facility_id, cp1.secured_status.period) == ("term-loan", "fy-2025")
