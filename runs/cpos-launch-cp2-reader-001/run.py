# Produced this run folder on 2026-11-05 (ruling docs/rulings/2026-11-05-cp2-reader-test.md).
# A second run here is refused by prepare(): the manifest now also pins the retained handoffs.
"""One paid CP-2 run over TDG's accepted CP-0/CP-1/CP-1A from runs/cpos-launch-live-002.

Without --live: prepare offline, pin the three accepted handoffs as retained, check, print.
With --live: also run CP-OS; only CP-2 can call the provider. live-002 is read, never written.
"""

import hashlib
import json
import shutil
import sys
from decimal import Decimal
from pathlib import Path

from deploy_workflow.owners.cpos import run_live_handoffs
from deploy_workflow.owners.cpos_launch import MAX_OUTPUT_TOKENS, checker, prepare

ROOT = Path.cwd()
OLD = ROOT / "runs/cpos-launch-live-002"
OUT = ROOT / "runs/cpos-launch-cp2-reader-001"
RULING = ROOT / "docs/rulings/2026-11-05-cp2-reader-test.md"
CAP = Decimal("8")
RETAINED = ("CP-0", "CP-1", "CP-1A")


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


prepared = prepare(
    OLD / "context.json",
    ROOT / "data/public-corpus/v1/TDG",
    OUT,
    config="sol-medium",
    cap=CAP,
    modules=["CP-2"],
)
assert prepared.ordered == (*RETAINED, "CP-2"), prepared.ordered
manifest = json.loads(prepared.manifest.read_text())
old = json.loads((OLD / "workflow.json").read_text())
old_sources = {k: v["sha256"] for k, v in old["sources"].items()}
sources = {k: v["sha256"] for k, v in manifest["sources"].items()}
assert sources == old_sources, "source set differs from live-002; retained handoffs would be stale"
for m in RETAINED:  # Unchanged instructions, so the retained answers answered the same question.
    assert manifest["instructions"][m]["sha256"] == old["instructions"][m]["sha256"], m

completed = json.loads(next(OLD.glob("completed-*.json")).read_text())
upstream: dict[str, str] = {}
retained = {}
for m in RETAINED:
    raw = (OLD / completed["modules"][m]).read_bytes()
    copy = OUT / "retained" / f"{m}.md"
    copy.parent.mkdir(exist_ok=True)
    if not copy.exists():
        shutil.copyfile(OLD / completed["modules"][m], copy)
    assert copy.read_bytes() == raw
    retained[m] = {
        "path": f"retained/{m}.md",
        "sha256": sha(raw),
        "source_hashes": sources,
        "upstream": dict(upstream),
    }
    upstream[m] = sha(raw)
manifest["retained_handoffs"] = retained
prepared.manifest.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
print("ordered:", prepared.ordered, "hold:", prepared.hold, "cap:", CAP)
print("retained:", {m: r["sha256"][:12] for m, r in retained.items()})
print("CP-2 instructions:", manifest["instructions"]["CP-2"]["sha256"])

if "--live" in sys.argv:
    report = run_live_handoffs(
        prepared.manifest,
        prepared.directory,
        ruling=RULING,
        check=checker(prepared.layout),
        max_turns=32,
        max_output_tokens=MAX_OUTPUT_TOKENS,
        on_handoff=lambda task, _: print(f"Accepted: {task.module_id}", flush=True),
        config="sol-medium",
    )
    print("Report:", report)
