"""Explicit environment-only CP-8 invocation over two immutable publications."""

import hashlib
from pathlib import Path

from deploy_workflow.owners.cpos import run_live_comparison

CASE = Path(__file__).resolve().parent
ROOT = CASE.parents[1]


def check(task, raw):
    return tuple(
        "Re-anchor the exact supplied delivery receipt hash for " + name
        for name in ("prior/delivery.json", "current/delivery.json")
        if hashlib.sha256(task.sources[name]).hexdigest() not in raw.decode()
    )


if __name__ == "__main__":
    print(
        run_live_comparison(
            CASE / "comparison.json",
            CASE / "execution",
            ruling=ROOT / "docs/rulings/2026-11-06-reader-cp8-comparison.md",
            check=check,
            max_turns=24,
            max_output_tokens=8000,
        )
    )
