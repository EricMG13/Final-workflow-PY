"""A stale head whose inputs return to an earlier settled set gets that settled result back.

Breaks caught: after replace_pack(B) and replace_pack(A) every head is stale, and `begin` refused
the module's own earlier settled input set, so no module could run or be restored.
"""

from pathlib import Path

import pytest
import test_connect_cp3c as tc

from deploy_vii.execution import Attempt, Execution, Head, HeadRestored

PLAN = ["CP-0", "CP-1", "CP-1A", "CP-2", "CP-2D"]  # the settled modules of tc.make_store, in order


def _heads(store: Execution) -> dict[str, Head]:
    return {h.module_id: h for h in store.read().heads}


def _restore(store: Execution, module_id: str) -> Attempt:
    """`begin` on a stale head back on its settled inputs: a refusal that names the restored
    attempt (no ticket is handed to a caller that would drive it)."""
    with pytest.raises(HeadRestored) as restored:
        store.begin(module_id)
    assert isinstance(restored.value, ValueError)  # every caller's refusal path applies
    return restored.value.attempt


def _swap_and_revert(store: Execution, pack: tc.PreparedPack) -> None:
    store.replace_pack(pack.model_copy(update={"sources": pack.sources[:1]}))  # pack B
    store.replace_pack(pack)  # back to pack A, byte for byte


def test_pack_swap_and_revert_restores_every_head_without_a_new_attempt(tmp_path: Path) -> None:
    store, pack = tc.make_store(tmp_path)
    before = _heads(store)
    attempts = store.read().attempts
    assert [a.status for a in attempts] == ["finished"] * len(attempts)
    _swap_and_revert(store, pack)
    assert {h.status for h in store.read().heads} == {"stale"}
    for module_id in PLAN:  # each begin needs its upstream restored first
        returned = _restore(store, module_id)
        mine = [a for a in attempts if a.module_id == module_id]
        assert returned == mine[-1] and returned.status == "finished"
        assert _heads(store)[module_id] == before[module_id]
    # Expected: the journal is as it was before the swap. No attempt was added, and every head
    # (status, result hash, inputs, qualification, no staleness notes) is the pre-swap record.
    assert store.read().attempts == attempts
    assert _heads(store) == before
    with pytest.raises(ValueError, match="settled or its one repair"):
        store.begin("CP-0")  # idempotent: a current head still refuses its settled input set


def test_a_current_settled_head_still_refuses_begin(tmp_path: Path) -> None:
    store, _ = tc.make_store(tmp_path)
    attempts = store.read().attempts
    for module_id in PLAN:
        with pytest.raises(ValueError, match="settled or its one repair"):
            store.begin(module_id)
    assert store.read().attempts == attempts


def test_a_consumer_is_refused_until_its_upstream_is_restored(tmp_path: Path) -> None:
    store, pack = tc.make_store(tmp_path)
    _swap_and_revert(store, pack)
    with pytest.raises(ValueError, match="unrun, stale or blocked"):
        store.begin("CP-1")
    _restore(store, "CP-0")
    assert _heads(store)["CP-1"].status == "stale"  # restoring CP-0 keeps its consumers stale


def test_a_head_rerun_on_the_other_pack_is_replaced_by_the_earlier_result(tmp_path: Path) -> None:
    store, pack = tc.make_store(tmp_path)
    original = _heads(store)["CP-0"]
    store.replace_pack(pack.model_copy(update={"sources": pack.sources[:1]}))  # pack B
    tc._settle(store, "CP-0", None, True)  # a real second CP-0 attempt on pack B
    on_b = _heads(store)["CP-0"]
    assert on_b.result_sha256 != original.result_sha256 and on_b.status == "restricted"
    assert len([a for a in store.read().attempts if a.module_id == "CP-0"]) == 2
    store.replace_pack(pack)  # back to pack A: the CP-0 head (on B) is stale again
    assert _heads(store)["CP-0"].status == "stale"
    returned = _restore(store, "CP-0")
    assert returned.inputs == original.inputs and returned.status == "finished"
    # The qualification an earlier head earned is not kept on the attempt: it comes back unrun
    # (None), never invented; every other field is the original head's.
    assert original.qualification is not None
    restored = _heads(store)["CP-0"]
    assert restored == original.model_copy(update={"qualification": None})
    assert restored.notes == ()
    assert len([a for a in store.read().attempts if a.module_id == "CP-0"]) == 2  # none added


def test_a_blocked_head_from_a_failed_repair_is_restored_as_blocked(tmp_path: Path) -> None:
    # review S03S14m. CP-0 attempt 0 is rejected (no head), its repair attempt 1 is also refused:
    # settle() makes that a `blocked` head. After the pack swap and revert the stale head comes
    # back as exactly that blocked result (no qualification: head_of never gives a blocked head
    # one), and no third attempt exists.
    pack = tc.make_pack()
    store = Execution.create(tmp_path / "store", pack)
    for number in (0, 1):
        ticket = store.begin("CP-0")
        assert ticket.number == number
        store.finish(ticket.ticket_id, "not a module", lambda _: ())
    attempts = store.read().attempts
    blocked = _heads(store)["CP-0"]
    assert blocked.status == "blocked" and blocked.result_sha256 == attempts[1].result_sha256
    _swap_and_revert(store, pack)
    assert _heads(store)["CP-0"].status == "stale"
    assert _restore(store, "CP-0") == attempts[1]
    assert _heads(store)["CP-0"] == blocked and blocked.qualification is None
    assert store.read().attempts == attempts
    with pytest.raises(ValueError, match="settled or its one repair"):
        store.begin("CP-0")


def test_a_consumer_of_a_replaced_head_is_restored_with_its_qualification(tmp_path: Path) -> None:
    # review S03S14m. CP-0 is rerun on pack B (a new result), then the pack reverts: restoring
    # CP-0's pack-A result puts CP-1's inputs back on the set it settled, and CP-1 (never rerun)
    # comes back as its pre-swap head, qualification included (same result hash).
    store, pack = tc.make_store(tmp_path)
    before = _heads(store)
    store.replace_pack(pack.model_copy(update={"sources": pack.sources[:1]}))
    tc._settle(store, "CP-0", None, True)
    store.replace_pack(pack)
    attempts = store.read().attempts
    _restore(store, "CP-0")
    assert _restore(store, "CP-1") == next(a for a in attempts if a.module_id == "CP-1")
    assert _heads(store)["CP-1"] == before["CP-1"] and before["CP-1"].qualification is not None
    assert store.read().attempts == attempts
