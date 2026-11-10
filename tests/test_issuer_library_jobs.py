"""The run API over a synthetic engine: review stages and validates, Start launches once."""

from __future__ import annotations

import errno
import hashlib
import json
import logging
import os
import select
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import tracemalloc
from collections.abc import Callable, Iterator
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor
from concurrent.futures import wait as futures_wait
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import httpx
import pytest
import uvicorn
from fastapi import HTTPException
from fastapi.testclient import TestClient
from issuer_library_support import (
    FAKE_STORE,
    HOST,
    ORIGIN,
    POST_HEADERS,
    add_delivery,
    call,
    client_of,
    fake_engine,
    fixture,
    locations,
    make_app,
    put,
)
from starlette.datastructures import FormData, UploadFile

import issuer_library.__main__ as main_module
import issuer_library.events as events_module
import issuer_library.jobs as jobs_module
import issuer_library.server as server_module
from issuer_library import notify
from issuer_library.events import progress
from issuer_library.jobs import Engine, job_view, mkdir_all_in, recorded_job
from issuer_library.launch import cookie_name
from issuer_library.server import Application
from issuer_library.settings import save_json

UPLOAD_HEADERS = {"X-Issuer-Library": "1", "Origin": ORIGIN}


def intake_entries(root: Path) -> list[str]:
    folder = root / "intake"
    return sorted(path.name for path in folder.iterdir()) if folder.is_dir() else []


def review_request(client: TestClient, paths: str, **fields: str) -> Any:
    data = {
        "context": "{}",
        "config": "sol-medium",
        "cap_usd": "10.00",
        "source_paths": paths,
        "modules": "CP-4",
        "max_turns": "7",
        **fields,
    }
    files = [("sources", ("../../original.txt", b"Synthetic source", "text/plain"))]
    return client.post("/api/runs/review", data=data, files=files, headers=UPLOAD_HEADERS)


def start_payload(job_id: str, confirm: bool = True) -> str:
    return json.dumps({"id": job_id, "review_id": "review-fingerprint", "confirm": confirm})


def reviewed(tmp_path: Path) -> tuple[Application, Path, TestClient, str]:
    app, root = make_app(tmp_path)
    app.engine = fake_engine(tmp_path)
    client = client_of(app)
    response = review_request(client, '["annual.txt"]')
    assert response.status_code == 200, response.text
    return app, root, client, response.json()["id"]


def wait_idle(app: Application) -> None:
    deadline = time.time() + 5
    while time.time() < deadline:
        with app.lock:
            if not app.active_jobs:
                return
        time.sleep(0.02)
    raise AssertionError("worker did not finish")


def test_upload_review_does_not_start_and_retains_the_folder_layout(tmp_path: Path) -> None:
    app, root = make_app(tmp_path)
    app.engine = fake_engine(tmp_path)
    client = client_of(app)
    response = review_request(client, '["filings/annual.txt"]')
    assert response.status_code == 200, response.text
    folder = root / "intake" / response.json()["id"]
    assert (folder / "sources/filings/annual.txt").read_bytes() == b"Synthetic source"
    job = json.loads((folder / "job.json").read_bytes())
    assert (job["modules"], job["max_turns"], job["config"]) == (["CP-4"], 7, "sol-medium")
    assert job["sources"][0]["path"] == "filings/annual.txt"
    assert json.loads((folder / "status.json").read_bytes())["state"] == "reviewed"
    assert not (folder / "synthetic-starts.txt").exists(), "review executed"
    assert not (root / "original.txt").exists(), "upload filename escaped staging"
    listed = client.get("/api/runs/list").json()
    assert listed == [], "a reviewed run is not recent activity"


@pytest.mark.parametrize(
    "paths",
    [
        '["../../original.txt"]',
        '["/etc/original.txt"]',
        '["a/../../original.txt"]',
        '["a/./b.txt"]',
        '["a\\\\b.txt"]',
        '["."]',
        '[""]',
        '["a","b"]',
        "not json",
        "[1]",
        "null",
    ],
)
def test_upload_refuses_paths_outside_the_chosen_folder(tmp_path: Path, paths: str) -> None:
    app, root = make_app(tmp_path)
    app.engine = fake_engine(tmp_path)
    client = client_of(app)
    response = review_request(client, paths)
    assert response.status_code == 400, f"{paths} accepted: {response.text}"
    assert not (root / "original.txt").exists(), "upload escaped staging"
    assert intake_entries(root) == [], "refused upload left an intake folder"


def test_upload_options_are_validated_before_staging(tmp_path: Path) -> None:
    app, root = make_app(tmp_path)
    app.engine = fake_engine(tmp_path)
    client = client_of(app)
    for fields, text in [
        ({"modules": "CP-4 cp-5"}, "CP codes"),
        ({"max_turns": "0"}, "Max turns"),
        # P bounds turns at 1-64 (key/jobs.go:465-471, "Max turns must be between 1 and 64").
        ({"max_turns": "65"}, "Max turns must be between 1 and 64"),
        ({"max_turns": "x"}, "Max turns"),
    ]:
        response = review_request(client, '["annual.txt"]', **fields)
        assert response.status_code == 400 and text in response.text, fields
    assert intake_entries(root) == []
    response = review_request(client, '["annual.txt"]', max_turns="", modules="")
    assert response.status_code == 200
    job = json.loads((root / "intake" / response.json()["id"] / "job.json").read_bytes())
    assert (job["max_turns"], job["modules"]) == (32, [])


def test_upload_total_limit_refuses_before_staging(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    app, root = make_app(tmp_path)
    app.engine = fake_engine(tmp_path)
    client = client_of(app)
    monkeypatch.setattr(server_module, "UPLOAD_LIMIT", 64)
    response = review_request(client, '["annual.txt"]')
    assert response.status_code == 400 and "512 MiB" in response.text
    assert intake_entries(root) == []


def test_workspace_store_comes_from_the_engine_with_the_catalogue(tmp_path: Path) -> None:
    app, root = make_app(tmp_path)
    app.engine = fake_engine(tmp_path)
    client = client_of(app)
    response = client.get("/api/workspace")
    assert response.status_code == 200, response.text
    assert response.json() == {"parsed": str(root), "folder": str(root)}
    broken = tmp_path / "broken"
    broken.mkdir()
    (broken / "store.py").write_text(
        "def workspace_store(root, catalogue):\n    raise OSError('x')\n"
    )
    app.engine = Engine(root=broken)
    response = client.get("/api/workspace")
    assert response.status_code == 503 and "could not be read" in response.text


def test_explicit_start_is_one_shot_under_concurrent_requests(tmp_path: Path) -> None:
    app, root, client, job_id = reviewed(tmp_path)
    invalid = client.post(
        "/api/runs/start", content=start_payload(job_id, False), headers=POST_HEADERS
    )
    assert invalid.status_code == 400, "implicit start accepted"
    extra = json.dumps({"id": job_id, "confirm": True, "extra": 1})
    for body in [extra, "[]", "x" * 9000]:
        assert client.post("/api/runs/start", content=body, headers=POST_HEADERS).status_code == 400
    unreviewed = client.post(
        "/api/runs/start", content=json.dumps({"id": job_id, "confirm": True}), headers=POST_HEADERS
    )
    assert unreviewed.status_code == 409, "a start without the reviewed fingerprint was accepted"
    codes: list[int] = []

    def start() -> None:
        codes.append(
            client.post(
                "/api/runs/start", content=start_payload(job_id), headers=POST_HEADERS
            ).status_code
        )

    threads = [threading.Thread(target=start) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert sorted(codes) == [202, 409]
    wait_idle(app)
    assert (root / "intake" / job_id / "synthetic-starts.txt").read_text() == "one\n"
    status = client.get(f"/api/runs/status?id={job_id}")
    assert status.status_code == 200 and status.json()["state"] == "stopped"
    assert status.json()["run_available"] is False
    assert client.get("/api/runs/list").json()[0]["id"] == job_id
    again = client.post("/api/runs/start", content=start_payload(job_id), headers=POST_HEADERS)
    assert again.status_code == 409 and "already been started" in again.text


def test_source_uploads_require_origin_and_custom_header(tmp_path: Path) -> None:
    app, _ = make_app(tmp_path)
    client = client_of(app)
    response = client.post(
        "/api/runs/review", content=b"anything", headers={"Origin": "https://untrusted.invalid"}
    )
    assert response.status_code == 403, "cross-origin upload accepted"
    assert client.post("/api/runs/review").status_code == 403, "implicit app request accepted"
    other = client.post("/api/runs/other", content="{}", headers=POST_HEADERS)
    assert other.status_code in (404, 405), "an unknown run action was handled"


def test_start_refuses_unconfigured_provider_before_creating_claim(tmp_path: Path) -> None:
    _, root, client, job_id = reviewed(tmp_path)
    folder = root / "intake" / job_id
    review = json.loads((folder / "review.json").read_bytes())
    review["provider_ready"] = False
    save_json(folder / "review.json", review)
    response = client.post("/api/runs/start", content=start_payload(job_id), headers=POST_HEADERS)
    assert response.status_code == 409, "unconfigured execution accepted"
    assert not (folder / "start.claim").exists(), "unconfigured run consumed its one-shot claim"


def test_corrupted_review_is_refused_before_starting(tmp_path: Path) -> None:
    _, root, client, job_id = reviewed(tmp_path)
    file = root / "intake" / job_id / "review.json"
    file.write_bytes(file.read_bytes() + b"{}")
    response = client.post("/api/runs/start", content=start_payload(job_id), headers=POST_HEADERS)
    assert response.status_code == 409, "corrupted review started a worker"
    file.unlink()
    response = client.post("/api/runs/start", content=start_payload(job_id), headers=POST_HEADERS)
    assert response.status_code == 409 and "Review this run" in response.text


def test_worker_uses_utf8_independent_of_windows_locale(tmp_path: Path) -> None:
    command = fake_engine(tmp_path).command("review", tmp_path)
    assert "-X" in command and "utf8" in command and "-I" in command


def test_status_only_offers_an_existing_run(tmp_path: Path) -> None:
    app, root = make_app(tmp_path)
    client = client_of(app)
    job_id = "web-" + "a" * 32
    folder = root / "intake" / job_id
    save_json(folder / "status.json", {"state": "failed"})

    def available() -> bool:
        response = client.get(f"/api/runs/status?id={job_id}")
        assert response.status_code == 200, response.text
        return bool(response.json()["run_available"])

    assert not available(), "failed validation offered a nonexistent run"
    (root / "runs" / job_id).mkdir(parents=True)
    assert available(), "retained run is unavailable"
    save_json(root / "runs" / job_id / "progress.json", {"module": "CP-1", "step": "accepted"})
    assert client.get(f"/api/runs/status?id={job_id}").json()["progress"]["module"] == "CP-1"
    assert client.get("/api/runs/status?id=web-short").status_code == 404
    assert client.get("/api/runs/status?id=web-" + "b" * 32).status_code == 404
    (folder / "status.json").write_text("{")
    assert client.get(f"/api/runs/status?id={job_id}").status_code == 500


def test_run_list_and_status_carry_review_and_progress(tmp_path: Path) -> None:
    app, root = make_app(tmp_path)
    client = client_of(app)
    a, b = "web-" + "a" * 32, "web-" + "b" * 32
    files = {
        f"intake/{a}/status.json": '{"state":"running","message":"Working"}',
        f"intake/{a}/review.json": (
            '{"review_id":"x","issuer":"Northbridge Group","pathway":"covenant_refinancing",'
            '"as_of":"2025-03-31","modules":["CP-0","CP-1"],"module_details":[{"id":"CP-0",'
            '"title":"Source readiness","purpose":"p"}],"cap_usd":"10.00"}'
        ),
        f"runs/{a}/progress.json": '{"module":"CP-1","step":"started","spent_usd":"0.10"}',
        f"intake/{b}/status.json": '{"state":"stopped","message":"Halted"}',
    }
    for name, text in files.items():
        (root / name).parent.mkdir(parents=True, exist_ok=True)
        (root / name).write_text(text)

    def check_a(row: dict[str, Any]) -> None:
        assert row["issuer"] == "Northbridge Group" and row["pathway"] == "covenant_refinancing"
        assert row["as_of"] == "2025-03-31"
        assert row["modules"] == ["CP-0", "CP-1"] and len(row["module_details"]) == 1
        assert row["progress"]["module"] == "CP-1" and row["run_available"] is True
        assert "cap_usd" not in row and "review_id" not in row, "review fields leaked"

    rows = client.get("/api/runs/list").json()
    assert sorted(row["id"] for row in rows) == [a, b]
    for row in rows:
        if row["id"] == a:
            check_a(row)
        else:
            assert "issuer" not in row and row["run_available"] is False, row
    status = client.get(f"/api/runs/status?id={a}")
    assert status.status_code == 200, status.text
    check_a(status.json())
    # A review or progress file that is not a JSON object is left out, not an error.
    (root / f"intake/{b}/review.json").write_text('["Northbridge Group"]')
    (root / f"runs/{b}").mkdir(parents=True)
    (root / f"runs/{b}/progress.json").write_text("{")
    row = client.get(f"/api/runs/status?id={b}").json()
    assert "issuer" not in row and "progress" not in row and row["run_available"] is True


def test_review_prepares_an_empty_workspace_without_executing(tmp_path: Path) -> None:
    root = tmp_path / "empty"
    root.mkdir()
    loc = server_module.Locations(state=tmp_path / "state", documents=tmp_path / "documents")
    app = Application(loc, str(root), HOST, engine=fake_engine(tmp_path))
    client = client_of(app)
    response = review_request(client, '["annual.txt"]')
    assert response.status_code == 200, response.text
    for name in ["runs", "deliverables"]:
        assert list((root / name).iterdir()) == [], f"fresh workspace {name} was not prepared"


def test_a_refused_review_leaves_no_intake_folder(tmp_path: Path) -> None:
    app, root = make_app(tmp_path)
    engine = fake_engine(tmp_path)
    (engine.root / "bridge.py").write_text(
        "import json,sys;print(json.dumps({'ok':False,'problems':['synthetic refusal']}));sys.exit(2)\n"
    )
    app.engine = engine
    client = client_of(app)
    response = review_request(client, '["annual.txt"]')
    assert response.status_code == 200 and response.json()["problems"] == ["synthetic refusal"]
    assert intake_entries(root) == []
    (engine.root / "bridge.py").write_text("import sys;print('not json');sys.exit(1)\n")
    response = review_request(client, '["annual.txt"]')
    assert response.status_code == 503 and "could not complete" in response.text
    assert intake_entries(root) == []


def test_worker_exit_without_a_result_is_recorded_as_interrupted(tmp_path: Path) -> None:
    app, root, client, job_id = reviewed(tmp_path)
    (app.engine.root / "bridge.py").write_text("import sys;sys.exit(3)\n")
    response = client.post("/api/runs/start", content=start_payload(job_id), headers=POST_HEADERS)
    assert response.status_code == 202
    wait_idle(app)
    status = json.loads((root / "intake" / job_id / "status.json").read_bytes())
    assert status["state"] == "interrupted" and "no automatic paid retry" in status["message"]


def test_save_json_waits_for_a_file_held_open(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Windows refuses to replace a file a scanner holds open for a moment."""
    name = tmp_path / "status.json"
    held = {"count": 0}
    real = os.replace

    def held_twice(source: Any, target: Any, **options: Any) -> None:
        if str(target) == str(name) and held["count"] < 2:
            held["count"] += 1
            raise PermissionError(13, "held open", str(target))
        real(source, target, **options)

    monkeypatch.setattr(os, "replace", held_twice)
    monkeypatch.setattr(time, "sleep", lambda _: None)
    save_json(name, {"state": "interrupted"})
    assert held["count"] == 2 and json.loads(name.read_bytes()) == {"state": "interrupted"}
    assert [path.name for path in tmp_path.iterdir()] == ["status.json"], "temporary file left"


# --- sub-task 5A: run events, progress from the event log, run-list recency, turn bound ---
# Ported from key/jobs_test.go (final-workflow P dd3dfa18); expected values are the Go ones.

EVENTS_ID = "web-" + "c0c0c0c0c0c0c0c0c0c0c0c0c0c0c0c0"

# Hand-written log: CP-0 accepted after one turn; CP-1 on its second turn.
EVENT_LINES = """{"at":"2026-11-07T10:00:00Z","event":"module_started","module":"CP-0"}
{"at":"2026-11-07T10:00:01Z","event":"turn","module":"CP-0","turn":1,"max_turns":32,"spent_usd":"0","held_usd":"1.50","cap_usd":"10"}
{"at":"2026-11-07T10:00:02Z","event":"module_accepted","module":"CP-0"}
{"at":"2026-11-07T10:00:03Z","event":"module_started","module":"CP-1"}
{"at":"2026-11-07T10:00:04Z","event":"turn","module":"CP-1","turn":1,"max_turns":32,"spent_usd":"0.40","held_usd":"1.50","cap_usd":"10"}
{"at":"2026-11-07T10:00:05Z","event":"turn","module":"CP-1","turn":2,"max_turns":32,"spent_usd":"0.85","held_usd":"1.60","cap_usd":"10"}
"""
ACTIVITY_LINES = """{"at":"2026-11-08T09:00:00Z","event":"module_started","module":"CP-0"}
{"at":"2026-11-08T09:00:01Z","event":"turn","module":"CP-0","turn":1,"max_turns":24,"spent_usd":"0.00","held_usd":"5.73","cap_usd":"10"}
{"at":"2026-11-08T09:00:02Z","event":"draft_rejected","module":"CP-0","writes_left":2}
{"at":"2026-11-08T09:00:03Z","event":"module_accepted","module":"CP-0"}
{"at":"2026-11-08T09:00:04Z","event":"delivery_started"}
{"at":"2026-11-08T09:00:05Z","event":"delivered"}
"""


def write_events(root: Path, job_id: str, text: str) -> None:
    put(root, f"runs/{job_id}/events.jsonl", text.encode())


def write_job(root: Path, job_id: str, state: str, when: float) -> None:
    put(root, f"intake/{job_id}/status.json", json.dumps({"state": state}).encode())
    os.utime(root / "intake" / job_id / "status.json", (when, when))


def listed_jobs(client: TestClient) -> list[str]:
    response = client.get("/api/runs/list")
    assert response.status_code == 200, response.text
    return [row["id"] for row in response.json()]


def get_events(client: TestClient) -> Any:
    return client.get(f"/api/runs/events?id={EVENTS_ID}")


def test_job_view_carries_the_first_event_time_as_started_at(tmp_path: Path) -> None:
    put(tmp_path, f"intake/{EVENTS_ID}/status.json", b'{"state":"stopped"}')
    view = job_view(str(tmp_path), EVENTS_ID)
    assert view is not None and "started_at" not in view, "a run with no log invented a time"
    write_events(tmp_path, EVENTS_ID, EVENT_LINES)
    view = job_view(str(tmp_path), EVENTS_ID)
    assert view is not None and view["started_at"] == "2026-11-07T10:00:00Z"
    write_events(tmp_path, EVENTS_ID, '{"event":"module_started","module":"CP-0"}\n')
    view = job_view(str(tmp_path), EVENTS_ID)
    assert view is not None and view.get("started_at") is None


def test_run_progress_folds_events(tmp_path: Path) -> None:
    folder = tmp_path / "runs" / EVENTS_ID
    rejected = (
        '{"at":"2026-11-07T10:00:06Z","event":"draft_rejected","module":"CP-1","writes_left":2}\n'
    )
    write_events(tmp_path, EVENTS_ID, EVENT_LINES + rejected)
    assert progress(folder) == {
        "module": "CP-1",
        "step": "repairing",
        "turn": 2,
        "max_turns": 32,
        "spent_usd": "0.85",
        "held_usd": "1.60",
        "cap_usd": "10",
        "accepted": 1,
    }
    accepted = '{"at":"x","event":"module_accepted","module":"CP-1"}\n'
    delivering = '{"at":"x","event":"delivery_started"}\n'
    write_events(tmp_path, EVENTS_ID, EVENT_LINES + accepted + delivering)
    got = progress(folder)
    assert got is not None and got["step"] == "delivering" and got["accepted"] == 2
    stopped = '{"at":"x","event":"stopped","reason":"budget"}\n'
    write_events(tmp_path, EVENTS_ID, EVENT_LINES + stopped)
    got = progress(folder)
    assert got is not None
    assert (got["step"], got["turn"], got["stopped_during"]) == ("stopped", 2, "running")
    other = '{"at":"x","event":"stopped","reason":"other"}\n'
    write_events(tmp_path, EVENTS_ID, EVENT_LINES + accepted + delivering + other)
    got = progress(folder)
    assert got is not None
    assert (got["step"], got["stopped_during"], got["accepted"]) == ("stopped", "delivering", 2)
    write_events(tmp_path, EVENTS_ID, '{"at":"x","event":"module_started","module":"CP-0"}\n')
    got = progress(folder)
    assert got is not None and (got["step"], got["accepted"]) == ("started", 0)


def test_run_progress_ignores_a_truncated_last_line(tmp_path: Path) -> None:
    write_events(tmp_path, EVENTS_ID, EVENT_LINES + '{"at":"2026-11-07T10:00:06Z","event":"tur')
    got = progress(tmp_path / "runs" / EVENTS_ID)
    assert got is not None, "truncated tail lost the progress"
    assert (got["turn"], got["step"], got["accepted"]) == (2, "running", 1)


def test_run_progress_falls_back_to_progress_json(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    folder = tmp_path / "runs" / EVENTS_ID
    assert progress(folder) is None, "progress from nothing"
    want = {"module": "CP-1", "step": "started", "spent_usd": "0.10"}
    put(tmp_path, f"runs/{EVENTS_ID}/progress.json", json.dumps(want).encode())
    assert progress(folder) == want, "retained fallback"
    # An empty log (run started, no module dispatched yet) has no progress; progress.json serves.
    write_events(tmp_path, EVENTS_ID, "")
    assert progress(folder) == want, "empty log"
    # A corrupt earlier line skips the whole log (documented fail-open, logged once).
    write_events(tmp_path, EVENTS_ID, "not json\n" + EVENT_LINES)
    with caplog.at_level(logging.WARNING, logger="issuer_library"):
        assert progress(folder) == want, "corrupt earlier line"
    warnings = [record for record in caplog.records if "unreadable line" in record.getMessage()]
    assert len(warnings) == 1 and EVENTS_ID in warnings[0].getMessage()


def test_run_progress_is_absent_with_neither_file(tmp_path: Path) -> None:
    app, root = make_app(tmp_path)
    client = client_of(app)
    write_job(root, EVENTS_ID, "running", time.time())
    response = client.get(f"/api/runs/status?id={EVENTS_ID}")
    assert response.status_code == 200, response.text
    assert "progress" not in response.json(), "progress invented"


def test_progress_of_a_cut_log_is_marked_incomplete(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    head = '{"at":"2026-11-07T10:00:00Z","event":"module_started","module":"CP-0"}\n'
    tail = (
        '{"at":"2026-11-07T10:00:02Z","event":"module_accepted","module":"CP-0"}\n'
        '{"at":"2026-11-07T10:00:05Z","event":"stopped","reason":"budget"}\n'
    )
    write_events(tmp_path, EVENTS_ID, head + tail)
    folder = tmp_path / "runs" / EVENTS_ID
    whole = progress(folder)
    assert whole is not None and "incomplete" not in whole and whole["accepted"] == 1
    monkeypatch.setattr(events_module, "EVENTS_LIMIT", len(head) + 10)
    cut = progress(folder)
    assert cut is not None and cut["incomplete"] is True, "cut log carries no incomplete mark"


def test_run_events_endpoint_lists_every_event_with_its_fields(tmp_path: Path) -> None:
    app, root = make_app(tmp_path)
    client = client_of(app)
    write_job(root, EVENTS_ID, "running", time.time())
    write_events(root, EVENTS_ID, ACTIVITY_LINES)
    response = get_events(client)
    body = response.json()
    assert response.status_code == 200 and len(body["events"]) == 6 and body["complete"], body
    events = body["events"]
    assert events[0]["at"] == "2026-11-08T09:00:00Z" and events[0]["event"] == "module_started"
    assert events[1]["held_usd"] == "5.73" and events[1]["turn"] == 1
    assert events[1]["max_turns"] == 24
    assert events[2]["writes_left"] == 2
    assert events[5]["event"] == "delivered"


def test_run_events_endpoint_drops_a_truncated_last_line(tmp_path: Path) -> None:
    app, root = make_app(tmp_path)
    client = client_of(app)
    write_job(root, EVENTS_ID, "running", time.time())
    kept = ACTIVITY_LINES[: ACTIVITY_LINES.rstrip("\n").rfind("\n") + 1]
    write_events(root, EVENTS_ID, kept + '{"event":"tur')
    response = get_events(client)
    body = response.json()
    assert response.status_code == 200 and len(body["events"]) == 5 and not body["complete"]


def test_run_events_endpoint_without_a_log_is_an_empty_list(tmp_path: Path) -> None:
    app, root = make_app(tmp_path)
    client = client_of(app)
    assert get_events(client).status_code == 404, "neither file"
    write_job(root, EVENTS_ID, "running", time.time())
    response = get_events(client)
    assert response.status_code == 200
    assert response.json() == {"events": [], "complete": True}


def test_run_events_stops_at_the_read_limit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(events_module, "EVENTS_LIMIT", 300)
    app, root = make_app(tmp_path)
    client = client_of(app)
    write_job(root, EVENTS_ID, "running", time.time())
    write_events(root, EVENTS_ID, ACTIVITY_LINES)
    response = get_events(client)
    body = response.json()
    assert response.status_code == 200 and not body["complete"], response.text
    assert 0 < len(body["events"]) < 6, response.text


def test_run_events_refuses_a_bad_id_and_reports_an_unreadable_log(tmp_path: Path) -> None:
    # Added for the Go routing (key/jobs.go:371-405): bad id is 404; a log that cannot be read
    # (here a directory) is 500 "Run events are unreadable".
    app, root = make_app(tmp_path)
    client = client_of(app)
    assert client.get("/api/runs/events?id=nope").status_code == 404
    (root / "runs" / EVENTS_ID / "events.jsonl").mkdir(parents=True)
    response = get_events(client)
    assert response.status_code == 500 and "Run events are unreadable" in response.text


def test_run_event_fields_follow_the_go_struct_decoding(tmp_path: Path) -> None:
    # Added: Go json.Unmarshal into runEvent (key/jobs.go:161-172). Unknown keys drop, null
    # decodes to an empty event, writes_left 0 stays, a float turn makes the line unreadable.
    app, root = make_app(tmp_path)
    client = client_of(app)
    write_job(root, EVENTS_ID, "running", time.time())
    write_events(
        root,
        EVENTS_ID,
        '{"event":"turn","turn":3,"extra":1,"reason":null,"writes_left":0}\nnull\n'
        '{"event":"turn","turn":1.5}\n{"event":"x"}\n',
    )
    body = get_events(client).json()
    assert body == {
        "events": [{"event": "turn", "turn": 3, "writes_left": 0}, {"event": ""}],
        "complete": False,
    }


def test_review_refuses_more_turns_than_the_loop_allows(tmp_path: Path) -> None:
    app, _ = make_app(tmp_path)
    app.engine = fake_engine(tmp_path)
    client = client_of(app)
    assert review_request(client, '["a.txt"]', max_turns="65").status_code == 400
    assert review_request(client, '["a.txt"]', max_turns="64").status_code == 200


def test_run_list_follows_recency_and_always_keeps_active_jobs(tmp_path: Path) -> None:
    app, root = make_app(tmp_path)
    client = client_of(app)
    now = time.time()
    # Ids sort opposite to age: the newest jobs have the smallest ids.
    for i in range(40):
        write_job(root, f"web-{0x100 + i:032x}", "complete", now - (i + 1) * 3600)
    newest = "web-" + "0" * 31 + "1"
    write_job(root, newest, "running", now)
    old_running = "web-" + "f" * 32
    write_job(root, old_running, "running", now - 500 * 3600)
    draft = "web-" + "a" * 32
    write_job(root, draft, "reviewed", now)
    ids = listed_jobs(client)
    assert len(ids) == 30, f"{len(ids)} rows, want the 30 cap: {ids}"
    assert ids[0] == newest, "the just-started job must lead the list"
    assert old_running in ids, "a running job must be listed even when its status file is old"
    assert draft not in ids, "a reviewed-only draft is not a run"
    # 28 finished jobs fill the remaining places: the 28 newest by write time.
    for i in range(28):
        assert f"web-{0x100 + i:032x}" in ids, f"finished job {i} (newer than the cut) missing"
    # key/jobs_test.go:661-663: an older finished job must not displace a newer one.
    assert f"web-{0x100 + 28:032x}" not in ids, "an older finished job displaced a newer one"


def test_review_run_list_many_stale_active_jobs_exceed_the_cap(tmp_path: Path) -> None:
    app, root = make_app(tmp_path)
    client = client_of(app)
    now = time.time()
    for i in range(35):
        write_job(root, f"web-{0x200 + i:032x}", "running", now - (100 + i) * 3600)
    for i in range(5):
        write_job(root, f"web-{0x300 + i:032x}", "running", now - (200 + i) * 3600)
    for i in range(10):
        write_job(root, f"web-{0x400 + i:032x}", "complete", now - i * 60)
    ids = listed_jobs(client)
    assert len(ids) == 40, f"{len(ids)} rows, want all 40 active jobs"
    for i, job_id in enumerate(ids):
        want = f"web-{0x200 + i:032x}" if i < 35 else f"web-{0x300 + i - 35:032x}"
        assert job_id == want, f"row {i} is {job_id}, want {want} (newest first)"


def test_review_run_list_equal_times_and_unreadable_status(tmp_path: Path) -> None:
    app, root = make_app(tmp_path)
    client = client_of(app)
    when = 1793966400.0  # 2026-11-06T12:00:00Z (key/jobs_test.go:800)
    for i in range(33):
        write_job(root, f"web-{0x500 + i:032x}", "complete", when)
    bad = {"web-" + "e" * 32: b"{not json", "web-" + "d" * 32: b""}
    for job_id, raw in bad.items():
        put(root, f"intake/{job_id}/status.json", raw)
    put(root, "intake/web-" + "c" * 32 + "/status.json/inner", b'{"state":"running"}')
    put(root, "intake/web-" + "b" * 32, b'{"state":"running"}')
    put(root, "intake/notes/status.json", b'{"state":"running"}')
    first, second = listed_jobs(client), listed_jobs(client)
    assert len(first) == 30 and first == second, f"{len(first)} rows: {first}"
    for i, job_id in enumerate(first):
        assert job_id == f"web-{0x500 + 32 - i:032x}", f"row {i} is {job_id}"


@pytest.mark.parametrize(
    "log",
    [
        '{"event":"stopped","reason":"\\udcff"}\n',
        '{"event":"module_started","module":"CP-\\ud800"}\n',
        '{"event":"turn","x":' + "[" * 1500 + "]" * 1500 + "}\n",
        '{"event":"turn"}\n{"x":' + "[" * 1500,
        '{"event":"turn"}\n{"x":' + "[" * 20000 + '\n{"event":"turn"}\n',
        "[" * 200000 + "\n",
    ],
)
def test_run_endpoints_survive_lone_surrogates_and_over_deep_lines(
    tmp_path: Path, log: str
) -> None:
    # Go reads a lone surrogate escape as U+FFFD and refuses over-deep nesting as an unreadable
    # line; neither fails a request (reviewer probes 5A-adv-1, 5A-adv-2).
    app, root = make_app(tmp_path)
    client = client_of(app)
    put(root, f"intake/{EVENTS_ID}/status.json", b'{"state":"running"}')
    write_events(root, EVENTS_ID, log)
    for path in (f"/api/runs/events?id={EVENTS_ID}", f"/api/runs/status?id={EVENTS_ID}"):
        assert client.get(path).status_code == 200, path
    assert client.get("/api/runs/list").status_code == 200


def test_run_list_decodes_status_like_the_go_struct(tmp_path: Path) -> None:
    # key/jobs.go:315-325: struct{State string}: missing or null state is "", "State" matches
    # case-insensitively, a non-string state is a decode error (skipped).
    app, root = make_app(tmp_path)
    cases = {
        "web-" + "1" * 32: b"{}",
        "web-" + "2" * 32: b'{"state":null,"message":"m"}',
        "web-" + "3" * 32: b'{"State":"running"}',
        "web-" + "4" * 32: b'{"state":5}',
    }
    for job_id, raw in cases.items():
        put(root, f"intake/{job_id}/status.json", raw)
    listed = listed_jobs(client_of(app))
    assert sorted(listed) == sorted(j for j in cases if j[4] in "123"), listed


# Resume: the fake bridge of the Go key (its review also echoes max_turns and resume_of; its start
# waits while <folder>/hold exists). Support's FAKE_BRIDGE lacks both and is not editable here.
RESUME_BRIDGE = """import json,sys,pathlib,time
folder=pathlib.Path(sys.argv[2])
job=json.loads((folder/'job.json').read_text())
if sys.argv[1]=='review':
 print(json.dumps({'ok':True,'review_id':'review-fingerprint','id':job['id'],'provider_ready':True,'counted':[],'cap_usd':job['cap_usd'],'max_turns':job['max_turns'],'resume_of':job.get('resume_of')}))
else:
 with (folder/'synthetic-starts.txt').open('a') as stream: stream.write('one\\n')
 while (folder/'hold').exists(): time.sleep(.02)
 time.sleep(.15)
 (folder/'status.json').write_text(json.dumps({'state':'stopped',
 'message':'Synthetic worker seam only; no provider called.'}))
"""
RESUME_STORE = (
    "def workspace_store(root, catalogue):\n    return {'parsed': catalogue['workspace']}\n"
)


def stopped_run(tmp_path: Path) -> tuple[Application, Path, TestClient, str]:
    app, root = make_app(tmp_path)
    engine = tmp_path / "resume-engine"
    engine.mkdir()
    (engine / "bridge.py").write_text(RESUME_BRIDGE)
    (engine / "store.py").write_text(RESUME_STORE)
    app.engine = Engine(root=engine, python=sys.executable)
    client = client_of(app)
    job_id = review_request(client, '["annual.txt"]').json()["id"]
    assert call(client, "POST", "/api/runs/start", start_payload(job_id)).status_code == 202
    for _ in range(100):
        status = root / "intake" / job_id / "status.json"
        with app.lock:
            idle = not app.active_jobs
        if idle and b'"stopped"' in status.read_bytes():
            return app, root, client, job_id
        time.sleep(0.05)
    raise AssertionError("the synthetic run did not stop")


def link_or_skip(link: Path, target: Path) -> None:
    try:
        link.symlink_to(target)
    except OSError as error:
        pytest.skip(f"symlinks unavailable: {error}")


def resume_body(job_id: str, **fields: Any) -> str:
    return json.dumps({"id": job_id, "cap_usd": "12.00", "max_turns": 9, **fields})


def test_resume_reviews_a_copy_of_the_stopped_run_as_a_new_job(tmp_path: Path) -> None:
    _, root, client, job_id = stopped_run(tmp_path)
    old_job = (root / "intake" / job_id / "job.json").read_bytes()
    response = call(client, "POST", "/api/runs/resume", resume_body(job_id))
    assert response.status_code == 200, response.text
    result = response.json()
    new = result["id"]
    assert new not in ("", job_id) and result["resume_of"] == job_id and result["max_turns"] == 9
    job = json.loads((root / "intake" / new / "job.json").read_bytes())
    assert list(job) == [
        "id", "workspace", "config", "cap_usd", "modules", "max_turns", "sources", "resume_of",
    ]  # fmt: skip
    assert (job["resume_of"], job["cap_usd"], job["max_turns"]) == (job_id, "12.00", 9)
    assert (job["config"], job["modules"]) == ("sol-medium", ["CP-4"])
    assert [source["path"] for source in job["sources"]] == ["annual.txt"]
    assert (root / "intake" / new / "sources" / "annual.txt").read_bytes() == b"Synthetic source"
    assert b'"reviewed"' in (root / "intake" / new / "status.json").read_bytes()
    assert (root / "intake" / job_id / "job.json").read_bytes() == old_job
    assert not (root / "intake" / new / "synthetic-starts.txt").exists(), "resume ran a worker"
    assert call(client, "GET", f"/api/runs/status?id={new}").json()["resume_of"] == job_id


def test_resume_refuses_a_running_or_reviewed_job(tmp_path: Path) -> None:
    _, root, client, job_id = stopped_run(tmp_path)
    for state in ("reviewed", "running"):
        save_json(root / "intake" / job_id / "status.json", {"state": state, "id": job_id})
        response = call(client, "POST", "/api/runs/resume", resume_body(job_id))
        assert response.status_code == 409, state
        assert "Only a stopped, failed or interrupted run can be resumed" in response.text
    assert len(intake_entries(root)) == 1, "a refused resume left an intake folder"


def test_resume_refuses_when_the_stopped_runs_inputs_are_gone(tmp_path: Path) -> None:
    _, root, client, job_id = stopped_run(tmp_path)
    shutil.rmtree(root / "intake" / job_id / "sources")
    response = call(client, "POST", "/api/runs/resume", resume_body(job_id))
    assert response.status_code == 409
    assert "The stopped run's inputs are no longer in the workspace" in response.text
    assert len(intake_entries(root)) == 1


def test_resume_refuses_a_bad_request(tmp_path: Path) -> None:
    _, _, client, job_id = stopped_run(tmp_path)
    for body in (
        resume_body("nope"),
        resume_body(job_id, cap_usd=""),
        resume_body(job_id, max_turns=0),
        resume_body(job_id, max_turns=65),
        resume_body(job_id, config="other"),
    ):
        assert call(client, "POST", "/api/runs/resume", body).status_code == 400, body


def test_resumed_job_starts_only_through_confirmed_start(tmp_path: Path) -> None:
    _, root, client, job_id = stopped_run(tmp_path)
    new = call(client, "POST", "/api/runs/resume", resume_body(job_id)).json()["id"]
    folder = root / "intake" / new
    assert not (folder / "start.claim").exists(), "resume claimed a start"
    refused = call(client, "POST", "/api/runs/start", start_payload(new, confirm=False))
    assert refused.status_code == 400
    assert not (folder / "synthetic-starts.txt").exists(), "an unconfirmed start ran"
    started = call(client, "POST", "/api/runs/start", start_payload(new))
    assert started.status_code == 202, started.text
    for _ in range(100):
        if (folder / "synthetic-starts.txt").exists():
            break
        time.sleep(0.05)
    assert (folder / "synthetic-starts.txt").read_text() == "one\n"


def test_resume_copies_only_the_listed_regular_files(tmp_path: Path) -> None:
    _, root, client, job_id = stopped_run(tmp_path)
    (root / "outside.txt").write_text("secret")
    sources = root / "intake" / job_id / "sources"
    link_or_skip(sources / "link.txt", root / "outside.txt")
    (sources / "unlisted.txt").write_text("late")
    response = call(client, "POST", "/api/runs/resume", resume_body(job_id))
    assert response.status_code == 200, response.text
    copied = sorted(p.name for p in (root / "intake" / response.json()["id"] / "sources").iterdir())
    assert copied == ["annual.txt"]


def test_resume_refuses_a_listed_source_that_is_now_a_link(tmp_path: Path) -> None:
    _, root, client, job_id = stopped_run(tmp_path)
    (root / "outside.txt").write_text("secret")
    listed = root / "intake" / job_id / "sources" / "annual.txt"
    listed.unlink()
    link_or_skip(listed, root / "outside.txt")
    response = call(client, "POST", "/api/runs/resume", resume_body(job_id))
    assert response.status_code == 409 and "no longer in the workspace" in response.text
    assert len(intake_entries(root)) == 1, "a refused resume left an intake folder"


def test_mkdir_all_in_creates_nested_and_accepts_existing(tmp_path: Path) -> None:
    mkdir_all_in(tmp_path, "intake/job/sources/a", 0o700)
    assert (tmp_path / "intake/job/sources/a").is_dir()
    mkdir_all_in(tmp_path, "intake/job", 0o700)
    mkdir_all_in(tmp_path, ".", 0o700)


def test_mkdir_all_in_refuses_files_and_escapes(tmp_path: Path) -> None:
    root, outside = tmp_path / "root", tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    (root / "file").write_text("x")
    with pytest.raises(OSError):
        mkdir_all_in(root, "file/child", 0o700)
    for name in ("../outside", "/abs", "a/../../b", ""):
        with pytest.raises(ValueError):
            mkdir_all_in(root, name, 0o700)
    link_or_skip(root / "link", outside)
    with pytest.raises(OSError):
        mkdir_all_in(root, "link/escaped", 0o700)
    assert not (outside / "escaped").exists(), "a directory was created outside the root"


def test_resume_reads_no_link_swapped_in_after_the_check(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, root, client, job_id = stopped_run(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "annual.txt").write_text("secret")
    sources = root / "intake" / job_id / "sources"
    real_open = os.open
    swapped: list[bool] = []

    def open_after_swap(path: Any, *args: Any, **kwargs: Any) -> int:
        # The first open of the source file: sources/ becomes a link just before it.
        if isinstance(path, str) and path.endswith("annual.txt") and not swapped:
            swapped.append(True)
            sources.rename(sources.with_name("sources-moved"))
            link_or_skip(sources, outside)
        return real_open(path, *args, **kwargs)

    monkeypatch.setattr(os, "open", open_after_swap)
    response = call(client, "POST", "/api/runs/resume", resume_body(job_id))
    assert swapped, "the swap never fired"
    assert response.status_code in (200, 409), response.text
    copies = (root / "intake").glob("web-*/sources/annual.txt")
    assert [p for p in copies if job_id not in str(p) and p.read_bytes() == b"secret"] == []


def test_resume_writes_nothing_through_a_link_swapped_in_after_the_check(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, root, client, job_id = stopped_run(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    real_mkdir = os.mkdir
    swapped: list[bool] = []

    def mkdir_then_swap(path: Any, *args: Any, **kwargs: Any) -> None:
        real_mkdir(path, *args, **kwargs)
        if str(path).endswith("sources") and not swapped:  # The new job's sources/ becomes a link.
            swapped.append(True)
            for folder in (root / "intake").iterdir():
                if folder.name != job_id and (folder / "sources").is_dir():
                    (folder / "sources").rmdir()
                    link_or_skip(folder / "sources", outside)

    monkeypatch.setattr(os, "mkdir", mkdir_then_swap)
    call(client, "POST", "/api/runs/resume", resume_body(job_id))
    assert swapped, "the swap never fired"
    assert list(outside.iterdir()) == [], "a file was created outside the workspace"


@pytest.mark.parametrize("inside", [False, True])
def test_resume_refuses_a_linked_intake_folder(tmp_path: Path, inside: bool) -> None:
    _, root, client, job_id = stopped_run(tmp_path)
    moved = (root if inside else tmp_path / "elsewhere") / "intake-real"
    moved.parent.mkdir(exist_ok=True)
    (root / "intake").rename(moved)
    link_or_skip(root / "intake", moved)
    before = sorted(p.name for p in moved.iterdir())
    response = call(client, "POST", "/api/runs/resume", resume_body(job_id))
    assert response.status_code == 400 and "The workspace is not writable" in response.text
    assert sorted(p.name for p in moved.iterdir()) == before, "a folder was created"


@pytest.mark.parametrize(
    "job",
    [
        b'{"sources":[{"path":"a.txt","sha256":0}]}',
        b'{"sources":[{"path":"a.txt","sha256":false}]}',
        b'{"modules":false}',
        b'{"modules":{}}',
        b'{"sources":0}',
        b'{"resume_of":5}',
        b'{"max_turns":9.0}',
        b'{"extra":NaN}',
        b'{"modules":false,"Modules":["CP-4"]}',
        b'{"sources":[{"path":5,"PATH":"a.txt"}]}',
        '{"\u017fources":0}'.encode(),
        b'{"extra":' + b"[" * 20000 + b"]" * 20000 + b"}",
    ],
)
def test_recorded_job_refuses_what_go_unmarshal_refuses(job: bytes) -> None:
    assert recorded_job(job) is None


def test_recorded_job_decodes_as_go_unmarshal_does() -> None:
    raw = b'{"CONFIG":"a","config":null,"Config":"b","modules":[null,"CP-4"],"sources":[null]}'
    assert recorded_job(raw) == {
        "config": "b",
        "modules": ["", "CP-4"],
        "sources": [{"path": "", "sha256": ""}],
    }
    assert (recorded_job(b'{"config":"c","Config":null}') or {})["config"] == "c"
    assert (recorded_job(b'{"modules":["CP-4"],"Modules":null}') or {})["modules"] == []
    assert recorded_job(b"null") == {"config": "", "modules": [], "sources": []}
    assert recorded_job(rb'{"config":"\udc80"}') == {
        "config": "\ufffd",
        "modules": [],
        "sources": [],
    }
    assert recorded_job(b'{"config":"\xff"}')["config"] == "\ufffd"
    assert (
        events_module.state_of(b'{"state":"stopped","STATE":"reviewed","State":null}') == "reviewed"
    )


@pytest.mark.parametrize(
    ("status", "resumes"),
    [
        (b'{"State":"stopped"}', True),
        (b'{"state":"stopped","State":"running"}', False),
        (b'{"state":"running","STATE":"stopped"}', True),
        (b'{"state":"stopped","State":null}', True),
        (b'{"state":5,"State":"stopped"}', False),
        ('{"\u017ftate":"stopped"}'.encode(), True),
        (b'{"state":"stopped","message":5}', False),
        (b'{"state":"stopped","Message":5}', False),
        (b'{"state":"stopped","id":5}', False),
        (b'{"state":"stopped","x":NaN}', False),
        (b'{"state":"stopped","message":"\xff"}', True),
        (b"null", False),
        (b'{"state":"stopped","x":' + b"[" * 20000 + b"]" * 20000 + b"}", False),
    ],
)
def test_resume_reads_the_stopped_status_as_go_unmarshal_does(
    tmp_path: Path, status: bytes, resumes: bool
) -> None:
    _, root, client, job_id = stopped_run(tmp_path)
    (root / "intake" / job_id / "status.json").write_bytes(status)
    response = call(client, "POST", "/api/runs/resume", resume_body(job_id))
    assert response.status_code == (200 if resumes else 409), response.text


def test_resume_reads_at_most_one_byte_past_the_limit(tmp_path: Path) -> None:
    _, _, client, job_id = stopped_run(tmp_path)
    big = resume_body(job_id, cap_usd="1" * (jobs_module.REQUEST_LIMIT + 1))
    response = call(client, "POST", "/api/runs/resume", big)
    assert response.status_code == 400
    assert "Choose a stopped run, a maximum spend and 1–64 turns" in response.text


def linked_log(tmp_path: Path, name: str, raw: bytes) -> Path:
    folder = tmp_path / "run"
    folder.mkdir()
    (tmp_path / "outside").write_bytes(raw)
    link_or_skip(folder / name, tmp_path / "outside")
    return folder


def test_events_reads_refuse_a_linked_log_or_progress(tmp_path: Path) -> None:
    line = b'{"at":"2026-11-07T10:00:00Z","event":"module_started","module":"LEAK"}\n'
    folder = linked_log(tmp_path, "events.jsonl", line)
    with pytest.raises(OSError) as error:
        events_module.read_events(folder)
    assert not isinstance(error.value, FileNotFoundError)
    assert events_module.progress(folder) is None and events_module.started(folder) == ""
    (folder / "progress.json").write_bytes(b'{"step":"started","module":"OLD"}')
    assert events_module.progress(folder) == {"step": "started", "module": "OLD"}
    (folder / "events.jsonl").unlink()
    (folder / "progress.json").unlink()
    (tmp_path / "outside").write_bytes(b'{"step":"started","module":"LEAK"}')
    link_or_skip(folder / "progress.json", tmp_path / "outside")
    assert events_module.progress(folder) is None


def test_events_read_of_a_fifo_is_refused_without_blocking(tmp_path: Path) -> None:
    folder = tmp_path / "run"
    folder.mkdir()
    if not hasattr(os, "mkfifo"):
        pytest.skip("FIFOs unavailable")
    os.mkfifo(folder / "events.jsonl")
    outcome: list[str] = []

    def read() -> None:
        try:
            events_module.read_events(folder)
            outcome.append("read")
        except OSError:
            outcome.append("refused")
        outcome.append(events_module.started(folder) or "empty")

    worker = threading.Thread(target=read, daemon=True)
    worker.start()
    worker.join(3)
    assert outcome == ["refused", "empty"]


HELD_BRIDGE = """import json,sys,pathlib,time
folder=pathlib.Path(sys.argv[2])
job=json.loads((folder/'job.json').read_text())
if sys.argv[1]=='review':
 print(json.dumps({'ok':True,'review_id':'review-fingerprint','id':job['id'],'provider_ready':True,'counted':[]}))
else:
 deadline=time.time()+60
 while not (folder/'release').exists() and time.time()<deadline: time.sleep(.01)
"""
QUITTING = "Credit OS is quitting for a new launch; use the window that launch opens."


def held_engine(tmp_path: Path, engine: Engine) -> Engine:
    """A worker that runs until <job>/release exists, then exits without a final status."""
    root = tmp_path / "held"
    shutil.copytree(engine.root, root)
    (root / "bridge.py").write_text(HELD_BRIDGE)
    return Engine(root=root, python=engine.python)


def missing_python(tmp_path: Path, engine: Engine) -> Engine:
    return Engine(root=engine.root, python=str(tmp_path / "no-such-python"))


def state_of(folder: Path) -> dict[str, Any]:
    value: dict[str, Any] = json.loads((folder / "status.json").read_bytes())
    return value


def restarted(tmp_path: Path, root: Path) -> Application:
    return Application(locations(tmp_path / "second"), str(root), HOST)


def start_job(client: TestClient, job_id: str) -> Any:
    return call(client, "POST", "/api/runs/start", start_payload(job_id))


def test_failed_spawn_releases_the_start_claim_but_a_started_worker_keeps_it(
    tmp_path: Path,
) -> None:
    app, root, client, job_id = reviewed(tmp_path)
    folder = root / "intake" / job_id
    good = app.engine
    app.engine = missing_python(tmp_path, good)
    first = start_job(client, job_id)
    assert first.status_code == 503 and "no model call was made" in first.text
    assert not (folder / "start.claim").exists(), "claim survived a spawn that never ran"
    status = client.get(f"/api/runs/status?id={job_id}").json()
    assert status["state"] == "failed" and "can be tried again" in status["message"]
    app.engine = good
    assert start_job(client, job_id).status_code == 202
    assert start_job(client, job_id).status_code == 409
    wait_idle(app)
    assert (folder / "synthetic-starts.txt").read_text() == "one\n"
    again = start_job(client, job_id)
    assert again.status_code == 409 and "already been started" in again.text


def test_unsavable_start_status_releases_the_start_claim(tmp_path: Path) -> None:
    app, root, client, job_id = reviewed(tmp_path)
    folder = root / "intake" / job_id
    (folder / "status.json").unlink()
    put(folder, "status.json/blocker", b"")
    assert start_job(client, job_id).status_code == 500
    assert not (folder / "synthetic-starts.txt").exists(), "a worker ran"
    assert not (folder / "start.claim").exists(), "claim survived"
    shutil.rmtree(folder / "status.json")
    put(folder, "status.json", b'{"state":"reviewed"}')
    assert start_job(client, job_id).status_code == 202
    wait_idle(app)


def test_review_concurrent_starts_around_a_failed_spawn(tmp_path: Path) -> None:
    app, root, client, job_id = reviewed(tmp_path)
    folder = root / "intake" / job_id
    good = app.engine
    app.engine = missing_python(tmp_path, good)

    def codes() -> dict[int, int]:
        seen: dict[int, int] = {}
        guard = threading.Lock()

        def one() -> None:
            code = start_job(client, job_id).status_code
            with guard:
                seen[code] = seen.get(code, 0) + 1

        threads = [threading.Thread(target=one) for _ in range(8)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        return seen

    assert codes() == {503: 8}
    assert not (folder / "start.claim").exists(), "claim left behind"
    with app.lock:
        app.engine = good
    assert codes() == {202: 1, 409: 7}
    wait_idle(app)
    assert (folder / "synthetic-starts.txt").read_text() == "one\n"


def test_a_stray_fork_holding_the_run_lock_does_not_turn_a_failed_spawn_retry_into_500(
    tmp_path: Path,
) -> None:
    app, root, client, job_id = reviewed(tmp_path)
    folder = root / "intake" / job_id
    fired: list[bool] = []
    ready_r, ready_w = os.pipe()
    hold_r, hold_w = os.pipe()
    helpers: list[threading.Thread] = []

    def hold_the_inherited_descriptors() -> None:
        # Runs in the forked child before close_fds: the child holds a copy of the lock fd.
        os.write(ready_w, b"x")
        select.select([hold_r], [], [], 30)

    class StrayForkEngine(Engine):
        def start(self, folder: Path, lock: Any) -> Any:
            if not fired:  # first attempt only: another thread forks while the lock is held
                fired.append(True)
                helper = threading.Thread(
                    target=subprocess.run,
                    args=(["/usr/bin/true"],),
                    kwargs={"preexec_fn": hold_the_inherited_descriptors},
                    daemon=True,
                )
                helpers.append(helper)
                helper.start()
                assert select.select([ready_r], [], [], 30)[0], "helper child never forked"
            return super().start(folder, lock)

    good = app.engine
    broken = missing_python(tmp_path, good)
    app.engine = StrayForkEngine(root=broken.root, python=broken.python)
    try:
        first = start_job(client, job_id)
        second = start_job(client, job_id)
    finally:
        os.write(hold_w, b"x")
        for helper in helpers:
            helper.join(30)
        for descriptor in (ready_r, ready_w, hold_r, hold_w):
            os.close(descriptor)
    assert not any(helper.is_alive() for helper in helpers), "helper child left running"
    assert (first.status_code, second.status_code) == (503, 503), (first.text, second.text)
    assert not (folder / "start.claim").exists(), "claim left behind"
    assert state_of(folder)["state"] == "failed"


def test_a_stray_fork_during_a_failed_status_save_does_not_block_the_next_start(
    tmp_path: Path,
) -> None:
    # Answer key: sb2/probes/t7adv_save_failure_stray_fork.py. The probe's outcome is 202 (the
    # lead's brief says "503, not 500"; no worker exists, so a start that is not refused is the
    # probe's key). Here: never 500, and a plain retry starts.
    app, root, client, job_id = reviewed(tmp_path)
    folder = root / "intake" / job_id
    (folder / "status.json").unlink()
    put(folder, "status.json/blocker", b"")
    ready_r, ready_w = os.pipe()
    hold_r, hold_w = os.pipe()
    helpers: list[threading.Thread] = []
    real_save = jobs_module.save_json

    def hold_the_inherited_descriptors() -> None:
        os.write(ready_w, b"x")
        select.select([hold_r], [], [], 30)

    def forking_save(path: Path, value: Any) -> None:
        if not helpers and isinstance(value, dict) and value.get("state") == "running":
            helper = threading.Thread(
                target=subprocess.run,
                args=(["/usr/bin/true"],),
                kwargs={"preexec_fn": hold_the_inherited_descriptors},
                daemon=True,
            )
            helpers.append(helper)
            helper.start()
            assert select.select([ready_r], [], [], 30)[0], "helper child never forked"
        real_save(path, value)

    jobs_module.save_json = forking_save
    try:
        first = start_job(client, job_id)
        shutil.rmtree(folder / "status.json")
        put(folder, "status.json", b'{"state":"reviewed"}')
        second = start_job(client, job_id)
    finally:
        jobs_module.save_json = real_save
        os.write(hold_w, b"x")
        for helper in helpers:
            helper.join(30)
        for descriptor in (ready_r, ready_w, hold_r, hold_w):
            os.close(descriptor)
        wait_idle(app)
    assert first.status_code == 500, first.text
    assert not any(helper.is_alive() for helper in helpers), "helper child left running"
    assert second.status_code == 202, second.text
    assert not (folder / "worker.lock").exists() or state_of(folder)["state"] != "running"


def stalling_fcntl(
    outer: str, armed: list[bool], opened: threading.Event, go: threading.Event
) -> Any:
    """fcntl for jobs.py whose next worker_alive flock, called from `outer`, waits on `go` (a
    descheduled thread between its open and its flock)."""
    import fcntl

    class StallingFcntl:
        def __getattr__(self, name: str) -> Any:
            return getattr(fcntl, name)

        def flock(self, descriptor: int, operation: int) -> Any:
            frame = sys._getframe
            caller, outer_name = frame(1).f_code.co_name, frame(2).f_code.co_name
            if armed[0] and caller == "worker_alive" and outer_name == outer:
                armed[0] = False
                opened.set()
                go.wait(20)
            return fcntl.flock(descriptor, operation)

    return StallingFcntl()


def resume_and_start_copy(client: Any, root: Path, job_id: str, starts: Path) -> int:
    """Resume the job from the other instance, start the copy, return the worker starts seen."""
    if call(client, "POST", "/api/runs/resume", resume_body(job_id)).status_code != 200:
        return 0
    copy = next(p.name for p in (root / "intake").iterdir() if p.name != job_id)
    start_job(client, copy)
    time.sleep(0.5)
    return starts.read_text().count("\n")


def drain_apps(*apps: Any) -> None:
    deadline = time.time() + 15
    for app in apps:
        while time.time() < deadline:
            with app.lock:
                if not app.active_jobs:
                    break
            time.sleep(0.05)


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX flock semantics")
@pytest.mark.parametrize("variant", ["adoption", "watch_worker"])
def test_a_liveness_probe_opened_before_a_failed_start_removed_the_lock_keeps_the_retry_running(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, variant: str
) -> None:
    # Answer key: sb2/probes/t7adv_stale_inode_adoption.py and t7adv_stale_inode_liveness.py. A
    # second instance opens worker.lock, is descheduled before flock (injected stall), the failed
    # start unlinks that inode and the retry's worker locks a new one: the retry's job must stay
    # "running", its worker alive, and no second worker may start.
    adoption = variant == "adoption"
    if not adoption:
        monkeypatch.setattr(jobs_module, "WORKER_POLL", 0.01)
    first_app, root, client_a, job_id = reviewed(tmp_path)
    folder = root / "intake" / job_id
    held_root = tmp_path / "held-engine"
    held_root.mkdir()
    (held_root / "bridge.py").write_text(RECORDING_BRIDGE)
    (held_root / "store.py").write_text((first_app.engine.root / "store.py").read_text())
    held = Engine(root=held_root, python=sys.executable)
    missing = Engine(root=held_root, python=str(tmp_path / "no-such-python"))
    second_app = restarted(tmp_path, root)
    second_app.engine = held
    opened, go = threading.Event(), threading.Event()
    armed = [False]
    attempts: list[int] = []
    adopters: list[threading.Thread] = []

    def adopt() -> None:
        with second_app.lock:
            jobs_module.adopt_jobs_locked(second_app, str(root))

    class SwitchEngine(Engine):
        def start(self, folder: Path, lock: Any) -> Any:
            attempts.append(1)
            if len(attempts) > 1:
                return Engine.start(held, folder, lock)
            if adoption:
                armed[0] = True
                thread = threading.Thread(target=adopt, daemon=True)
                adopters.append(thread)
                thread.start()
            else:
                adopt()
                assert job_id in second_app.active_jobs, "the watcher did not adopt the job"
                armed[0] = True
            assert opened.wait(10), "the liveness probe never opened the lock"
            return Engine.start(missing, folder, lock)

    first_app.engine = SwitchEngine(root=held_root, python=sys.executable)
    starts = root / "worker-starts.txt"
    outer = "adopt_jobs_locked" if adoption else "watch_worker"
    monkeypatch.setattr(jobs_module, "fcntl", stalling_fcntl(outer, armed, opened, go))
    try:
        first = start_job(client_a, job_id)
        retry = start_job(client_a, job_id)
        deadline = time.time() + 5
        while time.time() < deadline and not (starts.exists() and starts.read_text()):
            time.sleep(0.01)
        go.set()
        for thread in adopters:
            thread.join(10)
        if not adoption:
            time.sleep(0.3)  # the watcher's next polls, at 0.01 s
        settled = state_of(folder)["state"]
        alive = jobs_module.worker_alive(folder / "worker.lock")
        resumed_workers = 0
        if settled != "running":
            resumed_workers = resume_and_start_copy(client_of(second_app), root, job_id, starts)
    finally:
        go.set()
        (root / "release-all").write_bytes(b"")
        drain_apps(first_app, second_app)
    assert (first.status_code, retry.status_code) == (503, 202), (first.text, retry.text)
    assert settled == "running", f"a live worker's job was settled {settled!r}"
    assert alive, "the retry's worker was judged dead"
    assert resumed_workers < 2, "two workers for the same inputs"
    assert starts.read_text().count("\n") == 1


RECORDING_BRIDGE = """import json,os,sys,pathlib,time
folder=pathlib.Path(sys.argv[2])
job=json.loads((folder/'job.json').read_text())
if sys.argv[1]=='review':
 print(json.dumps({'ok':True,'review_id':'review-fingerprint','id':job['id'],'provider_ready':True,'counted':[]}))
else:
 ws=folder.parent.parent
 with (ws/'worker-starts.txt').open('a') as s: s.write(folder.name+' '+str(os.getpid())+'\\n')
 deadline=time.time()+60
 while not (ws/'release-all').exists() and time.time()<deadline: time.sleep(.01)
"""


def await_text(path: Path) -> None:
    deadline = time.time() + 5
    while time.time() < deadline and not (path.exists() and path.read_text()):
        time.sleep(0.01)


def await_settled(app: Application, folder: Path, job_id: str) -> None:
    """Wait until the job leaves running or the instance stops watching it (at most 3 s)."""
    deadline = time.time() + 3
    while time.time() < deadline and state_of(folder)["state"] == "running":
        with app.lock:
            if job_id not in app.active_jobs:
                return
        time.sleep(0.01)


def recording_engines(tmp_path: Path, engine: Engine) -> tuple[Engine, Engine]:
    """A worker that records its start and runs until release-all exists, and an engine whose
    interpreter is missing (its spawn fails)."""
    root = tmp_path / "held-engine"
    root.mkdir()
    (root / "bridge.py").write_text(RECORDING_BRIDGE)
    (root / "store.py").write_text((engine.root / "store.py").read_text())
    return (
        Engine(root=root, python=sys.executable),
        Engine(root=root, python=str(tmp_path / "no-such-python")),
    )


def settle_race_outcome(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    """A second instance's watcher judges a failed start's worker gone (after its unlink) and is
    descheduled before settle_job reads status.json (injected stall); the retry starts a live
    worker meanwhile."""
    monkeypatch.setattr(jobs_module, "WORKER_POLL", 0.01)
    first_app, root, client_a, job_id = reviewed(tmp_path)
    folder = root / "intake" / job_id
    held, missing = recording_engines(tmp_path, first_app.engine)
    held_root = held.root
    second_app = restarted(tmp_path, root)
    second_app.engine = held
    reached, go = threading.Event(), threading.Event()
    armed = [False]
    attempts: list[int] = []
    real_settle = jobs_module.settle_job

    def stalling_settle(path: Path) -> None:
        caller, outer = sys._getframe(1).f_code.co_name, sys._getframe(2).f_code.co_name
        if armed[0] and (caller, outer) == ("finish_job", "watch_worker"):
            armed[0] = False
            reached.set()
            go.wait(20)
        real_settle(path)

    class SwitchEngine(Engine):
        def start(self, folder: Path, lock: Any) -> Any:
            attempts.append(1)
            if len(attempts) > 1:
                return Engine.start(held, folder, lock)
            with second_app.lock:
                jobs_module.adopt_jobs_locked(second_app, str(root))
            assert job_id in second_app.active_jobs, "the other instance did not adopt the job"
            armed[0] = True
            return Engine.start(missing, folder, lock)

    first_app.engine = SwitchEngine(root=held_root, python=sys.executable)
    monkeypatch.setattr(jobs_module, "settle_job", stalling_settle)
    starts = root / "worker-starts.txt"
    resumed_workers = 0
    try:
        first = start_job(client_a, job_id)
        assert reached.wait(10), "the settle never reached its stall"
        retry = start_job(client_a, job_id)
        await_text(starts)
        go.set()
        await_settled(second_app, folder, job_id)
        settled = state_of(folder)["state"]
        alive = jobs_module.worker_alive(folder / "worker.lock")
        if settled != "running":
            resumed_workers = resume_and_start_copy(client_of(second_app), root, job_id, starts)
    finally:
        go.set()
        (root / "release-all").write_bytes(b"")
        drain_apps(first_app, second_app)
    workers = starts.read_text().count("\n") if starts.exists() else 0
    return SimpleNamespace(
        first=first, retry=retry, settled=settled, alive=alive, workers=workers + resumed_workers
    )


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX flock semantics")
@pytest.mark.parametrize(
    "in_gap", [False, True], ids=["after_unlink", "between_release_and_unlink"]
)
def test_another_instances_settle_never_marks_a_live_retry_interrupted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, in_gap: bool
) -> None:
    # Answer key: sb2/probes/t7adv_settle_toctou_preexisting.py (after_unlink) and
    # i24_held_stale_inode_settle_v2.py (between_release_and_unlink, staged for unlink-first: a
    # settle that opened the lock file before the unlink wins the flock on that inode once the
    # lock is released and must not take it as proof; the older gap, a verdict made between
    # release and unlink, no longer exists on POSIX, where the unlink comes first). Whatever
    # the retry's answer, a live worker's job is never settled, and no second worker starts.
    if in_gap:
        outcome = run_failed_start_race(
            tmp_path,
            monkeypatch,
            race_of(),
            stall_after_job_state_in_settle,
            settle_opens_first=True,
        )
        assert outcome.race.seen["stalled"], "the settle never reached its stall"
    else:
        outcome = settle_race_outcome(tmp_path, monkeypatch)
    assert outcome.first.status_code == 503, outcome.first.text
    if outcome.retry.status_code == 202:
        assert outcome.alive, "the retry's worker was judged dead"
        assert outcome.settled == "running", (
            f"a live worker's job was settled {outcome.settled!r} by the other instance"
        )
    assert outcome.workers < 2, "two workers for the same inputs"


def race_of() -> SimpleNamespace:
    return SimpleNamespace(
        reached=threading.Event(),
        go=threading.Event(),
        done=threading.Event(),
        opened=threading.Event(),
        released=threading.Event(),
        seen={},
        attempts=[],
    )


def run_failed_start_race(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    race: SimpleNamespace,
    install: Callable[[pytest.MonkeyPatch, SimpleNamespace], None],
    settle_opens_first: bool = False,
) -> SimpleNamespace:
    """The first start's spawn fails; another instance's settle_job wins the lock on the inode
    about to be unlinked (started between the failed start's release_lock and its unlink) and is
    stalled by `install`'s hook; the retry then locks a fresh inode and spawns a live worker.

    With `settle_opens_first` the settle instead opens the lock file before the failed start
    unlinks it and waits at its flock until release_lock has run (the order on POSIX, where the
    unlink comes first and the lock is held until after it): it then wins the flock on the
    unlinked inode and stalls, which the start's answer is awaited for (race.seen["stalled"])."""
    app, root, client, job_id = reviewed(tmp_path)
    folder = root / "intake" / job_id
    held, missing = recording_engines(tmp_path, app.engine)
    real_remove = jobs_module.remove_failed_run_lock

    class SwitchEngine(Engine):
        def start(self, folder: Path, lock: Any) -> Any:
            race.attempts.append(1)
            return Engine.start(missing if len(race.attempts) == 1 else held, folder, lock)

    def settle() -> None:
        try:
            jobs_module.settle_job(folder)
            race.seen["settle"] = "returned"
        except jobs_module.WorkerMayStillRun:
            race.seen["settle"] = "WorkerMayStillRun"
        finally:
            race.done.set()

    settler = threading.Thread(target=settle, name="racing-settle", daemon=True)

    def remove_with_a_settle_racing(path: Path, job: str) -> None:
        if "started" not in race.seen:
            race.seen["started"] = True
            race.seen["failed_start_ino"] = os.lstat(path).st_ino
            settler.start()
            if settle_opens_first:
                race.opened.wait(10)
            deadline = time.time() + 10
            while (
                not settle_opens_first
                and time.time() < deadline
                and not (race.reached.is_set() or race.done.is_set())
            ):
                time.sleep(0.005)
        real_remove(path, job)

    app.engine = SwitchEngine(root=held.root, python=sys.executable)
    install(monkeypatch, race)
    if settle_opens_first:
        settle_flock_waits_for_the_release(monkeypatch, race)
    monkeypatch.setattr(jobs_module, "remove_failed_run_lock", remove_with_a_settle_racing)
    starts = root / "worker-starts.txt"
    try:
        first = start_job(client, job_id)
        if settle_opens_first:
            race.seen["stalled"] = race.reached.wait(10)
        retry = start_job(client, job_id)
        await_text(starts)
        race.go.set()
        settler.join(10)
        settled = state_of(folder)["state"]
        alive = jobs_module.worker_alive(folder / "worker.lock")
        new_ino = os.lstat(folder / "worker.lock").st_ino
    finally:
        race.go.set()
        (root / "release-all").write_bytes(b"")
        drain_apps(app)
    workers = starts.read_text().count("\n") if starts.exists() else 0
    return SimpleNamespace(
        first=first,
        retry=retry,
        settled=settled,
        alive=alive,
        new_ino=new_ino,
        workers=workers,
        race=race,
    )


def settle_flock_waits_for_the_release(
    monkeypatch: pytest.MonkeyPatch, race: SimpleNamespace
) -> None:
    """The racing settle has opened the lock file when it reaches its flock, and gets the flock
    only after the failed start's release_lock has run; every other flock is untouched."""
    real_fcntl, real_release = jobs_module.fcntl, jobs_module.release_lock

    def flock_once_released(descriptor: int, operation: int) -> Any:
        if threading.current_thread().name == "racing-settle":
            race.opened.set()
            race.released.wait(10)
        return real_fcntl.flock(descriptor, operation)

    def release_then_signal(lock: int) -> None:
        real_release(lock)
        race.released.set()

    gated = SimpleNamespace(
        flock=flock_once_released, LOCK_EX=real_fcntl.LOCK_EX, LOCK_NB=real_fcntl.LOCK_NB
    )
    monkeypatch.setattr(jobs_module, "fcntl", gated)
    monkeypatch.setattr(jobs_module, "release_lock", release_then_signal)


def stall_after_job_state_in_settle(monkeypatch: pytest.MonkeyPatch, race: SimpleNamespace) -> None:
    real_job_state = jobs_module.job_state

    def stalling_job_state(folder: Path) -> Any:
        racing = threading.current_thread().name == "racing-settle"
        if racing and not race.reached.is_set() and sys._getframe(1).f_code.co_name == "settle_job":
            race.reached.set()
            race.go.wait(20)
        return real_job_state(folder)

    monkeypatch.setattr(jobs_module, "job_state", stalling_job_state)


def failed_write_and_stalled_settle_write(
    monkeypatch: pytest.MonkeyPatch, race: SimpleNamespace
) -> None:
    real_save = jobs_module.save_json

    def injected_save(path: Path, value: Any) -> Any:
        caller = sys._getframe(1).f_code.co_name
        state = value.get("state") if isinstance(value, dict) else None
        if caller == "launch_worker" and state == "failed" and len(race.attempts) == 1:
            raise OSError(28, "No space left on device (injected)")
        if caller == "settle_job" and not race.reached.is_set():
            race.reached.set()
            race.go.wait(20)
        return real_save(path, value)

    monkeypatch.setattr(jobs_module, "save_json", injected_save)


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX flock semantics")
def test_a_settle_holding_the_inode_about_to_be_unlinked_never_marks_a_live_retry_interrupted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Answer key: sb2/probes/i24_held_stale_inode_settle.py (items 2/4 review, M2). The settle
    # wins the flock on the failed start's inode and is descheduled after that, inside
    # settle_job before it reads status.json; the failed start unlinks the held inode and the
    # retry's live worker locks a fresh one. The settle must not take its held, unlinked inode
    # as proof: the job stays "running".
    race = race_of()
    outcome = run_failed_start_race(
        tmp_path, monkeypatch, race, stall_after_job_state_in_settle, settle_opens_first=True
    )
    assert race.seen["stalled"], "the settle never stalled holding the failed start's inode"
    assert outcome.first.status_code == 503, outcome.first.text
    assert outcome.retry.status_code == 202, outcome.retry.text
    assert outcome.new_ino != race.seen["failed_start_ino"], "the retry did not lock a fresh inode"
    assert outcome.alive, "the retry's worker was judged dead"
    assert outcome.settled == "running", (
        f"a live retry's job was settled {outcome.settled!r} from a held, unlinked inode"
    )


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX flock semantics")
def test_a_failed_start_whose_failed_write_fails_never_lets_a_stalled_settle_overwrite_the_retry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Answer key: sb2/probes/i24_residual_write_window.py (items 2/4 review, L1). The failed
    # start's "failed" write fails (full disk), so status.json still says "running" when its lock
    # is released; another instance's settle wins the lock before the unlink, reads "running",
    # and is descheduled between its check and its write. Whatever the retry answers, a live
    # worker's job is never written "interrupted" (it would be resumable: a second paid worker).
    race = race_of()
    outcome = run_failed_start_race(
        tmp_path, monkeypatch, race, failed_write_and_stalled_settle_write
    )
    if outcome.retry.status_code == 202 and outcome.alive:
        assert outcome.settled == "running", (
            f"a live retry's job was settled {outcome.settled!r} (residual write window)"
        )
    else:
        assert outcome.retry.status_code != 202, "the retry's worker was judged dead"


def await_left_active_jobs(app: Application, job_id: str) -> bool:
    """Whether the instance stops watching the job within 5 s."""
    deadline = time.time() + 5
    while time.time() < deadline:
        with app.lock:
            if job_id not in app.active_jobs:
                return True
        time.sleep(0.02)
    return False


def start_recording_worker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[Application, Path, TestClient, str, Engine]:
    """A reviewed run whose started worker records itself and stays until release-all exists.
    Returns the app (engine = the recording one), the workspace, client, job id, and the
    application's original engine."""
    monkeypatch.setattr(jobs_module, "WORKER_POLL", 0.01)
    app, root, client, job_id = reviewed(tmp_path)
    good = app.engine
    app.engine, _ = recording_engines(tmp_path, good)
    assert start_job(client, job_id).status_code == 202
    await_text(root / "worker-starts.txt")
    return app, root, client, job_id, good


def test_a_run_folder_removed_while_its_worker_runs_leaves_the_active_jobs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Answer key: sb2/probes/i24_run_folder_gone_stuck_active.py and i24_folder_gone_job_stuck.py
    # (items 2/4 review, M1; as at base 284b784c): with no run folder there is nothing to
    # settle, so once the worker exits the job is finished: the next start is not refused (409)
    # and a quit is not busy.
    app, root, client, job_id, good = start_recording_worker(tmp_path, monkeypatch)
    shutil.rmtree(root / "intake" / job_id)
    (root / "release-all").write_bytes(b"")
    try:
        left = await_left_active_jobs(app, job_id)
        other = review_request(client, '["annual.txt"]')
        assert other.status_code == 200, other.text
        app.engine = good
        started = start_job(client, other.json()["id"])
        with app.lock:
            in_flight = len(app.active_jobs)
    finally:
        (root / "release-all").write_bytes(b"")
        drain_apps(app)
    assert left, "the run stayed in active_jobs after its worker exited"
    assert started.status_code == 202, started.text
    assert in_flight <= 1, "the removed run still counts as in flight"


@pytest.mark.skipif(
    sys.platform == "win32" or (hasattr(os, "geteuid") and os.geteuid() == 0),
    reason="chmod 0400 has no effect on Windows or for root",
)
def test_a_read_only_run_lock_is_settled_not_stuck_and_not_logged_on_every_poll(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    # Answer key: sb2/probes/i24_lock_unwritable_stuck_active.py (items 2/4 review, M1,
    # scenario B): worker.lock opens read-only but not read-write. The job is settled once the
    # worker exits (as at base), not kept active; at WORKER_POLL 0.01 s a warning per poll would
    # be hundreds of records, so at most a few are allowed.
    app, root, _, job_id, _ = start_recording_worker(tmp_path, monkeypatch)
    folder = root / "intake" / job_id
    os.chmod(folder / "worker.lock", 0o400)
    try:
        with caplog.at_level(logging.WARNING, logger="issuer_library"):
            (root / "release-all").write_bytes(b"")
            left = await_left_active_jobs(app, job_id)
            time.sleep(0.3)  # Thirty more polls if it is still being watched.
        settled = state_of(folder)["state"]
    finally:
        os.chmod(folder / "worker.lock", 0o600)
        (root / "release-all").write_bytes(b"")
        drain_apps(app)
    warnings = [r for r in caplog.records if r.levelno >= logging.WARNING]
    assert left, "the run stayed in active_jobs after its worker exited"
    assert settled != "running", f"the job was left {settled!r}"
    assert len(warnings) <= 3, f"{len(warnings)} warnings logged over a few polls"


@pytest.mark.parametrize(
    "error",
    [
        RuntimeError("spawn went wrong"),
        ValueError("bad spawn value"),
        subprocess.SubprocessError("bad child data"),
    ],
    ids=["RuntimeError", "ValueError", "SubprocessError"],
)
def test_a_spawn_that_raises_anything_releases_the_claim_and_fails_the_job(
    tmp_path: Path, caplog: pytest.LogCaptureFixture, error: Exception
) -> None:
    # Answer key: sb2/probes/t7adv_non_oserror_spawn.py and the lead's ruling (item 4): any
    # exception from engine.start releases the claim, marks the job failed, logs, and answers the
    # normal refusal (503, "no model call was made"); the next start is not blocked.
    app, root, _, job_id = reviewed(tmp_path)
    folder = root / "intake" / job_id
    client = TestClient(
        app.asgi,
        base_url=ORIGIN,
        raise_server_exceptions=False,
        headers={"Cookie": f"{cookie_name(HOST)}={app.session.cookie}"},
    )

    class RaisingEngine(Engine):
        def start(self, folder: Path, lock: Any) -> Any:
            raise error

    good = app.engine
    app.engine = RaisingEngine(root=good.root, python=good.python)
    with caplog.at_level(logging.WARNING, logger="issuer_library"):
        first = start_job(client, job_id)
    assert first.status_code == 503 and "no model call was made" in first.text, first.text
    assert not (folder / "start.claim").exists(), "claim kept after a failed spawn"
    status = state_of(folder)
    assert status["state"] == "failed" and "can be tried again" in status["message"], status
    assert not app.active_jobs
    logged = [
        record
        for record in caplog.records
        if record.levelno >= logging.WARNING
        and job_id in record.getMessage()
        and str(error) in record.getMessage() + repr(record.exc_info)
    ]
    assert logged, "the spawn error was not logged with the run id"
    app.engine = good
    assert start_job(client, job_id).status_code == 202
    wait_idle(app)
    assert (folder / "synthetic-starts.txt").read_text() == "one\n"


def test_review_worker_that_started_and_failed_keeps_the_claim(tmp_path: Path) -> None:
    app, root, client, job_id = reviewed(tmp_path)
    (app.engine.root / "bridge.py").write_text("import sys\nsys.exit(3)\n")
    assert start_job(client, job_id).status_code == 202
    wait_idle(app)
    assert (root / "intake" / job_id / "start.claim").exists(), "claim released after a worker"
    again = start_job(client, job_id)
    assert again.status_code == 409 and "already been started" in again.text
    assert client.get(f"/api/runs/status?id={job_id}").json()["state"] == "interrupted"


def test_a_quitting_app_refuses_start_before_any_claim(tmp_path: Path) -> None:
    app, root, client, job_id = reviewed(tmp_path)
    app.quitting = True
    response = start_job(client, job_id)
    assert response.status_code == 503 and QUITTING in response.text
    folder = root / "intake" / job_id
    assert not (folder / "start.claim").exists() and not (folder / "synthetic-starts.txt").exists()


def test_restart_settles_a_running_job_whose_worker_is_gone(tmp_path: Path) -> None:
    _, root = make_app(tmp_path)
    jobs = {
        "unlocked": "running",
        "no-lock": "running",
        "complete": "complete",
        "reviewed": "reviewed",
    }
    folders = {}
    for number, (setup, state) in enumerate(jobs.items(), start=1):
        job_id = f"web-{number:032x}"
        folders[setup] = root / "intake" / job_id
        write_job(root, job_id, state, time.time())
        if setup != "no-lock":
            put(root, f"intake/{job_id}/worker.lock", b"")
    second = restarted(tmp_path, root)
    want = {"unlocked": "interrupted", "no-lock": "interrupted"} | {
        name: name for name in ("complete", "reviewed")
    }
    for setup, folder in folders.items():
        assert state_of(folder)["state"] == want[setup], setup
    assert "no automatic paid retry was made" in state_of(folders["unlocked"])["message"]
    assert "no automatic paid retry was made" in state_of(folders["no-lock"])["message"]
    assert second.active_jobs == set()


def test_restart_with_a_live_worker_keeps_its_job_active_until_it_ends(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(jobs_module, "WORKER_POLL", 0.01)
    first, root, client, job_id = reviewed(tmp_path)
    first.engine = held_engine(tmp_path, first.engine)
    folder = root / "intake" / job_id
    try:
        assert start_job(client, job_id).status_code == 202
        second = restarted(tmp_path, root)
        second.engine = first.engine
        other = client_of(second)
        assert state_of(folder)["state"] == "running", "a live worker's job was settled"
        staged = review_request(other, '["annual.txt"]').json()["id"]
        assert start_job(other, staged).status_code == 409
        raw = json.dumps({"workspace": str(tmp_path)})
        assert call(other, "POST", "/api/settings", raw).status_code == 409
        (folder / "release").write_bytes(b"")
        wait_idle(second)
        wait_idle(first)
        assert state_of(folder)["state"] == "interrupted"
    finally:
        for job in root.glob("intake/web-*"):
            (job / "release").write_bytes(b"")


def test_start_with_an_uncreatable_worker_lock_is_retryable(tmp_path: Path) -> None:
    app, root, client, job_id = reviewed(tmp_path)
    folder = root / "intake" / job_id
    lock = folder / "worker.lock"
    link_or_skip(lock, lock)  # opening it fails with a loop, never a lock
    first = start_job(client, job_id)
    assert first.status_code == 500 and "Start can be tried again" in first.text
    assert not (folder / "start.claim").exists(), "the start claim was kept"
    assert not (folder / "synthetic-starts.txt").exists(), "a worker started without its lock"
    assert state_of(folder)["state"] != "running"
    assert app.active_jobs == set()
    lock.unlink()
    assert start_job(client, job_id).status_code == 202
    wait_idle(app)


def test_restart_leaves_a_job_whose_lock_cannot_be_checked_as_it_is(tmp_path: Path) -> None:
    _, root = make_app(tmp_path)
    job_id = f"web-{9:032x}"
    write_job(root, job_id, "running", time.time())
    lock = root / "intake" / job_id / "worker.lock"
    link_or_skip(lock, lock)
    second = restarted(tmp_path, root)
    assert state_of(root / "intake" / job_id)["state"] == "running"
    assert second.active_jobs == set()


def run_main(monkeypatch: pytest.MonkeyPatch, state: Path) -> tuple[int, list[str]]:
    import issuer_library.__main__ as entry

    shown: list[str] = []
    argv = ["issuer-library", "--state-dir", str(state), "--no-browser", "--port", "80"]
    monkeypatch.setattr(sys, "argv", argv)
    monkeypatch.setattr(entry, "show_error", shown.append)
    return entry.main(), shown


def test_run_records_its_error_in_the_log_before_closing_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = logging.getLogger()
    monkeypatch.setattr(root, "handlers", [])
    try:
        code, shown = run_main(monkeypatch, tmp_path)
    finally:
        for handler in list(root.handlers):
            handler.close()
            root.removeHandler(handler)
    assert code == 1 and "port must be between" in shown[0]
    assert "port must be between 1024 and 65535" in (tmp_path / "library.log").read_text()


@pytest.mark.skip(
    reason="not applicable: Go's log.SetOutput swap has no Python equivalent; the root logger's"
    " file handler is not a process-wide writer that is closed when run() returns"
)
def test_log_output_no_longer_points_at_the_closed_library_log() -> None:
    raise AssertionError


GO_STATUS = [  # (status.json bytes, whether Go's JobStatus decode reads state "running")
    (b'{"state":"running"}', True),
    (b'{"State":"running"}', True),
    (b'{"state":"running","STATE":"stopped"}', False),
    (b'{"state":"running","message":5}', False),
    (b'{"state":"running","id":5}', False),
    (b'\xef\xbb\xbf{"state":"running"}', False),
    (b'{"state":"running","message":"\xff"}', True),
    (b"[" * 10000 + b"]" * 10000, False),
]


@pytest.mark.parametrize(("raw", "running"), GO_STATUS, ids=range(len(GO_STATUS)))
def test_settle_and_adopt_read_the_status_as_go_decodes_it(
    tmp_path: Path, raw: bytes, running: bool
) -> None:
    app, root = make_app(tmp_path)
    folder = root / "intake" / f"web-{3:032x}"
    put(root, f"intake/{folder.name}/status.json", raw)
    with app.lock:
        jobs_module.adopt_jobs_locked(app, str(root))
    assert (
        (folder / "status.json").read_bytes() != raw
        if running
        else ((folder / "status.json").read_bytes() == raw)
    )
    assert app.active_jobs == set()
    put(root, f"intake/{folder.name}/status.json", raw)
    jobs_module.settle_job(folder)
    assert ((folder / "status.json").read_bytes() != raw) is running
    assert restarted(tmp_path, root).active_jobs == set()


def test_watch_worker_logs_an_uncheckable_lock_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    app, _ = make_app(tmp_path)
    calls = {"n": 0}

    def alive(path: Path) -> bool:
        calls["n"] += 1
        if calls["n"] < 50:
            raise PermissionError(13, "denied")
        return False

    monkeypatch.setattr(jobs_module, "WORKER_POLL", 0.0)
    monkeypatch.setattr(jobs_module, "worker_alive", alive)
    monkeypatch.setattr(jobs_module, "finish_job", lambda lib, folder, job_id: None)
    with caplog.at_level(logging.WARNING, logger="issuer_library"):
        jobs_module.watch_worker(app, "web-" + "a" * 32, tmp_path)
    assert calls["n"] == 50 and len(caplog.records) == 1


# --- 5D: the review bound, slow reviews, streamed uploads and reviews in flight -------------------

REVIEW_IN_FLIGHT = (
    "A run review is in progress; wait for it to finish before changing the workspace"
)
SLOW_BRIDGE = """import json,sys,pathlib,time
folder=pathlib.Path(sys.argv[2])
job=json.loads((folder/'job.json').read_text())
if sys.argv[1]=='review':
 time.sleep(SECONDS)
 print(json.dumps({'ok':True,'review_id':'rid','id':job['id'],'provider_ready':True,'counted':[]}))
"""
HELD_REVIEW_BRIDGE = """import json,sys,pathlib,time
folder=pathlib.Path(sys.argv[2])
job=json.loads((folder/'job.json').read_text())
if sys.argv[1]=='review':
 deadline=time.time()+60
 while not (folder/'release').exists() and time.time()<deadline: time.sleep(.01)
 print(json.dumps({'ok':True,'review_id':'review-fingerprint','id':job['id'],'provider_ready':True,'counted':[]}))
else:
 (folder/'synthetic-starts.txt').write_text('one\\n')
 (folder/'status.json').write_text(json.dumps({'state':'stopped','message':'Synthetic only'}))
"""
REFUSING_BRIDGE = "import json\nprint(json.dumps({'ok':False,'problems':['synthetic refusal']}))\n"


def engine_with(tmp_path: Path, name: str, bridge: str) -> Engine:
    root = tmp_path / name
    root.mkdir()
    (root / "bridge.py").write_text(bridge)
    (root / "store.py").write_text(FAKE_STORE)
    return Engine(root=root, python=sys.executable)


def slow_review_engine(tmp_path: Path, seconds: str, name: str = "slow") -> Engine:
    return engine_with(tmp_path, name, SLOW_BRIDGE.replace("SECONDS", seconds))


def held_review_engine(tmp_path: Path) -> Engine:
    return engine_with(tmp_path, "held-review", HELD_REVIEW_BRIDGE)


POOL = ThreadPoolExecutor(max_workers=8)


def background(work: Callable[[], Any]) -> Future[Any]:
    return POOL.submit(work)


def review_in_thread(app: Application) -> Future[Any]:
    return background(lambda: review_request(client_of(app), '["annual.txt"]'))


def in_flight(app: Application) -> int:
    with app.lock:
        return app.reviews


def wait_reviews(app: Application, want: int) -> None:
    deadline = time.time() + 5
    while in_flight(app) != want:
        assert time.time() < deadline, f"{in_flight(app)} reviews in flight, want {want}"
        time.sleep(0.005)


def held_jobs(root: Path, want: int) -> list[Path]:
    deadline = time.time() + 5
    while True:
        jobs = sorted((root / "intake").glob("web-*/job.json"))
        if len(jobs) >= want:
            return [job.parent for job in jobs]
        assert time.time() < deadline, f"{len(jobs)} held reviews, want {want}"
        time.sleep(0.005)


def release_reviews(root: Path, want: int) -> None:
    for folder in held_jobs(root, want):
        (folder / "release").write_bytes(b"")


def switch_to(client: TestClient, workspace: str) -> Any:
    return call(client, "POST", "/api/settings", json.dumps({"workspace": workspace}))


def block_discovery(
    monkeypatch: pytest.MonkeyPatch, workspace: str
) -> tuple[threading.Event, threading.Event]:
    entered, release = threading.Event(), threading.Event()
    real = server_module.discover

    def hold(folder: str, seeds: Any) -> Any:
        if folder == workspace:
            entered.set()
            assert release.wait(10)
        return real(folder, seeds)

    monkeypatch.setattr(server_module, "discover", hold)
    return entered, release


class Live:
    """The app under a real uvicorn server on a loopback socket, as `__main__` runs it."""

    def __init__(self, base: Path, engine_of: Callable[[Path], Engine]) -> None:
        base.mkdir()
        listener = socket.socket()
        listener.bind(("127.0.0.1", 0))
        listener.listen(16)
        self.port = listener.getsockname()[1]
        self.root = base / "workspace"
        fixture(self.root)
        add_delivery(self.root, "report", "case-a", "EX")
        self.app = Application(locations(base), str(self.root), f"127.0.0.1:{self.port}")
        self.app.engine = engine_of(base)
        self.server = uvicorn.Server(
            uvicorn.Config(
                self.app.asgi, log_config=None, access_log=False, lifespan="off",
                timeout_graceful_shutdown=10,
            )
        )  # fmt: skip
        self.thread = threading.Thread(
            target=self.server.run, kwargs={"sockets": [listener]}, daemon=True
        )
        self.thread.start()
        deadline = time.time() + 10
        while not self.server.started:
            assert time.time() < deadline, "the server did not start"
            time.sleep(0.01)

    def client(self, timeout: float | None) -> httpx.Client:
        origin = f"http://127.0.0.1:{self.port}"
        cookie = f"{cookie_name(self.app.host)}={self.app.session.cookie}"
        headers = {"Cookie": cookie, "X-Issuer-Library": "1", "Origin": origin}
        return httpx.Client(base_url=origin, headers=headers, timeout=timeout, trust_env=False)

    def review(self, timeout: float | None = 30) -> httpx.Response:
        data = {
            "context": "{}",
            "config": "c",
            "cap_usd": "1",
            "source_paths": '["a.txt"]',
            "modules": "CP-4",
        }
        with self.client(timeout) as client:
            return client.post("/api/runs/review", data=data, files=[("sources", ("a.txt", b"x"))])

    def switch(self, workspace: str) -> httpx.Response:
        with self.client(10) as client:
            return client.post(
                "/api/settings",
                content=json.dumps({"workspace": workspace}),
                headers={"Content-Type": "application/json"},
            )

    def stop(self, bound: float = 10) -> bool:
        """Whether the server ended within the bound, which waits for every running handler."""
        self.server.should_exit = True
        self.thread.join(bound)
        return not self.thread.is_alive()


@pytest.fixture
def live(tmp_path: Path) -> Iterator[Callable[[Callable[[Path], Engine]], Live]]:
    started: list[Live] = []

    def start(engine_of: Callable[[Path], Engine]) -> Live:
        server = Live(tmp_path / f"live{len(started)}", engine_of)
        started.append(server)
        return server

    yield start
    for server in started:
        server.stop()


def test_slow_review_response_outlives_a_short_server_deadline(
    live: Callable[[Callable[[Path], Engine]], Live],
) -> None:
    server = live(lambda base: slow_review_engine(base, "2.5"))
    results = [background(server.review) for _ in range(2)]
    ids = set()
    for result in results:
        response = result.result(30)
        review = response.json()
        assert response.status_code == 200 and review["review_id"] == "rid" and review["id"]
        ids.add(review["id"])
    assert len(ids) == 2, f"reviews shared an id: {ids}"


def test_review_past_the_bound_is_reported_not_dropped(
    monkeypatch: pytest.MonkeyPatch, live: Callable[[Callable[[Path], Engine]], Live]
) -> None:
    monkeypatch.setattr(jobs_module, "REVIEW_TIMEOUT", 1.0)
    server = live(lambda base: slow_review_engine(base, "30"))
    started = time.time()
    response = server.review()
    assert response.status_code == 503 and time.time() - started < 10
    assert "CP-OS validation could not complete" in response.text
    assert intake_entries(server.root) == []


@pytest.mark.parametrize(("sleep", "status"), [("1.4", 200), ("4", 503)])
def test_review_just_under_and_just_over_the_bound(
    monkeypatch: pytest.MonkeyPatch,
    live: Callable[[Callable[[Path], Engine]], Live],
    sleep: str,
    status: int,
) -> None:
    monkeypatch.setattr(jobs_module, "REVIEW_TIMEOUT", 2.0)
    server = live(lambda base: slow_review_engine(base, sleep))
    started = time.time()
    response = server.review()
    elapsed = time.time() - started
    assert response.status_code == status, response.text
    assert server.stop()
    entries = intake_entries(server.root)
    if status == 200:
        assert response.json()["review_id"] == "rid" and len(entries) == 1
    else:
        assert elapsed <= 3.5 and entries == [], f"503 after {elapsed}s; intake {entries}"
        assert not list((server.root / "intake").glob("*/start.claim"))


def test_client_disconnect_mid_review(live: Callable[[Callable[[Path], Engine]], Live]) -> None:
    server = live(lambda base: slow_review_engine(base, "1.5"))
    with pytest.raises(httpx.TimeoutException):
        server.review(timeout=0.3)
    assert server.review().status_code == 200, "the server stopped serving after a disconnect"
    assert server.stop(10), "a handler is still running after the review bound"
    assert len(intake_entries(server.root)) == 2, "the abandoned draft and the completed one"


@pytest.mark.skip(
    reason="not applicable: asserts Go's per-response write-deadline extension on a keep-alive "
    "connection (http.Server WriteTimeout); uvicorn has no write timeout and this server extends "
    "no per-response deadline, so there is no deadline to keep or lose"
)
def test_other_endpoints_keep_the_server_write_timeout() -> None:
    raise AssertionError("not applicable")


def close_uploads(form: FormData) -> None:
    for upload in form.getlist("sources"):
        if isinstance(upload, UploadFile):
            upload.file.close()


def upload_of_size(tmp_path: Path, size: int, name: str = "big.pdf") -> tuple[FormData, str]:
    """A parsed review form whose one source is a file object of `size` bytes, and its sha256."""
    stream = tempfile.TemporaryFile()  # noqa: SIM115 (the calling test closes it through close_uploads)
    chunk = b"0123456789abcdef" * (1 << 16)  # 1 MiB
    hasher = hashlib.sha256()
    written = 0
    while written < size:
        part = chunk[: min(len(chunk), size - written)]
        stream.write(part)
        hasher.update(part)
        written += len(part)
    stream.seek(0)
    upload = UploadFile(file=stream, size=size, filename=name)
    form = FormData(
        [
            ("context", "{}"),
            ("config", "sol-medium"),
            ("cap_usd", "10.00"),
            ("source_paths", json.dumps([name])),
            ("sources", upload),
        ]
    )
    return form, hasher.hexdigest()


def test_upload_streams_each_source_within_the_exact_limit(tmp_path: Path) -> None:
    # The handler is called with the parsed form, so the transport's copy of the 64 MiB body is
    # outside the measurement; the file object is built before tracemalloc starts.
    app, root = make_app(tmp_path)
    app.engine = fake_engine(tmp_path)
    form, want = upload_of_size(tmp_path, 64 << 20)
    tracemalloc.start()
    try:
        response = jobs_module.review_run(app, form)
        peak = tracemalloc.get_traced_memory()[1]
    finally:
        tracemalloc.stop()
        close_uploads(form)
    assert response.status_code == 200, response.body
    folder = root / "intake" / json.loads(response.body)["id"]
    job = json.loads((folder / "job.json").read_bytes())
    assert [source["sha256"] for source in job["sources"]] == [want]
    assert (folder / "sources" / "big.pdf").stat().st_size == 64 << 20
    assert peak <= 16 << 20, f"handling a 64 MiB upload allocated {peak >> 20} MiB"
    before = intake_entries(root)
    form, _ = upload_of_size(tmp_path, (64 << 20) + 1)
    try:
        with pytest.raises(HTTPException) as refused:
            jobs_module.review_run(app, form)
    finally:
        close_uploads(form)
    assert refused.value.status_code == 400 and "up to 64 MiB each" in refused.value.detail
    assert intake_entries(root) == before, "a refused upload left a folder"


def test_upload_larger_than_its_declared_size_is_refused_after_a_bounded_read(
    tmp_path: Path,
) -> None:
    app, root = make_app(tmp_path)
    app.engine = fake_engine(tmp_path)
    form, _ = upload_of_size(tmp_path, (64 << 20) + 1)
    upload = form.getlist("sources")[0]
    assert isinstance(upload, UploadFile)
    upload.size = None
    try:
        with pytest.raises(HTTPException) as refused:
            jobs_module.review_run(app, form)
    finally:
        close_uploads(form)
    assert refused.value.status_code == 400
    assert refused.value.detail == "Source upload is too large or unreadable: big.pdf"
    assert intake_entries(root) == []


def test_workspace_save_spelled_with_a_leading_double_slash_is_no_switch_during_a_review(
    tmp_path: Path,
) -> None:
    # Go's filepath.Clean collapses a leading "//" to "/", so it is the same workspace.
    app, root = make_app(tmp_path)
    app.engine = held_review_engine(tmp_path)
    client = client_of(app)
    try:
        done = review_in_thread(app)
        wait_reviews(app, 1)
        response = switch_to(client, f"/{root}")
        assert response.status_code == 200, response.text
        release_reviews(root, 1)
        assert done.result(30).status_code == 200
        wait_reviews(app, 0)
    finally:
        release_reviews(root, 0)


def test_workspace_switch_is_refused_while_a_review_is_in_flight(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    app, root = make_app(tmp_path)
    app.engine = held_review_engine(tmp_path)
    client = client_of(app)
    other = tmp_path / "other"
    other.mkdir()
    discovered: list[str] = []
    real = server_module.discover

    def count(folder: str, seeds: Any) -> Any:
        if folder == str(other):
            discovered.append(folder)
        return real(folder, seeds)

    monkeypatch.setattr(server_module, "discover", count)
    try:
        done = review_in_thread(app)
        wait_reviews(app, 1)
        refused = switch_to(client, str(other))
        assert refused.status_code == 409 and refused.text == REVIEW_IN_FLIGHT + "\n"
        assert discovered == [], "a switch refused for the review still discovered it"
        for same in (str(root), f"{root}{os.sep}", str(root / ".")):
            response = switch_to(client, same)
            assert response.status_code == 200, f"{same!r}: {response.text}"
        assert app.config.workspace == str(root)
        release_reviews(root, 1)
        review = done.result(30)
        assert review.status_code == 200 and review.json()["ok"] is True
        wait_reviews(app, 0)
        started = start_job(client, review.json()["id"])
        assert started.status_code == 202, started.text
        wait_idle(app)
        assert switch_to(client, str(other)).status_code == 200
        assert app.config.workspace == str(other)
    finally:
        release_reviews(root, 0)


def test_a_review_past_the_bound_releases_the_workspace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(jobs_module, "REVIEW_TIMEOUT", 1.0)
    app, root = make_app(tmp_path)
    app.engine = held_review_engine(tmp_path)
    client = client_of(app)
    other = tmp_path / "other"
    other.mkdir()
    try:
        done = review_in_thread(app)
        wait_reviews(app, 1)
        assert switch_to(client, str(other)).status_code == 409
        assert done.result(30).status_code == 503
        assert in_flight(app) == 0
        assert switch_to(client, str(other)).status_code == 200
    finally:
        release_reviews(root, 0)


def test_a_review_whose_client_went_away_holds_the_workspace_until_it_ends(
    tmp_path: Path, live: Callable[[Callable[[Path], Engine]], Live]
) -> None:
    server = live(lambda base: held_review_engine(base))
    other = tmp_path / "other"
    other.mkdir()
    try:
        with pytest.raises(httpx.TimeoutException):
            server.review(timeout=1.0)
        wait_reviews(server.app, 1)
        assert server.switch(str(other)).status_code == 409
        release_reviews(server.root, 1)
        wait_reviews(server.app, 0)
        response = server.switch(str(other))
        assert response.status_code == 200, response.text
    finally:
        release_reviews(server.root, 0)


def test_review_errors_leave_no_review_in_flight(tmp_path: Path) -> None:
    app, _ = make_app(tmp_path)
    good = fake_engine(tmp_path)
    client = client_of(app)
    cases = [
        ("missing runtime", missing_python(tmp_path, good), '["annual.txt"]', 503),
        (
            "validator refusal",
            engine_with(tmp_path, "refusing", REFUSING_BRIDGE),
            '["annual.txt"]',
            200,
        ),
        ("refused upload", good, '["../outside.txt"]', 400),
    ]
    for label, engine, paths, status in cases:
        app.engine = engine
        response = review_request(client, paths)
        assert response.status_code == status, f"{label}: {response.text}"
        assert in_flight(app) == 0, f"{label}: reviews in flight"
    assert switch_to(client, str(tmp_path)).status_code == 200


def test_two_reviews_in_flight_refuse_the_switch_until_both_end(tmp_path: Path) -> None:
    app, root = make_app(tmp_path)
    app.engine = held_review_engine(tmp_path)
    client = client_of(app)
    other = tmp_path / "other"
    other.mkdir()
    try:
        done = [review_in_thread(app) for _ in range(2)]
        wait_reviews(app, 2)
        assert switch_to(client, str(other)).status_code == 409
        (held_jobs(root, 2)[0] / "release").write_bytes(b"")
        finished, pending = futures_wait(done, timeout=30, return_when=FIRST_COMPLETED)
        assert len(finished) == 1 and next(iter(finished)).result().status_code == 200
        wait_reviews(app, 1)
        assert switch_to(client, str(other)).status_code == 409
        release_reviews(root, 1)
        assert next(iter(pending)).result(30).status_code == 200
        wait_reviews(app, 0)
        assert switch_to(client, str(other)).status_code == 200
    finally:
        release_reviews(root, 0)


def test_a_review_started_during_a_switch_refuses_it_at_commit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    app, root = make_app(tmp_path)
    app.engine = held_review_engine(tmp_path)
    other = tmp_path / "other"
    other.mkdir()
    entered, release = block_discovery(monkeypatch, str(other))
    try:
        switched = background(lambda: switch_to(client_of(app), str(other)))
        assert entered.wait(10)
        done = review_in_thread(app)
        wait_reviews(app, 1)
        release.set()
        response = switched.result(30)
        assert response.status_code == 409 and response.text == REVIEW_IN_FLIGHT + "\n"
        with app.lock:
            workspace, catalogue = app.config.workspace, app.catalogue.workspace
        assert workspace == str(root) and catalogue == str(root)
        release_reviews(root, 1)
        review = done.result(30)
        assert review.status_code == 200
        assert (root / "intake" / review.json()["id"] / "review.json").exists()
    finally:
        release.set()
        release_reviews(root, 0)


def test_start_during_a_workspace_switch_refuses_the_switch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    app, root, client, job_id = reviewed(tmp_path)
    other = tmp_path / "other"
    other.mkdir()
    entered, release = block_discovery(monkeypatch, str(other))
    try:
        switched = background(lambda: switch_to(client_of(app), str(other)))
        assert entered.wait(10)
        assert start_job(client, job_id).status_code == 202
        release.set()
        response = switched.result(30)
        assert response.status_code == 409
        assert "Wait for the active run" in response.text
        wait_idle(app)
        with app.lock:
            workspace, catalogue = app.config.workspace, app.catalogue.workspace
        assert workspace == str(root) and catalogue == str(root)
    finally:
        release.set()


def test_a_quitting_app_refuses_review_before_counting_or_staging(tmp_path: Path) -> None:
    app, root = make_app(tmp_path)
    app.engine = fake_engine(tmp_path)
    app.quitting = True
    response = review_request(client_of(app), '["annual.txt"]')
    assert response.status_code == 503 and QUITTING in response.text
    assert in_flight(app) == 0 and not (root / "intake").exists()


def test_a_quitting_app_refuses_resume_before_counting_or_copying(tmp_path: Path) -> None:
    app, root, client, job_id = stopped_run(tmp_path)
    before = intake_entries(root)
    app.quitting = True
    response = call(client, "POST", "/api/runs/resume", resume_body(job_id))
    assert response.status_code == 503 and QUITTING in response.text
    assert in_flight(app) == 0 and intake_entries(root) == before


# Sub-task 5E: one native notice per finished run when no tab watches (Go jobs_test.go 1879-2290).
ORIGIN_NS = 1_794_139_200_000_000_000  # 2026-11-08T12:00:00Z, as in the Go tests.
SECOND_NS = 1_000_000_000
HOLD_FILE_BRIDGE = """import json,sys,pathlib,time
folder=pathlib.Path(sys.argv[2])
job=json.loads((folder/'job.json').read_text())
if sys.argv[1]=='review':
 print(json.dumps({'ok':True,'review_id':'review-fingerprint','id':job['id'],'provider_ready':True,'counted':[],'cap_usd':job['cap_usd'],'max_turns':job['max_turns']}))
else:
 while (folder/'hold').exists(): time.sleep(.02)
 (folder/'status.json').write_text(json.dumps({'state':'stopped','message':'synthetic'}))
"""
EXIT_GATE_BRIDGE = """import json,sys,pathlib,time
folder=pathlib.Path(sys.argv[2])
job=json.loads((folder/'job.json').read_text())
if sys.argv[1]=='review':
 print(json.dumps({'ok':True,'review_id':'review-fingerprint','id':job['id'],'provider_ready':True,'counted':[],'cap_usd':job['cap_usd'],'max_turns':job['max_turns']}))
else:
 (folder/'status.json').write_text(json.dumps({'state':'stopped','message':'synthetic'}))
 while (folder/'exit-gate').exists(): time.sleep(.02)
"""


class FakeClock:
    """A settable clock in integer nanoseconds, safe for the threads that read it."""

    def __init__(self) -> None:
        self.value = ORIGIN_NS
        self.mutex = threading.Lock()

    def read(self) -> int:
        with self.mutex:
            return self.value

    def add(self, seconds: float) -> None:
        with self.mutex:
            self.value += int(seconds * SECOND_NS)


def bridge_engine(tmp_path: Path, bridge: str) -> Engine:
    root = tmp_path / "bridge-engine"
    root.mkdir()
    (root / "bridge.py").write_text(bridge)
    (root / "store.py").write_text(FAKE_STORE)
    return Engine(root=root, python=sys.executable)


def finished_folder(root: Path, job_id: str) -> Path:
    """The folder of a run whose worker wrote its final stopped status (Go finishedFolder)."""
    folder = root / "intake" / job_id
    folder.mkdir(parents=True)
    (folder / "status.json").write_text('{"state":"stopped","message":"synthetic"}')
    return folder


def clocked_app(tmp_path: Path) -> tuple[Application, Path, FakeClock, list[tuple[str, str]]]:
    app, root = make_app(tmp_path)
    clock = FakeClock()
    notices: list[tuple[str, str]] = []
    app.now = clock.read
    app.notifier = lambda title, body: notices.append((title, body))
    return app, root, clock, notices


@pytest.mark.parametrize(
    ("poll_first", "poll_after", "want"),
    [(True, True, 0), (False, False, 1), (True, False, 1)],
    ids=[
        "A poll after the finish gives no native notice",
        "No poll at all gives one native notice",
        "A poll only before the finish gives one native notice",
    ],
)
def test_a_finished_run_notifies_natively_only_when_no_tab_watches(
    tmp_path: Path, poll_first: bool, poll_after: bool, want: int
) -> None:
    app, root, clock, calls = clocked_app(tmp_path)
    app.engine = bridge_engine(tmp_path, HOLD_FILE_BRIDGE)
    client = client_of(app)
    pauses: list[int] = []

    def pause(seconds: float) -> None:
        pauses.append(1)  # Only the finish_job thread calls pause.
        clock.add(seconds)
        if poll_after and len(pauses) == 3:
            client.get("/api/runs/list")

    done = threading.Event()
    app.pause = pause
    app.on_finished = lambda _id: done.set()
    job_id = review_request(client, '["annual.txt"]').json()["id"]
    hold = root / "intake" / job_id / "hold"
    hold.write_bytes(b"")
    assert call(client, "POST", "/api/runs/start", start_payload(job_id)).status_code == 202
    if poll_first:
        assert client.get("/api/runs/list").status_code == 200
    clock.add(1)  # Time passes between that poll and the finish.
    hold.unlink()
    assert done.wait(10), "finish_job did not return"
    assert len(calls) == want, calls
    if want == 1:
        assert calls[0] == ("Credit OS", "Run stopped")


@pytest.mark.parametrize(
    ("query", "polls", "want"),
    [
        ("", True, 0),  # A notifying tab saw the final state before the finish was recorded.
        ("?notify=0", True, 1),  # A tab without notice permission saw it: the native notice.
        ("", False, 1),  # No tab polled.
    ],
)
def test_one_notice_per_finished_run(tmp_path: Path, query: str, polls: bool, want: int) -> None:
    job_id = "web-" + "d1" * 16
    app, root, clock, notices = clocked_app(tmp_path)
    folder = finished_folder(root, job_id)
    app.pause = clock.add
    app.active_jobs = {job_id}  # The run's finish_job is pending.
    if polls:
        assert client_of(app).get("/api/runs/list" + query).status_code == 200
    clock.add(1)  # Teardown and wait: the finish is recorded after the poll.
    jobs_module.finish_job(app, folder, job_id)
    assert len(notices) == want


@pytest.mark.parametrize(("query", "want"), [("", 0), ("?notify=0", 1), ("?notify=1", 0)])
def test_a_poll_from_a_tab_that_cannot_notify_does_not_count_as_watching(
    tmp_path: Path, query: str, want: int
) -> None:
    job_id = "web-" + "d2" * 16
    app, root, clock, notices = clocked_app(tmp_path)
    folder = finished_folder(root, job_id)
    client = client_of(app)
    polled: list[bool] = []

    def pause(seconds: float) -> None:
        clock.add(seconds)
        if not polled:  # The tab's poll lands while finish_job waits, after the finish.
            polled.append(True)
            client.get("/api/runs/list" + query)

    app.pause = pause
    jobs_module.finish_job(app, folder, job_id)
    assert len(notices) == want


def test_a_poll_between_final_status_and_finish_gives_no_native_notice(tmp_path: Path) -> None:
    app, root, clock, notices = clocked_app(tmp_path)
    app.engine = bridge_engine(tmp_path, EXIT_GATE_BRIDGE)
    app.pause = clock.add
    done = threading.Event()
    app.on_finished = lambda _id: done.set()
    client = client_of(app)
    job_id = review_request(client, '["annual.txt"]').json()["id"]
    folder = root / "intake" / job_id
    gate = folder / "exit-gate"
    gate.write_bytes(b"")
    assert call(client, "POST", "/api/runs/start", start_payload(job_id)).status_code == 202
    for _ in range(200):
        if '"stopped"' in (folder / "status.json").read_text():
            break
        time.sleep(0.025)
    else:
        raise AssertionError("worker never wrote its final status")
    client.get("/api/runs/list")
    gate.unlink()
    assert done.wait(15), "finish_job did not return"
    assert notices == []


def test_a_poll_of_a_failed_start_leaves_no_mark_for_the_retry(tmp_path: Path) -> None:
    job_id = "web-" + "d3" * 16
    app, root, clock, notices = clocked_app(tmp_path)
    folder = finished_folder(root, job_id)  # Stopped, standing for failed: no finish pending.
    app.pause = clock.add
    assert client_of(app).get("/api/runs/list").status_code == 200
    assert app.saw_finish == set(), "a run with no pending finish was marked"
    clock.add(1)
    app.active_jobs = {job_id}  # The retry started.
    jobs_module.finish_job(app, folder, job_id)
    assert len(notices) == 1


def test_a_same_tick_poll_after_the_mark_was_taken_counts_as_watching(tmp_path: Path) -> None:
    job_id = "web-" + "d4" * 16
    app, root, clock, notices = clocked_app(tmp_path)
    folder = finished_folder(root, job_id)
    client = client_of(app)
    app.active_jobs = {job_id}
    polled: list[bool] = []

    def pause(seconds: float) -> None:
        if not polled:
            polled.append(True)
            client.get("/api/runs/list")  # The clock has not moved since finished was set.
        clock.add(seconds)

    app.pause = pause
    jobs_module.finish_job(app, folder, job_id)
    assert notices == []


def test_the_first_notify_value_decides_whether_a_poll_counts(tmp_path: Path) -> None:
    # Go's Query().Get takes the first value: notify=0&notify=1 is a tab that cannot notify.
    for query, want in (("notify=0&notify=1", 1), ("notify=1&notify=0", 0)):
        job_id = "web-" + "e7" * 16
        app, root, clock, notices = clocked_app(tmp_path / str(want))
        folder = finished_folder(root, job_id)
        app.pause = clock.add
        app.active_jobs = {job_id}
        assert client_of(app).get("/api/runs/list?" + query).status_code == 200
        clock.add(1)
        jobs_module.finish_job(app, folder, job_id)
        assert len(notices) == want, query


def test_a_nul_in_the_notice_text_is_logged_not_raised(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    exe = tmp_path / "WindowsPowerShell" / "v1.0" / "powershell.exe"
    exe.parent.mkdir(parents=True)
    exe.symlink_to("/usr/bin/true")
    monkeypatch.setattr(notify, "sys", SimpleNamespace(platform="win32"))
    monkeypatch.setattr(notify, "system_directory", lambda: str(tmp_path))
    (tmp_path / "job").mkdir()
    (tmp_path / "job" / "status.json").write_text('{"state":"stopped"}')
    (tmp_path / "job" / "review.json").write_text('{"issuer":"A\\u0000B"}')
    lib = SimpleNamespace(notifier=notify.toast)
    with caplog.at_level("WARNING", logger="issuer_library"):
        jobs_module.notice_finish(cast(Any, lib), tmp_path / "job", "web-x")
    assert any("Run web-x: native notice failed" in r.getMessage() for r in caplog.records)


posix_only = pytest.mark.skipif(sys.platform == "win32", reason="POSIX flock and FIFO semantics")
RUNNING = b'{"state":"running"}'


def running_job(root: Path, number: int) -> Path:
    job_id = f"web-{number:032x}"
    write_job(root, job_id, "running", time.time())
    return root / "intake" / job_id


def adoption_warnings(caplog: pytest.LogCaptureFixture) -> list[str]:
    return [r.getMessage() for r in caplog.records if r.levelno >= logging.WARNING]


def test_a_status_link_is_not_read_or_overwritten_by_adoption(tmp_path: Path) -> None:
    app, root = make_app(tmp_path)
    target = tmp_path / "outside.json"
    target.write_bytes(RUNNING)
    folder = root / "intake" / f"web-{1:032x}"
    folder.mkdir(parents=True)
    link_or_skip(folder / "status.json", target)
    assert jobs_module.job_state(folder) is None
    with app.lock:
        jobs_module.adopt_jobs_locked(app, str(root))
    assert target.read_bytes() == RUNNING
    assert (folder / "status.json").is_symlink()
    assert app.active_jobs == set()


@posix_only
def test_a_worker_lock_link_cannot_be_checked_and_leaves_the_job_alone(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    import fcntl

    app, root = make_app(tmp_path)
    folder = running_job(root, 2)
    before = (folder / "status.json").read_bytes()
    target = tmp_path / "held.lock"
    target.write_bytes(b"")
    link_or_skip(folder / "worker.lock", target)
    holder = os.open(target, os.O_RDWR)
    try:
        fcntl.flock(holder, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with pytest.raises(OSError):
            jobs_module.worker_alive(folder / "worker.lock")
        with caplog.at_level(logging.WARNING, logger="issuer_library"), app.lock:
            jobs_module.adopt_jobs_locked(app, str(root))
    finally:
        os.close(holder)
    assert (folder / "status.json").read_bytes() == before
    assert app.active_jobs == set()
    assert any("cannot be checked" in message for message in adoption_warnings(caplog))


@posix_only
@pytest.mark.parametrize("existing", [True, False])
def test_hold_worker_lock_refuses_a_link_and_touches_nothing(
    tmp_path: Path, existing: bool
) -> None:
    import fcntl

    target = tmp_path / "elsewhere.lock"
    if existing:
        target.write_bytes(b"")
    link_or_skip(tmp_path / "worker.lock", target)
    with pytest.raises(OSError):
        jobs_module.hold_worker_lock(tmp_path / "worker.lock")
    if not existing:
        assert not target.exists()
        return
    descriptor = os.open(target, os.O_RDWR)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
    finally:
        os.close(descriptor)


@posix_only
def test_a_status_fifo_does_not_hang_startup(tmp_path: Path) -> None:
    _, root = make_app(tmp_path)
    folder = root / "intake" / f"web-{4:032x}"
    folder.mkdir(parents=True)
    os.mkfifo(folder / "status.json")
    built: list[Application] = []
    thread = threading.Thread(target=lambda: built.append(restarted(tmp_path, root)), daemon=True)
    thread.start()
    thread.join(5)
    assert not thread.is_alive(), "Application() blocked on a status.json FIFO"
    assert built[0].active_jobs == set()


@posix_only
def test_a_worker_lock_fifo_raises_without_blocking(tmp_path: Path) -> None:
    folder = tmp_path / "job"
    folder.mkdir()
    os.mkfifo(folder / "worker.lock")
    outcome: list[BaseException | None] = []

    def check() -> None:
        try:
            jobs_module.worker_alive(folder / "worker.lock")
            outcome.append(None)
        except OSError as error:
            outcome.append(error)

    thread = threading.Thread(target=check, daemon=True)
    thread.start()
    thread.join(5)
    assert not thread.is_alive(), "worker_alive blocked on a FIFO"
    assert isinstance(outcome[0], OSError)


def test_adoption_logs_a_refused_status_but_not_a_missing_or_settled_one(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    app, root = make_app(tmp_path)
    refused = root / "intake" / f"web-{5:032x}"
    refused.mkdir(parents=True)
    link_or_skip(refused / "status.json", tmp_path / "nowhere.json")
    (root / "intake" / f"web-{6:032x}").mkdir()
    write_job(root, f"web-{7:032x}", "done", time.time())
    with caplog.at_level(logging.WARNING, logger="issuer_library"), app.lock:
        jobs_module.adopt_jobs_locked(app, str(root))
    messages = adoption_warnings(caplog)
    assert len(messages) == 1 and refused.name in messages[0]


def test_adoption_logs_an_intake_folder_that_cannot_be_listed(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    app, _ = make_app(tmp_path)
    with caplog.at_level(logging.WARNING, logger="issuer_library"), app.lock:
        jobs_module.adopt_jobs_locked(app, str(tmp_path / "fresh"))
    assert adoption_warnings(caplog) == []  # A missing intake folder is normal.
    (tmp_path / "file").write_bytes(b"")
    with caplog.at_level(logging.WARNING, logger="issuer_library"), app.lock:
        jobs_module.adopt_jobs_locked(app, str(tmp_path / "file" / "x"))
    messages = adoption_warnings(caplog)
    assert len(messages) == 1 and "intake" in messages[0]


# C11 call sites: every rediscovery runs through Application.refresh(), outside the lock.


def finish_on_thread(app: Application, folder: Path, job_id: str) -> threading.Thread:
    app.active_jobs.add(job_id)
    thread = threading.Thread(
        target=jobs_module.finish_job, args=(app, folder, job_id), daemon=True
    )
    thread.start()
    return thread


def counted_discovery(monkeypatch: pytest.MonkeyPatch) -> dict[str, int]:
    """Wrap discover to count entries and the most that ran at once."""
    seen = {"now": 0, "max": 0, "total": 0}
    guard = threading.Lock()
    real = server_module.discover

    def counting(folder: str, seeds: Any) -> Any:
        with guard:
            seen["now"] += 1
            seen["total"] += 1
            seen["max"] = max(seen["max"], seen["now"])
        try:
            time.sleep(0.01)
            return real(folder, seeds)
        finally:
            with guard:
                seen["now"] -= 1

    monkeypatch.setattr(server_module, "discover", counting)
    return seen


def test_a_finishing_run_does_not_hold_the_lock_while_it_discovers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(notify, "tab_watching", lambda lib: True)
    job_id = "web-" + "f1" * 16
    app, root, _, _ = clocked_app(tmp_path)
    folder = finished_folder(root, job_id)
    finished: list[str] = []
    app.on_finished = finished.append
    entered, release = block_discovery(monkeypatch, str(root))
    thread = finish_on_thread(app, folder, job_id)
    try:
        assert entered.wait(10), "finish_job never discovered"
        assert app.lock.acquire(timeout=2), "finish_job holds the catalogue lock while it discovers"
        app.lock.release()
        started = time.time()
        assert client_of(app).get("/api/runs/list").status_code == 200
        assert time.time() - started < 5
    finally:
        release.set()
        thread.join(10)
    assert not thread.is_alive()
    assert finished == [job_id]


def test_discoveries_never_overlap(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(notify, "tab_watching", lambda lib: True)
    app, root, _, _ = clocked_app(tmp_path)
    seen = counted_discovery(monkeypatch)
    ids = ["web-" + f"{n:02x}" * 16 for n in range(1, 5)]
    folders = [finished_folder(root, job_id) for job_id in ids]
    threads = [finish_on_thread(app, f, i) for f, i in zip(folders, ids, strict=True)]
    ticking = threading.Thread(
        target=main_module.rediscover, args=(app, lambda: seen["total"] >= 12, 0.01), daemon=True
    )
    ticking.start()
    posts = [
        threading.Thread(
            target=call, args=(client_of(app), "POST", "/api/refresh", "{}"), daemon=True
        )
        for _ in range(3)
    ]
    for post in posts:
        post.start()
    for thread in [*threads, ticking, *posts]:
        thread.join(30)
        assert not thread.is_alive()
    assert seen["total"] > 1
    assert seen["max"] == 1, f"{seen['max']} discoveries ran at once"


def test_a_quitting_library_discovers_nothing_but_still_notices_a_finish(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(notify, "tab_watching", lambda lib: False)
    job_id = "web-" + "f3" * 16
    app, root, _, notices = clocked_app(tmp_path)
    folder = finished_folder(root, job_id)
    seen = counted_discovery(monkeypatch)
    finished: list[str] = []
    app.on_finished = finished.append
    app.active_jobs.add(job_id)
    app.quitting = True
    assert app.refreshing.acquire(timeout=1)  # An idle quit leaves it held for good.
    thread = threading.Thread(
        target=jobs_module.finish_job, args=(app, folder, job_id), daemon=True
    )
    thread.start()
    thread.join(10)
    assert not thread.is_alive(), "finish_job waits on a quitting library"
    assert len(notices) == 1 and finished == [job_id]
    ticking = threading.Thread(
        target=main_module.rediscover, args=(app, lambda: False, 0.01), daemon=True
    )
    ticking.start()
    ticking.join(5)
    assert not ticking.is_alive(), "rediscover keeps waiting on a quitting library"
    refused = call(client_of(app), "POST", "/api/refresh", "{}")
    assert refused.status_code == 503 and refused.text == server_module.LIBRARY_QUITTING + "\n"
    assert seen["total"] == 0, "a quitting library discovered"


@pytest.mark.skipif(sys.platform == "win32", reason="the POSIX lock open")
def test_a_transient_lock_open_error_keeps_a_held_lock_job_active(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Answer key: sb2/probes/i24rr_emfile_live_descendant.py and
    # i24rr_transient_open_error_finishes_held_lock.py. EMFILE at the settle's lock open says
    # nothing about the holder, so the job stays active, not finished as "nothing to settle".
    import errno

    monkeypatch.setattr(notify, "tab_watching", lambda lib: False)
    job_id = "web-" + "f4" * 16
    app, root, _, notices = clocked_app(tmp_path)
    folder = finished_folder(root, job_id)
    (folder / "status.json").write_text('{"state":"running","message":"synthetic"}')
    holder = jobs_module.hold_worker_lock(folder / "worker.lock")
    real_open = os.open

    def open_failing_on_the_lock(path: Any, *args: Any, **kwargs: Any) -> int:
        if Path(path).name == "worker.lock":
            raise OSError(errno.EMFILE, os.strerror(errno.EMFILE))
        return real_open(path, *args, **kwargs)

    app.active_jobs.add(job_id)
    monkeypatch.setattr(jobs_module.os, "open", open_failing_on_the_lock)
    try:
        jobs_module.finish_job(app, folder, job_id)
    finally:
        monkeypatch.undo()
        os.close(holder)
    assert jobs_module.still_active(app, job_id), "a held lock's job left active_jobs on EMFILE"
    assert state_of(folder)["state"] == "running" and not notices


MISSING = object()
LISTED = ["CP-4:legal-none", "CP-2:quotes-none"]
ACCEPT_REFUSAL = "Accept the listed limitations before starting"
REVIEW_AGAIN = "Review this run again before starting"


def reviewed_with_counted(
    tmp_path: Path, counted: object
) -> tuple[Application, Path, TestClient, str]:
    """A reviewed job whose approved review.json lists `counted` (MISSING leaves the key out)."""
    app, root, client, job_id = reviewed(tmp_path)
    path = root / "intake" / job_id / "review.json"
    review = json.loads(path.read_bytes())
    if counted is MISSING:
        review.pop("counted", None)
    else:
        review["counted"] = counted
    save_json(path, review)
    return app, root, client, job_id


def accept_body(job_id: str, **fields: Any) -> str:
    return json.dumps({"id": job_id, "review_id": "review-fingerprint", "confirm": True, **fields})


def assert_nothing_started(app: Application, root: Path, job_id: str) -> None:
    folder = root / "intake" / job_id
    assert not (folder / "start.claim").exists(), "a refused start took the one-shot claim"
    assert not (folder / "synthetic-starts.txt").exists(), "a worker was launched"
    assert not (root / "runs" / job_id).exists(), "a refused start created runs/<id>"
    assert not app.active_jobs, "a refused start marked the job active"


def post_start(client: TestClient, body: str) -> Any:
    return client.post("/api/runs/start", content=body, headers=POST_HEADERS)


@pytest.mark.parametrize("fields", [{}, {"accept_limitations": False}])
def test_start_with_counted_limitations_needs_acceptance(
    tmp_path: Path, fields: dict[str, Any]
) -> None:
    app, root, client, job_id = reviewed_with_counted(tmp_path, LISTED)
    response = post_start(client, accept_body(job_id, **fields))
    assert response.status_code == 400 and ACCEPT_REFUSAL in response.text
    assert_nothing_started(app, root, job_id)


def test_start_with_counted_limitations_accepted_starts(tmp_path: Path) -> None:
    app, root, client, job_id = reviewed_with_counted(tmp_path, LISTED)
    response = post_start(client, accept_body(job_id, accept_limitations=True))
    assert response.status_code == 202 and response.json()["state"] == "running"
    assert (root / "intake" / job_id / "start.claim").exists()
    wait_idle(app)
    assert (root / "intake" / job_id / "synthetic-starts.txt").read_text() == "one\n"


@pytest.mark.parametrize("fields", [{}, {"accept_limitations": False}])
def test_start_with_nothing_counted_needs_no_acceptance(
    tmp_path: Path, fields: dict[str, Any]
) -> None:
    app, root, client, job_id = reviewed_with_counted(tmp_path, [])
    response = post_start(client, accept_body(job_id, **fields))
    assert response.status_code == 202 and response.json()["state"] == "running"
    assert (root / "intake" / job_id / "start.claim").exists()
    wait_idle(app)


@pytest.mark.parametrize(
    "fields",
    [
        {"accept_limitations": "true"},
        {"accept_limitations": 1},
        {"accept_limitations": None},
        {"accept_limitations": True, "extra": 1},
    ],
)
@pytest.mark.parametrize("counted", [[], LISTED])
def test_start_refuses_a_non_boolean_acceptance_or_unknown_key(
    tmp_path: Path, counted: list[str], fields: dict[str, Any]
) -> None:
    app, root, client, job_id = reviewed_with_counted(tmp_path, counted)
    response = post_start(client, accept_body(job_id, **fields))
    assert response.status_code == 400, response.text
    assert "Explicit confirmation of a reviewed run is required" in response.text
    assert_nothing_started(app, root, job_id)


@pytest.mark.parametrize(
    "counted", [MISSING, None, "CP-4:legal-none", [1], [["CP-4:legal-none"]], {"a": "b"}]
)
@pytest.mark.parametrize("fields", [{}, {"accept_limitations": True}])
def test_start_with_a_malformed_counted_is_the_invalid_review_answer(
    tmp_path: Path, counted: object, fields: dict[str, Any]
) -> None:
    app, root, client, job_id = reviewed_with_counted(tmp_path, counted)
    response = post_start(client, accept_body(job_id, **fields))
    assert response.status_code == 409 and response.text == REVIEW_AGAIN + "\n"
    assert_nothing_started(app, root, job_id)


def test_a_refused_acceptance_leaves_the_job_startable(tmp_path: Path) -> None:
    app, root, client, job_id = reviewed_with_counted(tmp_path, LISTED)
    for fields in ({}, {"accept_limitations": False}, {"accept_limitations": "yes"}):
        assert post_start(client, accept_body(job_id, **fields)).status_code == 400
        assert_nothing_started(app, root, job_id)
    again = post_start(client, accept_body(job_id, accept_limitations=True))
    assert again.status_code == 202, again.text
    wait_idle(app)
    assert (root / "intake" / job_id / "synthetic-starts.txt").read_text() == "one\n"


OLD_REVIEW_KEYS = [
    "ok",
    "review_id",
    "id",
    "engine_revision",
    "issuer",
    "issuer_id",
    "pathway",
    "as_of",
    "modules",
    "module_details",
    "config",
    "provider",
    "model",
    "effort",
    "cap_usd",
    "hold_usd",
    "max_turns",
    "resume_of",
    "retained_modules",
    "retained_note",
    "prices_as_of",
    "provider_ready",
    "provider_key",
    "sources",
    "ignored",
    "report_sections",
    "omitted",
    "scope",
]


def test_a_review_written_before_expectations_must_be_made_again(tmp_path: Path) -> None:
    app, root, client, job_id = reviewed(tmp_path)
    path = root / "intake" / job_id / "review.json"
    current = json.loads(path.read_bytes())
    old = {key: current.get(key, "x") for key in OLD_REVIEW_KEYS}
    old.update(review_id="review-fingerprint", provider_ready=True)
    for key in ("issue_classification", "documents", "expectations", "counted", "without"):
        assert key not in old
    save_json(path, old)
    for fields in ({}, {"accept_limitations": True}):
        response = post_start(client, accept_body(job_id, **fields))
        assert response.status_code == 409 and response.text == REVIEW_AGAIN + "\n"
        assert_nothing_started(app, root, job_id)
    save_json(path, {**old, "counted": []})  # A fresh review lists its counted items.
    assert post_start(client, accept_body(job_id)).status_code == 202
    wait_idle(app)


def test_a_lock_error_other_than_contention_keeps_the_job_watched(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """ENOLCK (a network share) once, at the lock call that proves a worker dead: the watcher
    must survive, the job stay active until the error clears, then settle and leave."""
    monkeypatch.setattr(jobs_module, "WORKER_POLL", 0.01)
    app, root, _, _ = clocked_app(tmp_path)
    job_id = "web-" + "ab" * 16
    folder = root / "intake" / job_id
    folder.mkdir(parents=True)
    (folder / "status.json").write_text('{"state":"running","message":"x"}')
    (folder / "worker.lock").write_bytes(b"")
    real = jobs_module.fcntl
    failures: list[int] = []

    def flock(descriptor: int, operation: int) -> None:
        if threading.current_thread().name == "watcher" and not failures:
            failures.append(1)
            raise OSError(errno.ENOLCK, "No locks available")
        real.flock(descriptor, operation)

    monkeypatch.setattr(
        jobs_module,
        "fcntl",
        SimpleNamespace(flock=flock, LOCK_EX=real.LOCK_EX, LOCK_NB=real.LOCK_NB),
    )
    died: list[str] = []
    monkeypatch.setattr(threading, "excepthook", lambda args: died.append(repr(args.exc_value)))
    app.active_jobs.add(job_id)

    class Done:
        def wait(self) -> int:
            return 0

    caplog.set_level(logging.WARNING)
    watcher = threading.Thread(
        target=jobs_module.watch, args=(app, job_id, folder, Done()), name="watcher", daemon=True
    )
    watcher.start()
    watcher.join(5)
    assert failures == [1], "the injected lock error never fired"
    assert died == [], f"the watch thread died on a lock error: {died}"
    assert not watcher.is_alive(), "the watcher never settled the job after the error cleared"
    with app.lock:
        assert job_id not in app.active_jobs
    assert state_of(folder)["state"] == "interrupted"
    assert any("No locks available" in message for message in adoption_warnings(caplog))
