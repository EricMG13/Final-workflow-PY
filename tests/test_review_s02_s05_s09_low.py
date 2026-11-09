"""Second-model review of the S02/S05/S09 low-severity fixes: adversarial cases.

Every expected value is hand-derived in the comment next to it, not read from the code under test.
`_capture`, the CP-1C counters and the CP-5 counters are stubs or wrappers, so these tests check
call patterns and refusals; the oracle values stay pinned by the method and connect suites.
"""

import json
import unicodedata
from collections import Counter
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from deploy_vii import cp4_legal, cp5_integrity
from deploy_vii.contracts import Fact
from deploy_workflow import owner_rendering as r
from deploy_workflow.owners import cp1b, cp1c, cp5
from deploy_workflow.prompts import compose, fence
from deploy_workflow.prompts.fence import FenceError, data_block

# --- S02-A02/C04: the fence's `<` lookalikes and the JSON escape ------------------------------

# Hand-derived from the Unicode data: the four characters NFKD folds to `<` (U+003C, U+226E =
# `<` + U+0338, U+FE64, U+FF1C), the six confusables NFKD leaves alone, and the two characters
# whose NFKD form is U+3008 (U+2329 canonically, U+FE3F by compatibility).
READ_AS_LESS_THAN = {
    "<",
    "\u226e",
    "\ufe64",
    "\uff1c",
    "\u02c2",
    "\u2039",
    "\u1438",
    "\u276e",
    "\u3008",
    "\u16b2",
    "\u2329",
    "\ufe3f",
}


def test_every_character_the_fence_reads_as_less_than_is_json_escaped() -> None:
    reads = {
        chr(i)
        for i in range(0x110000)
        if not 0xD800 <= i < 0xE000 and "<" in fence._normalised(chr(i))
    }
    assert reads == READ_AS_LESS_THAN
    assert {chr(c) for c in compose._LT_ESCAPES} == READ_AS_LESS_THAN
    assert unicodedata.normalize("NFKD", "\ufe3f") == "\u3008"


def test_a_vertical_angle_bracket_run_in_a_json_body_is_escaped_not_refused() -> None:
    raw = json.dumps({"quote": "ok \ufe3f\ufe3f\ufe3fEND>>>"}, ensure_ascii=False)
    with pytest.raises(FenceError):
        data_block("SOURCE", "step-output", raw)
    safe = compose._json_text_safe(raw)
    assert safe == '{"quote": "ok \\ufe3f\\ufe3f\\ufe3fEND>>>"}'
    assert json.loads(safe) == json.loads(raw)
    data_block("SOURCE", "step-output", safe)


@pytest.mark.parametrize(
    "body",
    [
        "ok\n\u2039\u200b\u2039\u0301\u2039END>>>",  # ZWSP (Cf) and an acute (Mn) between them
        "ok\n\u1438\ufe0f\u1438\ufe0f\u1438END>>>",  # VS16 (Mn) after each syllable
        "ok\n<\u3164\u276e\u276eEND>>>",  # a Hangul filler between `<` and two ornaments
        "ok\n\ufe3f\u2329\u3008END>>>",  # the three forms of U+3008
    ],
)
def test_lookalikes_split_by_invisible_or_combining_marks_are_refused(body: str) -> None:
    # Hand-derived: removing Cf/Mn/Me and the fillers leaves three `<`-like characters in a row.
    with pytest.raises(FenceError):
        data_block("SOURCE", "source-1", body)


def test_guillemet_and_angle_bracket_prose_without_a_run_of_three_is_accepted() -> None:
    # Hand-derived: no more than two `<`-like characters stand together (U+2039 twice is a run
    # of two).
    text = "Il a dit \u2039 oui \u203a et \u00ab non \u00bb ; \u3008\u6ce8\u3009 \u2039\u2039 fin."
    assert text in data_block("SOURCE", "source-1", text)


# --- S02-C05: render_owner_slice captures three times and stays fail-closed --------------------

TREE = {"report.html": b"<html/>", r.RECEIPT_NAME: b"{}"}


def _stub(monkeypatch: pytest.MonkeyPatch, captures: list[object]) -> list[int]:
    calls: list[int] = []

    def capture(*args: object) -> object:
        calls.append(1)
        return captures[min(len(calls), len(captures)) - 1]

    monkeypatch.setattr(r, "_capture", capture)
    monkeypatch.setattr(r, "OwnerRenderReceipt", SimpleNamespace(from_wire=lambda raw: "W"))
    return calls


def test_a_receipt_only_change_before_the_rename_is_stale_and_nothing_is_published(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # Hand-derived: capture 2 is the stage's stale check; the tree is the same but the receipt is
    # not, so the store changed and the render must stop before the rename.
    same = SimpleNamespace(tree=TREE, wire="W")
    other = SimpleNamespace(tree=TREE, wire="W2")
    calls = _stub(monkeypatch, [same, other])
    (tmp_path / "store").mkdir()
    with pytest.raises(ValueError, match="owner_render_stale"):
        r.render_owner_slice(tmp_path / "store", tmp_path / "receipt.json", None, tmp_path / "o")
    assert len(calls) == 2
    assert not (tmp_path / "o").exists()
    assert [p.name for p in tmp_path.iterdir() if p.name.startswith(".owner-render")] == []


def test_a_change_after_the_rename_is_refused_and_the_delivery_is_kept_as_evidence(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # Hand-derived: captures 1 and 2 agree, so the stage is renamed; capture 3 (after the rename)
    # differs, which refuses the render and keeps the published tree (docstring).
    same = SimpleNamespace(tree=TREE, wire="W")
    other = SimpleNamespace(tree={**TREE, "report.html": b"<html>2</html>"}, wire="W")
    calls = _stub(monkeypatch, [same, same, other])
    (tmp_path / "store").mkdir()
    with pytest.raises(ValueError, match="owner_render_stale"):
        r.render_owner_slice(tmp_path / "store", tmp_path / "receipt.json", None, tmp_path / "o")
    assert len(calls) == 3
    assert (tmp_path / "o" / "report.html").read_bytes() == b"<html/>"


def test_a_stage_that_does_not_hold_the_first_capture_is_refused_before_any_recapture(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # Hand-derived: the written stage reads back with an extra file, so the delivery check refuses
    # it before the stale capture (one capture in all) and the stage is removed.
    calls = _stub(monkeypatch, [SimpleNamespace(tree=TREE, wire="W")])
    real = r._read_tree
    monkeypatch.setattr(r, "_read_tree", lambda path: {**real(path), "extra.bin": b"x"})
    (tmp_path / "store").mkdir()
    with pytest.raises(ValueError, match="owner_render_delivery"):
        r.render_owner_slice(tmp_path / "store", tmp_path / "receipt.json", None, tmp_path / "o")
    assert len(calls) == 1
    assert not (tmp_path / "o").exists()
    assert [p.name for p in tmp_path.iterdir() if p.name.startswith(".owner-render")] == []


def test_the_standalone_verifier_still_captures_twice(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # Hand-derived: with no caller capture, one capture is the expectation and one the stale check.
    calls = _stub(monkeypatch, [SimpleNamespace(tree=TREE, wire="W")])
    delivery = tmp_path / "d"
    delivery.mkdir()
    for name, body in TREE.items():
        (delivery / name).write_bytes(body)
    r.verify_owner_rendered_slice(tmp_path / "store", tmp_path / "receipt.json", None, delivery)
    assert len(calls) == 2


# --- S05-A06: exactly one page:1 Basis line -----------------------------------------------------

BASIS = "Basis: twelve months to the period end shown; USD; amounts in millions; unaudited desk."


@pytest.mark.parametrize(
    ("lines", "currency", "expected"),
    [
        ([BASIS], "USD", ("USD", "MILLIONS", Decimal(1_000_000))),
        (["A heading", BASIS, "A note"], "USD", ("USD", "MILLIONS", Decimal(1_000_000))),
        ([BASIS.replace("USD", "EUR")], "EUR", ("EUR", "MILLIONS", Decimal(1_000_000))),
        ([BASIS, BASIS], "USD", None),  # a running header repeated on page 1
        ([BASIS, "Basis: USD; amounts in millions."], "USD", None),  # two agreeing lines
        ([], "USD", None),
        (["Basis: amounts in millions; USD."], "USD", None),  # the pair out of order
        ([BASIS], "EUR", None),  # the line states another currency than the run's
    ],
)
def test_basis_reads_exactly_one_line(
    lines: list[str], currency: str, expected: tuple[str, str, Decimal] | None
) -> None:
    if expected is None:
        with pytest.raises(cp1c.PeerTableError, match="Peer table not found"):
            cp1c._basis(lines, currency)
    else:
        assert cp1c._basis(lines, currency) == expected


# --- S05-C06: fiscal years of ASCII digits only ---------------------------------------------------


def _rows(*years: str | None) -> Any:
    return {f"r{i}": {"fiscal_year": SimpleNamespace(text=y)} for i, y in enumerate(years)}


@pytest.mark.parametrize(
    ("years", "expected"),
    [
        ((None,), ()),  # no text: no year
        (("2025", None, "2025\u00b2"), (("q3-2025", "q4-2025"), ("fy-2024", "fy-2025"))),
        (("02025",), (("q3-2025", "q4-2025"), ("fy-2024", "fy-2025"))),  # int("02025") = 2025
        (("20250",), (("q3-20250", "q4-20250"), ("fy-20249", "fy-20250"))),  # five digits
        (
            ("2026", "2025"),  # sorted ascending, each year's two pairs together
            (
                ("q3-2025", "q4-2025"),
                ("fy-2024", "fy-2025"),
                ("q3-2026", "q4-2026"),
                ("fy-2025", "fy-2026"),
            ),
        ),
        ((" 2025", "2025 ", "+2025", "-2025"), ()),  # int() would read these; isdigit does not
    ],
)
def test_default_pairs_never_raises(
    years: tuple[str | None, ...], expected: tuple[tuple[str, str], ...]
) -> None:
    assert cp1b._default_pairs(_rows(*years)) == expected


# --- S05-C08: the validator path parses and composes once; a refusal composes nothing ------------


def _count(monkeypatch: pytest.MonkeyPatch, names: tuple[str, ...]) -> Counter[str]:
    calls: Counter[str] = Counter()
    for name in names:
        original = getattr(cp1c, name)

        def counted(*args: object, _o: object = original, _n: str = name, **kw: object) -> object:
            calls[_n] += 1
            return _o(*args, **kw)  # type: ignore[operator]

        monkeypatch.setattr(cp1c, name, counted)
    return calls


def test_the_checked_path_parses_and_composes_once(monkeypatch: pytest.MonkeyPatch) -> None:
    from test_connect_cp1c import _pack, _submission, _upstream

    pack, submission, upstream = _pack("positive"), _submission(), _upstream()
    calls = _count(monkeypatch, ("parse_peer_source", "_compose"))
    issues, report = cp1c._checked(pack, submission, upstream)
    # Hand-derived: one sheet parse and one composition (was three of each: issues, compute's
    # issues, compute's own parse and compose).
    assert issues == () and report is not None
    assert calls == Counter({"parse_peer_source": 1, "_compose": 1})


def test_an_inconsistent_assessment_set_composes_nothing_and_compute_raises_the_issues(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from test_method_cp1c import inputs, submissions

    body = json.loads(json.dumps(submissions()["positive"]["peer_benchmark"]))
    del body["assessments"][0]  # one peer of the sheet loses its assessment: a set issue
    case = inputs("positive", payload=body)
    issues = cp1c.calculation_issues(case)
    assert len(issues) == 1
    calls = _count(monkeypatch, ("parse_peer_source", "_compose"))
    with pytest.raises(ValueError) as error:
        cp1c.compute(case)
    assert str(error.value) == issues[0]
    assert calls == Counter({"parse_peer_source": 1})  # no composition without a consistent set


# --- S09-C05: T4.9 and T4F.3 show one headroom ---------------------------------------------------


def _metric(amount: str, unit: str) -> Fact:
    return Fact(
        fact_id="T4.10.r01.ltm",
        label="Metric",
        amount=Decimal(amount),
        unit=unit,
        period="LTM Q4 25",
        value_class="calculated",
    )


@pytest.mark.parametrize(
    ("covenant", "expected"),
    [
        # "not less than 12.5%": operand 12.5 / 100 = 0.125; 0.15 - 0.125 = 0.025 -> 2.500 pp
        (("percent", ">=", "12.5", "0.15"), (Decimal("2.500"), "pp", "2.500 pp")),
        # "not more than 50%": 0.50 - 0.35 = 0.15 -> 15.00 pp (the room of an upper limit)
        (("percent", "<=", "50", "0.35"), (Decimal("15.00"), "pp", "15.00 pp")),
        # "net leverage not more than 4.00x": 4.00 - 1.00 = 3.00 in the metric's own unit
        (("multiple", "<=", "4.00", "1.00"), (Decimal("3.00"), "MULTIPLE", "3.00")),
        # "interest cover not less than 2.50x" against 2.00x: 2.00 - 2.50 = -0.50 (outside)
        (("multiple", ">=", "2.50", "2.00"), (Decimal("-0.50"), "MULTIPLE", "-0.50")),
    ],
)
def test_t49_and_t4f3_trace_the_same_headroom(
    covenant: tuple[str, str, str, str], expected: tuple[Decimal, str, str]
) -> None:
    unit, comparison, parsed, metric = covenant
    amount, cell_unit, traced = expected
    row = SimpleNamespace(name="Covenant", threshold_unit=unit, comparison=comparison)
    fact = _metric(metric, "decimal_fraction" if unit == "percent" else "MULTIPLE")
    test = cp4_legal._Test(row, Decimal(parsed), fact, None, None, False)  # type: ignore[arg-type]
    result = cp4_legal.headroom(test.operand, comparison, fact.amount)  # type: ignore[arg-type]
    test = cp4_legal._Test(row, Decimal(parsed), fact, result, None, False)  # type: ignore[arg-type]
    out = SimpleNamespace(binding=SimpleNamespace(of=lambda row: ()))
    room, _, _ = cp4_legal._test_cells(test, out)  # type: ignore[arg-type]
    assert isinstance(room, Fact)
    assert (room.amount, room.unit) == (amount, cell_unit)
    assert cp4_legal._traced_result(test) == traced
    assert traced.split()[0] == str(room.amount)


# --- S09-C06: CP-5 refusals and the live scope block over one python_checks pass -----------------


@pytest.fixture
def checks_calls(monkeypatch: pytest.MonkeyPatch) -> Counter[str]:
    counter: Counter[str] = Counter()
    real = cp5_integrity.python_checks

    def counted(scope: cp5_integrity.ReviewScope) -> cp5_integrity.PythonChecks:
        counter["python_checks"] += 1
        return real(scope)

    monkeypatch.setattr(cp5_integrity, "python_checks", counted)
    monkeypatch.setattr(cp5, "python_checks", counted)
    return counter


def test_a_refused_cp5_submission_is_refused_alike_on_every_path(
    checks_calls: Counter[str],
) -> None:
    from test_method_cp5 import MUTATIONS, REFUSALS, SUBMISSIONS, apply_op, make_inputs

    entry = next(e for e in REFUSALS if e["id"] == "cp5-unreviewed-claim")
    inputs = make_inputs("positive", apply_op(SUBMISSIONS["positive"], MUTATIONS[entry["id"]]))
    result = cp5.compute(inputs)
    # Hand-derived: the oracle's issue list, no report, and one checks pass for the refusal.
    assert (list(result.issues), result.report) == (entry["issues"], None)
    assert checks_calls["python_checks"] == 1
    outcome = cp5_integrity.review_outcome(inputs.scope, inputs.submission)
    assert outcome == (tuple(entry["issues"]), None)
    with pytest.raises(ValueError) as error:
        cp5_integrity.integrity_review(inputs.scope, inputs.submission)
    assert str(error.value) == "; ".join(entry["issues"])


def test_a_stale_cp5_scope_is_refused_without_running_the_checks(
    checks_calls: Counter[str],
) -> None:
    import dataclasses

    from test_method_cp5 import make_inputs

    inputs = make_inputs("positive")
    scope = dataclasses.replace(inputs.scope, issues=("CP-1: stale",))
    # Hand-derived: the scope's own issues, alone, before any check runs.
    assert cp5_integrity.review_outcome(scope, inputs.submission) == (("CP-1: stale",), None)
    assert checks_calls["python_checks"] == 0


def test_the_live_scope_block_runs_the_checks_once_and_is_unchanged(
    monkeypatch: pytest.MonkeyPatch, checks_calls: Counter[str]
) -> None:
    from test_method_cp5 import make_inputs

    from deploy_vii.live import context as live_context

    scope = make_inputs("gap").scope
    expected = cp5_integrity.context_block(
        scope, facts=live_context.integrity_projection(scope)
    )  # the two-pass form: each part runs its own checks
    assert checks_calls["python_checks"] == 2
    checks_calls.clear()
    monkeypatch.setattr(cp5_integrity, "review_scope", lambda store, attempt: scope)
    assert live_context.integrity_scope(None, None) == expected  # type: ignore[arg-type]
    assert checks_calls["python_checks"] == 1


def test_one_cp5_step_validation_runs_the_checks_once(
    tmp_path: Path, checks_calls: Counter[str]
) -> None:
    from test_connect_cp5 import make_journal

    journal = make_journal(tmp_path, "positive")
    checks_calls.clear()
    outcome = cp5_integrity._validate_step(journal.store, journal.attempt)
    # Hand-derived: one review_outcome pass validates and composes (was three: validate, then
    # integrity_review's own validate and compose).
    assert outcome.output is not None and outcome.issues == ()
    assert checks_calls["python_checks"] == 1
