"""Resume the checked case with CP-OS and immutable seeded drafts."""

import hashlib
import json
import os
import runpy
from collections.abc import Mapping
from dataclasses import replace
from decimal import Decimal
from pathlib import Path

from deploy_workflow.model.adapter import LiveAdapter
from deploy_workflow.model.handoff import HandoffExecutor
from deploy_workflow.model.redact import Redactor
from deploy_workflow.model.turn import ModelSpec
from deploy_workflow.owners.cpos import HandoffPlan, HandoffTask, run_handoffs
from deploy_workflow.workflow import _put

CASE = Path(__file__).resolve().parent
CAMPAIGN = CASE.parent
ROOT = CASE.parents[2]
CHECK = runpy.run_path(str(CAMPAIGN / "fresh-tdg/run.py"))["check"]
RULING = ROOT / "docs/rulings/2026-11-05-remaining-modules.md"


class ReviewRequired(Exception):
    pass


def observe(task: HandoffTask, raw: bytes) -> None:
    digest = hashlib.sha256(raw).hexdigest()
    reviews = json.loads((CAMPAIGN / "verification.json").read_bytes())["recovery"]["reviews"]
    if reviews.get(task.module_id, {}).get("sha256") != digest:
        _put(CASE / (task.module_id + ".md"), raw)
        raise ReviewRequired(f"{task.module_id} retained for review: {digest}")


def run(environ: Mapping[str, str] | None = None) -> Path:
    manifest = CASE / "workflow.json"
    plan = HandoffPlan.model_validate_json(manifest.read_bytes())
    record = json.loads((CAMPAIGN / "verification.json").read_bytes())
    reconciled = record["recovery"]["cp6_cost_reconciliation"]
    if plan.provider_cap_usd + Decimal(reconciled["total_previous_usd"]) != Decimal(
        record["continuation_cap_usd"]
    ):
        raise ValueError("Recovery and reconciled charges must share the campaign ceiling")
    pins = json.loads((CASE / "drafts.json").read_bytes())
    if set(pins) != {"CP-1", "CP-1A", "CP-2", "CP-3", "CP-4", "CP-5"}:
        raise ValueError("All six targeted repairs require their original pinned drafts")
    drafts: dict[str, bytes] = {}
    for module, pin in pins.items():
        raw = (CASE / pin["path"]).read_bytes()
        instruction = (CASE / plan.instructions[module].path).read_bytes()
        if (
            hashlib.sha256(raw).hexdigest() != pin["sha256"]
            or pin["sha256"].encode() not in instruction
        ):
            raise ValueError(f"Seeded draft identity changed: {module}")
        drafts[module] = raw

    class SeededExecutor(HandoffExecutor):
        def __call__(self, task: HandoffTask) -> bytes:
            return super().__call__(replace(task, draft=drafts.get(task.module_id)))

    environment = os.environ if environ is None else environ
    state = CASE / "execution"
    execute = SeededExecutor(
        state / "live",
        adapter=LiveAdapter(
            ModelSpec("sol-medium", "openai", "gpt-6.1-sol", "medium"),
            RULING,
            environ=environment,
        ),
        cap_usd=plan.provider_cap_usd,
        check=CHECK,
        redactor=Redactor.from_environ(environment),
        max_turns=24,
        max_output_tokens=20000,
    )
    return run_handoffs(manifest, state, execute=execute, check=CHECK, on_handoff=observe)


if __name__ == "__main__":
    try:
        print("Verified CP-OS publication:", run())
    except ReviewRequired as error:
        print(error)
