"""D1 chart case (reviewer probe d1_chart_note.py): a chart block routed from a module whose own
handoff reads Blocked carries the status and the module's reason line in its note, as a table
block from the same module does."""

import hashlib
import json
from pathlib import Path

from deploy_workflow.handoff_delivery import delivery_files

TEXT = (
    "---\nissuer_id: tdg\nmodule_id: CP-4\nqa_status: Blocked\n---\n## Request\n"
    "Scope for **TransDigm Group Incorporated**.\n\n"
    "**Gate outcome: Blocked.** No executed deed.\n"
    "## Sources\nNone.\n## Findings\n### Financials\n| Metric | FY2024 |\n|---|---:|\n"
    "| Revenue | 1,200.0 |\n### Wall\n| Period | Principal USDm |\n|---|---|\n| FY2025 | 150 |\n"
    "## Calculations\nNone.\n## Gaps\nNone.\n## Next module\nDelivery.\n"
)
RAW = TEXT.encode()


def test_chart_block_from_a_blocked_module_carries_status_and_reason(tmp_path: Path) -> None:
    (tmp_path / "CP-4.md").write_bytes(RAW)
    manifest = tmp_path / "delivery.json"
    run = {
        "run_id": "r1",
        "issuer_id": "TDG",
        "issuer_name": "TransDigm Group Incorporated",
        "as_of": "2024-09-30",
        "case_kind": "public",
        "pathway": "covenant_refinancing",
        "requested_modules": ["CP-4"],
    }
    table = {"module_id": "CP-4", "heading": "Financials", "kind": "table"}
    chart = {"module_id": "CP-4", "heading": "Wall", "kind": "chart"}
    manifest.write_text(
        json.dumps(
            {
                "run": run,
                "handoffs": {
                    "CP-4": {"path": "CP-4.md", "sha256": hashlib.sha256(RAW).hexdigest()}
                },
                "layout": {
                    "blocks": ["capacity", "maturity-wall"],
                    "scope": "synthetic regression",
                    "routes": [
                        table
                        | {"block_id": "capacity", "table_header": "Metric"}
                        | {"label": "Financials"},
                        chart
                        | {
                            "block_id": "maturity-wall",
                            "figure_id": "S.4",
                            "value_columns": ["Principal USDm"],
                            "orientation": "period-rows",
                            "chart_unit": "US$m",
                        },
                    ],
                },
            }
        )
    )
    blocks = json.loads(delivery_files(manifest)["report-view.json"])["blocks"]
    by_id = {b["block_id"]: b for b in blocks}
    assert by_id["maturity-wall"]["kind"] == "chart"
    for block_id in ("capacity", "maturity-wall"):
        note = by_id[block_id]["note"]
        assert "Blocked" in note
        assert "Gate outcome: Blocked. No executed deed." in note
