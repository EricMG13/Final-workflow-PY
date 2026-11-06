"""The HTTP boundary over the fixture workspace: origin checks, pinned files and settings."""

from __future__ import annotations

import base64
import json
import threading
from pathlib import Path

import pytest
from issuer_library_support import (
    HOST,
    ORIGIN,
    POST_HEADERS,
    REPORT,
    client_of,
    fixture,
    locations,
    make_app,
    put,
    put_json,
)

import issuer_library.server as server_module
from issuer_library.model import Catalogue, digest
from issuer_library.server import Application
from issuer_library.settings import Config, Locations, load_config, save_json

WEB = Path(__file__).resolve().parents[1] / "apps/issuer-library/web"


def test_launcher_delivery_is_verified_and_presented_like_any_deliverable(
    tmp_path: Path,
) -> None:
    app, root = make_app(tmp_path)
    client = client_of(app)
    folder = root / "runs/launched/deliveries/abc"
    files = {
        "report.html": b"<html><body>Report</body></html>",
        "view.json": (
            b'{"run":{"run_id":"r","issuer_id":"nbg","issuer_name":"Northbridge",'
            b'"as_of":"2025-03-31"}}'
        ),
        "CP-1.md": b"# CP-1\n",
    }
    for name, raw in files.items():
        put(root, f"runs/launched/deliveries/abc/{name}", raw)
    save_json(folder / "delivery.json", {"files": {n: digest(r) for n, r in files.items()}})
    assert client.post("/api/refresh", content="{}", headers=POST_HEADERS).status_code == 200
    found = [
        artifact
        for run in app.catalogue.real
        for artifact in run.artifacts
        if run.id == "launched" and artifact.folder == "runs/launched/deliveries/abc"
    ]
    assert found and found[0].available, "launcher delivery missing from its run"
    shown = client.get(found[0].href + "&embedded=1")
    assert shown.status_code == 200 and b"data-library-presentation" in shown.content
    saved = client.get(found[0].href + "&download=1")
    assert "abc.html" in saved.headers["content-disposition"]
    assert b"data-library-presentation" not in saved.content
    put(root, "runs/launched/deliveries/abc/report.html", b"changed")
    client.post("/api/refresh", content="{}", headers=POST_HEADERS)
    assert any("deliveries/abc" in issue for issue in app.catalogue.issues)


def test_http_boundary_and_changed_file(tmp_path: Path) -> None:
    app, root = make_app(tmp_path)
    client = client_of(app)
    for name in [
        "/",
        "/screen.js",
        "/fonts/RedHatText-Regular.woff2",
        "/api/catalogue",
        "/files/deliverables/report/report.html",
    ]:
        assert client.get(name).status_code == 200, name
    for name in [
        "/files/AGENTS.md",
        "/files/../secret",
        "/legacy-catalog.json",
        "/new-run.test.cjs",
    ]:
        assert client.get(name).status_code == 404, f"exposed {name}"
    for headers in [
        {"Host": "attacker.invalid"},
        {"Origin": "https://attacker.invalid"},
        {"Sec-Fetch-Site": "cross-site"},
    ]:
        response = client.get("/api/catalogue", headers=headers)
        assert response.status_code == 403, "cross-origin request admitted"
        assert response.headers["cache-control"] == "no-store"
    assert client.post("/api/quit", content="{}").status_code == 403, "unprotected state change"
    response = client.get("/files/deliverables/report/report.html")
    policy = response.headers["content-security-policy"]
    assert "sandbox allow-scripts" in policy and "allow-same-origin" not in policy
    put(root, "deliverables/report/report.html", b"new unverified version")
    assert client.get("/files/deliverables/report/report.html").status_code == 409


def test_refresh_settings_and_policy(tmp_path: Path) -> None:
    app, root = make_app(tmp_path)
    client = client_of(app)
    put(root, "runs/added/CP-0.md", b"added")
    response = client.post("/api/refresh", content="{}", headers=POST_HEADERS)
    assert len(Catalogue.model_validate_json(response.content).real) == 2
    other = tmp_path / "other"
    put(other, "runs/other/CP-0.md", b"other")
    raw = json.dumps({"workspace": str(other)})
    response = client.post("/api/settings", content=raw, headers=POST_HEADERS)
    assert response.status_code == 200, response.text
    assert client.get("/files/runs/case-a/CP-0.md").status_code == 404
    reloaded = Application(app.loc, "", HOST)
    assert reloaded.config.workspace == str(other), "settings did not persist"
    app.locked = True
    assert client.post("/api/settings", content=raw, headers=POST_HEADERS).status_code == 403
    app.locked = False
    for body in ['{"workspace":"relative"}', '{"workspace":"/x","extra":1}', "{", "x" * 9000]:
        assert client.post("/api/settings", content=body, headers=POST_HEADERS).status_code == 400
    missing = json.dumps({"workspace": str(tmp_path / "missing")})
    assert client.post("/api/settings", content=missing, headers=POST_HEADERS).status_code == 400


def test_policy_precedence_and_no_silent_fallback(tmp_path: Path) -> None:
    loc = Locations(
        state=tmp_path / "state",
        documents=tmp_path / "documents",
        policy=tmp_path / "policy" / "settings.json",
    )
    save_json(loc.state / "settings.json", Config(workspace=str(tmp_path)))
    managed = tmp_path / "managed"
    managed.mkdir()
    assert loc.policy is not None
    save_json(loc.policy, Config(workspace=str(managed)))
    config, locked = load_config(loc)
    assert locked and config.workspace == str(managed), "policy lost precedence"
    with pytest.raises(ValueError, match="disabled by IT"):
        Application(loc, str(tmp_path), HOST)
    loc.policy.write_text("{")
    with pytest.raises(ValueError, match="invalid configuration"):
        load_config(loc)
    save_json(loc.policy, {"workspace": "relative"})
    with pytest.raises(ValueError, match="absolute"):
        load_config(loc)


def test_concurrent_refresh_and_readers(tmp_path: Path) -> None:
    app, _ = make_app(tmp_path)
    client = client_of(app)
    codes: list[int] = []

    def read() -> None:
        codes.append(client.get("/api/catalogue").status_code)

    def refresh() -> None:
        codes.append(client.post("/api/refresh", content="{}", headers=POST_HEADERS).status_code)

    threads = [threading.Thread(target=target) for _ in range(20) for target in (read, refresh)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert codes == [200] * 40


def test_pinned_link_cannot_silently_open_later_version(tmp_path: Path) -> None:
    app, root = make_app(tmp_path)
    client = client_of(app)
    old = app.catalogue.real[0].artifacts[0].href
    # Replace and publish a new, internally valid bundle in the same directory.
    content = b"<!doctype html><p>Later revision</p>"
    put(root, "deliverables/report/report.html", content)
    record = json.loads((root / "deliverables/report/delivery.json").read_bytes())
    record["files"]["report.html"] = digest(content)
    put_json(root, "deliverables/report/delivery.json", record)
    client.post("/api/refresh", content="{}", headers=POST_HEADERS)
    assert client.get(old).status_code == 409, "old screen opened new report bytes"


def test_report_range_requests(tmp_path: Path) -> None:
    app, _ = make_app(tmp_path)
    client = client_of(app)
    name = "/files/deliverables/report/report.html"
    response = client.get(name, headers={"Range": "bytes=0-14"})
    assert (response.status_code, response.content) == (206, b"<!doctype html>")
    assert response.headers["content-range"] == f"bytes 0-14/{len(REPORT)}"
    assert client.get(name, headers={"Range": "bytes=-3"}).content == REPORT[-3:]
    assert client.get(name, headers={"Range": "bytes=5-"}).content == REPORT[5:]
    for bad in ["bytes=999-", "bytes=5-2"]:
        assert client.get(name, headers={"Range": bad}).status_code == 416, bad
    # RFC 9110 section 14.2: a Range the server does not understand is ignored, not refused.
    for ignored in ["bytes=", "chunks=0-1", "bytes=0-1,4-5"]:
        response = client.get(name, headers={"Range": ignored})
        assert (response.status_code, response.content) == (200, REPORT), ignored
    assert client.get(name).headers["accept-ranges"] == "bytes"


def test_response_uses_the_bytes_that_were_verified(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    app, root = make_app(tmp_path)
    client = client_of(app)
    file = root / "deliverables/report/report.html"
    original = file.read_bytes()
    real = server_module.read_file

    def read_then_change(workspace: Path, name: str) -> bytes:
        raw = real(workspace, name)
        file.write_bytes(b"X" * len(original))
        return raw

    monkeypatch.setattr(server_module, "read_file", read_then_change)
    response = client.get("/files/deliverables/report/report.html")
    assert (response.status_code, response.content) == (200, original)


def test_embedded_presentation_preserves_retained_and_exported_report_bytes(
    tmp_path: Path,
) -> None:
    app, root = make_app(tmp_path)
    client = client_of(app)
    name = "/files/deliverables/report/report.html"
    original = (root / "deliverables/report/report.html").read_bytes()
    symbol = base64.b64encode((WEB / "brand/symbol.svg").read_bytes()).decode()
    for query in ["?embedded=1", "?download=1"]:
        response = client.get(name + query)
        assert response.status_code == 200, response.text
        body = response.content
        if query == "?embedded=1":
            start = body.find(b"<style data-library-presentation>")
            end = body.rfind(b"</script>") + len(b"</script>")
            assert 0 <= start < end, "embedded presentation is missing"
            assert f"data:image/svg+xml;base64,{symbol}".encode() in body
            assert body[:start] + body[end:] == original
        else:
            assert body == original, "HTML export changed original bytes"
        policy = response.headers["content-security-policy"]
        assert "allow-same-origin" not in policy and "connect-src 'none'" in policy
        if query == "?embedded=1":
            assert f"frame-ancestors {ORIGIN}" in policy
        else:
            assert response.headers["content-disposition"].startswith("attachment;")
    assert (root / "deliverables/report/report.html").read_bytes() == original
    assert client.get(name + "?embedded=1&download=1").content == original
    assert "frame-ancestors 'none'" in client.get(name).headers["content-security-policy"]
    assert "frame-src 'self'" in client.get("/").headers["content-security-policy"]
    sandboxed = client.get(name + "?embedded=1", headers={"Origin": "null"})
    assert sandboxed.status_code == 403, "sandboxed child can access the application origin"


@pytest.mark.parametrize(
    "original", [b"<p>Original fragment</p>", b"<HTML><BODY>Original report</BODY></HTML>"]
)
def test_report_presentation_keeps_fragments_and_original_storage(
    tmp_path: Path, original: bytes
) -> None:
    app, _ = make_app(tmp_path)
    result = app.report_presentation(original)
    assert b"data-library-presentation" in result
    if b"</BODY>" in original:
        assert result.endswith(b"</BODY></HTML>"), "insertion lost the original document ending"
    else:
        assert result.startswith(original)


def test_assets_are_only_the_packaged_front_end(tmp_path: Path) -> None:
    app, _ = make_app(tmp_path)
    client = client_of(app)
    assert (
        client.get("/context-form.html")
        .headers["content-security-policy"]
        .endswith(f"frame-ancestors {ORIGIN}")
    )
    assert client.get("/icons/plus.svg").headers["content-type"] == "image/svg+xml; charset=utf-8"
    for name in ["/engine/store.py", "/fonts", "/brand/x/y.svg", "/api", "/designs/build.py"]:
        assert client.get(name).status_code == 404, name
    assert client.put("/api/catalogue").status_code == 405


def test_quit_stops_the_server_once_no_run_is_active(tmp_path: Path) -> None:
    app, _ = make_app(tmp_path)
    client = client_of(app)
    stopped = threading.Event()
    app.stop = stopped.set
    app.active_jobs.add("web-" + "a" * 32)
    assert client.post("/api/quit", content="{}", headers=POST_HEADERS).status_code == 409
    app.active_jobs.clear()
    response = client.post("/api/quit", content="{}", headers=POST_HEADERS)
    assert response.json() == {"stopped": True} and stopped.wait(2)


def test_index_cache_failure_is_a_notice_not_a_failure(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    fixture(root)
    loc = locations(tmp_path)
    loc.state.mkdir(parents=True)
    (loc.state / "index.json").mkdir()
    app = Application(loc, str(root), HOST)
    assert app.catalogue.issues[-1].startswith("Search index could not be saved")
