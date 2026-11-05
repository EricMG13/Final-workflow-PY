"""Explicit single-module test command, using the existing CP-OS exchange.

This is a campaign fixture, not an orchestration layer. The caller selects one
task; broader workflow ordering/publication remains CP-OS's responsibility.
Launch with OPENAI_API_KEY. No credential-file access or automatic next module.
"""

import hashlib
import json
import os
import sys
from decimal import ROUND_HALF_EVEN, Decimal, localcontext
from fractions import Fraction
from pathlib import Path
from tempfile import TemporaryDirectory
from types import MappingProxyType

from pydantic import TypeAdapter

from deploy_vii.contracts import Run
from deploy_workflow.handoff_delivery import (
    DeliveryRequest,
    HandoffInput,
    MarkdownLayout,
    section,
    table,
)
from deploy_workflow.markdown_delivery import markdown_files
from deploy_workflow.model.adapter import LiveAdapter
from deploy_workflow.model.handoff import HandoffExecutor
from deploy_workflow.model.redact import Redactor
from deploy_workflow.model.turn import ModelSpec
from deploy_workflow.owners.cpos import HandoffTask, _handoff, _pinned_inputs
from deploy_workflow.workflow import _put

CAMPAIGN = Path(__file__).resolve().parent
ROOT = CAMPAIGN.parents[1]


def load_task(path):
    spec = json.loads(path.read_bytes())

    def pinned(entries):
        return _pinned_inputs(
            path.parent, TypeAdapter(dict[str, HandoffInput]).validate_json(json.dumps(entries))
        )

    task = HandoffTask(
        Run.model_validate_json(json.dumps(spec["run"])),
        spec["module_id"],
        pinned({"instruction": spec["instructions"]})["instruction"],
        MappingProxyType(pinned(spec["sources"])),
        MappingProxyType(pinned(spec["handoffs"])),
        1,
        (),
        draft=None if not spec.get("draft") else pinned({"draft": spec["draft"]})["draft"],
    )
    expected = json.loads((path.parent / spec["checks"]).read_bytes())
    layout = (
        None
        if not spec.get("layout")
        else MarkdownLayout.model_validate_json((path.parent / spec["layout"]).read_bytes())
    )

    def check(current, raw):
        text = raw.decode()
        issues = []
        for name, content in current.handoffs.items():
            if hashlib.sha256(content).hexdigest() not in text:
                issues.append("Re-anchor the supplied exact current handoff hash for " + name)
        for term in expected.get("required_terms", []):
            if term.casefold() not in text.casefold():
                issues.append("Preserve the supplied scope/period/definition: " + term)
        for grid in expected.get("numeric_tables", []):
            try:
                headers, rows = table(section(text.splitlines(), grid["heading"]))
                assert headers == grid["columns"]
                assert len(rows) == len(grid["rows"])
                for (_, _, actual), wanted in zip(rows, grid["rows"], strict=True):
                    assert actual[0] == wanted[0], "Source period/order mismatch"
                    assert all(
                        a == w if w == "—" else Fraction(a) == Fraction(w)
                        for a, w in zip(actual[1:], wanted[1:], strict=True)
                    ), "Source or independent calculation mismatch at " + wanted[0]
            except (AssertionError, ValueError, ArithmeticError) as error:
                issues.append(grid["heading"] + ": " + str(error))
        if current.module_id == "CP-1B":
            try:
                headers, rows = table(
                    section(text.splitlines(), "Financial performance / comparator register")
                )
                assert headers[:5] == ["Metric", "Prior", "Current", "Absolute change", "Change %"]
                for label, (prior, latest) in expected["pairs"].items():
                    matches = [r[2] for r in rows if r[2][0] == label]
                    if len(matches) != 1:
                        issues.append("Retain exactly one comparison row: " + label)
                        continue
                    values = matches[0][1:5]
                    delta = Fraction(latest) - Fraction(prior)
                    growth = delta / Fraction(prior) * 100
                    with localcontext() as context:
                        context.prec = 60
                        percent = (
                            Decimal(growth.numerator) / Decimal(growth.denominator)
                        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)
                    if (
                        Fraction(values[0]) != Fraction(prior)
                        or Fraction(values[1]) != Fraction(latest)
                        or Fraction(values[2]) != delta
                        or not values[3].endswith("%")
                        or Decimal(values[3][:-1]) != percent
                    ):
                        issues.append(
                            "Source/independent arithmetic mismatch in "
                            + label
                            + "; reread the source and use calculate, preserving the signed original pair."
                        )
            except (AssertionError, ValueError, ArithmeticError) as error:
                issues.append("Comparator structure/number check refused: " + str(error))
        if layout is not None:
            try:
                with TemporaryDirectory() as temporary:
                    base = Path(temporary)
                    (base / "answer.md").write_bytes(raw)
                    request = DeliveryRequest(
                        run=current.run,
                        handoffs={
                            current.module_id: HandoffInput(
                                path="answer.md", sha256=hashlib.sha256(raw).hexdigest()
                            )
                        },
                        layout=layout,
                    )
                    markdown_files(request, base)
            except ValueError as error:
                issues.append("Existing delivery adapter refused: " + str(error))
        return tuple(issues)

    return spec, task, check


def main():
    path = Path(sys.argv[1]).resolve()
    spec, task, check = load_task(path)
    environment = dict(os.environ)
    if not environment.get("OPENAI_API_KEY"):
        raise RuntimeError("Explicit paid launch requires OPENAI_API_KEY in the environment")
    loop = HandoffExecutor(
        CAMPAIGN / "live",
        adapter=LiveAdapter(
            ModelSpec("sol-medium", "openai", "gpt-6.1-sol", "medium"),
            ROOT / "docs/rulings/2026-11-05-remaining-modules.md",
            environ=environment,
        ),
        cap_usd=Decimal(25),
        check=check,
        redactor=Redactor.from_environ(environment),
        max_turns=32,
        max_output_tokens=24000,
    )
    print("START", task.run.run_id, task.module_id, flush=True)
    raw, retained_path = _handoff(task, path.parent, loop, check, 1)
    _put(path.parent / spec["output"], raw)
    print(
        "RETAINED",
        retained_path,
        "charged_usd",
        str(loop.budget.spent),
        "manual source/instruction review and consumption still required",
        flush=True,
    )


if __name__ == "__main__":
    main()
