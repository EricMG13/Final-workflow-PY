"""The run API over a synthetic engine: review stages and validates, Start launches once."""

from __future__ import annotations

import json
import logging
import os
import shutil
import sys
import threading
import time
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from issuer_library_support import (
    HOST,
    ORIGIN,
    POST_HEADERS,
    call,
    client_of,
    fake_engine,
    locations,
    make_app,
    put,
)

import issuer_library.events as events_module
import issuer_library.jobs as jobs_module
import issuer_library.server as server_module
from issuer_library.events import progress
from issuer_library.jobs import Engine, job_view, mkdir_all_in, recorded_job
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
 print(json.dumps({'ok':True,'review_id':'review-fingerprint','id':job['id'],'provider_ready':True,'cap_usd':job['cap_usd'],'max_turns':job['max_turns'],'resume_of':job.get('resume_of')}))
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
 print(json.dumps({'ok':True,'review_id':'review-fingerprint','id':job['id'],'provider_ready':True}))
else:
 deadline=time.time()+60
 while not (folder/'release').exists() and time.time()<deadline: time.sleep(.01)
"""
QUITTING = "Issuer Library is quitting for a new launch; use the window that launch opens."


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
