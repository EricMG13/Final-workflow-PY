"""S19 review regressions: the server boundary, request bodies, ranges, downloads and the port.

Expected values are written here by hand; no provider is called.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import socket
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from issuer_library_support import HOST, ORIGIN, POST_HEADERS, REPORT, client_of, make_app

import issuer_library.__main__ as launcher
from issuer_library import server
from issuer_library.settings import Locations

BOUNDARY = {
    "cache-control": "no-store",
    "x-content-type-options": "nosniff",
    "referrer-policy": "no-referrer",
    "cross-origin-resource-policy": "same-origin",
}


@pytest.mark.parametrize("endpoint", ["/api/settings", "/api/runs/start"])
def test_a_declared_oversized_body_is_refused_before_it_is_read(tmp_path, endpoint, monkeypatch):
    app, _ = make_app(tmp_path)
    called: list[bytes] = []
    monkeypatch.setattr(app, "apply_settings", lambda raw: called.append(raw))
    monkeypatch.setattr(server, "start_run", lambda lib, raw: called.append(raw))
    response = client_of(app).post(endpoint, content=b"x" * 8193, headers=POST_HEADERS)
    assert response.status_code == 400 and not called


def run_asgi(app, path: str, chunks: int) -> tuple[int, int]:
    """POST chunks of 1 KiB with no Content-Length; how many the server asked for, and status."""
    received = 0
    status = 0

    async def receive():
        nonlocal received
        received += 1
        return {"type": "http.request", "body": b"x" * 1024, "more_body": received < chunks}

    async def send(message):
        nonlocal status
        if message["type"] == "http.response.start":
            status = message["status"]

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "root_path": "",
        "server": ("127.0.0.1", 54321),
        "client": ("127.0.0.1", 50000),
        "headers": [
            (b"host", HOST.encode()),
            (b"origin", ORIGIN.encode()),
            (b"x-issuer-library", b"1"),
            (b"content-type", b"application/json"),
        ],
    }
    asyncio.run(app(scope, receive, send))
    return received, status


@pytest.mark.parametrize("endpoint", ["/api/settings", "/api/runs/start"])
def test_an_undeclared_body_stops_being_read_at_the_limit(tmp_path, endpoint):
    app, _ = make_app(tmp_path)
    received, status = run_asgi(app.asgi, endpoint, chunks=65536)  # 64 MiB offered
    assert status == 400
    assert received <= 9, f"read {received} KiB of a request limited to 8 KiB"


def test_a_small_settings_body_still_applies(tmp_path):
    app, _ = make_app(tmp_path)
    other = tmp_path / "other"
    other.mkdir()
    response = client_of(app).post(
        "/api/settings", content=json.dumps({"workspace": str(other)}), headers=POST_HEADERS
    )
    assert response.status_code == 200 and response.json()["workspace"] == str(other)


def test_an_unhandled_error_answers_with_the_boundary_headers(tmp_path, monkeypatch):
    app, _ = make_app(tmp_path)

    def broken():
        raise RuntimeError("store bug")

    monkeypatch.setattr(app, "catalogue_locked", broken)
    client = TestClient(app.asgi, base_url=ORIGIN, raise_server_exceptions=False)
    response = client.get("/api/catalogue")
    assert (response.status_code, response.text) == (500, "Internal error\n")
    assert {key: response.headers.get(key) for key in BOUNDARY} == BOUNDARY


def test_a_missing_presentation_asset_stops_the_start_with_its_name(tmp_path, monkeypatch):
    web = tmp_path / "web"
    web.mkdir()
    for name in ("legacy-catalog.json", "report-adapter.css", "report-adapter.js"):
        (web / name).write_bytes((server.WEB / name).read_bytes())
    monkeypatch.setattr(server, "WEB", web)
    with pytest.raises(ValueError, match=r"brand\.css is missing"):
        make_app(tmp_path)


def test_presentation_assets_are_read_once(tmp_path, monkeypatch):
    app, _ = make_app(tmp_path)
    reads: list[Path] = []
    real = Path.read_bytes

    def counting(self):
        reads.append(self)
        return real(self)

    monkeypatch.setattr(Path, "read_bytes", counting)
    client = client_of(app)
    name = "/files/deliverables/report/report.html?embedded=1"
    for _ in range(3):
        body = client.get(name + "&sha256=" + server.digest(REPORT)).content
        assert b"data-library-presentation" in body
    assert not [path for path in reads if path.parent == server.WEB]


@pytest.mark.parametrize(
    ("filename", "expected"),
    [
        ("report.html", 'attachment; filename="report.html"'),
        ("notes\\", "attachment; filename*=UTF-8''notes%5C"),
        ('say "hi".txt', "attachment; filename*=UTF-8''say%20%22hi%22.txt"),
        ("line\r\nbreak.txt", "attachment; filename*=UTF-8''line%0D%0Abreak.txt"),
        ("émetteur.pdf", "attachment; filename*=UTF-8''%C3%A9metteur.pdf"),
    ],
)
def test_download_names_are_always_a_well_formed_header(filename, expected):
    assert server.attachment(filename) == expected


def test_ranges_follow_rfc_9110(tmp_path):
    app, _ = make_app(tmp_path)
    client = client_of(app)
    name = "/files/deliverables/report/report.html"
    for ignored in ["items=0-3", "bytes=0-1,5-6", "bytes=-", "bytes=x-y"]:
        response = client.get(name, headers={"Range": ignored})
        assert (response.status_code, response.content) == (200, REPORT), ignored
    unsatisfiable = client.get(name, headers={"Range": "bytes=999-"})
    assert unsatisfiable.status_code == 416
    assert unsatisfiable.headers["content-range"] == f"bytes */{len(REPORT)}"
    assert client.get(name, headers={"Range": "bytes=1-3"}).content == REPORT[1:4]


def arguments(**values) -> argparse.Namespace:
    return argparse.Namespace(**{"port": 0, "workspace": "", "no_browser": True, **values})


def test_an_unbindable_derived_port_falls_back_and_is_recorded(tmp_path):
    loc = Locations(state=tmp_path / "state", documents=tmp_path)
    loc.state.mkdir()
    derived = launcher.stable_port(loc)
    blocker = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        blocker.bind(("127.0.0.1", derived))
    except OSError:
        blocker.close()
        pytest.skip(f"derived port {derived} is already taken on this host")
    try:
        listener = launcher.bind_or_reuse(loc, arguments())
        assert listener is not None
        port = listener.getsockname()[1]
        assert port != derived
        assert json.loads((loc.state / "port.json").read_text()) == {"port": port}
        assert launcher.stable_port(loc) == port
        listener.close()
        explicit = arguments(port=derived)
        with pytest.raises(ValueError, match="occupied by another application"):
            launcher.bind_or_reuse(loc, explicit)
    finally:
        blocker.close()


def test_a_malformed_port_record_is_ignored(tmp_path):
    loc = Locations(state=tmp_path / "state", documents=tmp_path)
    loc.state.mkdir()
    for record in ['{"port": true}', '{"port": 80}', "[1]", "not json"]:
        (loc.state / "port.json").write_text(record)
        assert 49000 <= launcher.stable_port(loc) < 59000, record
