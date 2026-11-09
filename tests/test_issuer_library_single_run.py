"""single_run: the walk's per-run expectations, read from a run's own files, equal the key."""

import json
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DESIGNS = ROOT / "apps/issuer-library/designs"
sys.path.insert(0, str(DESIGNS))
import single_run

FOLDER = "cpos-launch-cp2-reader-001"
KEY = json.loads((DESIGNS / "single-run-answer-key.json").read_text())


@pytest.fixture(scope="module")
def found(tmp_path_factory: pytest.TempPathFactory) -> dict:
    ws = tmp_path_factory.mktemp("ws")
    (ws / "runs").mkdir()
    shutil.copytree(ROOT / "runs" / FOLDER, ws / "runs" / FOLDER)  # the source stays read-only
    return single_run.expectations(ws, FOLDER)


def test_run_values_equal_the_key(found: dict) -> None:
    run = KEY["run"]
    assert found["folder_id"] == run["folder_id"]["value"]
    assert found["issuer_name"] == run["issuer_name"]["value"]
    assert found["as_of"] == run["as_of"]["value"]
    assert found["title"] == run["pathway_title"]["value"]
    assert found["modules"] == run["run_modules_in_order"]["value"]


def test_modules_and_delivery_equal_the_key(found: dict) -> None:
    assert found["module_titles"] == [m["title"]["value"] for m in KEY["modules"]]
    for module in KEY["modules"]:
        assert found["handoffs"][f"{module['module_id']}.md"] == module["handoff_sha256"]["value"]
    assert found["delivery_id"] == KEY["delivery"]["delivery_id"]["value"]
    built = KEY["delivery"]["built_from_files"]["value"]
    assert found["handoffs"] == {n: h for n, h in built.items() if n.startswith("CP-")}
    assert all(found["handoff_bytes_match"].values())


def test_evidence_line_equals_the_key(found: dict) -> None:
    want = KEY["evidence"]
    got = found["evidence"][0]
    assert got["module"] == want["handoff"]["value"]
    assert got["file"] == want["cited_source_name"]["value"]
    assert got["line"] == int(want["locator"]["value"].removeprefix("line "))
    assert got["key"] == f"{FOLDER}/deliveries/{found['delivery_id']}/CP-2.md:9"
    assert len({e["key"] for e in found["evidence"]}) == len(found["evidence"])
    # the key's cells: its line text split the way the inspector shows them
    cells = [c.strip() for c in want["line_text"]["value"].strip("|").split("|") if c.strip()]
    assert got["cells"] == cells
    assert want["issuer_source_named_on_that_line"]["value"]["name"] in got["cells"]


def test_the_keys_fact_is_among_those_citing_that_line(tmp_path: Path) -> None:
    view = json.loads(next((ROOT / "runs" / FOLDER).glob("deliveries/*/view.json")).read_text())
    module = next(
        m for m in view["modules"] if m["module_id"] == KEY["evidence"]["handoff"]["value"]
    )
    citing = [
        f["fact_id"]
        for f in module["facts"]
        if any(c["locator"] == KEY["evidence"]["locator"]["value"] for c in f["citations"])
    ]
    assert KEY["evidence"]["fact_id"]["value"] in citing


def test_the_fixture_records_no_events_and_no_spend(found: dict) -> None:
    activity = KEY["activity"]
    assert activity["events_jsonl_present"]["value"] is False
    assert found["activity"] == {"events": None, "spent_usd": None}  # missing is not zero


def test_a_missing_delivery_or_file_is_named_not_defaulted(tmp_path: Path) -> None:
    (tmp_path / "runs" / "r").mkdir(parents=True)
    with pytest.raises(single_run.Unreadable, match="cannot read"):
        single_run.expectations(tmp_path, "r")
    (tmp_path / "runs" / "r" / "workflow.json").write_text("{}")
    with pytest.raises(single_run.Unreadable, match="expected one delivery"):
        single_run.expectations(tmp_path, "r")


def test_events_and_spend_come_from_the_runs_own_log_and_status(tmp_path: Path) -> None:
    run = tmp_path / "runs" / "web-1"
    run.mkdir(parents=True)
    (run / "events.jsonl").write_text('{"event": "module_started"}\n{"event": "delivered"}\n')
    (tmp_path / "intake/a").mkdir(parents=True)
    (tmp_path / "intake/a/status.json").write_text('{"run_id": "web-1", "spent_usd": "0.0005"}')
    (tmp_path / "intake/b").mkdir()
    (tmp_path / "intake/b/status.json").write_text('{"run_id": "web-2", "spent_usd": "9"}')
    found = single_run.activity_of(tmp_path, run)
    assert [e["event"] for e in found["events"]] == ["module_started", "delivered"]
    assert found["spent_usd"] == "0.0005"
