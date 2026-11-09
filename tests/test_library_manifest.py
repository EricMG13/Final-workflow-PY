"""Manifest writer against the hand-written answer key (tests/fixtures/library-manifest/writer)."""

import copy
import importlib.util
import json
import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
KEYS = ROOT / "tests/fixtures/library-manifest/writer"
spec = importlib.util.spec_from_file_location(
    "library_manifest", ROOT / "apps/issuer-library/engine/library_manifest.py"
)
lm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lm)
CASES = ["synthetic", "retained", "edge"]


def workspace(case: str, tmp_path: Path) -> tuple[Path, str]:
    shutil.copytree(KEYS / case / "workspace", tmp_path, dirs_exist_ok=True)
    plan = KEYS / case / "copy.json"
    for item in json.loads(plan.read_text()) if plan.exists() else []:
        source = ROOT / item["from"]
        if not source.is_file():
            pytest.skip(f"{item['from']} is absent")
        (tmp_path / item["to"]).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, tmp_path / item["to"])
    (run_id,) = [p.name for p in (tmp_path / "runs").iterdir()]
    return tmp_path, run_id


def key(case: str) -> dict:
    return json.loads((KEYS / case / "expected-library.json").read_text())


def without_chart_rows(manifest: dict) -> dict:
    manifest = copy.deepcopy(manifest)
    manifest["run"]["metrics"] = {}
    manifest["sources"] = {k: v for k, v in manifest["sources"].items() if not k.startswith("cp1_")}
    return manifest


@pytest.mark.parametrize("case", CASES)
def test_build_matches_key_except_chart_rows(case, tmp_path):
    root, run_id = workspace(case, tmp_path)
    assert lm.build(root, run_id) == without_chart_rows(key(case))


@pytest.mark.xfail(strict=True, reason="R-24: chart-row rule awaits the owner")
@pytest.mark.parametrize("case", CASES)
def test_build_matches_full_key(case, tmp_path):
    root, run_id = workspace(case, tmp_path)
    assert lm.build(root, run_id) == key(case)


@pytest.mark.parametrize("case", CASES)
def test_row_metrics_match_key(case, tmp_path):
    root, run_id = workspace(case, tmp_path)
    expected = key(case)
    doc = lm._doc(root, f"runs/{run_id}/CP-1.md")
    tables, got = lm._chart_rows(doc), {}
    for table in [k for k in expected["sources"] if k.startswith("cp1_")]:
        pinned = expected["sources"][table]
        (row,) = [r for r in tables[table] if r.line == pinned["line"]]
        assert lm._pin(doc, row.line) == pinned
        got |= lm._row_metrics(table, row)
    assert got == expected["run"]["metrics"]


@pytest.mark.parametrize("cell", ["Not supplied: x", "-3", "abc", "1.2.3", ""])
def test_row_metrics_omit_unusable_cells(cell):
    cells = {"Period": "p", "Basis and limitation": "b", "Reporting unit": "x"}
    cells |= {"Total debt / EBITDA": cell, "Net debt / EBITDA": "1,250.5"}
    got = lm._row_metrics("cp1_leverage", lm._Row(3, cells))
    assert list(got) == ["net_leverage"] and got["net_leverage"]["value"] == "1250.5"
    assert lm._row_metrics("cp1_leverage", lm._Row(3, cells | {"Reporting unit": "US$m"})) == {}


def edit(root, run_id, name, change):
    path = root / "runs" / run_id / name
    path.write_text(change(path.read_text(encoding="utf-8")), encoding="utf-8")


@pytest.mark.parametrize("case", CASES)
def test_write_bytes_and_no_temp_file(case, tmp_path):
    root, run_id = workspace(case, tmp_path)
    edit(root, run_id, "context.json", lambda t: t.replace("Lane Logistics", "Å Lane"))
    path = lm.write(root, run_id)
    want = json.dumps(lm.build(root, run_id), indent=2, ensure_ascii=False) + "\n"
    assert path.read_bytes() == want.encode("utf-8")
    assert sorted(p.name for p in path.parent.glob(".library-*")) == []


def test_write_failure_leaves_nothing(tmp_path, monkeypatch):
    root, run_id = workspace("synthetic", tmp_path)

    def boom(*_):
        raise OSError("probe")

    monkeypatch.setattr(lm.os, "replace", boom)
    with pytest.raises(OSError, match="probe"):
        lm.write(root, run_id)
    left = [p.name for p in (root / "runs" / run_id).iterdir()]
    assert not [n for n in left if n.startswith(".library-") or n == "library.json"]


def test_missing_expectations_raises(tmp_path):
    root, run_id = workspace("missing-expectations", tmp_path)
    wanted = (KEYS / "missing-expectations/expected-error.txt").read_text().strip()
    with pytest.raises(lm.ManifestError, match="expectations.json") as err:
        lm.build(root, run_id)
    assert wanted in str(err.value)


def test_missing_identity_name_raises(tmp_path):
    root, run_id = workspace("synthetic", tmp_path)
    edit(root, run_id, "context.json", lambda t: t.replace('"issuer_name"', '"issuer_name_x"'))
    with pytest.raises(lm.ManifestError, match="issuer_name"):
        lm.build(root, run_id)


def test_nested_array_in_context(tmp_path):
    root, run_id = workspace("synthetic", tmp_path)

    def nest(text):
        data = json.loads(text)
        data["run"]["extra"] = [[1, 2]]
        return json.dumps(data, indent=2) + "\n"

    edit(root, run_id, "context.json", nest)
    assert lm.build(root, run_id)["run"]["private_side"] is True


def test_cp1_handoff_and_metrics_do_not_need_a_request(tmp_path, monkeypatch):
    root, run_id = workspace("edge", tmp_path)
    monkeypatch.setattr(lm, "_chosen_row", lambda rows, *_: rows[0] if rows else None)
    edit(root, run_id, "workflow.json", lambda t: t.replace('"CP-1",', ""))
    manifest = lm.build(root, run_id)
    assert manifest["run"]["handoff"] == f"runs/{run_id}/CP-1.md"
    assert "leverage" in manifest["run"]["metrics"]


def test_workflow_upper_cases_only_the_first_letter(tmp_path):
    root, run_id = workspace("edge", tmp_path)
    edit(root, run_id, "context.json", lambda t: t.replace('"credit_snapshot"', '"LBO_snapshot"'))
    assert lm.build(root, run_id)["run"]["workflow"] == "LBO snapshot"


def test_malformed_optional_inputs_raise(tmp_path):
    root, run_id = workspace("synthetic", tmp_path)
    run = root / "runs" / run_id
    receipt = next(run.glob("completed-*.json"))
    (run / "completed-copy.json").write_bytes(receipt.read_bytes())
    with pytest.raises(lm.ManifestError, match="more than one"):
        lm.build(root, run_id)
    (run / "completed-copy.json").unlink()
    receipt.write_text("{not json")
    with pytest.raises(lm.ManifestError, match="completed-"):
        lm.build(root, run_id)
    receipt.unlink()
    broken = run / "deliveries" / "zz-broken"
    broken.mkdir()
    (broken / "delivery.json").write_text("{not json")
    with pytest.raises(lm.ManifestError, match="delivery.json"):
        lm.build(root, run_id)
