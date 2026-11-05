"""Run one explicit retained committee repair with the shared recovery budget."""

import json
import os
import runpy
import sys
from decimal import Decimal
from pathlib import Path

from deploy_workflow.model.adapter import LiveAdapter
from deploy_workflow.model.handoff import HandoffExecutor
from deploy_workflow.model.redact import Redactor
from deploy_workflow.model.turn import ModelSpec
from deploy_workflow.owners.cpos import _handoff
from deploy_workflow.workflow import _put

RECOVERY = Path(__file__).resolve().parent
CAMPAIGN = RECOVERY.parent
ROOT = CAMPAIGN.parents[1]

if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in {"committee-wording", "quarter"}:
        raise SystemExit("Select committee-wording or quarter")
    case = RECOVERY / sys.argv[1]
    fixture = runpy.run_path(str(CAMPAIGN / "run_module.py"))
    spec, task, check = fixture["load_task"](case / "task.json")
    cap = Decimal(json.loads((RECOVERY / "workflow.json").read_bytes())["provider_cap_usd"])
    loop = HandoffExecutor(
        RECOVERY / "execution/live",
        adapter=LiveAdapter(
            ModelSpec("sol-medium", "openai", "gpt-6.1-sol", "medium"),
            ROOT / "docs/rulings/2026-11-05-remaining-modules.md",
            environ=os.environ,
        ),
        cap_usd=cap,
        check=check,
        redactor=Redactor.from_environ(os.environ),
        max_turns=24,
        max_output_tokens=20000,
    )
    raw, path = _handoff(task, case, loop, check, 1)
    _put(case / spec["output"], raw)
    print("CP-6 repair retained for source review:", path)
