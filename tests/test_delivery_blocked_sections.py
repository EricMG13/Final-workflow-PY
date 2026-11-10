"""D1 answer key: a report section routed from a module whose own handoff reads Blocked
(will_refuse) or Restricted (limited) carries that status and the module's reason line.

A-live tests read the retained A-live run in place (ALIVE; D1_ALIVE_COPY overrides the path) and
skip, stating why, when it is absent. They rebuild its report through
handoff_delivery.delivery_files, the entry point that wrote that run's report-view.json. Reason
lines are read from the retained handoffs; cell values are sha256 digests of the retained
report-view.json blocks (tests/fixtures/alive-d1/retained-blocks.json). The portable test at the
end runs everywhere on hand-written handoffs through the same entry point.

The status/reason slot is a block's `note` or `state` (the renderer's existing slots); cell
content is not the slot. A reason line is compared with its `**` bold markers removed.
"""

import hashlib
import html
import json
import os
import re
from pathlib import Path

import pytest

from deploy_workflow.handoff_delivery import delivery_files
from deploy_workflow.handoff_outcome import actual_of

ALIVE = Path(
    os.environ.get("D1_ALIVE_COPY")
    or "/Users/ericguei/Library/Application Support/Claude/side-session-notes/"
    "local_6dd3c4fd-b818-4b8a-8cbd-10a4368bbb28/sb2/logs/alive-copy/ws/runs/"
    "web-58d058451a6bfb7620b579bbd74b52df"
)
RETAINED = json.loads(
    (Path(__file__).parent / "fixtures" / "alive-d1" / "retained-blocks.json").read_text()
)["blocks"]
needs_alive = pytest.mark.skipif(
    not ALIVE.is_dir(), reason=f"not applicable: retained A-live run not present at {ALIVE}"
)
CP4_BLOCKS = (
    "covenant-tests-headroom",
    "red-flags",
    "lender-protection-score",
    "capacity",
    "ebitda-definition",
    "documents-structure",
)
CP2D_BLOCKS = ("liquidity-runway", "funding-gap")


def _digest(data: object) -> str:
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()


def _handoff(root: Path, module: str) -> Path:
    return next((root / "requests" / module).glob("*/1.response.md"))


def _copy_run(tmp_path: Path) -> Path:
    """The manifest and the handoffs it names, copied writable (the retained run is read-only)."""
    root = tmp_path / "run"
    manifest = next(ALIVE.glob("delivery-*.json"))
    request = json.loads(manifest.read_text())
    for spec in request["handoffs"].values():
        (root / spec["path"]).parent.mkdir(parents=True, exist_ok=True)
        (root / spec["path"]).write_bytes((ALIVE / spec["path"]).read_bytes())
    (root / "delivery.json").write_bytes(manifest.read_bytes())
    return root


def _reason(module: str, line: int) -> str:
    """The module's reason line (1-based `line` of its handoff), bold markers removed."""
    text = _handoff(ALIVE, module).read_text().split("\n")[line - 1]
    return text.replace("**", "")


def _built(tmp_path: Path, ready_cp3c: bool = False) -> tuple[dict[str, dict], str]:
    root = _copy_run(tmp_path)
    manifest = root / "delivery.json"
    if ready_cp3c:  # CP-3C states no status in the copy; give it one that reads `ready`
        path = _handoff(root, "CP-3C")
        path.write_text("---\ncommittee_status: Committee Ready\n---\n" + path.read_text())
        request = json.loads(manifest.read_text())
        request["handoffs"]["CP-3C"]["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        manifest.write_text(json.dumps(request))
    files = delivery_files(manifest)
    blocks = json.loads(files["report-view.json"])["blocks"]
    return {b["block_id"]: b for b in blocks}, files["report.html"].decode()


def _slot(block: dict) -> str:
    return f"{block.get('note') or ''} | {block['state']}"


def _values(block: dict) -> str:
    return _digest({k: v for k, v in block.items() if k not in ("note", "state")})


@needs_alive
def test_fixture_handoffs_read_as_the_key_says() -> None:
    reads = {
        m: actual_of(m, _handoff(ALIVE, m).read_text())[0]
        for m in ("CP-2D", "CP-3C", "CP-4", "CP-5")
    }
    assert reads == {
        "CP-2D": "limited",
        "CP-3C": "unconfirmed",
        "CP-4": "will_refuse",
        "CP-5": "will_refuse",
    }
    assert _reason("CP-4", 16).startswith("Gate outcome: Blocked. No executed governing credit")
    assert _reason("CP-4", 16).endswith("needed to clear that evidence gate.")
    assert _reason("CP-2D", 17).startswith("Outcome: Ready with Limitations for historical")
    assert _reason("CP-5", 19).startswith("Decision: historical findings are traceable")


@pytest.fixture(scope="module")
def alive(tmp_path_factory: pytest.TempPathFactory) -> tuple[dict[str, dict], str]:
    return _built(tmp_path_factory.mktemp("alive"))


@needs_alive
@pytest.mark.parametrize("block_id", CP4_BLOCKS)
def test_cp4_blocks_carry_blocked_and_the_reason_line(alive: tuple, block_id: str) -> None:
    slot = _slot(alive[0][block_id])
    assert "Blocked" in slot
    assert _reason("CP-4", 16) in slot.replace("**", "")


@needs_alive
@pytest.mark.parametrize("block_id", CP2D_BLOCKS)
def test_cp2d_blocks_carry_restricted_and_the_reason_line(alive: tuple, block_id: str) -> None:
    slot = _slot(alive[0][block_id])
    assert "Restricted" in slot
    assert _reason("CP-2D", 17) in slot.replace("**", "")


@needs_alive
def test_cp5_reader_summary_carries_blocked_and_the_reason_line(alive: tuple) -> None:
    banner = re.search(r'<section id="delivery-limits".*?</section>', alive[1], re.DOTALL)
    assert banner
    items = [html.unescape(i) for i in re.findall(r"<li>(.*?)</li>", banner[0], re.DOTALL)]
    (item,) = [i for i in items if "(CP-5 line" in i]
    assert "Blocked" in item
    assert _reason("CP-5", 19) in item.replace("**", "")


@needs_alive
def test_cell_values_are_unchanged_from_the_retained_report_view(alive: tuple) -> None:
    changed = [b for b, block in alive[0].items() if _values(block) != RETAINED[b]["values"]]
    assert alive[0].keys() == RETAINED.keys()
    assert changed == []


@needs_alive
def test_unconfirmed_modules_get_no_status_note(alive: tuple) -> None:
    for block_id in ("maturity-wall", "refinancing-paths", "lme-creditor-exposure"):
        assert _digest(alive[0][block_id]) == RETAINED[block_id]["whole"]


@needs_alive
def test_a_module_that_reads_ready_gets_no_status_note(tmp_path: Path) -> None:
    blocks, _ = _built(tmp_path, ready_cp3c=True)
    assert actual_of("CP-3C", _handoff(tmp_path / "run", "CP-3C").read_text())[0] == "ready"
    for block_id in ("refinancing-paths", "lme-creditor-exposure"):
        assert _digest(blocks[block_id]) == RETAINED[block_id]["whole"]


HEAD = (
    "---\nissuer_id: tdg\nmodule_id: {m}\n{status}\n---\n"
    "## Request\nScope for **TransDigm Group Incorporated**.\n\n{lead}\n"
)
TAIL = (
    "## Sources\nNone.\n## Findings\n### Financials\n"
    "| Metric | FY2024 |\n|---|---:|\n| Revenue | 1,200.0 |\n"
)
TAIL += "## Calculations\nNone.\n## Gaps\nNone.\n## Next module\nDelivery.\n"
SYNTHETIC = (  # module, block, front-matter status line, status word the block must carry, lead
    (
        "CP-4",
        "capacity",
        "qa_status: Blocked",
        "Blocked",
        "**Gate outcome: Blocked.** No executed deed.",
    ),
    (
        "CP-2D",
        "funding-gap",
        "qa_status: Restricted",
        "Restricted",
        "**Outcome: Restricted.** No forecast.",
    ),
    (
        "CP-3C",
        "refinancing-paths",
        "committee_status: Committee Ready",
        None,
        "**Outcome: Ready.** Complete.",
    ),
)


def test_synthetic_blocked_and_restricted_sections_carry_status_and_reason(tmp_path: Path) -> None:
    """Hand-written handoffs, no retained run: scope is the delivery rule only."""
    handoffs, routes = {}, []
    for module, block, status, _, lead in SYNTHETIC:
        raw = (HEAD.format(m=module, status=status, lead=lead) + TAIL).encode()
        (tmp_path / f"{module}.md").write_bytes(raw)
        handoffs[module] = {"path": f"{module}.md", "sha256": hashlib.sha256(raw).hexdigest()}
        routes.append(
            {"module_id": module, "heading": "Financials", "kind": "table", "block_id": block}
            | {"table_header": "Metric", "label": "Financials"}
        )
    manifest = tmp_path / "delivery.json"
    manifest.write_text(
        json.dumps(
            {
                "run": {
                    "run_id": "r1",
                    "issuer_id": "TDG",
                    "issuer_name": "TransDigm Group Incorporated",
                    "as_of": "2024-09-30",
                    "case_kind": "public",
                    "pathway": "covenant_refinancing",
                    "requested_modules": list(handoffs),
                },
                "handoffs": handoffs,
                "layout": {
                    "blocks": [r["block_id"] for r in routes],
                    "routes": routes,
                    "scope": "synthetic regression",
                },
            }
        )
    )
    blocks = {
        b["block_id"]: b for b in json.loads(delivery_files(manifest)["report-view.json"])["blocks"]
    }
    for module, block, status, word, lead in SYNTHETIC:
        assert actual_of(module, (tmp_path / f"{module}.md").read_text())[0] != "unconfirmed"
        slot = _slot(blocks[block])
        if word is None:  # reads ready: the label is all the note holds
            assert blocks[block]["note"] == "Financials"
            assert "Ready" not in slot.replace("Financials", "")
        else:
            assert word in slot
            assert lead.replace("**", "") in slot.replace("**", "")
