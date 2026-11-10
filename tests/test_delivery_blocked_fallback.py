"""D1 follow-up (lead ruling, 2026-11-10): a Blocked module whose Request section has no bold-led
reason line carries its status and the words "reason not stated in the handoff" in the note of its
routed block; no line of the reader's own account stands in. Also the yield chart block (RV.1)
carries a Blocked module's status and reason, as a table block does."""

import hashlib
import json
from pathlib import Path
from typing import Any

from deploy_workflow.handoff_delivery import delivery_files

RUN = {
    "run_id": "r1",
    "issuer_id": "TDG",
    "issuer_name": "TransDigm Group Incorporated",
    "as_of": "2024-09-30",
    "case_kind": "public",
    "pathway": "covenant_refinancing",
    "requested_modules": ["CP-4"],
}
NO_REASON = (
    "---\nissuer_id: tdg\nmodule_id: CP-4\nqa_status: Blocked\n---\n## Request\n"
    "Scope for **TransDigm Group Incorporated** only.\n\n"
    "Nothing else is asked.\n"
    "## Sources\nNone.\n## Findings\n### Financials\n| Metric | FY2024 |\n|---|---:|\n"
    "| Revenue | 1,200.0 |\n"
    "## Calculations\nNone.\n## Gaps\nNone.\n## Next module\nDelivery.\n"
)
YIELD = (
    "---\nissuer_id: tdg\nmodule_id: CP-3\nqa_status: Blocked\n---\n## Request\n"
    "Scope for **TransDigm Group Incorporated**.\n\n"
    "**Gate outcome: Blocked.** No executed deed.\n"
    "## Sources\nNone.\n## Findings\n### Pair pricing\n"
    "| Instrument | Maturity | Price basis | Yield, % |\n|---|---|---|---:|\n"
    "| Note A | 2030-01-15 | Assume clean | 5.60 |\n"
    "| Note A | 2030-01-15 | Assume dirty | 5.70 |\n"
    "## Calculations\nNone.\n## Gaps\nNone.\n## Next module\nDelivery.\n"
)


def blocks_of(
    tmp_path: Path, module_id: str, text: str, layout: dict[str, Any], pathway: str
) -> dict[str, Any]:
    raw = text.encode()
    (tmp_path / f"{module_id}.md").write_bytes(raw)
    manifest = tmp_path / "delivery.json"
    manifest.write_text(
        json.dumps(
            {
                "run": RUN | {"requested_modules": [module_id], "pathway": pathway},
                "handoffs": {
                    module_id: {
                        "path": f"{module_id}.md",
                        "sha256": hashlib.sha256(raw).hexdigest(),
                    }
                },
                "layout": layout | {"scope": "synthetic regression"},
            }
        )
    )
    blocks = json.loads(delivery_files(manifest)["report-view.json"])["blocks"]
    return {b["block_id"]: b for b in blocks}


def test_blocked_module_without_a_reason_line_says_the_reason_is_not_stated(tmp_path: Path) -> None:
    layout = {
        "blocks": ["capacity"],
        "routes": [
            {
                "module_id": "CP-4",
                "heading": "Financials",
                "kind": "table",
                "block_id": "capacity",
                "table_header": "Metric",
                "label": "Financials",
            }
        ],
    }
    note = blocks_of(tmp_path, "CP-4", NO_REASON, layout, "covenant_refinancing")["capacity"][
        "note"
    ]
    assert "CP-4 Blocked: reason not stated in the handoff" in note
    assert "qa_status" not in note


def test_yield_chart_block_from_a_blocked_module_carries_status_and_reason(tmp_path: Path) -> None:
    layout = {
        "blocks": ["yield-against-maturity"],
        "routes": [
            {
                "module_id": "CP-3",
                "heading": "Pair pricing",
                "kind": "table",
                "block_id": "yield-against-maturity",
                "table_header": "Instrument",
            }
        ],
    }
    block = blocks_of(tmp_path, "CP-3", YIELD, layout, "relative_value")["yield-against-maturity"]
    assert block["kind"] == "chart"
    assert "CP-3 Blocked: Gate outcome: Blocked. No executed deed." in block["note"]
