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


def test_fy_beats_ltm_on_the_same_date(tmp_path):
    rows = [lev(LTM25, "3.10", "2.10"), lev(FY25, "4.10", "3.10"), lev(FY24, "5.10", "4.10")]
    text = chart_text(leverage_table(*rows))
    manifest, _ = built(tmp_path, text)
    assert shown(manifest) == {"leverage": ("4.10", FY25), "net_leverage": ("3.10", FY25)}
    assert manifest["run"]["gaps"] == [HTML_GAP]
    pinned(manifest, text, "cp1_leverage", rows[1])
    assert sources_of(manifest) == ["cp1_leverage"]


def test_ltm_is_taken_when_no_fy_row_is_on_the_latest_date(tmp_path):
    rows = [lev(FY24, "5.10", "4.10"), lev(LTM25, "3.10", "2.10")]
    text = chart_text(leverage_table(*rows))
    manifest, _ = built(tmp_path, text)
    assert shown(manifest) == {"leverage": ("3.10", LTM25), "net_leverage": ("2.10", LTM25)}
    pinned(manifest, text, "cp1_leverage", rows[1])


def test_fy_and_two_ltm_rows_on_the_latest_date_give_no_row(tmp_path):
    rows = [lev(FY25), lev(LTM25), lev(LTM25, "3.50", "2.50"), lev(FY24, "5.10", "4.10")]
    manifest, _ = built(tmp_path, chart_text(leverage_table(*rows)))
    assert manifest["run"]["metrics"] == {} and sources_of(manifest) == []
    assert manifest["run"]["gaps"] == [HTML_GAP]


def test_two_fy_rows_on_the_latest_date_give_no_row_and_no_older_fallback(tmp_path):
    rows = [lev(FY25), lev(FY25, "4.50", "3.50"), lev(FY24, "5.10", "4.10")]
    manifest, _ = built(tmp_path, chart_text(leverage_table(*rows)))
    assert manifest["run"]["metrics"] == {} and sources_of(manifest) == []


def test_rows_dated_after_as_of_are_ignored(tmp_path):
    # The edge run's as-of date is 2025-06-30.
    rows = [
        lev("FY2026 ended 2026-06-30", "9.10", "8.10"),
        lev("LTM ended 2025-09-30", "9.20", "8.20"),
        lev(FY25, "4.10", "3.10"),
    ]
    liquidity = [liq("2025-07-01", "999", "888"), liq("2025-06-30", "101", "51")]
    text = chart_text(leverage_table(*rows), liquidity_table(*liquidity))
    manifest, _ = built(tmp_path, text)
    assert shown(manifest) == {
        "leverage": ("4.10", FY25),
        "net_leverage": ("3.10", FY25),
        "cash": ("101", "2025-06-30"),
        "undrawn": ("51", "2025-06-30"),
    }
    pinned(manifest, text, "cp1_leverage", rows[2])
    pinned(manifest, text, "cp1_liquidity", liquidity[1])


def test_only_later_rows_give_no_metric_and_no_gap(tmp_path):
    text = chart_text(leverage_table(lev("FY2026 ended 2026-06-30")))
    manifest, _ = built(tmp_path, text)
    assert manifest["run"]["metrics"] == {} and manifest["run"]["gaps"] == [HTML_GAP]


@pytest.mark.parametrize("interim", ["H1 2025", "H2 2025", "9M 2025", "Q2 2025"])
def test_interim_rows_do_not_block_and_are_not_selected(tmp_path, interim):
    rows = [lev(f"{interim} ended 2025-06-30", "7.10", "6.10"), lev("FY2024 ended 2024-12-31")]
    manifest, _ = built(tmp_path, chart_text(leverage_table(*rows)))
    assert shown(manifest) == {
        "leverage": ("4.00", "FY2024 ended 2024-12-31"),
        "net_leverage": ("3.00", "FY2024 ended 2024-12-31"),
    }


def test_interim_row_alone_gives_no_metric(tmp_path):
    manifest, _ = built(tmp_path, chart_text(leverage_table(lev("H1 2025 ended 2025-06-30"))))
    assert manifest["run"]["metrics"] == {} and manifest["run"]["gaps"] == [HTML_GAP]


def test_the_latest_row_need_not_be_the_first(tmp_path):
    rows = [lev(FY24, "5.10", "4.10"), lev(FY25, "4.10", "3.10")]
    cover = [cov(FY24, "2.10"), cov("LTM ended 2025-03-31", "2.20"), cov(FY25, "2.90")]
    liquidity = [liq("2024-12-31", "10", "5"), liq("2025-06-30", "20", "6")]
    text = chart_text(leverage_table(*rows), cover_table(*cover), liquidity_table(*liquidity))
    manifest, _ = built(tmp_path, text)
    assert shown(manifest) == {
        "leverage": ("4.10", FY25),
        "net_leverage": ("3.10", FY25),
        "coverage": ("2.90", FY25),
        "cash": ("20", "2025-06-30"),
        "undrawn": ("6", "2025-06-30"),
    }
    pinned(manifest, text, "cp1_coverage", cover[2])
    pinned(manifest, text, "cp1_liquidity", liquidity[1])


def test_the_kind_year_is_not_compared_with_the_date_year(tmp_path):
    text = chart_text(leverage_table(lev("FY2030 ended 2025-06-30", "4.10", "3.10")))
    manifest, _ = built(tmp_path, text)
    assert shown(manifest)["leverage"] == ("4.10", "FY2030 ended 2025-06-30")
    assert manifest["run"]["gaps"] == [HTML_GAP]


def test_an_impossible_date_makes_the_table_unreadable_and_adds_the_gap(tmp_path):
    rows = [lev("FY2025 ended 2025-02-30", "4.10", "3.10"), lev(FY24, "5.10", "4.10")]
    cover = [cov(FY25, "2.90")]
    text = chart_text(leverage_table(*rows), cover_table(*cover))
    manifest, _ = built(tmp_path, text)
    assert shown(manifest) == {"coverage": ("2.90", FY25)}
    assert sources_of(manifest) == ["cp1_coverage"]
    assert manifest["run"]["gaps"] == [HTML_GAP, FORMAT_GAP]


def test_one_off_format_row_makes_its_whole_table_unreadable(tmp_path):
    rows = [lev(FY25, "4.10", "3.10"), lev("FY2024 / 2024-06-30", "5.10", "4.10")]
    manifest, _ = built(tmp_path, chart_text(leverage_table(*rows)))
    assert manifest["run"]["metrics"] == {} and sources_of(manifest) == []
    assert manifest["run"]["gaps"] == [HTML_GAP, FORMAT_GAP]


def test_two_liquidity_rows_on_the_latest_date_give_no_row(tmp_path):
    rows = [
        liq("2025-06-30", "10", "1"),
        liq("2025-06-30", "20", "2"),
        liq("2024-06-30", "30", "3"),
    ]
    manifest, _ = built(tmp_path, chart_text(liquidity_table(*rows)))
    assert manifest["run"]["metrics"] == {} and sources_of(manifest) == []


def test_a_duplicate_heading_gives_no_metric_and_no_gap(tmp_path):
    first, second = leverage_table(lev(FY25)), leverage_table(lev(FY24, "5.10", "4.10"))
    text = chart_text(first, second, cover_table(cov(FY25, "2.90")))
    manifest, _ = built(tmp_path, text)
    assert shown(manifest) == {"coverage": ("2.90", FY25)}
    assert sources_of(manifest) == ["cp1_coverage"]
    assert manifest["run"]["gaps"] == [HTML_GAP]


def test_a_row_with_the_wrong_cell_count_gives_no_metric_and_no_gap(tmp_path):
    short = f"| {FY25} | 4.10 | 3.10 | x |"
    rows = [short, lev(FY24, "5.10", "4.10")]
    long = f"| {FY25} | 2.90 | x | cov basis | extra |"
    text = chart_text(leverage_table(*rows), cover_table(long, cov(FY24, "2.10")))
    manifest, _ = built(tmp_path, text)
    assert manifest["run"]["metrics"] == {} and sources_of(manifest) == []
    assert manifest["run"]["gaps"] == [HTML_GAP]


@pytest.mark.parametrize("cell", ["4,10", "12,34", "1250,000"])
def test_an_admission_unreadable_number_is_no_metric_but_its_sibling_stays(tmp_path, cell):
    rows = [lev(FY25, debt=cell, net="1,250.5"), lev(FY24, "5.10", "4.10")]
    text = chart_text(leverage_table(*rows))
    manifest, _ = built(tmp_path, text)
    assert shown(manifest) == {"net_leverage": ("1250.5", FY25)}
    pinned(manifest, text, "cp1_leverage", rows[0])


def test_thousands_separators_are_written_without_commas(tmp_path):
    text = chart_text(liquidity_table(liq("2025-06-30", cash="12,345", undrawn="1,250.5")))
    manifest, _ = built(tmp_path, text)
    assert shown(manifest) == {"cash": ("12345", "2025-06-30"), "undrawn": ("1250.5", "2025-06-30")}


def test_a_blank_basis_gives_no_metric_for_the_row(tmp_path):
    rows = [lev(FY25, basis=""), lev(FY24, "5.10", "4.10")]
    manifest, _ = built(tmp_path, chart_text(leverage_table(*rows)))
    assert manifest["run"]["metrics"] == {} and sources_of(manifest) == []
    assert manifest["run"]["gaps"] == [HTML_GAP]


def test_a_wrong_unit_gives_no_metric(tmp_path):
    manifest, _ = built(tmp_path, chart_text(liquidity_table(liq("2025-06-30", unit="US$bn"))))
    assert manifest["run"]["metrics"] == {} and sources_of(manifest) == []


def test_not_supplied_in_the_chosen_row_is_not_replaced_by_an_older_row(tmp_path):
    rows = [lev(FY25, debt="Not supplied: no filing", net="3.10"), lev(FY24, "5.10", "4.10")]
    text = chart_text(leverage_table(*rows))
    manifest, _ = built(tmp_path, text)
    assert shown(manifest) == {"net_leverage": ("3.10", FY25)}
    pinned(manifest, text, "cp1_leverage", rows[0])
    both = lev(FY25, debt="Not supplied: a", net="Not supplied: b")
    manifest, _ = built(tmp_path / "second", chart_text(leverage_table(both, rows[1])))
    assert manifest["run"]["metrics"] == {} and sources_of(manifest) == []


def test_a_missing_table_gives_no_metric_and_no_gap(tmp_path):
    text = chart_text(leverage_table(lev(FY25)), liquidity_table(liq("2025-06-30")))
    manifest, _ = built(tmp_path, text)
    assert sorted(manifest["run"]["metrics"]) == ["cash", "leverage", "net_leverage", "undrawn"]
    assert sources_of(manifest) == ["cp1_leverage", "cp1_liquidity"]
    assert manifest["run"]["gaps"] == [HTML_GAP]


def test_a_missing_cp1_file_gives_no_metric_and_no_gap(tmp_path):
    manifest, _ = built(tmp_path, None)
    assert manifest["run"]["metrics"] == {} and sources_of(manifest) == []
    assert manifest["run"]["gaps"] == [HTML_GAP]
    assert "handoff_CP-1" not in manifest["sources"]


def test_the_format_gap_appears_once_for_two_off_format_tables(tmp_path):
    text = chart_text(
        leverage_table(lev("FY2025 / 2025-06-30")),
        cover_table(cov("FY2025"), cov("FY2024")),
        liquidity_table(liq("2025-06-30", "20", "6")),
    )
    manifest, _ = built(tmp_path, text)
    assert shown(manifest) == {"cash": ("20", "2025-06-30"), "undrawn": ("6", "2025-06-30")}
    assert manifest["run"]["gaps"] == [HTML_GAP, FORMAT_GAP]


def test_a_liquidity_period_with_the_ratio_format_is_off_format(tmp_path):
    manifest, _ = built(tmp_path, chart_text(liquidity_table(liq("FY2025 ended 2025-06-30"))))
    assert manifest["run"]["metrics"] == {}
    assert manifest["run"]["gaps"] == [HTML_GAP, FORMAT_GAP]


def test_the_format_gap_follows_the_expectation_gaps_and_the_html_gap(tmp_path):
    text = chart_text(leverage_table(lev("FY2025")))
    manifest, _ = built(tmp_path, text, case="synthetic")
    assert manifest["run"]["gaps"] == [
        PRIVATE_GAP,
        LEGAL_GAP,
        HTML_GAP,
        FORMAT_GAP,
    ]


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
