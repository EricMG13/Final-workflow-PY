"""S15 review regressions for CP-DR: a damaged evidence row is the named record fault (never a
bare ValueError, never a path built from a bad item id), a rerun's mixed retrieval instants give
the dossier block the latest one, a brief step journaled valid without its lock is locked again,
a pending attempt whose research step is already valid settles on resubmission, and the brief
step refuses tool-loop rules.

Synthetic regressions over the cpdr-research-owner oracle staging; expected values are literals.
"""

import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import cpdr_consumers as cc
import cpdr_runs as runs
import pytest

from deploy_vii.execution import Execution
from deploy_workflow.owners import cpdr
from deploy_workflow.research import evidence as record
from deploy_workflow.workflow import WorkflowError

EARLIER = "2025-12-01T09:30:00Z"  # an instant an earlier run kept for one unchanged item


def _row(**edit: Any) -> dict[str, Any]:
    row: dict[str, Any] = {
        "item_id": "ev-1",
        "family": "f",
        "published": "2025-06-30",
        "locator": "a",
        "sha256": "0" * 64,
        "retrieved": runs.RETRIEVED,
        "path": "x.txt",
        "origin": "supplied",
        "url": None,
    }
    return {**row, **edit}


@pytest.mark.parametrize("published", ["2025-13-45", "June 30, 2025", ""])
def test_a_published_value_that_is_not_a_date_is_the_named_record_fault(published: str) -> None:
    with pytest.raises(record.EvidenceRecordInvalid, match="published is not an ISO date"):
        cpdr._items([_row(published=published)])


def test_a_bad_item_id_is_the_named_record_fault() -> None:
    with pytest.raises(record.EvidenceRecordInvalid, match="item_id must be ev-<n>"):
        cpdr._items([_row(item_id="../../outside")])


def _write(research: Path, rows: list[Mapping[str, Any]]) -> None:
    (research / record.EVIDENCE_FILE).write_text(json.dumps(rows), encoding="utf-8")


def test_no_path_is_built_from_a_bad_item_id(tmp_path: Path) -> None:
    research = tmp_path / "research"
    research.mkdir()
    (tmp_path / "outside.txt").write_bytes(b"not staged")
    _write(research, [_row(item_id="../outside")])
    with pytest.raises(record.EvidenceRecordInvalid, match="item_id must be ev-<n>"):
        cpdr._evidence_items(research)


def test_a_damaged_published_value_is_evidence_unrecorded_in_the_view(tmp_path: Path) -> None:
    """Before: research_view raised ValueError('month must be in 1..12')."""
    store, ticket = runs.locked("positive", tmp_path)
    path = cpdr.research_dir(store) / record.EVIDENCE_FILE
    rows = json.loads(path.read_text(encoding="utf-8"))
    rows[0]["published"] = "2025-13-45"
    path.write_text(json.dumps(rows), encoding="utf-8")
    attempt = next(a for a in store.read().attempts if a.ticket_id == ticket)
    with pytest.raises(WorkflowError) as raised:
        cpdr.research_view(store, attempt)
    assert raised.value.code == "evidence_unrecorded"


# --- the dossier block's retrieval instant --------------------------------------------------


def _settled_with_kept(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Execution:
    """CP-DR settled over a rerun's staging: ev-1 unchanged keeps EARLIER, ev-2/3 take the clock."""
    write = record.write_evidence

    def kept(path: Path, accepted: Any, retrieved: str, _: Any = None) -> bytes:
        return write(path, accepted, retrieved, {"ev-1": EARLIER})

    monkeypatch.setattr(record, "write_evidence", kept)
    store = cc.settled_through_cpdr(tmp_path, ("CP-1", cpdr.MODULE_ID, "CP-1C"))
    rows = record.read_evidence(cpdr.research_dir(store) / record.EVIDENCE_FILE)
    assert [r["retrieved"] for r in rows] == [EARLIER, runs.RETRIEVED, runs.RETRIEVED]
    return store


def test_mixed_retrieval_instants_give_the_latest_to_the_dossier_block(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Before: 'the evidence record has no single retrieval instant' stopped the consumer."""
    store = _settled_with_kept(tmp_path, monkeypatch)
    attempt = store.begin("CP-1C")
    attempt = next(a for a in store.read().attempts if a.ticket_id == attempt.ticket_id)
    (item,) = cpdr.dossier_item(store, attempt, cpdr.research_dir(store))
    assert item.retrieved == runs.RETRIEVED  # 2026-01-11T08:00:00Z, later than EARLIER


# --- crash windows of submit ----------------------------------------------------------------


def test_a_valid_brief_without_its_lock_is_locked_by_the_research_submit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A crash between journaling the brief step and writing the lock: before, every research
    submit raised NOT_LOCKED and the brief could not be resubmitted."""
    store, ticket = runs.seeded("positive", tmp_path)

    def crash(*_: Any) -> None:
        raise OSError("killed before the lock")

    with monkeypatch.context() as patch:
        patch.setattr(cpdr, "_lock", crash)
        with pytest.raises(OSError, match="killed before the lock"):
            cpdr.submit(store, ticket, cpdr.BRIEF_STEP, runs.defaults_only("positive"), None)
    path = cpdr.research_dir(store) / cpdr.BRIEF_FILE
    assert not path.exists()
    journal = cpdr.submit(
        store, ticket, cpdr.RESEARCH_STEP, runs.research_payload("positive"), None
    ).journal
    assert path.exists()
    assert [s.status for s in journal.steps] == ["valid", "valid"]
    assert journal.status == "finished"


def _restated(payload: str) -> str:
    body = json.loads(payload)
    body["answers"][0]["uncertainty"] = (body["answers"][0].get("uncertainty") or "") + " Restated"
    return json.dumps(body)


def test_a_pending_attempt_with_its_valid_research_step_settles_on_resubmission(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store, ticket = runs.locked("positive", tmp_path)
    payload = runs.research_payload("positive")

    def crash(*_: Any, **__: Any) -> Any:
        raise OSError("killed before finish")

    with monkeypatch.context() as patch:
        patch.setattr(Execution, "finish", crash)
        with pytest.raises(OSError, match="killed before finish"):
            cpdr.submit(store, ticket, cpdr.RESEARCH_STEP, payload, None)
    attempt = next(a for a in store.read().attempts if a.ticket_id == ticket)
    assert (attempt.status, [s.status for s in attempt.steps]) == ("pending", ["valid", "valid"])
    with pytest.raises(ValueError, match="already retains a different response"):
        cpdr.submit(store, ticket, cpdr.RESEARCH_STEP, _restated(payload), None)
    journal = cpdr.submit(store, ticket, cpdr.RESEARCH_STEP, payload, None).journal
    assert journal.status == "finished"
    assert [h.module_id for h in store.read().heads].count(cpdr.MODULE_ID) == 1


def test_the_brief_step_refuses_tool_loop_rules(tmp_path: Path) -> None:
    store, ticket = runs.seeded("positive", tmp_path)
    with pytest.raises(ValueError, match=re.escape("The CP-DR brief step has no tool-loop rules")):
        cpdr.submit(store, ticket, cpdr.BRIEF_STEP, runs.defaults_only("positive"), lambda _: ())
