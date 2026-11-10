"""Manifest writer against the hand-written answer key (tests/fixtures/library-manifest/writer)."""

import hashlib
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
import tempfile
import threading
from pathlib import Path

import pytest
from hypothesis import HealthCheck, example, given, settings
from hypothesis import strategies as st

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


UNUSABLE = ["Not supplied: x", "-3", "abc", "1.2.3", "", "4,10", "12,34", "1250,000"]


@pytest.mark.parametrize("cell", UNUSABLE)
def test_row_metrics_omit_unusable_cells(cell):
    cells = {"Period": "p", "Basis and limitation": "b", "Reporting unit": "x"}
    cells |= {"Total debt / EBITDA": cell, "Net debt / EBITDA": "1,250.5"}
    got = lm._row_metrics("cp1_leverage", lm._Row(3, cells))
    assert list(got) == ["net_leverage"] and got["net_leverage"]["value"] == "1250.5"
    assert lm._row_metrics("cp1_leverage", lm._Row(3, cells | {"Reporting unit": "US$m"})) == {}
    assert lm._row_metrics("cp1_leverage", lm._Row(3, cells | {"Basis and limitation": ""})) == {}


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


def test_cp1_handoff_and_metrics_do_not_need_a_request(tmp_path):
    root, run_id = workspace("edge", tmp_path)
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


def test_write_keeps_the_original_error_when_fdopen_already_closed_the_descriptor(
    tmp_path, monkeypatch
):
    root, run_id = workspace("synthetic", tmp_path)
    real_fdopen = os.fdopen

    def fails_after_the_file_layer_owns_the_fd(fd, mode="r", *args, **kwargs):
        if "w" in mode:
            kwargs["encoding"] = "no-such-codec"
        return real_fdopen(fd, mode, *args, **kwargs)

    monkeypatch.setattr(lm.os, "fdopen", fails_after_the_file_layer_owns_the_fd)
    with pytest.raises(LookupError, match="no-such-codec"):
        lm.write(root, run_id)
    assert [p.name for p in run_dir(root, run_id).glob(".library-*")] == []


def test_a_failed_cleanup_keeps_the_original_error_and_names_the_temp_file(tmp_path, monkeypatch):
    root, run_id = workspace("synthetic", tmp_path)
    real_unlink = os.unlink

    def replace_fails(*_, **__):
        raise OSError("replace failed")

    def unlink_fails(path, *args, **kwargs):
        if str(path).startswith(".library-"):
            raise OSError("unlink failed")
        return real_unlink(path, *args, **kwargs)

    monkeypatch.setattr(lm.os, "replace", replace_fails)
    monkeypatch.setattr(lm.os, "unlink", unlink_fails)
    with pytest.raises(OSError, match="replace failed") as raised:
        lm.write(root, run_id)
    (left,) = [p.name for p in run_dir(root, run_id).glob(".library-*")]
    assert raised.value.__notes__ == [f"temp file {left} was not removed: unlink failed"]


def test_replacing_os_open_selects_the_by_path_walk(tmp_path, monkeypatch):
    # `_read` and `write` choose the dir_fd walk by `os.open in os.supports_dir_fd`.
    root, run_id = workspace("synthetic", tmp_path)
    monkeypatch.setattr(lm, "_read_pinned", lambda *_: pytest.fail("pinned walk used"))
    real_open = os.open
    monkeypatch.setattr(lm.os, "open", lambda *a, **k: real_open(*a, **k))
    assert lm.os.open not in os.supports_dir_fd
    assert lm._read(root, f"runs/{run_id}/context.json") is not None


# ---- R-26 row selection: hand-written CP-1 tables, answers written here by hand ----------------

FORMAT_GAP = "CP-1 chart periods are not in the fixed format"
HTML_GAP = "HTML Model not published by app runs"
PRIVATE_GAP = (
    "Private-side run: the dealer run is indicative and no market-observed pricing is available."
)
LEGAL_GAP = "No executed credit agreement or indenture was supplied, so legal analysis will refuse."
LEV_HEAD = "### Chart data: leverage"
COV_HEAD = "### Chart data: interest cover"
LIQ_HEAD = "### Chart data: liquidity"
LEV_COLUMNS = (
    "| Period | Total debt / EBITDA | Net debt / EBITDA | Reporting unit | Basis and limitation |"
)
COV_COLUMNS = "| Period | EBITDA / cash interest | Reporting unit | Basis and limitation |"
LIQ_COLUMNS = (
    "| Period | Cash | Undrawn committed facilities | Reporting unit | Basis and limitation |"
)


def table(head, columns, *rows):
    divider = "| " + " | ".join("---" for _ in columns.strip("|").split("|")) + " |"
    return "\n".join([head, "", columns, divider, *rows])


def lev(period, debt="4.00", net="3.00", unit="x", basis="lev basis"):
    return f"| {period} | {debt} | {net} | {unit} | {basis} |"


def cov(period, value="2.00", unit="x", basis="cov basis"):
    return f"| {period} | {value} | {unit} | {basis} |"


def liq(period, cash="100", undrawn="50", unit="US$m", basis="liq basis"):
    return f"| {period} | {cash} | {undrawn} | {unit} | {basis} |"


def leverage_table(*rows):
    return table(LEV_HEAD, LEV_COLUMNS, *rows)


def cover_table(*rows):
    return table(COV_HEAD, COV_COLUMNS, *rows)


def liquidity_table(*rows):
    return table(LIQ_HEAD, LIQ_COLUMNS, *rows)


def chart_text(*tables):
    return "Hand-written CP-1 for a selection case.\n\n" + "\n\n".join(tables) + "\n"


def built(tmp_path, text, case="edge"):
    """Build the manifest of the `case` workspace after its CP-1.md is replaced by `text`."""
    root, run_id = workspace(case, tmp_path)
    path = root / "runs" / run_id / "CP-1.md"
    if text is None:
        path.unlink()
    else:
        path.write_text(text, encoding="utf-8")
    return lm.build(root, run_id), run_id


def shown(manifest):
    """The metrics as {name: (value, period)}."""
    return {k: (m["value"], m["period"]) for k, m in manifest["run"]["metrics"].items()}


def pinned(manifest, text, source, row):
    """The cp1_* source is the line of `row` in `text`, with the file's sha256."""
    lines = text.split("\n")
    assert manifest["sources"][source] == {
        "path": manifest["sources"][source]["path"],
        "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "line": lines.index(row) + 1,
        "quote": row,
    }
    assert manifest["sources"][source]["path"].endswith("/CP-1.md")


def sources_of(manifest):
    return sorted(k for k in manifest["sources"] if k.startswith("cp1_"))


FY25 = "FY2025 ended 2025-06-30"
FY24 = "FY2024 ended 2024-06-30"
LTM25 = "LTM ended 2025-06-30"


SELECTION = json.loads((KEYS / "selection-cases.json").read_text(encoding="utf-8"))["cases"]


@pytest.mark.parametrize("c", SELECTION, ids=[c["id"] for c in SELECTION])
def test_selection_case_gives_the_hand_written_answers(tmp_path, c):
    """Each case of selection-cases.json: its CP-1 text, built (and, where stated, written)."""
    text = None if c["cp1"] is None else "\n".join(c["cp1"])
    want = c["expect"]
    manifest, _ = built(tmp_path / "built", text, case=c.get("case", "edge"))
    if "metrics" in want:
        assert shown(manifest) == {k: tuple(v) for k, v in want["metrics"].items()}
    for name, pair in want.get("metrics_include", {}).items():
        assert shown(manifest)[name] == tuple(pair)
    if "metric_names" in want:
        assert sorted(manifest["run"]["metrics"]) == want["metric_names"]
    if "sources" in want:
        assert sources_of(manifest) == want["sources"]
    for source, row in want.get("pinned", []):
        pinned(manifest, text, source, row)
    for source in want.get("absent_sources", []):
        assert source not in manifest["sources"]
    if "gaps" in want:
        assert manifest["run"]["gaps"] == want["gaps"]
    if "discovered_metrics" in want:
        run = written_and_discovered(tmp_path / "written", text)
        assert sorted(run.metrics) == want["discovered_metrics"]


def test_the_format_gap_follows_the_expectation_gaps_when_the_model_is_published(tmp_path):
    root, run_id = workspace("synthetic", tmp_path)
    edit(root, run_id, "CP-1.md", lambda _: chart_text(leverage_table(lev("FY2025"))))
    receipt = next((root / "runs" / run_id).glob("completed-*.json"))
    receipt.write_text(
        receipt.read_text(encoding="utf-8").replace(
            '"cp_model_published": false', '"cp_model_published": true'
        ),
        encoding="utf-8",
    )
    assert lm.build(root, run_id)["run"]["gaps"] == [
        PRIVATE_GAP,
        LEGAL_GAP,
        FORMAT_GAP,
    ]


# ---- item 6: the writer's manifests are admitted by discovery unchanged -------------------------


@pytest.mark.parametrize("case", CASES)
def test_writer_output_is_admitted_by_discovery(case, tmp_path):
    from issuer_library.discovery import discover
    from issuer_library.model import Catalogue

    root, run_id = workspace(case, tmp_path)
    lm.write(root, run_id)
    cat = discover(str(root), Catalogue())
    assert not [issue for issue in cat.issues if run_id in issue]
    (run,) = [r for r in cat.real if r.id == run_id]
    assert not [gap for gap in run.gaps if gap.startswith("Run metadata rejected")]
    assert sorted(run.metrics) == sorted(key(case)["run"]["metrics"])


# ---- item 7: one hand-written list of Period cells ----------------------------------------------

# (cell, valid for leverage and interest cover, valid for liquidity)
PERIOD_CELLS = [
    ("FY2025 ended 2025-06-30", True, False),
    ("FY2024 ended 2025-06-30", True, False),
    ("LTM ended 2025-06-30", True, False),
    ("H1 2025 ended 2025-06-30", True, False),
    ("H2 2024 ended 2024-12-31", True, False),
    ("9M 2025 ended 2025-09-30", True, False),
    ("Q1 2025 ended 2025-03-31", True, False),
    ("Q4 2025 ended 2025-12-31", True, False),
    ("FY2024 ended 2024-02-29", True, False),
    ("FY2025 ended 2025-02-29", False, False),
    ("FY2025 ended 2025-02-30", False, False),
    ("FY2025 ended 2025-13-01", False, False),
    ("fy2025 ended 2025-06-30", False, False),
    ("FY2025  ended 2025-06-30", False, False),
    ("FY2025 ended  2025-06-30", False, False),
    ("FY2025 / 2025-06-30", False, False),
    ("FY2025", False, False),
    ("FY25 ended 2025-06-30", False, False),
    ("LTM 2025-06-30", False, False),
    ("LTM2025 ended 2025-06-30", False, False),
    ("H3 2025 ended 2025-06-30", False, False),
    ("Q5 2025 ended 2025-06-30", False, False),
    ("Q1 ended 2025-03-31", False, False),
    ("H1 ended 2025-06-30", False, False),
    ("FY2025 ended 2025-6-30", False, False),
    ("FY2025 ended 2025-06-30 (restated)", False, False),
    ("2025-06-30", False, True),
    ("2024-02-29", False, True),
    ("2025-02-30", False, False),
    ("2025-06-31", False, False),
    ("2025-6-30", False, False),
    ("30/06/2025", False, False),
    ("2025-06-30 (audited)", False, False),
    ("", False, False),
]
RATIO_TABLES = {"leverage": (leverage_table, lev), "interest cover": (cover_table, cov)}


@pytest.mark.parametrize(("cell", "ratio_valid", "liquidity_valid"), PERIOD_CELLS)
def test_writer_period_format_gives_the_hand_written_answers(
    tmp_path, cell, ratio_valid, liquidity_valid
):
    for name, (table_of, row_of) in RATIO_TABLES.items():
        manifest, _ = built(tmp_path / name, chart_text(table_of(row_of(cell))))
        assert (FORMAT_GAP not in manifest["run"]["gaps"]) is ratio_valid, name
    manifest, _ = built(tmp_path / "liquidity", chart_text(liquidity_table(liq(cell))))
    assert (FORMAT_GAP not in manifest["run"]["gaps"]) is liquidity_valid


@pytest.mark.parametrize(("cell", "ratio_valid", "liquidity_valid"), PERIOD_CELLS)
def test_launcher_period_check_gives_the_same_answers(cell, ratio_valid, liquidity_valid):
    from deploy_workflow.owners import cpos_launch

    check = getattr(cpos_launch, "_period_issues", None)
    if check is None:
        pytest.skip(
            "cpos_launch._period_issues is not on this branch yet (R-26 launcher check, PR #93)"
        )
    assert (check("h", cell, "S.1") == []) is ratio_valid
    assert (check("h", cell, "S.3") == []) is liquidity_valid


# ---- R-26 fix round 1: a chart table needs the exact header; non-finite values write no metric --


def written_and_discovered(tmp_path, text):
    """Write the `edge` manifest with CP-1.md = `text`, then run discovery on it."""
    from issuer_library.discovery import discover
    from issuer_library.model import Catalogue

    root, run_id = workspace("edge", tmp_path)
    (root / "runs" / run_id / "CP-1.md").write_text(text, encoding="utf-8")
    lm.write(root, run_id)
    cat = discover(str(root), Catalogue())
    assert not [issue for issue in cat.issues if run_id in issue]
    (run,) = [r for r in cat.real if r.id == run_id]
    assert not [gap for gap in run.gaps if gap.startswith("Run metadata rejected")]
    return run


def only_html_gap(manifest):
    assert manifest["run"]["metrics"] == {} and sources_of(manifest) == []
    assert manifest["run"]["gaps"] == [HTML_GAP]


# ---- R-26 fix round 2: the writer's output is admitted by discovery, or it is not written -------


def write_then_discover(root, run_id):
    """Write the manifest, run discovery on the workspace; return (run, issues, rejected gaps)."""
    from issuer_library.discovery import discover
    from issuer_library.model import Catalogue

    lm.write(root, run_id)
    cat = discover(str(root), Catalogue())
    issues = [issue for issue in cat.issues if run_id in issue]
    (run,) = [r for r in cat.real if r.id == run_id]
    rejected = [gap for gap in run.gaps if gap.startswith("Run metadata rejected")]
    return run, issues, rejected


def metrics_are_stated_by_their_pinned_quote(root, run_id):
    """Every metric written to library.json has its value among discovery's numbers of its quote."""
    from issuer_library.discovery import stated_numbers

    manifest = json.loads((root / "runs" / run_id / "library.json").read_text(encoding="utf-8"))
    for name, metric in manifest["run"]["metrics"].items():
        quote = manifest["sources"][metric["source"]]["quote"]
        assert metric["value"] in stated_numbers(quote), (name, metric["value"], quote)


# Hand derivation with discovery.number_runs / run_number / accounting_number (whole pinned line).
# Leverage line:  | FY2025 ended 2025-06-30 | Not supplied (see note | 3.10 | x | lev basis |
#   number runs: "2025" (depth 0), "2025-06-30" (depth 0), "3.10" (depth 1: the "(" in the debt cell
#   is never closed).  "2025" -> stated "2025".  "2025-06-30" is not a whole number -> nothing.
#   "3.10" has depth 1 and is preceded by " ", not "(" -> accounting_number gives None -> nothing.
#   stated_numbers(line) == ["2025"].  The debt cell is not a number; net 3.10 is not stated.
#   So no metric: {}.
# Liquidity line: | 2025-06-30 | Not supplied (pending | 50 | US$m | liq basis |
#   runs: "2025-06-30" (nothing), "50" at depth 1 preceded by " " -> nothing.  stated == [].
#   cash is not a number; undrawn 50 is not stated.  So no metric: {}.
PROBE_ROWS = [
    (
        "leverage",
        lambda: chart_text(leverage_table(lev(FY25, debt="Not supplied (see note", net="3.10"))),
    ),
    (
        "liquidity",
        lambda: chart_text(
            liquidity_table(liq("2025-06-30", cash="Not supplied (pending", undrawn="50"))
        ),
    ),
]


@pytest.mark.parametrize(("name", "make"), PROBE_ROWS, ids=[n for n, _ in PROBE_ROWS])
def test_an_unclosed_bracket_before_a_value_writes_a_manifest_discovery_admits(
    tmp_path, name, make
):
    text = make()
    manifest, _ = built(tmp_path / "built", text)
    assert manifest["run"]["metrics"] == {}
    root, run_id = workspace("edge", tmp_path / "written")
    (root / "runs" / run_id / "CP-1.md").write_text(text, encoding="utf-8")
    run, issues, rejected = write_then_discover(root, run_id)
    assert issues == [] and rejected == []
    assert run.metrics == {}
    metrics_are_stated_by_their_pinned_quote(root, run_id)


def test_write_refuses_and_leaves_nothing_when_discovery_would_reject_the_run(tmp_path):
    # context.json run.as_of is a string (build accepts it) but not a calendar date (admission
    # rejects it: "invalid evidence date").
    root, run_id = workspace("edge", tmp_path)
    edit(
        root,
        run_id,
        "context.json",
        lambda t: t.replace('"as_of": "2025-06-30"', '"as_of": "2025-13-40"', 1),
    )
    assert lm.build(root, run_id)["run"]["date"] == "2025-13-40"
    with pytest.raises(lm.ManifestError, match="invalid evidence date"):
        lm.write(root, run_id)
    left = [p.name for p in (root / "runs" / run_id).iterdir()]
    assert not [n for n in left if n.startswith(".library-") or n == "library.json"]


# Cells: plain numbers in many shapes, Not supplied texts, brackets, pipes, emphasis, blanks.
VALUE_CELLS = st.one_of(
    st.sampled_from(
        [
            "3.10",
            "1,250",
            "007",
            "-35",
            "(35)",
            "$50",
            "−12",
            "4,10",
            "0",
            "12.5",
            "1,250.5",
            "–35",
            "35)",
            "(35",
            "1 234",
            "1.2e3",
            "Not supplied (see note",
            "Not supplied: x)",
            "Not supplied",
            "(a) 12",
            "n/a",
            "**3.1**",
            "a \\| 3.1",
            "",
            "(n/a)",
            "x (3.1",
            "3.1)",
            "[3.1",
            "3.1]",
            "(3.1",
            "- 5",
            "5%",
            "US$ 20",
        ]
    ),
    st.text(alphabet="0123456789.,()-$ −–*`[]a|\\", max_size=12).map(
        lambda s: s.replace("|", "\\|")
    ),
)
BASIS_CELLS = st.sampled_from(
    ["lev basis", "gross (see note", "(x", "**bold** `code", "a \\| b", "", "net (of cash)", "3.1"]
)
RATIO_PERIODS = st.sampled_from(
    [FY25, FY24, LTM25, "H1 2025 ended 2025-06-30", "FY2025", "FY2025 ended 2025-02-30"]
)
LIQ_PERIODS = st.sampled_from(["2025-06-30", "2025-03-31", "2024-12-31", "2025-02-30", "FY2025"])
UNITS = st.sampled_from(["x", "x", "x", "US$m"])
LIQ_UNITS = st.sampled_from(["US$m", "US$m", "US$m", "x"])


@st.composite
def generated_chart_text(draw):
    lev_rows = draw(
        st.lists(
            st.builds(lev, RATIO_PERIODS, VALUE_CELLS, VALUE_CELLS, UNITS, BASIS_CELLS),
            min_size=1,
            max_size=4,
        )
    )
    cov_rows = draw(
        st.lists(
            st.builds(cov, RATIO_PERIODS, VALUE_CELLS, UNITS, BASIS_CELLS), min_size=1, max_size=4
        )
    )
    liq_rows = draw(
        st.lists(
            st.builds(liq, LIQ_PERIODS, VALUE_CELLS, VALUE_CELLS, LIQ_UNITS, BASIS_CELLS),
            min_size=1,
            max_size=4,
        )
    )
    return chart_text(leverage_table(*lev_rows), cover_table(*cov_rows), liquidity_table(*liq_rows))


PROBE_TEXTS = [make() for _, make in PROBE_ROWS]


@settings(
    max_examples=150,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@example(text=PROBE_TEXTS[0])
@example(text=PROBE_TEXTS[1])
@given(text=generated_chart_text())
def test_whatever_the_chart_rows_say_the_written_manifest_is_admitted_or_absent(text):
    with tempfile.TemporaryDirectory() as scratch:
        root, run_id = workspace("edge", Path(scratch))
        (root / "runs" / run_id / "CP-1.md").write_text(text, encoding="utf-8")
        library = root / "runs" / run_id / "library.json"
        try:
            _, issues, rejected = write_then_discover(root, run_id)
        except lm.ManifestError:
            assert not library.exists()
            return
        assert library.exists()
        assert issues == [] and rejected == []
        metrics_are_stated_by_their_pinned_quote(root, run_id)
