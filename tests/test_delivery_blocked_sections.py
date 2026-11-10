"""D1 answer key: a report section routed from a module whose own handoff reads Blocked
(will_refuse) or Restricted (limited) carries that status and the module's reason line.

Inputs are the A-live run's own handoffs and delivery manifest (tests/fixtures/alive-d1), rebuilt
through handoff_delivery.delivery_files, the entry point that wrote that run's report-view.json.
Expected values are frozen: the reason lines are read from the fixture handoffs, and the cell
values are sha256 digests of the retained report-view.json blocks (retained-blocks.json).

The status/reason slot is a block's `note` or `state` (the renderer's existing slots); cell
content is not the slot. A reason line is compared with its `**` bold markers removed.
"""

import hashlib
import html
import json
import re
import shutil
from pathlib import Path

import pytest

from deploy_workflow.handoff_delivery import delivery_files
from deploy_workflow.handoff_outcome import actual_of

FIXTURE = Path(__file__).parent / "fixtures" / "alive-d1"
RETAINED = json.loads((FIXTURE / "retained-blocks.json").read_text())["blocks"]
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


def _reason(module: str, line: int) -> str:
    """The module's reason line (1-based `line` of its handoff), bold markers removed."""
    text = _handoff(FIXTURE, module).read_text().split("\n")[line - 1]
    return text.replace("**", "")


def _built(tmp_path: Path, ready_cp3c: bool = False) -> tuple[dict[str, dict], str]:
    root = tmp_path / "run"
    shutil.copytree(FIXTURE, root)
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


def test_fixture_handoffs_read_as_the_key_says() -> None:
    reads = {
        m: actual_of(m, _handoff(FIXTURE, m).read_text())[0]
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


@pytest.mark.parametrize("block_id", CP4_BLOCKS)
def test_cp4_blocks_carry_blocked_and_the_reason_line(alive: tuple, block_id: str) -> None:
    slot = _slot(alive[0][block_id])
    assert "Blocked" in slot
    assert _reason("CP-4", 16) in slot.replace("**", "")


@pytest.mark.parametrize("block_id", CP2D_BLOCKS)
def test_cp2d_blocks_carry_restricted_and_the_reason_line(alive: tuple, block_id: str) -> None:
    slot = _slot(alive[0][block_id])
    assert "Restricted" in slot
    assert _reason("CP-2D", 17) in slot.replace("**", "")


def test_cp5_reader_summary_carries_blocked_and_the_reason_line(alive: tuple) -> None:
    banner = re.search(r'<section id="delivery-limits".*?</section>', alive[1], re.DOTALL)
    assert banner
    items = [html.unescape(i) for i in re.findall(r"<li>(.*?)</li>", banner[0], re.DOTALL)]
    (item,) = [i for i in items if "(CP-5 line" in i]
    assert "Blocked" in item
    assert _reason("CP-5", 19) in item.replace("**", "")


def test_cell_values_are_unchanged_from_the_retained_report_view(alive: tuple) -> None:
    changed = [b for b, block in alive[0].items() if _values(block) != RETAINED[b]["values"]]
    assert alive[0].keys() == RETAINED.keys()
    assert changed == []


def test_unconfirmed_modules_get_no_status_note(alive: tuple) -> None:
    for block_id in ("maturity-wall", "refinancing-paths", "lme-creditor-exposure"):
        assert _digest(alive[0][block_id]) == RETAINED[block_id]["whole"]


def test_a_module_that_reads_ready_gets_no_status_note(tmp_path: Path) -> None:
    blocks, _ = _built(tmp_path, ready_cp3c=True)
    assert actual_of("CP-3C", _handoff(tmp_path / "run", "CP-3C").read_text())[0] == "ready"
    for block_id in ("refinancing-paths", "lme-creditor-exposure"):
        assert _digest(blocks[block_id]) == RETAINED[block_id]["whole"]
