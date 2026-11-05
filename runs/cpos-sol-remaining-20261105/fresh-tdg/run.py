"""Explicit CP-OS invocation with a durable handoff review boundary; no scheduler."""

import hashlib
import json
import re
import runpy
from pathlib import Path

from deploy_workflow.handoff_delivery import plain
from deploy_workflow.markdown_delivery import literal_module
from deploy_workflow.owners.cpos import run_live_handoffs

CASE = Path(__file__).resolve().parent
CAMPAIGN = CASE.parent
ROOT = CASE.parents[2]
ORIGINAL = runpy.run_path(str(ROOT / "runs/cpos-sol-medium-20261105/run.py"))


def check(task, raw):
    issues = (
        list(ORIGINAL["check"](task, raw))
        if task.module_id in {"CP-0", "CP-1", "CP-1A", "CP-2"}
        else []
    )
    text = raw.decode()
    if task.module_id == "CP-2":
        # The inherited check reads bare Markdown cells; emphasis is presentation.
        for recipient, words in {
            "CP-3C": ("refinancing",),
            "CP-4": ("legal", "covenant"),
            "CP-6": ("committee", "challenge"),
        }.items():
            rows = [
                plain(line).lower()
                for line in text.splitlines()
                if re.match(r"^\|\s*" + re.escape(recipient) + r"\s*(?:\||/|—)", plain(line))
            ]
            issue = "Use the current registry recipient role for " + recipient
            if len(rows) == 1 and all(word in rows[0] for word in words) and issue in issues:
                issues.remove(issue)
    for name, content in task.handoffs.items():
        if hashlib.sha256(content).hexdigest() not in text:
            issues.append("Re-anchor exact current supplied handoff hash: " + name)
    data = json.loads((CASE / "workflow.json").read_bytes())
    module, _, metadata = literal_module(task.module_id, raw)
    for route in data["layout"]["routes"]:
        if route["module_id"] != task.module_id:
            continue
        kind = "table" if route["kind"] == "chart" else route["kind"]
        found = [t for t in module.tables if metadata[t.table_id] == (route["heading"], kind)]
        if len(found) != 1:
            issues.append(
                "Existing delivery selector needs exactly one populated "
                + kind
                + " under H3/H2 "
                + route["heading"]
                + ". Preserve all source values and analysis."
            )
    return tuple(issues)


class ReviewRequired(Exception):
    pass


def observe(task, raw):
    digest = hashlib.sha256(raw).hexdigest()
    reviewed = json.loads((CAMPAIGN / "verification.json").read_bytes()).get("fresh_reviews", {})
    if reviewed.get(task.module_id, {}).get("sha256") != digest:
        (CASE / (task.module_id + ".md")).write_bytes(raw)
        raise ReviewRequired(
            task.module_id + " retained for host source/instruction review: " + digest
        )


def main():
    # Use the actual shared campaign directory; budget audit refuses symlink state.
    state = CAMPAIGN
    try:
        report = run_live_handoffs(
            CASE / "workflow.json",
            state,
            ruling=ROOT / "docs/rulings/2026-11-05-remaining-modules.md",
            check=check,
            on_handoff=observe,
            max_turns=32,
            max_output_tokens=24000,
        )
        print("Verified CP-OS publication:", report)
    except ReviewRequired as error:
        print(error)


if __name__ == "__main__":
    main()
