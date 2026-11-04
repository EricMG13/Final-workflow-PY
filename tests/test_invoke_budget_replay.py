"""The replay verifiers enforce the per-step invoke budget (CP1H-R5: 64). A receipt is built with
the cap raised, so its step holds more calls than the budget allows, then verified at the real cap:
64 calls in a step verify, 65 are rejected (closes the ada415ca review's Low)."""

import importlib
from pathlib import Path
from typing import Any

import pytest

from deploy_vii.execution import Execution
from deploy_workflow import financial_workflow as fin
from deploy_workflow import owner_workflow as own
from deploy_workflow.workflow import WorkflowError

fw: Any = importlib.import_module("tests.test_financial_workflow")
PAGE = {"source_id": "identity", "first_page": 1, "last_page": 1}
RAISED = 128  # the cap while the receipt is built; the verifier then checks the real one


def _financial(tmp_path: Path, calls: int, monkeypatch: pytest.MonkeyPatch) -> tuple[Any, Path]:
    workflow, pack = fw.start(tmp_path, gap=True)
    real = fin.MAX_INVOKES
    monkeypatch.setattr(fin, "MAX_INVOKES", RAISED)
    for _ in range(calls):
        assert workflow.invoke("read_pages", PAGE)["status"] == "ok"
    assert workflow.submit_review(fw.readiness(pack, gap=True))["status"] == "valid"
    assert workflow.publish_model()["status"] == "refused"
    receipt = workflow.write_receipt(tmp_path / "receipt.json")
    monkeypatch.setattr(fin, "MAX_INVOKES", real)
    return Execution(tmp_path / "store"), receipt


def _owner(tmp_path: Path, calls: int, monkeypatch: pytest.MonkeyPatch) -> tuple[Any, Path]:
    pack = fw.make_pack(True)
    workflow = own.OwnerWorkflow.create(
        tmp_path / "store", pack, publication_directory=tmp_path / "model"
    )
    real = own.MAX_INVOKES
    monkeypatch.setattr(own, "MAX_INVOKES", RAISED)
    for _ in range(calls):
        assert workflow.invoke("read_pages", PAGE)["status"] == "ok"
    assert workflow.submit_review(fw.readiness(pack, gap=True))["status"] == "valid"
    assert workflow.publish()["status"] == "refused"
    receipt = workflow.write_receipt(tmp_path / "receipt.json")
    monkeypatch.setattr(own, "MAX_INVOKES", real)
    return Execution(tmp_path / "store"), receipt


def test_the_verifiers_hold_the_budget_at_sixty_four() -> None:
    assert fin.MAX_INVOKES == 64 and own.MAX_INVOKES == 64


@pytest.mark.parametrize("calls", [33, 64])
def test_a_financial_receipt_with_up_to_sixty_four_calls_verifies(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, calls: int
) -> None:
    store, receipt = _financial(tmp_path, calls, monkeypatch)
    fin.verify_financial_slice_receipt(store, receipt, model_directory=None)


def test_a_financial_receipt_with_sixty_five_calls_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store, receipt = _financial(tmp_path, 65, monkeypatch)
    with pytest.raises(WorkflowError) as caught:
        fin.verify_financial_slice_receipt(store, receipt, model_directory=None)
    assert caught.value.code == "identity_mismatch"


@pytest.mark.parametrize("calls", [33, 64])
def test_an_owner_receipt_with_up_to_sixty_four_calls_verifies(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, calls: int
) -> None:
    store, receipt = _owner(tmp_path, calls, monkeypatch)
    own.verify_owner_run_receipt(store, receipt, publication_directory=None)


def test_an_owner_receipt_with_sixty_five_calls_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store, receipt = _owner(tmp_path, 65, monkeypatch)
    with pytest.raises(WorkflowError) as caught:
        own.verify_owner_run_receipt(store, receipt, publication_directory=None)
    assert caught.value.code == "identity_mismatch"
