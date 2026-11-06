"""Offline check only: the real bridge with LiveAdapter.complete replaced, so nothing is sent."""

import importlib.util
import json
import os
import sys
from pathlib import Path

REAL = Path(os.environ["CHECK_ROOT"]) / "apps/issuer-library/engine/bridge.py"
FIXTURE = Path(os.environ["CHECK_ROOT"]) / "apps/issuer-library/designs/reader-fixture/CP-1.md"
spec = importlib.util.spec_from_file_location("real_bridge", REAL)
bridge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bridge)

from deploy_workflow.model.adapter import AdapterReply, LiveAdapter
from deploy_workflow.model.turn import ToolCall, Turn, Usage

calls = []


def complete(self, request, **kwargs):
    context = json.loads(request.messages[1].text)
    job = json.loads((Path(sys.argv[2]) / "job.json").read_text())
    plan = json.loads((Path(job["workspace"]) / "runs" / job["id"] / "workflow.json").read_text())
    run = plan["run"]
    lines = [
        f"# {context['module_id']}",
        "",
        "## Request",
        f"{run['issuer_name']} as of {run['as_of']}.",
        "",
        "## Sources",
        "",
    ]
    lines += [f"- {n} {h}" for n, h in context["sources"].items()]
    lines += [f"- {n} {h['sha256']}" for n, h in context["handoffs"].items()]
    lines += ["", "## Findings", ""]
    if context["module_id"] == "CP-1":
        # The synthetic fixture holds this module's reader section and all four chart tables.
        fixture = FIXTURE.read_text(encoding="utf-8")
        lines += [fixture[fixture.index("### Reader summary") : fixture.index("## Calculations")]]
    else:
        lines += ["### Reader summary", "", "| Bottom line | Confidence | Main limitation |"]
        lines += ["| --- | --- | --- |", "| A fake engine finding only. | Low | Fake data. |", ""]
        lines += ["| Finding | Creditor impact | Confidence |", "| --- | --- | --- |"]
        lines += ["| One item was observed. | None. | Low |", ""]
    for route in plan["layout"]["routes"]:
        if route["module_id"] == context["module_id"]:
            lines += [f"### {route['heading']}", ""]
            if route["kind"] == "chart":
                continue
            lines += (
                ["| Item | Value |", "| --- | --- |", "| Observed | 0 |", ""]
                if route["kind"] == "table"
                else ["A located finding.", ""]
            )
    for heading in ("Calculations", "Gaps", "Next module"):
        lines += [f"## {heading}", "", "None.", ""]
    calls.append(context["module_id"])
    if len(calls) > int(os.environ.get("FAKE_REJECT_AFTER", "1000000")):
        lines = ["# Not a handoff"]
    turn = Turn(
        "",
        (ToolCall(str(len(calls)), "write_handoff", {"markdown": "\n".join(lines)}),),
        Usage(
            input_tokens=10,
            cached_read_tokens=0,
            cache_write_tokens=0,
            output_tokens=5,
            reasoning_tokens=0,
        ),
        "tool_use",
        "fake",
        "fake",
        200,
        billed_usd=None,
    )
    return AdapterReply("ok", turn, None, 200, None, None, 1, 2, turn.usage, billed_usd=None)


LiveAdapter.complete = complete
bridge.main()
