"""Shared fixtures for the Issuer Library tests: a hand-written workspace and a synthetic engine."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient
from pydantic import BaseModel

from issuer_library.jobs import Engine
from issuer_library.launch import cookie_name
from issuer_library.model import DeliveryView, Manifest, Metric, Source, blank_run, digest
from issuer_library.server import Application
from issuer_library.settings import Locations

HOST = "127.0.0.1:54321"
ORIGIN = f"http://{HOST}"
POST_HEADERS = {"X-Issuer-Library": "1", "Content-Type": "application/json", "Origin": ORIGIN}
EVIDENCE = b"Issuer: Example Industries\nSector: Industrials\nRevenue: 0\nVerified scope\n"
REPORT = b"<!doctype html><title>Report</title><p>Retained report</p>"
FAKE_BRIDGE = """import json,sys,pathlib,time
folder=pathlib.Path(sys.argv[2])
job=json.loads((folder/'job.json').read_text())
if sys.argv[1]=='review':
 print(json.dumps({'ok':True,'review_id':'review-fingerprint','id':job['id'],'provider_ready':True,'cap_usd':job['cap_usd']}))
else:
 with (folder/'synthetic-starts.txt').open('a') as stream: stream.write('one\\n')
 time.sleep(.15)
 (folder/'status.json').write_text(json.dumps({'state':'stopped','message':'Synthetic worker seam only; no provider called.'}))
"""
FAKE_STORE = """def workspace_store(root, catalogue):
    return {'parsed': catalogue['workspace'], 'folder': str(root)}
"""


def put(root: Path, name: str, raw: bytes) -> None:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)


def put_json(root: Path, name: str, value: Any) -> None:
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json", by_alias=True)
    put(root, name, json.dumps(value).encode())


def fixture(root: Path) -> Manifest:
    """One admitted run, case-a, with a pinned identity, sector, metric and handoff."""
    put(root, "runs/case-a/CP-0.md", EVIDENCE)
    run = blank_run("case-a")
    run.issuer = "EX"
    run.name = "Example Industries"
    run.identity_source = "identity"
    run.sector = "Industrials"
    run.sector_source = "sector"
    run.date = "2024-12-31"
    run.period = "FY2024"
    run.handoff = "runs/case-a/CP-0.md"
    run.metrics["revenue"] = Metric(
        value="0", unit="USD m", period="FY2024", basis="Reported revenue", source="revenue"
    )
    manifest = Manifest(schema="issuer-library-run/1", run=run)
    lines = EVIDENCE.decode().split("\n")
    for key, number in {"identity": 1, "sector": 2, "revenue": 3, "check": 4}.items():
        manifest.sources[key] = Source(
            path="runs/case-a/CP-0.md",
            sha256=digest(EVIDENCE),
            line=number,
            quote=lines[number - 1],
        )
    put_json(root, "runs/case-a/library.json", manifest)
    return manifest


def add_delivery(root: Path, folder: str, run_id: str, issuer: str) -> None:
    view = DeliveryView(mode="candidate")
    view.run.run_id = run_id
    view.run.issuer_id = issuer
    view.run.issuer_name = "Example Industries"
    view.run.as_of = "2024-12-31"
    raw = view.model_dump_json().encode()
    put(root, f"deliverables/{folder}/view.json", raw)
    put(root, f"deliverables/{folder}/report.html", REPORT)
    put_json(
        root,
        f"deliverables/{folder}/delivery.json",
        {"files": {"view.json": digest(raw), "report.html": digest(REPORT)}},
    )


def locations(tmp_path: Path) -> Locations:
    return Locations(state=tmp_path / "state", documents=tmp_path / "documents")


def make_app(tmp_path: Path) -> tuple[Application, Path]:
    root = tmp_path / "workspace"
    fixture(root)
    add_delivery(root, "report", "case-a", "EX")
    return Application(locations(tmp_path), str(root), HOST), root


def client_of(app: Application) -> TestClient:
    cookie = f"{cookie_name(HOST)}={app.session.cookie}"
    return TestClient(app.asgi, base_url=ORIGIN, headers={"Cookie": cookie})


def call(client: TestClient, method: str, endpoint: str, body: str = "") -> Any:
    if method == "POST":
        return client.post(endpoint, content=body, headers=POST_HEADERS)
    return client.get(endpoint)


def fake_engine(tmp_path: Path) -> Engine:
    """A synthetic process boundary: review answers, start writes a stopped status; no provider."""
    root = tmp_path / "engine"
    root.mkdir()
    (root / "bridge.py").write_text(FAKE_BRIDGE)
    (root / "store.py").write_text(FAKE_STORE)
    return Engine(root=root, python=sys.executable)
