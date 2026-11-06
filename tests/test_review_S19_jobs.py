"""S19 review regressions: the run API's uploads, recent list, one-run guard and store bound.

Expected values are written here by hand; no provider is called (synthetic engines only).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest
from issuer_library_support import (
    HOST,
    ORIGIN,
    POST_HEADERS,
    client_of,
    fake_engine,
    make_app,
)

from deploy_workflow import platform_io
from issuer_library import jobs
from issuer_library.server import Application

UPLOAD_HEADERS = {"X-Issuer-Library": "1", "Origin": ORIGIN}
FORM = {"context": "{}", "config": "sol-medium", "cap_usd": "10.00"}


def review(client, paths: list[str], files: list[tuple[str, bytes]]):
    data = {**FORM, "source_paths": json.dumps(paths)}
    upload = [("sources", (name, raw, "text/plain")) for name, raw in files]
    return client.post("/api/runs/review", data=data, files=upload, headers=UPLOAD_HEADERS)


def test_staged_uploads_are_opened_in_binary_mode(tmp_path, monkeypatch):
    """Windows text-mode fds turn LF into CRLF; create must OR in O_BINARY (here a stand-in bit)."""
    binary = 1 << 29
    seen: list[int] = []
    real_open = os.open

    def recording(path, flags, mode=0o777, **kwargs):
        seen.append(flags)
        return real_open(path, flags & ~binary, mode, **kwargs)

    monkeypatch.setattr(os, "O_BINARY", binary, raising=False)
    monkeypatch.setattr(platform_io.os, "open", recording)
    target = tmp_path / "source.txt"
    jobs.create(target, b"line one\nline two\n")
    assert seen and all(flags & binary for flags in seen)
    assert target.read_bytes() == b"line one\nline two\n"
    with pytest.raises(FileExistsError):
        jobs.create(target, b"replacement")
    assert target.read_bytes() == b"line one\nline two\n"


@pytest.mark.parametrize(
    "name",
    ["CONIN$", "CONOUT$", "COM¹", "LPT².txt", "NUL .txt", "report.", "report ", "a/b:c.txt"],
)
def test_windows_device_and_trimmed_names_are_refused(monkeypatch, name):
    monkeypatch.setattr(jobs.os, "name", "nt")
    assert not jobs.valid_source_path(name)


def test_ordinary_windows_names_are_still_accepted(monkeypatch):
    monkeypatch.setattr(jobs.os, "name", "nt")
    for name in ["annual report.pdf", "2024/Q4 results.txt", "CONSOLE.txt", "com10.txt"]:
        assert jobs.valid_source_path(name), name


def test_posix_keeps_its_own_names(monkeypatch):
    monkeypatch.setattr(jobs.os, "name", "posix")
    assert jobs.valid_source_path("report.") and jobs.valid_source_path("CON")


def write_status(intake: Path, job_id: str, state: str, when: float) -> None:
    folder = intake / job_id
    folder.mkdir(parents=True)
    status = folder / "status.json"
    status.write_text(json.dumps({"state": state, "message": state}))
    os.utime(status, (when, when))


def test_recent_jobs_are_newest_first_by_status_time_and_keep_a_running_job(tmp_path):
    intake = tmp_path / "intake"
    now = time.time()
    # 31 stopped jobs whose random ids all sort above the running one.
    for n in range(31):
        write_status(intake, f"web-{'f' * 30}{n:02d}", "stopped", now - 86400 + n)
    running = "web-" + "0" * 32
    write_status(intake, running, "running", now - 2 * 86400)
    newest = "web-" + "1" * 32
    write_status(intake, newest, "complete", now)
    listed = [job["id"] for job in jobs.recent_jobs(str(tmp_path))]
    assert listed[0] == newest
    assert listed[1] == f"web-{'f' * 30}30" and listed[29] == f"web-{'f' * 30}02"
    assert len(listed) == 31 and listed[-1] == running


def test_a_path_that_is_both_file_and_folder_is_a_400(tmp_path):
    app, _ = make_app(tmp_path)
    app.engine = fake_engine(tmp_path)
    client = client_of(app)
    for paths in (["a", "a/b.txt"], ["a/b/c.txt", "a/b"]):
        response = review(client, paths, [("x", b"x"), ("y", b"y")])
        assert response.status_code == 400, paths
        assert "both a file and a folder" in response.text


def test_a_collision_found_only_when_staging_is_a_400(tmp_path, monkeypatch):
    """Windows folds case: 'A' then 'a/b.txt' collide in makedirs, after the path checks."""
    app, root = make_app(tmp_path)
    app.engine = fake_engine(tmp_path)
    real = os.makedirs

    def folding(name, mode=0o777, exist_ok=False):
        if Path(name).name == "a" and Path(name).parent.name == "sources":
            raise FileExistsError(17, "File exists", str(name))
        return real(name, mode, exist_ok)

    monkeypatch.setattr(jobs.os, "makedirs", folding)
    response = review(client_of(app), ["A", "a/b.txt"], [("A", b"x"), ("b.txt", b"y")])
    assert (response.status_code, response.text) == (400, "Could not retain source: a/b.txt\n")
    assert not list((root / "intake").iterdir()), "a refused upload left its staging folder"


def reviewed(client) -> str:
    response = review(client, ["a.txt"], [("a.txt", b"x")])
    assert response.status_code == 200, response.text
    return response.json()["id"]


def start(client, job_id: str):
    body = json.dumps({"id": job_id, "review_id": "review-fingerprint", "confirm": True})
    return client.post("/api/runs/start", content=body, headers=POST_HEADERS)


def test_a_failed_spawn_releases_the_one_shot_claim(tmp_path, monkeypatch):
    app, root = make_app(tmp_path)
    app.engine = fake_engine(tmp_path)
    client = client_of(app)
    job_id = reviewed(client)
    folder = root / "intake" / job_id

    def locked(self, folder):
        raise PermissionError(13, "Access is denied", "bridge.py")

    monkeypatch.setattr(jobs.Engine, "start", locked)
    response = start(client, job_id)
    assert (response.status_code, response.text) == (503, "CP-OS runtime could not start\n")
    assert not (folder / "start.claim").exists(), "no worker ran, yet the claim was kept"
    status = json.loads((folder / "status.json").read_text())
    assert status == {
        "state": "failed",
        "message": "CP-OS runtime could not start; no model call was made.",
    }
    assert not app.active_jobs
    monkeypatch.undo()
    retried = start(client, job_id)
    assert retried.status_code == 202, retried.text
    assert json.loads((folder / "worker.json").read_text())["pid"] > 0
    deadline = time.time() + 10
    while app.active_jobs and time.time() < deadline:
        time.sleep(0.05)
    assert (folder / "synthetic-starts.txt").read_text() == "one\n"


def running_job(root: Path, job_id: str, pid: int | None) -> Path:
    folder = root / "intake" / job_id
    (folder / "start.claim").write_bytes(b"")
    (folder / "status.json").write_text(json.dumps({"state": "running", "message": "m"}))
    if pid is not None:
        (folder / "worker.json").write_text(json.dumps({"pid": pid}))
    return folder


def test_a_live_worker_from_an_earlier_library_blocks_a_second_paid_start(tmp_path, monkeypatch):
    monkeypatch.setattr(jobs, "ORPHAN_POLL", 0.05)
    app, root = make_app(tmp_path)
    app.engine = fake_engine(tmp_path)
    client = client_of(app)
    first, second = reviewed(client), reviewed(client)
    worker = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
    try:
        folder = running_job(root, first, worker.pid)
        restarted = Application(app.loc, str(root), HOST, engine=app.engine)
        assert restarted.active_jobs == {first}
        again = client_of(restarted)
        refused = start(again, second)
        assert refused.status_code == 409 and "already active" in refused.text
        quit_refused = again.post("/api/quit", content="{}", headers=POST_HEADERS)
        assert quit_refused.status_code == 409
        worker.kill()
        worker.wait()
        deadline = time.time() + 10
        while restarted.active_jobs and time.time() < deadline:
            time.sleep(0.05)
        assert not restarted.active_jobs
        assert json.loads((folder / "status.json").read_text())["state"] == "interrupted"
    finally:
        worker.kill()
        worker.wait()


def test_a_running_job_without_a_live_worker_is_marked_interrupted_on_start(tmp_path):
    app, root = make_app(tmp_path)
    app.engine = fake_engine(tmp_path)
    client = client_of(app)
    dead_job, unrecorded, second = reviewed(client), reviewed(client), reviewed(client)
    finished = subprocess.run([sys.executable, "-c", "pass"], check=True)
    assert finished.returncode == 0
    dead = subprocess.Popen([sys.executable, "-c", "pass"])
    dead.wait()
    running_job(root, dead_job, dead.pid)
    running_job(root, unrecorded, None)
    restarted = Application(app.loc, str(root), HOST, engine=app.engine)
    assert not restarted.active_jobs
    states = {job["id"]: job["state"] for job in client_of(restarted).get("/api/runs/list").json()}
    assert states[dead_job] == states[unrecorded] == "interrupted"
    response = start(client_of(restarted), second)
    assert response.status_code == 202, response.text
    deadline = time.time() + 10
    while restarted.active_jobs and time.time() < deadline:
        time.sleep(0.05)


SLOW_STORE = """import time
def workspace_store(root, catalogue):
    time.sleep(1.5)
    return {"runs": {}}
"""


def test_a_store_that_does_not_answer_is_a_503_naming_the_time_limit(tmp_path, monkeypatch):
    monkeypatch.setattr(jobs, "STORE_TIMEOUT", 0.3)
    app, _ = make_app(tmp_path)
    engine = tmp_path / "slow-engine"
    engine.mkdir()
    (engine / "store.py").write_text(SLOW_STORE)
    app.engine = jobs.Engine(root=engine)
    client = client_of(app)
    began = time.monotonic()
    response = client.get("/api/workspace")
    assert response.status_code == 503
    assert response.text == (
        "the workspace store did not finish within 0.3 seconds; check that the workspace "
        "folder is available locally, then reload\n"
    )
    assert time.monotonic() - began < 1.2
    # The stuck read still holds the one slot, so a second read waits its turn, then refuses.
    assert client.get("/api/workspace").status_code == 503
    time.sleep(1.6)
    monkeypatch.setattr(jobs, "STORE_TIMEOUT", 5.0)
    assert client.get("/api/workspace").json() == {"runs": {}}
    assert threading.active_count() < 50
