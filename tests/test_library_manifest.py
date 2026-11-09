"""Manifest writer against the hand-written answer key (tests/fixtures/library-manifest/writer)."""

import copy
import importlib.util
import json
import os
import re
import shutil
import signal
import socket
import stat
import subprocess
import sys
import threading
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

    def boom(*_, **__):
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


def run_dir(root, run_id):
    return root / "runs" / run_id


def refused(root, run_id, match):
    with pytest.raises(lm.ManifestError, match=match) as err:
        lm.build(root, run_id)
    assert "missing" not in str(err.value)


def test_linked_context_is_refused(tmp_path):
    root, run_id = workspace("synthetic", tmp_path / "ws")
    real = tmp_path / "real-context.json"
    path = run_dir(root, run_id) / "context.json"
    path.rename(real)
    path.symlink_to(real)
    refused(root, run_id, "context.json is a link")


def test_dangling_link_is_a_link_not_missing(tmp_path):
    root, run_id = workspace("synthetic", tmp_path)
    path = run_dir(root, run_id) / "expectations.json"
    path.unlink()
    path.symlink_to(tmp_path / "nowhere.json")
    refused(root, run_id, "expectations.json is a link")


def test_linked_optional_handoff_is_refused(tmp_path):
    root, run_id = workspace("synthetic", tmp_path / "ws")
    outside = tmp_path / "CP-1.md"
    outside.write_text("# outside\n", encoding="utf-8")
    (run_dir(root, run_id) / "CP-1.md").unlink()
    (run_dir(root, run_id) / "CP-1.md").symlink_to(outside)
    refused(root, run_id, "CP-1.md is a link")


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="no FIFOs")
def test_fifo_is_refused_without_blocking(tmp_path):
    root, run_id = workspace("synthetic", tmp_path)
    path = run_dir(root, run_id) / "expectations.json"
    path.unlink()
    os.mkfifo(path)
    outcome = []

    def attempt():
        try:
            lm.build(root, run_id)
        except lm.ManifestError as err:
            outcome.append(str(err))

    worker = threading.Thread(target=attempt, daemon=True)
    worker.start()
    worker.join(10)
    assert not worker.is_alive(), "build blocked on a FIFO"
    assert outcome and "not a regular file" in outcome[0] and "missing" not in outcome[0]


def test_linked_run_folder_is_refused_and_nothing_is_written(tmp_path):
    root, run_id = workspace("synthetic", tmp_path / "ws")
    elsewhere = tmp_path / "elsewhere"
    shutil.move(str(run_dir(root, run_id)), elsewhere)
    run_dir(root, run_id).symlink_to(elsewhere, target_is_directory=True)
    with pytest.raises(lm.ManifestError, match="link"):
        lm.write(root, run_id)
    assert not (elsewhere / "library.json").exists()
    assert [p.name for p in elsewhere.glob(".library-*")] == []


def test_linked_delivery_folder_is_refused(tmp_path):
    root, run_id = workspace("synthetic", tmp_path / "ws")
    deliveries = run_dir(root, run_id) / "deliveries"
    (first,) = [p for p in deliveries.iterdir() if p.is_dir()]
    moved = tmp_path / "moved"
    shutil.move(str(first), moved)
    first.symlink_to(moved, target_is_directory=True)
    refused(root, run_id, "link")


@pytest.mark.parametrize("name", ["../../../outside", "..", ".", "", "a/b", "a\\b", "x..y", "a\0b"])
def test_module_name_that_is_not_plain_is_refused(tmp_path, name):
    root, run_id = workspace("synthetic", tmp_path / "ws")
    (tmp_path / "outside.md").write_text("OUTSIDE SECRET LINE\n", encoding="utf-8")

    def add(text):
        data = json.loads(text)
        data["run"]["requested_modules"].append(name)
        return json.dumps(data, indent=2) + "\n"

    edit(root, run_id, "workflow.json", add)
    with pytest.raises(lm.ManifestError, match="not a plain name"):
        lm.build(root, run_id)


def test_non_string_module_name_is_refused(tmp_path):
    root, run_id = workspace("synthetic", tmp_path)

    def add(text):
        data = json.loads(text)
        data["run"]["requested_modules"].append(7)
        return json.dumps(data, indent=2) + "\n"

    edit(root, run_id, "workflow.json", add)
    with pytest.raises(lm.ManifestError, match="not a plain name"):
        lm.build(root, run_id)


def test_write_refuses_a_run_folder_swapped_for_a_link_after_build(tmp_path, monkeypatch):
    root, run_id = workspace("synthetic", tmp_path / "ws")
    outside = tmp_path / "outside"
    outside.mkdir()
    real_build = lm.build

    def build_then_swap(*args):
        manifest = real_build(*args)
        shutil.move(str(run_dir(root, run_id)), tmp_path / "moved")
        run_dir(root, run_id).symlink_to(outside, target_is_directory=True)
        return manifest

    monkeypatch.setattr(lm, "build", build_then_swap)
    with pytest.raises(lm.ManifestError, match="link") as err:
        lm.write(root, run_id)
    assert "missing" not in str(err.value)
    assert list(outside.iterdir()) == []


@pytest.mark.skipif(os.geteuid() == 0, reason="root ignores file modes")
def test_unreadable_file_is_a_typed_error_with_its_true_cause(tmp_path):
    root, run_id = workspace("synthetic", tmp_path)
    path = run_dir(root, run_id) / "context.json"
    path.chmod(0)
    try:
        with pytest.raises(lm.ManifestError, match="cannot be read") as err:
            lm.build(root, run_id)
    finally:
        path.chmod(0o644)
    assert "not a regular file" not in str(err.value)
    assert "Permission denied" in str(err.value)


def test_run_folder_that_is_a_file_is_a_typed_error(tmp_path):
    root, run_id = workspace("synthetic", tmp_path)
    shutil.rmtree(run_dir(root, run_id))
    run_dir(root, run_id).write_text("not a folder")
    with pytest.raises(lm.ManifestError, match="not a folder") as err:
        lm.build(root, run_id)
    assert "missing" not in str(err.value)


@pytest.mark.parametrize(
    "name", ["cp-0", "CP-0 ", "\ud800", "x" * 300, "CP-0\u200b", "CP\u20110", "CP-"]
)
def test_module_name_outside_the_code_shape_is_refused(tmp_path, name):
    root, run_id = workspace("synthetic", tmp_path / "ws")

    def add(text):
        data = json.loads(text)
        data["run"]["requested_modules"].append(name)
        return json.dumps(data, indent=2, ensure_ascii=True) + "\n"

    edit(root, run_id, "workflow.json", add)
    with pytest.raises(lm.ManifestError, match="not a plain name"):
        lm.build(root, run_id)


def test_read_does_not_follow_a_run_folder_swapped_for_a_link_during_build(tmp_path, monkeypatch):
    root, run_id = workspace("synthetic", tmp_path / "ws")
    outside = tmp_path / "outside"
    shutil.copytree(run_dir(root, run_id), outside)
    context = json.loads((outside / "context.json").read_text(encoding="utf-8"))
    context["run"]["reporting_currency"] = "OUTSIDE"
    (outside / "context.json").write_text(json.dumps(context, indent=2) + "\n", encoding="utf-8")
    real_open = lm.events.open_regular
    first = []

    def link_during_the_first_open(*args, **kwargs):
        if first:
            return real_open(*args, **kwargs)
        first.append(True)
        home = run_dir(root, run_id)
        shutil.move(str(home), tmp_path / "moved")
        home.symlink_to(outside, target_is_directory=True)
        try:
            return real_open(*args, **kwargs)
        finally:
            home.unlink()
            shutil.move(str(tmp_path / "moved"), str(home))

    monkeypatch.setattr(lm.events, "open_regular", link_during_the_first_open)
    try:
        manifest = lm.build(root, run_id)
    except lm.ManifestError:
        manifest = None
    assert first, "the swap hook never ran, so this test checked nothing"
    if manifest is not None:
        assert manifest["run"]["currency"] != "OUTSIDE"


def test_absent_deliveries_folder_still_reads_as_missing_not_an_error(tmp_path):
    root, run_id = workspace("synthetic", tmp_path)
    shutil.rmtree(run_dir(root, run_id) / "deliveries")
    assert lm.build(root, run_id)["run"]["id"] == run_id


def test_write_refuses_a_workspace_root_that_is_a_link(tmp_path):
    root, run_id = workspace("synthetic", tmp_path / "ws")
    alias = tmp_path / "alias"
    alias.symlink_to(root, target_is_directory=True)
    with pytest.raises(lm.ManifestError, match="link"):
        lm.write(alias, run_id)


def test_write_error_paths_name_a_file_run_folder_and_a_missing_one(tmp_path, monkeypatch):
    root, run_id = workspace("synthetic", tmp_path)
    monkeypatch.setattr(lm, "build", lambda *_: {})
    shutil.rmtree(run_dir(root, run_id))
    with pytest.raises(lm.ManifestError, match="missing"):
        lm.write(root, run_id)
    run_dir(root, run_id).write_text("x")
    with pytest.raises(lm.ManifestError, match="not a folder"):
        lm.write(root, run_id)


@pytest.mark.skipif(not hasattr(socket, "AF_UNIX"), reason="no AF_UNIX sockets")
def test_socket_is_not_a_regular_file(tmp_path, monkeypatch):
    root, run_id = workspace("synthetic", tmp_path)
    path = run_dir(root, run_id) / "expectations.json"
    path.unlink()
    sock = socket.socket(socket.AF_UNIX)
    try:
        monkeypatch.chdir(path.parent)  # a socket path is limited to ~100 characters
        sock.bind(path.name)
        refused(root, run_id, "not a regular file")
    finally:
        sock.close()


KILL_CHILD = """
import importlib.util, os, signal, sys
from pathlib import Path
module_path, root, run_id, stage = sys.argv[1:5]
spec = importlib.util.spec_from_file_location("library_manifest", module_path)
lm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lm)
real_fdopen, real_replace = os.fdopen, os.replace


def die():
    os.kill(os.getpid(), signal.SIGKILL)


class Half:
    def __init__(self, stream):
        self.stream = stream

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return self.stream.__exit__(*exc)

    def write(self, text):
        self.stream.write(text[: len(text) // 2])
        self.stream.flush()
        die()


def fdopen(fd, mode="r", *args, **kwargs):
    stream = real_fdopen(fd, mode, *args, **kwargs)
    return Half(stream) if "w" in mode else stream


def replace(*args, **kwargs):
    die()


os.fdopen = fdopen if stage == "mid-write" else real_fdopen
if stage == "before-replace":
    os.replace = replace
lm.write(Path(root), run_id)
"""


@pytest.mark.skipif(
    not hasattr(signal, "SIGKILL") or os.open not in os.supports_dir_fd,
    reason="needs SIGKILL and dir_fd",
)
@pytest.mark.parametrize("stage", ["mid-write", "before-replace"])
@pytest.mark.parametrize("had_old", [True, False])
def test_sigkill_during_write_leaves_the_old_library_json_whole(tmp_path, stage, had_old):
    root, run_id = workspace("synthetic", tmp_path)
    target = run_dir(root, run_id) / "library.json"
    if had_old:
        target.write_text("OLD", encoding="utf-8")
    done = subprocess.run(
        [sys.executable, "-c", KILL_CHILD, str(lm.__file__), str(root), run_id, stage],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert done.returncode == -signal.SIGKILL, done.stderr
    if had_old:
        assert target.read_text(encoding="utf-8") == "OLD"
    else:
        assert not target.exists()


def test_linked_report_names_its_full_workspace_path(tmp_path):
    root, run_id = workspace("synthetic", tmp_path / "ws")
    deliveries = run_dir(root, run_id) / "deliveries"
    (first,) = [p for p in deliveries.iterdir() if p.is_dir()]
    (first / "report.html").rename(tmp_path / "real-report.html")
    (first / "report.html").symlink_to(tmp_path / "real-report.html")
    expected = f"runs/{run_id}/deliveries/{first.name}/report.html is a link"
    refused(root, run_id, re.escape(expected))


def test_delivery_copy_is_not_read_through_a_link_swapped_in_after_the_deliveries_listing(
    tmp_path, monkeypatch
):
    root, run_id = workspace("synthetic", tmp_path / "ws")
    outside = tmp_path / "outside"
    shutil.copytree(run_dir(root, run_id), outside)
    (outside / "deliveries").mkdir(exist_ok=True)
    (first,) = [p for p in (run_dir(root, run_id) / "deliveries").iterdir() if p.is_dir()]
    (first / "CP-0.md").unlink()
    real_down = lm._downstream
    fired = []

    def swapped(*args):
        fired.append(True)
        home = run_dir(root, run_id)
        shutil.move(str(home), tmp_path / "moved")
        home.symlink_to(outside, target_is_directory=True)
        try:
            return real_down(*args)
        finally:
            home.unlink()
            shutil.move(str(tmp_path / "moved"), str(home))

    monkeypatch.setattr(lm, "_downstream", swapped)
    try:
        manifest = lm.build(root, run_id)
    except lm.ManifestError as err:
        assert "link" in str(err)
        manifest = None
    assert fired, "the swap hook never ran, so this test checked nothing"
    if manifest is not None:
        done = {r["id"]: r["done"] for r in manifest["checklist"]["requirements"]}
        assert done["downstream"] is False


def test_linked_folder_refusal_names_the_file_and_the_folder(tmp_path):
    root, run_id = workspace("synthetic", tmp_path / "ws")
    elsewhere = tmp_path / "elsewhere"
    shutil.move(str(run_dir(root, run_id)), elsewhere)
    run_dir(root, run_id).symlink_to(elsewhere, target_is_directory=True)
    refused(
        root,
        run_id,
        re.escape(f"runs/{run_id}/context.json is under a link (runs/{run_id})"),
    )


@pytest.mark.skipif(not os.path.isdir("/dev/fd"), reason="needs /dev/fd to count descriptors")
def test_write_closes_the_temp_descriptor_when_fdopen_fails(tmp_path, monkeypatch):
    root, run_id = workspace("synthetic", tmp_path)
    before = len(os.listdir("/dev/fd"))

    real_fdopen = os.fdopen

    def boom(fd, mode="r", *args, **kwargs):
        if "w" in mode:
            raise RuntimeError("fdopen")
        return real_fdopen(fd, mode, *args, **kwargs)

    monkeypatch.setattr(lm.os, "fdopen", boom)
    for _ in range(5):
        with pytest.raises(RuntimeError, match="fdopen"):
            lm.write(root, run_id)
    assert len(os.listdir("/dev/fd")) == before
    assert [p.name for p in run_dir(root, run_id).glob(".library-*")] == []


@pytest.mark.skipif(os.name != "posix", reason="POSIX file modes")
def test_published_library_json_is_owner_only(tmp_path):
    root, run_id = workspace("synthetic", tmp_path)
    target = lm.write(root, run_id)
    assert stat.S_IMODE(os.stat(target).st_mode) == 0o600
