"""The run API over a synthetic engine: review stages and validates, Start launches once."""

from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from issuer_library_support import HOST, ORIGIN, POST_HEADERS, client_of, fake_engine, make_app

import issuer_library.server as server_module
from issuer_library.jobs import Engine
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
        ({"max_turns": "201"}, "Max turns"),
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
