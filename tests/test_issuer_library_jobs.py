"""The run API over a synthetic engine: review stages and validates, Start launches once."""

from __future__ import annotations

import json
import logging
import os
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
    client_of,
    fake_engine,
    make_app,
    put,
)

import issuer_library.events as events_module
import issuer_library.server as server_module
from issuer_library.events import progress
from issuer_library.jobs import Engine, job_view
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
    when = 1794052800.0  # 2026-11-06T12:00:00Z
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
