"""S15 review regressions for CP-8: a decision field's text is the value its quote states (whole
words; a recorded absence stays a gap; one value is not two fields), the missing-quote wording,
and a pending attempt whose one step is already valid settles on resubmission.

Synthetic regressions over the cp8-owner oracle literals with stated edits; expected issue texts
are literals written here.
"""

import json
from pathlib import Path
from typing import Any

import cp8_runs as runs
import pytest
import test_method_cp8 as method

from deploy_vii.execution import Execution
from deploy_workflow.owners import cp8

NOREC = "Portfolio posture and position size were not recorded."
DECISION = "Decision: Neutral action bias with Medium confidence on the Northbridge Term Loan."


def ref(quote: str, locator: str = "page:1") -> dict[str, str]:
    return {"source_id": "prior_case", "locator": locator, "quote": quote}


def test_a_recorded_absence_cannot_be_filled_from_its_own_quote() -> None:
    """The adversarial repro: before, every edit below validated with no issue and T7.1 showed
    posture 'were not' and instrument 'Neutral' as known sourced values."""
    lit = method.positive()
    lit["decision"]["posture"] = {"text": "were not", "quote": ref(NOREC)}
    lit["decision"]["size"] = {"text": "position size", "quote": ref(NOREC)}
    lit["decision"]["instrument"] = {"text": "Neutral", "quote": ref(DECISION)}
    assert method.validator_issues(lit) == (
        "decision.instrument: text Neutral is the decision.action_bias text",
        "decision.posture: the quote states the posture is not recorded",
        "decision.size: the quote states the size is not recorded",
    )


def test_a_narrowed_quote_of_a_not_recorded_sentence_is_still_refused() -> None:
    """The sentence on the page is judged, not only the quoted part of it."""
    lit = method.positive()
    lit["decision"]["posture"] = {"text": "Portfolio posture", "quote": ref("Portfolio posture")}
    assert method.validator_issues(lit) == (
        "decision.posture: the quote states the posture is not recorded",
    )


@pytest.mark.parametrize(
    ("field", "text"),
    [
        ("instrument", "Northbridge Term Lo"),  # a cut word inside the quote
        ("instrument", "orthbridge Term Loan"),
        ("decision_maker_role", "Investment Committ"),
    ],
)
def test_a_cut_word_does_not_occur_in_the_quote(field: str, text: str) -> None:
    lit = method.positive()
    lit["decision"][field]["text"] = text
    assert method.validator_issues(lit) == (
        f"decision.{field}: text {text} does not occur in the quote",
    )


def test_a_word_cut_at_the_quote_edge_is_judged_on_the_page() -> None:
    """The quote itself ends inside a page word: whole in the quote, cut on the page."""
    lit = method.positive()
    cut = DECISION.removesuffix("an.")  # "... on the Northbridge Term Lo"
    lit["decision"]["instrument"] = {"text": "Northbridge Term Lo", "quote": ref(cut)}
    assert method.validator_issues(lit) == (
        "decision.instrument: text Northbridge Term Lo does not occur in the quote",
    )


def test_a_stated_posture_and_size_are_accepted() -> None:
    stated = "Portfolio posture: Defensive. Position size: Core holding."
    packed = method.edited_pack("prior_case", NOREC, f"{NOREC}\n{stated}")
    lit = method.positive()
    lit["decision"]["posture"] = {
        "text": "Defensive",
        "quote": ref("Portfolio posture: Defensive."),
    }
    lit["decision"]["size"] = {"text": "Core holding", "quote": ref("Position size: Core holding.")}
    report = method.settle(lit, packed=packed)
    cells = method.cells(report, "T7.1", "d01")
    assert (cells["posture"].status, cells["posture"].text) == ("known", "Defensive")
    assert (cells["size"].status, cells["size"].text) == ("known", "Core holding")
    assert not any(r.startswith(("posture", "size")) for r in method.row_ids(report, "T7.8"))


def test_the_positive_literal_still_settles() -> None:
    method.settle(method.positive())


def test_a_text_without_its_quote_says_so() -> None:
    """Before: 'text and quote are given together', the opposite of the defect."""
    lit = method.positive()
    lit["decision"]["instrument"] = {"text": "Northbridge Term Loan"}
    assert method.validator_issues(lit) == ("decision.instrument: text needs its quote",)


def test_the_t7_8_rows_and_texts_are_unchanged_by_the_gap_row_refactor() -> None:
    report = method.settle(method.positive())
    expected = method.EXPECTED["cases"]["positive"]
    got = [f for f in report.facts if f.table_id == "T7.8"]
    table = next(t for t in expected["tables"] if t["table_id"] == "T7.8")
    want = [f for r in table["rows"] for f in r["facts"]]
    assert [(f.fact_id, f.text) for f in got] == [(f["fact_id"], f["text"]) for f in want]


# --- a crash between the journaled step and `finish` -----------------------------------------


def _crash(*_: Any, **__: Any) -> Any:
    raise OSError("killed before finish")


def _crashed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Execution, str, str]:
    """CP-0 settled, then the CP-8 step journaled valid and the process killed before finish."""
    _, pack = runs.start("positive", tmp_path)
    store = Execution(tmp_path / "store")
    ticket = next(
        a.ticket_id
        for a in store.read().attempts
        if a.module_id == "CP-8" and a.status == "pending"
    )
    payload = runs.literal("positive", "submission", pack)
    with monkeypatch.context() as patch:
        patch.setattr(Execution, "finish", _crash)
        with pytest.raises(OSError, match="killed before finish"):
            cp8.submit(store, ticket, cp8.STEP_ID, payload, None)
    return store, ticket, payload


def test_a_pending_attempt_with_its_valid_step_settles_on_resubmission(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Before: the resubmission raised 'Submit the next module step in order' and the attempt
    could never finish."""
    store, ticket, payload = _crashed(tmp_path, monkeypatch)
    attempt = next(a for a in store.read().attempts if a.ticket_id == ticket)
    assert (attempt.status, [s.status for s in attempt.steps]) == ("pending", ["valid"])
    settled = cp8.submit(store, ticket, cp8.STEP_ID, payload, None).journal
    assert settled.status == "finished"
    assert [h.module_id for h in store.read().heads].count("CP-8") == 1


def test_a_different_response_for_a_judged_step_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store, ticket, payload = _crashed(tmp_path, monkeypatch)
    other = json.loads(payload)
    other["synthesis"]["text"] += " Restated"
    with pytest.raises(ValueError, match="already retains a different response"):
        cp8.submit(store, ticket, cp8.STEP_ID, json.dumps(other), None)
