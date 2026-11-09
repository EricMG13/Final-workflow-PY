"""C02: a one-step module's submit resumes after a crash between its valid step and `finish`.

CP-1B, CP-1C and CP-1D settle through `cp1a.submit_one_step`. Their real journals need a promoted
CP-1 (minutes), so the journal protocol is driven on CP-0's one-step chain, which uses the same
`Execution.submit_step`/`finish` calls: the module identity, validator and builder are CP-0's.
Expected outcomes are the protocol's, written by hand: after the crash the attempt is pending
with one valid step; the retry with the same payload settles it (finished, still one step, the
head's module equal to the uncrashed run's); a retry with another payload is refused.
"""

from pathlib import Path
from typing import Any

import pytest
import test_source_workflow as sw

from deploy_vii import cp0_workflow, live
from deploy_vii.contracts import Module
from deploy_vii.execution import Attempt, Execution
from deploy_workflow.owners import cp1a, cp1b, cp1c, cp1d


def _build(output: str, attempt: Attempt) -> Module:
    return Module.model_validate_json(output)


CP0 = cp1a.OneStep("CP-0", "source_readiness", cp0_workflow._validate_review, _build, None)


def _begun(root: Path) -> tuple[Execution, str, str]:
    pack = sw.make_pack()
    store = Execution.create(root, pack)
    return store, store.begin("CP-0").ticket_id, sw.readiness(pack)


def _validate(store: Execution) -> Any:
    return lambda pack, current: cp0_workflow._validate_review(store, pack, current)


def _crash_at_finish(monkeypatch: pytest.MonkeyPatch, submit: Any) -> None:
    def crash(*_: object, **__: object) -> None:
        raise RuntimeError("simulated crash")

    with monkeypatch.context() as patch:
        patch.setattr(Execution, "finish", crash)
        with pytest.raises(RuntimeError, match="simulated crash"):
            submit()


def _head(store: Execution) -> Module:
    head = next(h for h in store.read().heads if h.module_id == "CP-0")
    return store.head_module(head)


def _reference(root: Path) -> Module:
    store, ticket, payload = _begun(root)
    attempt = cp1a.submit_one_step(store, ticket, CP0, payload, _validate(store))
    assert attempt.status == "finished"
    return _head(store)


def test_a_crash_before_finish_resumes_with_the_same_payload(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store, ticket, payload = _begun(tmp_path / "x")
    _crash_at_finish(
        monkeypatch, lambda: cp1a.submit_one_step(store, ticket, CP0, payload, _validate(store))
    )
    crashed = next(a for a in store.read().attempts if a.ticket_id == ticket)
    assert (crashed.status, [s.status for s in crashed.steps]) == ("pending", ["valid"])
    resumed = cp1a.submit_one_step(store, ticket, CP0, payload, _validate(store))
    assert (resumed.status, [s.status for s in resumed.steps]) == ("finished", ["valid"])
    assert _head(store) == _reference(tmp_path / "reference")


def test_a_different_payload_after_the_crash_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store, ticket, payload = _begun(tmp_path / "x")
    _crash_at_finish(
        monkeypatch, lambda: cp1a.submit_one_step(store, ticket, CP0, payload, _validate(store))
    )
    with pytest.raises(ValueError, match="already retains a different response"):
        cp1a.submit_one_step(store, ticket, CP0, payload + " ", _validate(store))


@pytest.mark.parametrize("module", [cp1b, cp1c, cp1d])
def test_each_cp1_one_step_submit_resumes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, module: Any
) -> None:
    """The module's own `submit`, pointed at CP-0's chain, settles after the crash."""
    monkeypatch.setattr(module, "MODULE_ID", "CP-0")
    monkeypatch.setattr(module, "STEP_ID", "source_readiness")
    monkeypatch.setattr(module, "_validate_step", cp0_workflow._validate_review)
    monkeypatch.setattr(module, "_candidate", _build)
    monkeypatch.setattr(module, "QUALIFICATION", None)

    def identity(schema: object, payload: str) -> tuple[str, tuple[str, ...]]:
        return payload, ()

    if module is cp1d:
        monkeypatch.setattr(live.schema, "normalise", identity)
    else:
        monkeypatch.setattr(module, "normalise", identity)
    store, ticket, payload = _begun(tmp_path / "x")
    _crash_at_finish(
        monkeypatch, lambda: module.submit(store, ticket, "source_readiness", payload, None)
    )
    done = module.submit(store, ticket, "source_readiness", payload, None)
    assert (done.journal.status, [s.status for s in done.journal.steps]) == (
        "finished",
        ["valid"],
    )
    assert _head(store) == _reference(tmp_path / "reference")


class _Spy:
    """Counts `Execution.submit_step` calls."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self.calls = 0
        real = Execution.submit_step

        def counted(*args: Any, **kwargs: Any) -> Attempt:
            self.calls += 1
            return real(*args, **kwargs)

        monkeypatch.setattr(Execution, "submit_step", counted)


def test_the_resume_does_not_journal_the_step_again_and_a_finished_ticket_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store, ticket, payload = _begun(tmp_path / "x")
    _crash_at_finish(
        monkeypatch, lambda: cp1a.submit_one_step(store, ticket, CP0, payload, _validate(store))
    )
    spy = _Spy(monkeypatch)
    cp1a.submit_one_step(store, ticket, CP0, payload, _validate(store))
    assert spy.calls == 0  # the retained valid step is settled, not submitted again
    with pytest.raises(ValueError, match="absent, finished or belongs to another module"):
        cp1a.submit_one_step(store, ticket, CP0, payload, _validate(store))
    assert spy.calls == 1  # a settled ticket takes the ordinary path, which refuses it


def test_a_different_payload_never_reaches_the_journal_or_the_validator(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store, ticket, payload = _begun(tmp_path / "x")
    _crash_at_finish(
        monkeypatch, lambda: cp1a.submit_one_step(store, ticket, CP0, payload, _validate(store))
    )
    before = store.read()
    spy = _Spy(monkeypatch)
    with pytest.raises(ValueError, match="already retains a different response"):
        cp1a.submit_one_step(store, ticket, CP0, payload + " ", _validate(store))
    assert spy.calls == 0 and store.read() == before


def test_a_ticket_of_another_module_is_refused(tmp_path: Path) -> None:
    store, ticket, payload = _begun(tmp_path / "x")
    other = cp1a.OneStep("CP-1B", "earnings_delta", CP0.validate, _build, None)
    with pytest.raises(ValueError, match="absent, finished or belongs to another module"):
        cp1a.submit_one_step(store, ticket, other, payload, _validate(store))
