"""Explicit paid module test launcher; offline prechecks are not analytical approval.

Run one module at a time with OPENAI_API_KEY in the launching environment.
Expected financial source observations come from the earlier frozen direct-source
extraction, never from production calculations or this run's model answer.
"""

import hashlib
import json
import os
import re
import sys
from decimal import Decimal
from pathlib import Path

from deploy_vii.contracts import Run
from deploy_workflow.model.adapter import LiveAdapter
from deploy_workflow.model.handoff import HandoffExecutor
from deploy_workflow.model.redact import Redactor
from deploy_workflow.model.turn import ModelSpec
from deploy_workflow.owners.cpos import HandoffTask
from deploy_workflow.workflow import _put

root = Path(__file__).resolve().parents[2]
case = Path(__file__).resolve().parent
inputs = json.loads((case / "inputs.json").read_text())


def check(task, raw):
    module = task.module_id
    text = raw.decode()
    issues = []
    for term in ("TransDigm", "2024"):
        if term not in text:
            issues.append("Re-anchor issuer and historical period explicitly: " + term)
    if module == "CP-0":
        for term in ("105", "106", "109", "GAAP", "million", "ready"):
            if term.lower() not in text.lower():
                issues.append("Source readiness is missing required located detail: " + term)
        if "visual" not in text.lower():
            issues.append(
                "State visual fidelity was not verified with the supplied text-only tools."
            )
    if module == "CP-1":
        from deploy_workflow.handoff_delivery import HandoffInput, ModelDelivery
        from deploy_workflow.model_handoff_delivery import _annual_cells, _AnnualReader

        layout = ModelDelivery.model_validate_json(json.dumps(inputs["model"]))
        try:
            reader = _AnnualReader(
                raw, HandoffInput(path="CP-1.md", sha256=hashlib.sha256(raw).hexdigest()), layout
            )
            reader.validate()
            _annual_cells(reader)
            frozen = json.loads(
                (root / "runs/cpos-tdg-fresh-001/source-observations.json").read_text()
            )
            for table_name in ("income", "cash", "balance"):
                headers, rows = reader.selected(table_name)
                columns = (
                    ["Sep 30, 2024", "Sep 30, 2023"]
                    if table_name == "balance"
                    else ["FY2024", "FY2023", "FY2022"]
                )
                for source_row in frozen[table_name]["rows"]:
                    aliases = {
                        "Basic and diluted weighted-average shares outstanding": "Weighted-average shares outstanding: Basic and diluted",
                        "(Gain) loss on settlement of the Esterline Retirement Plan": "(Gain) loss on settlement of the Esterline Retirement Plan (the “ERP”)",
                        "Common stock": "Common stock—$.01 par value",
                    }
                    labels = {source_row[0], aliases.get(source_row[0], source_row[0])}

                    def label_key(value):
                        return "".join(c for c in value.casefold() if c.isalnum())

                    matches = [
                        r[2]
                        for r in rows
                        if label_key(r[2][0]) in {label_key(label) for label in labels}
                    ]
                    if len(matches) != 1:
                        issues.append("Missing/duplicate source row: " + source_row[0])
                        continue
                    actual = [matches[0][headers.index(c)] for c in columns]
                    if actual != source_row[1:]:
                        issues.append(
                            "Source-literal mismatch in "
                            + table_name
                            + " / "
                            + source_row[0]
                            + ": preserve the original period columns, signs and glyphs; reread source page "
                            + str(frozen[table_name]["page"])
                        )
            # Complete primary-statement coverage, separately from the Model's selected rows.
            all_rows = [
                [cell.strip() for cell in line.strip("|").split("|")]
                for line in text.splitlines()
                if line.startswith("|")
            ]
            for expected in frozen["comprehensive"]["rows"]:
                matching = [
                    row
                    for row in all_rows
                    if len(row) >= 4
                    and row[0].casefold() == expected[0].casefold()
                    and row[1:4] == expected[1:]
                ]
                if not matching:
                    issues.append(
                        "Comprehensive-income source row missing/different: " + expected[0]
                    )
            equity = [
                row
                for row in all_rows
                if len(row) == 12
                and row[2:11] in [expected[1:] for expected in frozen["equity"]["rows"]]
            ]
            if [row[2:11] for row in equity] != [
                expected[1:] for expected in frozen["equity"]["rows"]
            ]:
                issues.append(
                    "Retain all 31 equity rows in source order with the instructed 12-column layout; preserve actual share counts, monetary amounts, signs and source dashes."
                )
        except (ValueError, KeyError) as error:
            issues.append("Existing Model input adapter refused: " + str(error))
    if module == "CP-1A":
        for heading in (
            "Company, business and revenue model",
            "Ownership and control",
            "Transaction and capital allocation summary",
            "Timeline and governance behavior (absorbed CP-2C)",
        ):
            if text.count("### " + heading) != 1:
                issues.append("Existing report selector needs exactly one H3 heading: " + heading)
        for recipient, required in {
            "CP-3C": ("refinancing",),
            "CP-4": ("legal", "covenant"),
            "CP-6": ("committee", "challenge"),
        }.items():
            matches = [
                line.lower()
                for line in text.splitlines()
                if re.match(r"^\|\s*" + re.escape(recipient) + r"\s*(?:\||/|—)", line)
            ]
            if len(matches) != 1 or any(word not in matches[0] for word in required):
                issues.append(
                    "Consumer row must reflect current registry role for "
                    + recipient
                    + ": "
                    + ", ".join(required)
                )
    if module == "CP-2":
        for token in (
            "**Assessment —",
            "**Thesis —",
            "### Ranked strengths, weaknesses and key risks",
            "**Strengths**",
            "**Weaknesses**",
        ):
            if token not in text:
                issues.append("Existing report selector requires: " + token)
        for upstream in ("CP-1", "CP-1A"):
            if hashlib.sha256(task.handoffs[upstream]).hexdigest() not in text:
                issues.append("Retain the supplied current handoff hash for " + upstream)
        for recipient, words in {
            "CP-3C": ("refinancing",),
            "CP-4": ("legal", "covenant"),
            "CP-6": ("committee", "challenge"),
        }.items():
            rows = [
                line.lower()
                for line in text.splitlines()
                if re.match(r"^\|\s*" + re.escape(recipient) + r"\s*(?:\||/|—)", line)
            ]
            if len(rows) != 1 or any(word not in rows[0] for word in words):
                issues.append("Use the current registry recipient role for " + recipient)
    if module in {"CP-1", "CP-1A", "CP-2"}:
        from deploy_workflow.handoff_delivery import mapped_module

        try:
            mapped_module(module, raw)
        except ValueError as error:
            issues.append("Existing report input adapter refused: " + str(error))
    return tuple(issues)


def main():
    environment = dict(os.environ)
    if not environment.get("OPENAI_API_KEY"):
        raise RuntimeError("Launch with OPENAI_API_KEY; this script never reads credential files")
    ruling = root / "docs/rulings/2026-11-05-live-loop-tests.md"
    module = sys.argv[1]
    if module == "orchestrate":
        from deploy_workflow.owners.cpos import run_live_handoffs

        print(
            run_live_handoffs(
                case / "workflow.json",
                case,
                ruling=ruling,
                check=check,
                environ=environment,
                max_turns=32,
                max_output_tokens=32000,
            ),
            flush=True,
        )
        return
    order = ["CP-0", "CP-1", "CP-1A", "CP-2"]
    if module not in order:
        raise ValueError("Select CP-0, CP-1, CP-1A, CP-2 or orchestrate")
    sources = {}
    for name, spec in inputs["sources"].items():
        raw = (case / spec["path"]).read_bytes()
        if hashlib.sha256(raw).hexdigest() != spec["sha256"]:
            raise RuntimeError("source hash changed")
        sources[name] = raw
    upstreams = {
        name: (case / inputs.get("handoffs", {}).get(name, f"{name}.md")).read_bytes()
        for name in order[: order.index(module)]
    }
    adapter = LiveAdapter(
        ModelSpec("sol-medium", "openai", "gpt-6.1-sol", "medium"), ruling, environ=environment
    )
    loop = HandoffExecutor(
        case / "live",
        adapter=adapter,
        cap_usd=Decimal(10),
        check=check,
        redactor=Redactor.from_environ(environment),
        max_turns=32,
        max_output_tokens=32000,
    )
    task = HandoffTask(
        Run.model_validate_json(json.dumps(inputs["run"])),
        module,
        (case / f"{module}-instructions.md").read_bytes(),
        sources,
        upstreams,
        1,
        (),
    )
    print("START", module, flush=True)
    answer = loop(task)
    _put(case / f"{module}.md", answer)
    print(
        "RETAINED",
        module,
        "bytes",
        len(answer),
        "budget_charged_usd",
        str(loop.budget.spent),
        "manual source/instruction review pending",
        flush=True,
    )


if __name__ == "__main__":
    main()
