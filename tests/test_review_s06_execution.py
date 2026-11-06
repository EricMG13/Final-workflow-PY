"""S06 review fixes in ``deploy_vii.execution``: bounded issues, rejection staleness, replace.

Expected texts and statuses are literals; the journal fixtures are the CP-2D connect tests'.
"""

from pathlib import Path

import pytest
import test_connect_cp2d as tc

from deploy_vii import execution
from deploy_vii.contracts import Module
from deploy_vii.execution import MAX_ISSUE_CHARS, Execution, bounded_issues


def _lines(count: int) -> tuple[str, ...]:
    return tuple(f"issue {n}" for n in range(1, count + 1))


def test_bounding_a_bounded_list_keeps_its_count_and_twentieth_issue() -> None:
    once = bounded_issues(_lines(35))
    assert once == (*_lines(20), "15 further issues not listed")
    assert bounded_issues(once) == once
    assert bounded_issues(bounded_issues(once)) == once


@pytest.mark.parametrize("count", [0, 1, 20])
def test_short_lists_are_unchanged(count: int) -> None:
    assert bounded_issues(_lines(count)) == _lines(count)


def test_raw_lists_keep_the_bytes_earlier_versions_wrote() -> None:
    # The host verifier recomputes bounded_issues over a validator's raw issues.
    assert bounded_issues(_lines(21)) == (*_lines(20), "1 further issues not listed")
    long = "x" * (MAX_ISSUE_CHARS + 5)
    assert bounded_issues((long,)) == ("x" * (MAX_ISSUE_CHARS - 1) + "…",)


def test_a_21_line_list_with_an_unbounded_line_is_bounded_again() -> None:
    raw = (*_lines(19), "y" * (MAX_ISSUE_CHARS + 1), "3 further issues not listed")
    assert bounded_issues(raw) == (
        *_lines(19),
        "y" * (MAX_ISSUE_CHARS - 1) + "…",
        "1 further issues not listed",
    )


def _reject(store: Execution, module_id: str) -> None:
    attempt = store.begin(module_id)
    run = store.read().run
    candidate = Module(
        run_id=run.run_id,
        issuer_id=run.issuer_id,
        as_of=run.as_of,
        module_id=module_id,
        inputs=attempt.inputs,
        attempt=attempt.number,
    )
    finished = store.finish(attempt.ticket_id, candidate.model_dump_json(), lambda _: ("no",))
    assert finished.issues == ("no",)


def _heads(store: Execution) -> dict[str, str]:
    return {head.module_id: head.status for head in store.read().heads}


def test_a_rejected_rerun_keeps_its_consumers_current(tmp_path: Path) -> None:
    store = Execution.create(tmp_path / "store", tc.PACK)
    for module_id in ("CP-0", "CP-1A", "CP-1", "CP-2"):  # CP-1A settles before CP-1 exists
        tc._settle(store, module_id)
    # CP-1 settled, so CP-1A's inputs gain the CP-1 context and it may begin again.
    _reject(store, "CP-1A")
    assert _heads(store) == {
        "CP-0": "restricted",
        "CP-1A": "restricted",
        "CP-1": "restricted",
        "CP-2": "restricted",
    }
    with pytest.raises(ValueError, match="Input set is settled"):
        store.begin("CP-2")  # still current, so nothing to rerun


def test_a_new_head_still_stales_its_consumers(tmp_path: Path) -> None:
    store = Execution.create(tmp_path / "store", tc.PACK)
    for module_id in ("CP-0", "CP-1A", "CP-1", "CP-2"):
        tc._settle(store, module_id)
    tc._settle(store, "CP-1A")  # settles a new head with the CP-1 context bound
    assert _heads(store)["CP-2"] == "stale"
    assert store.begin("CP-2").number == 0


def test_the_current_pointer_is_swapped_with_the_retrying_replace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[tuple[str, str]] = []
    real = execution.platform_io.replace

    def spy(source: str | Path, target: str | Path) -> None:
        calls.append((Path(source).name[:5], Path(target).name))
        real(source, target)

    monkeypatch.setattr(execution.platform_io, "replace", spy)
    Execution.create(tmp_path / "store", tc.PACK)
    assert (".tmp-", "current") in calls
