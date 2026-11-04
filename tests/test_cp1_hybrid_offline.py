"""CP-1 hybrid, offline end-to-end (CP1H T8): ``_run_pathway(through="CP-1")`` over the o2 case.

One scripted run through the real ToolLoop and OwnerWorkflow, with no network. The frozen o2
payloads drive CP-0 and the five CP-1 steps; the script then departs from them in three places
that the hybrid tickets changed (a malformed-JSON call, a same-step financials repair, the turn
nudge). A second run freezes CP-0 and runs CP-1 again.

Coverage gap, by design: no earnings_update fixture is scripted (the frozen o2 payloads bind the
portfolio pack), so this proves the harness path on ``portfolio_decision``, not the SHC pack.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import o2_case
import pytest

from deploy_vii.execution import Execution
from deploy_workflow import replay
from deploy_workflow import run_pathway as rp
from deploy_workflow.model import loop as loop_module
from deploy_workflow.model.adapter import AdapterReply, recorded_adapter
from deploy_workflow.model.turn import (
    Message,
    ToolCall,
    Turn,
    TurnRequest,
    dump_json,
    turn_to_json,
)
from deploy_workflow.owner_workflow import AUDIT
from deploy_workflow.run_inputs import CheckedRun, check_arguments, stage_sources

CP0_CP1_STEPS = (
    "source_readiness",
    "source_context",
    "financials",
    "narrative",
    "readiness",
    "quality",
)
BAD_JSON = "error: bad arguments: invalid JSON"
REOPENED = (
    "\nHarness: this step is reopened for one correction; reads before this point no longer "
    "count, so read again every page you cite and extract the statements again"
    " and run search_pack again before any absence claim."
)
SMALL_BUDGET = 5  # model requests per step for this test only; the nudge starts at 3 left


@dataclass(frozen=True)
class Seen:
    step_id: str
    call_index: int
    messages: tuple[Message, ...]


class Scenario(o2_case.ScriptAdapter):
    """The o2 script, plus the departures the test needs. Every request is kept for the asserts.

    - source_context, request 0: a call with malformed argument JSON beside two searches;
      request 1: one more search; request 2: the frozen plan (searches and the valid submit).
    - financials, request 0: the frozen extraction and then an empty (invalid) submit; request 1:
      the frozen plan again (the model re-extracts and submits the frozen payload).
    Everything else is the frozen plan, answered by ``ScriptAdapter`` itself.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.seen: list[Seen] = []

    def complete(
        self, request: TurnRequest, *, invocation_digest: str, call_index: int, reservation_id: str
    ) -> AdapterReply:
        step_id = [t.name for t in request.tools if t.name.startswith("submit_")][-1]
        step_id = step_id.removeprefix("submit_")
        self.seen.append(Seen(step_id, call_index, tuple(request.messages)))
        plan: list[tuple[str, dict[str, Any], str | None]] | None = None
        search = [("search_pack", {"query": q, "source_id": i}) for i, q in o2_case.SEARCHES]
        if step_id == "source_context" and call_index == 0:
            plan = [
                ("search_pack", {}, "invalid JSON"),
                *[(n, a, None) for n, a in search],
            ]
        elif step_id == "source_context" and call_index == 1:
            plan = [(search[0][0], search[0][1], None)]
        elif step_id == "financials" and call_index == 0:
            frozen = o2_case.frozen_financials()
            calls = [(c["tool"], dict(c["arguments"]), None) for c in frozen["tool_calls"]]
            plan = [*calls, ("submit_financials", {}, None)]
        if plan is None:
            return super().complete(
                request,
                invocation_digest=invocation_digest,
                call_index=call_index,
                reservation_id=reservation_id,
            )
        calls_out = tuple(
            ToolCall(
                f"call-{invocation_digest[:12]}-{call_index}-{n}",
                name,
                arguments,
                bad_arguments=bad,
            )
            for n, (name, arguments, bad) in enumerate(plan)
        )
        turn = Turn(
            "",
            calls_out,
            o2_case.USAGE,
            "tool_use",
            self._model.model,
            f"o2-{invocation_digest[:12]}",
            200,
        )
        line = {
            "invocation_digest": invocation_digest,
            "call_index": call_index,
            "response": turn_to_json(turn),
        }
        with self._file.open("a", encoding="utf-8") as handle:
            handle.write(dump_json(line) + "\n")
        usage = o2_case.USAGE
        return AdapterReply(
            "ok", turn, None, 200, None, None, o2_case.STARTED, o2_case.FINISHED, usage, None
        )


def _checked(root: Path, run_id: str) -> tuple[CheckedRun, Path]:
    empty = root / "check-recordings"
    empty.mkdir(parents=True, exist_ok=True)
    run_dir = root / "run"
    checked = check_arguments(
        case_id=o2_case.CASE_ID,
        sources=o2_case.case_sources(),
        context=o2_case.CASE / "context.json",
        pathway=o2_case.PATHWAY,
        model=o2_case.MODEL,
        adapter=recorded_adapter(o2_case.MODEL, empty),
        cap_usd=o2_case.CAP,
        run_dir=run_dir,
        run_id=run_id,
    )
    return checked, run_dir


def _statuses(run_dir: Path) -> dict[str, str]:
    return {h.module_id: h.status for h in Execution(run_dir / "execution").read().heads}


def _run_json(run_dir: Path) -> dict[str, Any]:
    loaded: dict[str, Any] = json.loads((run_dir / "run.json").read_text())
    return loaded


def _tool_status(message: Message) -> str:
    """The ``status`` the harness reported in a submit's tool message (before any Harness line)."""
    status: str = json.loads(message.text.split("\nHarness:")[0])["status"]
    return status


def _steps(seen: list[Seen], step_id: str) -> list[Seen]:
    return [s for s in seen if s.step_id == step_id]


def test_through_cp1_end_to_end_with_a_bad_json_call_a_financials_repair_a_nudge_and_a_rerun(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(loop_module, "MAX_TURNS", SMALL_BUDGET)
    first = tmp_path / "first"
    (first / "recordings").mkdir(parents=True)
    (first / "check").mkdir()
    checked, run_dir = o2_case._prepare(first, recorded_adapter(o2_case.MODEL, first / "check"))
    script = Scenario(first / "recordings", CP0_CP1_STEPS, run_dir / "execution", o2_case.MODEL)
    outcome = rp._run_pathway(checked, run_dir, script, o2_case.test_prompt_for, through="CP-1")

    # (5) the run ends "stopped" with through: CP-1; CP-0 and CP-1 settled; CP-1A pending; no
    # CP-MODEL publish and no owner receipt.
    assert outcome.outcome == "stopped" and outcome.stopped_reason == "through: CP-1"
    assert _run_json(run_dir)["stopped_reason"] == "through: CP-1"
    statuses = _statuses(run_dir)
    assert set(statuses) == {"CP-0", "CP-1"}
    # (1) both modules settle on the frozen payloads, each with a "restricted" head.
    assert statuses == {"CP-0": "restricted", "CP-1": "restricted"}
    assert not (run_dir / "owner-run.json").exists()
    published = run_dir / "publication"
    assert not published.exists() or not any(published.iterdir())

    seen = script.seen
    # The steps ran in walk order, each once (a same-step repair stays in its step).
    order = [s.step_id for i, s in enumerate(seen) if i == 0 or seen[i - 1].step_id != s.step_id]
    assert order == list(CP0_CP1_STEPS)

    # (2) the malformed-JSON call is answered with the error, in place, and the run continues.
    context = _steps(seen, "source_context")
    assert [s.call_index for s in context] == [0, 1, 2]
    first_bad = next(m for m in context[1].messages if m.text == BAD_JSON)
    assert first_bad.role == "tool" and (first_bad.tool_call_id or "").endswith("-0-0")
    assert [m.role for m in context[1].messages].count("system") == 1

    # (4) the nudge: with 5 requests allowed, 3 remain after request 1 (index 1), not before.
    nudge = "\nHarness: 3 of 5 calls remain in this step; the step must end with"
    assert nudge in context[2].messages[-1].text
    assert context[2].messages[-1].text.endswith("submit_source_context.")
    assert not any("calls remain" in m.text for m in context[1].messages)

    # (3) financials: the first submit is invalid; the next request continues the SAME
    # conversation, with the reopen line, no REPAIR block, one system message; then it is valid.
    money = _steps(seen, "financials")
    assert [s.call_index for s in money] == [0, 1]
    again = money[1].messages
    assert again[: len(money[0].messages)] == money[0].messages  # the same opening, kept whole
    assert [m.role for m in again].count("system") == 1
    reopened = again[-1]
    assert reopened.role == "tool" and _tool_status(reopened) == "invalid"
    assert reopened.text.endswith(REOPENED)
    assert "and extract the statements again" in reopened.text
    assert not any("REPAIR" in m.text for m in again)
    # The same repair, read directly from the journal: one CP-1 attempt, the invalid financials
    # submit recorded as a step repair, and the financials step valid in the end.
    snap = Execution(run_dir / "execution").read()
    cp1 = [a for a in snap.attempts if a.module_id == "CP-1"]
    assert len(cp1) == 1
    assert [(x.step_id, x.status) for x in cp1[0].step_repairs] == [("financials", "invalid")]
    assert ("financials", "valid") in [(x.step_id, x.status) for x in cp1[0].steps]


    # (6) second run: CP-0 replayed from the first, CP-1 run again on the script.
    second = tmp_path / "second"
    checked2, run_dir2 = _checked(second, "o2-synthetic-rerun")
    found = replay.check_replay(checked2, run_dir2, run_dir, frozenset({"CP-1"}))
    assert found.replayed == ("CP-0",) and found.unreplayable == ()
    stage_sources(checked2, run_dir2)
    (second / "recordings").mkdir()
    steps = CP0_CP1_STEPS[1:]
    rerun = Scenario(second / "recordings", steps, run_dir2 / "execution", o2_case.MODEL)
    again_out = rp._run_pathway(
        checked2, run_dir2, rerun, o2_case.test_prompt_for, replay=found, through="CP-1"
    )
    sent = {s.step_id for s in rerun.seen}
    assert rerun.seen and "source_readiness" not in sent  # no CP-0 request
    assert "source_context" in sent  # CP-1 ran again on the script
    live = run_dir2 / "execution" / AUDIT / "replays"
    schemas = [json.loads(p.read_bytes())["schema_version"] for p in sorted(live.iterdir())]
    assert schemas == ["replay/1"]  # one record, for CP-0; no replay-live/1 record
    # Fixture limit (CP1H-R11a): the frozen o2 CP-1 payloads bind the first run's run_id, so the
    # rerun's CP-1 head is blocked and the stop reason says so.
    unsettled = "through CP-1: the module did not settle (head: blocked)"
    assert again_out.outcome == "stopped" and again_out.stopped_reason == unsettled
    assert _run_json(run_dir2)["stopped_reason"] == unsettled
    assert _statuses(run_dir2) == {"CP-0": "restricted", "CP-1": "blocked"}

