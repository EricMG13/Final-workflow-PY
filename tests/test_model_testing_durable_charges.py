from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest
from test_model_testing_budget import call
from test_model_testing_records import fields as record_fields

from deploy_workflow.model.budget import Budget, read_reservation_snapshot
from deploy_workflow.model.budget import BudgetError as ProducerBudgetError
from deploy_workflow.model.record import CallRecord
from deploy_workflow.model.redact import Redactor
from deploy_workflow.model_testing.budget import (
    BudgetError as ModelBudgetError,
)
from deploy_workflow.model_testing.budget import (
    UnknownCharge,
    account_spend,
    require_budget,
)
from deploy_workflow.model_testing.records import JournalError, read_run


def _run(run_dir: Path) -> None:
    run_dir.mkdir(parents=True)
    (run_dir / "run.json").write_text(
        json.dumps(
            {
                "case_id": "case-1",
                "pathway": "credit_snapshot",
                "config_id": "sol-medium",
                "run_id": "run-1",
                "mode": "live",
                "cap_usd": "20",
                "sources": [],
                "cp_dr_invoked": False,
                "replayed_from_run": None,
                "outcome": "stopped",
                "stopped_reason": "crashed",
                "ruling_path": "ruling.md",
                "ruling_sha256": "a" * 64,
                "ruling_date": "2026-11-03",
            }
        )
    )


def test_unmatched_crash_hold_is_carried_as_durable_debit(tmp_path: Path) -> None:
    run_dir = tmp_path / "run-1"
    _run(run_dir)
    budget = Budget(Decimal(20), run_dir / "execution")
    budget.reserve("random-marker-id", Decimal(3), config_id="sol-medium")

    meta, records = read_run(run_dir)

    assert records == ()
    assert len(meta.durable_debits) == 1
    debit = meta.durable_debits[0]
    assert debit.config_id == "sol-medium"
    assert debit.reserved_usd == Decimal(3)
    assert debit.effective_usd == Decimal(3)
    assert debit.unresolved is True


def test_run_json_cannot_supply_runtime_durable_debits(tmp_path: Path) -> None:
    run_dir = tmp_path / "run-1"
    _run(run_dir)
    run_json = run_dir / "run.json"
    body = json.loads(run_json.read_text())
    body["durable_debits"] = [{"call_id": "invented", "effective_usd": "9"}]
    run_json.write_text(json.dumps(body))

    with pytest.raises(JournalError, match="unexpected field"):
        read_run(run_dir)


def test_zero_fields_without_producer_refusal_evidence_are_rejected(tmp_path: Path) -> None:
    run_dir = tmp_path / "run-1"
    _run(run_dir)
    no_error = CallRecord(
        **record_fields(
            run_id="run-1",
            reserved_usd=Decimal(0),
            settled_usd=Decimal(0),
            request_id=None,
            http_status=None,
            first_byte_at=None,
            finished_at=None,
            input_tokens=None,
            output_tokens=None,
            reported_model=None,
            error_class=None,
            error=None,
        )
    )
    (run_dir / "calls.jsonl").write_text(no_error.model_dump_json() + "\n")

    with pytest.raises(JournalError, match="has no reservation marker"):
        read_run(run_dir)


def test_inexact_marker_aggregate_is_a_named_read_refusal(tmp_path: Path) -> None:
    run_dir = tmp_path / "run-1"
    _run(run_dir)
    budget = Budget(Decimal(20), run_dir / "execution")
    for marker_id in ("one", "two"):
        budget.reserve(marker_id, Decimal(1), config_id="sol-medium")
    marker = run_dir / "execution" / "owner-run-audit" / "reservations" / "two"
    marker.write_text(
        json.dumps({"usd": "1e-121", "config_id": "sol-medium", "retry_of": None})
    )

    with pytest.raises(JournalError, match="exact"):
        read_run(run_dir)


def test_inexact_final_account_total_is_a_named_budget_refusal(tmp_path: Path) -> None:
    first_dir, second_dir = tmp_path / "run-1", tmp_path / "run-2"
    _run(first_dir)
    _run(second_dir)
    second_json = second_dir / "run.json"
    second_body = json.loads(second_json.read_text())
    second_body["run_id"] = "run-2"
    second_json.write_text(json.dumps(second_body))
    paid = call("sol-medium", "1", reserved="1", run_id="run-1")
    (first_dir / "calls.jsonl").write_text(paid.model_dump_json() + "\n")
    paid_markers = Budget(Decimal(20), first_dir / "execution")
    paid_markers.reserve("paid", Decimal(1), config_id="sol-medium")
    paid_markers.settle("paid", Decimal(1))
    hold_markers = Budget(Decimal(20), second_dir / "execution")
    hold_markers.reserve("tiny", Decimal("1e-121"), config_id="sol-medium")
    runs = [read_run(first_dir), read_run(second_dir)]

    with pytest.raises(ModelBudgetError, match="exact"):
        account_spend(runs, "openai")


def test_retry_child_requires_retained_unknown_parent(tmp_path: Path) -> None:
    run_dir = tmp_path / "run-1"
    _run(run_dir)
    budget = Budget(Decimal(20), run_dir / "execution")
    budget.reserve("parent", Decimal(3), config_id="sol-medium")
    budget.settle("parent", None, retryable=True)
    budget.reserve("retry", Decimal(2), retry_of="parent", config_id="sol-medium")
    budget.settle("retry", Decimal(2))
    parent_record = call("sol-medium", None, reserved="3", status="unknown", run_id="run-1")
    retry_record = call("sol-medium", "2", reserved="2", index=1, run_id="run-1")
    (run_dir / "calls.jsonl").write_text(
        parent_record.model_dump_json() + "\n" + retry_record.model_dump_json() + "\n"
    )
    assert account_spend([read_run(run_dir)], "openai") == Decimal(5)

    marker_dir = run_dir / "execution" / "owner-run-audit" / "reservations"
    (marker_dir / "parent").unlink()
    (marker_dir / "parent.settled").unlink()
    (run_dir / "calls.jsonl").unlink()

    with pytest.raises(JournalError, match="retry.*parent|parent.*retry"):
        read_run(run_dir)


def test_retry_child_parent_must_be_unknown_and_retryable(tmp_path: Path) -> None:
    run_dir = tmp_path / "run-1"
    _run(run_dir)
    budget = Budget(Decimal(20), run_dir / "execution")
    budget.reserve("parent", Decimal(3), config_id="sol-medium")
    budget.settle("parent", Decimal(3))
    marker_dir = run_dir / "execution" / "owner-run-audit" / "reservations"
    (marker_dir / "retry").write_text(
        json.dumps({"usd": "2", "config_id": "sol-medium", "retry_of": "parent"})
    )
    (marker_dir / "retry.settled").write_text(
        json.dumps({"status": "settled", "usd": "2", "retryable": False})
    )

    with pytest.raises(ProducerBudgetError, match="parent is not retryable unknown"):
        read_reservation_snapshot(run_dir / "execution")


def test_retry_graph_refuses_multiple_children(tmp_path: Path) -> None:
    run_dir = tmp_path / "run-1"
    _run(run_dir)
    budget = Budget(Decimal(20), run_dir / "execution")
    budget.reserve("parent", Decimal(3), config_id="sol-medium")
    budget.settle("parent", None, retryable=True)
    budget.reserve("first-retry", Decimal(2), retry_of="parent", config_id="sol-medium")
    budget.settle("first-retry", Decimal(2))
    marker_dir = run_dir / "execution" / "owner-run-audit" / "reservations"
    (marker_dir / "second-retry").write_text(
        json.dumps(
            {"usd": "2", "config_id": "sol-medium", "retry_of": "parent"}
        )
    )

    with pytest.raises(ProducerBudgetError, match="more than one retry"):
        read_reservation_snapshot(run_dir / "execution")


def test_retry_graph_refuses_self_cycle_and_cross_config_parent(tmp_path: Path) -> None:
    run_dir = tmp_path / "run-1"
    _run(run_dir)
    budget = Budget(Decimal(20), run_dir / "execution")
    budget.reserve("parent", Decimal(3), config_id="sol-medium")
    budget.settle("parent", None, retryable=True)
    marker_dir = run_dir / "execution" / "owner-run-audit" / "reservations"
    parent_path = marker_dir / "parent"
    parent = json.loads(parent_path.read_text())
    parent["retry_of"] = "parent"
    parent_path.write_text(json.dumps(parent))

    with pytest.raises(ProducerBudgetError, match="points to itself"):
        read_reservation_snapshot(run_dir / "execution")

    parent["retry_of"] = None
    parent_path.write_text(json.dumps(parent))
    (marker_dir / "child").write_text(
        json.dumps({"usd": "2", "config_id": "sol-high", "retry_of": "parent"})
    )
    with pytest.raises(ProducerBudgetError, match="different config"):
        read_reservation_snapshot(run_dir / "execution")


def test_recorded_charge_and_unmatched_hold_count_once_and_stop_config(tmp_path: Path) -> None:
    run_dir = tmp_path / "run-1"
    _run(run_dir)
    charge = call("sol-medium", "2", reserved="2", run_id="run-1")
    (run_dir / "calls.jsonl").write_text(charge.model_dump_json() + "\n")
    budget = Budget(Decimal(20), run_dir / "execution")
    budget.reserve("recorded-charge", Decimal(2), config_id="sol-medium")
    budget.settle("recorded-charge", Decimal(2))
    budget.reserve("crash-hold", Decimal(3), config_id="sol-medium")

    meta, records = read_run(run_dir)
    batch = [(meta, records)]

    assert account_spend(batch, "openai") == Decimal(5)
    assert "durable_debits" not in meta.model_dump(mode="json")
    with pytest.raises(UnknownCharge, match="sol-medium"):
        require_budget("sol-medium", batch, Decimal(0))


def test_recorded_unknown_matches_marker_without_double_counting(tmp_path: Path) -> None:
    run_dir = tmp_path / "run-1"
    _run(run_dir)
    record = call("sol-medium", None, reserved="3", status="unknown", run_id="run-1")
    (run_dir / "calls.jsonl").write_text(record.model_dump_json() + "\n")
    budget = Budget(Decimal(20), run_dir / "execution")
    budget.reserve("random-id", Decimal(3), config_id="sol-medium")
    budget.settle("random-id", None)

    meta, records = read_run(run_dir)

    assert not meta.durable_debits
    assert account_spend([(meta, records)], "openai") == Decimal(3)


def test_identical_records_and_markers_keep_their_multiplicity(tmp_path: Path) -> None:
    run_dir = tmp_path / "run-1"
    _run(run_dir)
    records = (
        call("sol-medium", "2", reserved="2", run_id="run-1", index=0),
        call("sol-medium", "2", reserved="2", run_id="run-1", index=1),
    )
    (run_dir / "calls.jsonl").write_text("".join(r.model_dump_json() + "\n" for r in records))
    budget = Budget(Decimal(20), run_dir / "execution")
    for marker in ("first", "second"):
        budget.reserve(marker, Decimal(2), config_id="sol-medium")
        budget.settle(marker, Decimal(2))

    meta, loaded = read_run(run_dir)

    assert loaded == records
    assert not meta.durable_debits
    assert account_spend([(meta, loaded)], "openai") == Decimal(4)


def test_zero_charge_marker_does_not_consume_unmarked_refusal(tmp_path: Path) -> None:
    run_dir = tmp_path / "run-1"
    _run(run_dir)
    source = call("sol-medium", "0", reserved="0", run_id="run-1").model_dump()
    identity_fields = (
        "run_id",
        "case_id",
        "pathway",
        "module_id",
        "step_id",
        "attempt",
        "call_index",
        "config_id",
        "provider",
        "requested_model",
        "requested_effort",
        "invocation_digest",
        "started_at",
        "finished_at",
    )
    refusal = CallRecord.refused(
        Redactor(),
        error_class="NotSent",
        error="request was not sent",
        **{field: source[field] for field in identity_fields},
    )
    charged_zero = call(
        "sol-medium", "0", reserved="0", run_id="run-1", index=1
    )
    (run_dir / "calls.jsonl").write_text(
        refusal.model_dump_json() + "\n" + charged_zero.model_dump_json() + "\n"
    )
    budget = Budget(Decimal(20), run_dir / "execution")
    budget.reserve("zero-charge", Decimal(0), config_id="sol-medium")
    budget.settle("zero-charge", Decimal(0))

    meta, records = read_run(run_dir)

    assert records == (refusal, charged_zero)
    assert not meta.durable_debits


def test_duplicate_markers_leave_one_unmatched_debit(tmp_path: Path) -> None:
    run_dir = tmp_path / "run-1"
    _run(run_dir)
    one_record = call("sol-medium", "2", reserved="2", run_id="run-1")
    (run_dir / "calls.jsonl").write_text(one_record.model_dump_json() + "\n")
    budget = Budget(Decimal(20), run_dir / "execution")
    for marker in ("recorded", "orphaned"):
        budget.reserve(marker, Decimal(2), config_id="sol-medium")
        budget.settle(marker, Decimal(2))

    meta, records = read_run(run_dir)

    assert account_spend([(meta, records)], "openai") == Decimal(4)
    assert len(meta.durable_debits) == 1
    with pytest.raises(UnknownCharge, match="sol-medium"):
        require_budget("sol-medium", [(meta, records)], Decimal(0))


def test_charge_record_without_marker_is_refused(tmp_path: Path) -> None:
    run_dir = tmp_path / "run-1"
    _run(run_dir)
    (run_dir / "calls.jsonl").write_text(
        call("sol-medium", "2", reserved="2", run_id="run-1").model_dump_json() + "\n"
    )

    with pytest.raises(JournalError, match="has no reservation marker"):
        read_run(run_dir)


def test_zero_charge_with_send_evidence_is_not_a_pre_reserve_refusal(tmp_path: Path) -> None:
    run_dir = tmp_path / "run-1"
    _run(run_dir)
    sent_zero = CallRecord(
        **record_fields(
            run_id="run-1",
            reserved_usd=Decimal(0),
            settled_usd=Decimal(0),
            request_id="req-sent",
            http_status=200,
        )
    )
    (run_dir / "calls.jsonl").write_text(sent_zero.model_dump_json() + "\n")

    with pytest.raises(JournalError, match="has no reservation marker"):
        read_run(run_dir)


def test_producer_shaped_not_sent_refusal_with_release_marker_costs_zero(
    tmp_path: Path,
) -> None:
    run_dir = tmp_path / "run-1"
    _run(run_dir)
    source = call("sol-medium", "0", reserved="0", run_id="run-1").model_dump()
    identity_fields = (
        "run_id",
        "case_id",
        "pathway",
        "module_id",
        "step_id",
        "attempt",
        "call_index",
        "config_id",
        "provider",
        "requested_model",
        "requested_effort",
        "invocation_digest",
        "started_at",
        "finished_at",
    )
    base = {field: source[field] for field in identity_fields}
    refused = CallRecord.refused(
        Redactor(), error_class="NotSent", error="request was not sent", **base
    )
    (run_dir / "calls.jsonl").write_text(refused.model_dump_json() + "\n")
    budget = Budget(Decimal(20), run_dir / "execution")
    budget.reserve("released-call", Decimal(2), config_id="sol-medium")
    budget.release("released-call")

    meta, records = read_run(run_dir)

    assert records == (refused,)
    assert not meta.durable_debits
    assert account_spend([(meta, records)], "openai") == Decimal(0)


def test_unmatched_known_charge_is_counted_and_still_stops_config(tmp_path: Path) -> None:
    run_dir = tmp_path / "run-1"
    _run(run_dir)
    budget = Budget(Decimal(20), run_dir / "execution")
    budget.reserve("settled-unmatched", Decimal(4), config_id="sol-medium")
    budget.settle("settled-unmatched", Decimal(3))

    meta, records = read_run(run_dir)
    batch = [(meta, records)]

    assert account_spend(batch, "openai") == Decimal(3)
    with pytest.raises(UnknownCharge, match="sol-medium"):
        require_budget("sol-medium", batch, Decimal(0))


def test_symlinked_marker_refused_without_modification(tmp_path: Path) -> None:
    run_dir = tmp_path / "run-1"
    _run(run_dir)
    budget = Budget(Decimal(20), run_dir / "execution")
    budget.reserve("real-id", Decimal(3), config_id="sol-medium")
    marker_dir = run_dir / "execution" / "owner-run-audit" / "reservations"
    original = marker_dir / "real-id"
    target = tmp_path / "outside"
    target.write_bytes(original.read_bytes())
    original.unlink()
    original.symlink_to(target)
    before = target.read_bytes()

    with pytest.raises(JournalError, match="symbolic link"):
        read_run(run_dir)

    assert target.read_bytes() == before


def test_orphan_settlement_marker_refused_and_reader_does_not_create_state(
    tmp_path: Path,
) -> None:
    run_dir = tmp_path / "run-1"
    _run(run_dir)
    execution = run_dir / "execution"
    assert not execution.exists()
    assert read_run(run_dir)[1] == ()
    assert not execution.exists()

    marker_dir = execution / "owner-run-audit" / "reservations"
    marker_dir.mkdir(parents=True)
    (marker_dir / "orphan.settled").write_text(
        '{"status":"settled","usd":"1","retryable":false}'
    )
    with pytest.raises(JournalError, match="has no reservation"):
        read_run(run_dir)


def test_invalid_marker_money_refused_without_repair(tmp_path: Path) -> None:
    run_dir = tmp_path / "run-1"
    _run(run_dir)
    budget = Budget(Decimal(20), run_dir / "execution")
    budget.reserve("bad-money", Decimal(3), config_id="sol-medium")
    marker = run_dir / "execution" / "owner-run-audit" / "reservations" / "bad-money"
    marker.write_text(json.dumps({"usd": "NaN", "config_id": "sol-medium", "retry_of": None}))
    before = marker.read_bytes()

    with pytest.raises(JournalError, match="finite"):
        read_run(run_dir)

    assert marker.read_bytes() == before
