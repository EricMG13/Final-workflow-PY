"""Offline check only: the real bridge with LiveAdapter.complete replaced, so nothing is sent."""

import importlib.util
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

REAL = Path(os.environ["CHECK_ROOT"]) / "apps/issuer-library/engine/bridge.py"
FIXTURE = Path(os.environ["CHECK_ROOT"]) / "apps/issuer-library/designs/reader-fixture/CP-1.md"
spec = importlib.util.spec_from_file_location("real_bridge", REAL)
bridge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bridge)

from deploy_vii.cp4_legal import DRAFT_LIMITATION
from deploy_workflow.model.adapter import AdapterReply, LiveAdapter
from deploy_workflow.model.turn import ToolCall, Turn, Usage
from deploy_workflow.owners.cpos_launch import (
    CONSUMER_SENTENCE,
    CONSUMERS,
    OPENING,
    PRO_FORMA,
    PROVISIONAL_PARAGRAPH,
)

calls = []


KEY = Path(os.environ["CHECK_ROOT"]) / "tests/fixtures/primary-pro-forma/checker-cases.json"
# Frozen cases whose expected result is accepted, one per module; FAKE_MALFORMED=CP-2 writes the
# rejected case below instead (a missing Cash row, which a model can repair by adding it).
ACCEPTED = {
    "CP-1A": "cp1a-sources-uses-valid-user-entered",
    "CP-1D": "cp1d-register-valid",
    "CP-2": "cp2-full-valid",
}
MALFORMED = {"CP-2": "cap-no-cash-row"}

# Task 10: the frozen Provisional cases (rehearsal-key.json names them). CP-4 writes the accepted
# case whose register has an executed and a draft row, or under FAKE_MALFORMED=CP-4 the rejected
# unknown-status case; the consumers write the case that labels the limitation Provisional.
PROVISIONAL_KEY = (
    Path(os.environ["CHECK_ROOT"]) / "tests/fixtures/primary-provisional/checker-cases.json"
)
CP4_CASE = "executed-plus-draft-with-limitation"
CP4_MALFORMED_CASE = "malformed-unknown-status"
CONSUMER_CASE = "cp6-upstream-draft-with-word"


def key_findings(case_id: str) -> str:
    """The frozen key's findings for one case; an unknown id raises."""
    cases = {c["id"]: c for c in json.loads(KEY.read_text(encoding="utf-8"))["cases"]}
    return str(cases[case_id]["findings"])


def pro_forma_findings(module: str, instructions: str) -> str:
    """The key's findings when the instructions carry this module's pro forma paragraph."""
    if module not in PRO_FORMA or PRO_FORMA[module] not in instructions:
        return ""
    malformed = os.environ.get("FAKE_MALFORMED") == module
    return key_findings((MALFORMED if malformed else ACCEPTED)[module]).strip()


def provisional_answer(case_id: str) -> dict[str, Any]:
    """The frozen key's answer texts for one case, DRAFT_LIMITATION filled in; unknown id raises."""
    cases = {c["id"]: c for c in json.loads(PROVISIONAL_KEY.read_text(encoding="utf-8"))["cases"]}
    given = cases[case_id]["answer"]
    return {
        k: v.replace("{DRAFT_LIMITATION}", DRAFT_LIMITATION) if v else v for k, v in given.items()
    }


def provisional_answer_for(module: str, instructions: str) -> dict[str, Any] | None:
    """The key's answer when the instructions carry this module's Provisional text, else None."""
    if module == "CP-4" and PROVISIONAL_PARAGRAPH in instructions:
        # FAKE_MALFORMED holds one module id, so CP-2 and CP-4 are never malformed together.
        malformed = os.environ.get("FAKE_MALFORMED") == module
        return provisional_answer(CP4_MALFORMED_CASE if malformed else CP4_CASE)
    if module in CONSUMERS and CONSUMER_SENTENCE in instructions:
        return provisional_answer(CONSUMER_CASE)
    return None


def handoff_markdown(context: dict[str, Any], plan: dict[str, Any], instructions: str) -> str:
    run = plan["run"]
    provisional = provisional_answer_for(context["module_id"], instructions)
    limitation = provisional["main_limitation"] if provisional else "Fake data."
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
    opening = (
        [f"### {OPENING[context['module_id']]}", "", "A fake engine view only.", ""]
        if context["module_id"] in OPENING
        else []
    )
    if context["module_id"] == "CP-1":
        # The synthetic fixture holds this module's reader section and all four chart tables; the
        # opening view goes directly after its reader summary, before the first chart table.
        fixture = FIXTURE.read_text(encoding="utf-8")
        start, charts = fixture.index("### Reader summary"), fixture.index("### Chart data:")
        lines += [fixture[start:charts].rstrip(), ""] + opening
        lines += [fixture[charts : fixture.index("## Calculations")]]
    else:
        lines += ["### Reader summary", "", "| Bottom line | Confidence | Main limitation |"]
        lines += [
            "| --- | --- | --- |",
            f"| A fake engine finding only. | Low | {limitation} |",
            "",
        ]
        lines += ["| Finding | Creditor impact | Confidence |", "| --- | --- | --- |"]
        lines += ["| One item was observed. | None. | Low |", ""] + opening
    if provisional and provisional["findings_text"]:
        lines += [provisional["findings_text"], ""]
    held = pro_forma_findings(context["module_id"], instructions)
    held_headings = set(re.findall(r"^### (.+)$", held + "\n".join(lines), re.MULTILINE))
    if held:
        lines += [held, ""]
    for route in plan["layout"]["routes"]:
        if route["module_id"] == context["module_id"] and route["heading"] not in held_headings:
            lines += [f"### {route['heading']}", ""]
            if provisional and provisional["routed_sections_text"]:
                lines += [provisional["routed_sections_text"], ""]
            if route["kind"] == "chart":
                continue
            lines += (
                ["| Item | Value |", "| --- | --- |", "| Observed | 0 |", ""]
                if route["kind"] == "table"
                else ["A located finding.", ""]
            )
    if provisional and provisional["register"]:
        lines += ["### Legal document register", "", provisional["register"], ""]
    for heading in ("Calculations", "Gaps", "Next module"):
        lines += [f"## {heading}", "", "None.", ""]
    return "\n".join(lines)


def complete(self: LiveAdapter, request: Any, **kwargs: Any) -> AdapterReply:
    context = json.loads(request.messages[1].text)
    job = json.loads((Path(sys.argv[2]) / "job.json").read_text())
    plan = json.loads((Path(job["workspace"]) / "runs" / job["id"] / "workflow.json").read_text())
    markdown = handoff_markdown(context, plan, request.messages[0].text)
    calls.append(context["module_id"])
    if len(calls) > int(os.environ.get("FAKE_REJECT_AFTER", "1000000")):
        markdown = "# Not a handoff"
    turn = Turn(
        "",
        (ToolCall(str(len(calls)), "write_handoff", {"markdown": markdown}),),
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


if __name__ == "__main__":
    adapter: Any = LiveAdapter
    adapter.complete = complete
    bridge.main()
