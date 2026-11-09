"""The HTTP boundary over the fixture workspace: origin checks, pinned files and settings."""

from __future__ import annotations

import base64
import json
import os
import stat
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from issuer_library_support import (
    HOST,
    ORIGIN,
    POST_HEADERS,
    REPORT,
    call,
    client_of,
    fake_engine,
    fixture,
    locations,
    make_app,
    put,
    put_json,
)

import issuer_library.server as server_module
from issuer_library.jobs import Engine
from issuer_library.launch import cookie_name
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
    for bad in ["bytes=999-", "bytes=5-2", "bytes=", "chunks=0-1"]:
        assert client.get(name, headers={"Range": bad}).status_code == 416, bad
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


COUNTING_STORE = """import os, time
def workspace_store(root, catalogue):
    with open({counter!r}, 'a') as stream:
        stream.write('run\\n')
    time.sleep(.2)
    if os.path.exists({fail!r}):
        raise RuntimeError('store failed')
    return {{'ok': True}}
"""
HELD_STORE = """import os, time
def workspace_store(root, catalogue):
    with open({starts!r}, 'a') as stream:
        stream.write('x')
    n = os.path.getsize({starts!r})
    while not os.path.exists({release!r}):
        time.sleep(.02)
    return {{'run': n}}
"""


def counting_engine(tmp_path: Path) -> tuple[Engine, Path, Path]:
    """The fake engine whose store appends one line to a counter per run and fails while the
    fail file exists."""
    engine = fake_engine(tmp_path)
    counter, fail = tmp_path / "store-runs.txt", tmp_path / "fail"
    (engine.root / "store.py").write_text(
        COUNTING_STORE.format(counter=str(counter), fail=str(fail))
    )
    return engine, counter, fail


def store_runs(counter: Path) -> int:
    return counter.read_text().count("run\n") if counter.exists() else 0


def test_workspace_store_runs_once_until_a_file_changes(tmp_path: Path) -> None:
    app, root = make_app(tmp_path)
    app.engine, counter, _ = counting_engine(tmp_path)
    client = client_of(app)
    for _ in range(2):
        assert call(client, "GET", "/api/workspace").status_code == 200
    assert store_runs(counter) == 1, "two reads ran the store more than once"
    put(root, "runs/case-a/extra-note.md", b"a longer file than before")
    call(client, "GET", "/api/workspace")
    assert store_runs(counter) == 2, "after a file change the store did not rerun once"


def test_catalogue_rebuild_alone_does_not_rerun_the_store(tmp_path: Path) -> None:
    app, _ = make_app(tmp_path)
    app.engine, counter, _ = counting_engine(tmp_path)
    client = client_of(app)
    call(client, "GET", "/api/workspace")
    with app.lock:
        app.catalogue.built_at = "2001-01-01T00:00:00Z"
    call(client, "GET", "/api/workspace")
    app.refresh()
    call(client, "GET", "/api/workspace")
    assert store_runs(counter) == 1, "a rebuild that changed only built_at ran the store again"


def test_concurrent_workspace_reads_share_one_store(tmp_path: Path) -> None:
    app, _ = make_app(tmp_path)
    app.engine, counter, _ = counting_engine(tmp_path)

    def read() -> int:
        return int(call(client_of(app), "GET", "/api/workspace").status_code)

    with ThreadPoolExecutor(max_workers=8) as pool:
        codes = [future.result() for future in [pool.submit(read) for _ in range(8)]]
    assert codes == [200] * 8
    assert store_runs(counter) == 1, "8 parallel reads ran the store more than once"


def test_refresh_clears_the_workspace_cache(tmp_path: Path) -> None:
    app, _ = make_app(tmp_path)
    app.engine, counter, _ = counting_engine(tmp_path)
    client = client_of(app)
    call(client, "GET", "/api/workspace")
    call(client, "POST", "/api/refresh", "{}")
    call(client, "GET", "/api/workspace")
    assert store_runs(counter) == 2, "a read after /api/refresh did not rerun the store"


def test_a_failed_store_is_not_cached(tmp_path: Path) -> None:
    app, _ = make_app(tmp_path)
    app.engine, counter, fail = counting_engine(tmp_path)
    client = client_of(app)
    fail.write_bytes(b"")
    assert call(client, "GET", "/api/workspace").status_code == 503
    fail.unlink()
    assert call(client, "GET", "/api/workspace").status_code == 200
    call(client, "GET", "/api/workspace")
    assert store_runs(counter) == 2, "expected failure, then one success, then a hit"


def test_settings_clear_the_workspace_cache_even_when_refused(tmp_path: Path) -> None:
    app, _ = make_app(tmp_path)
    app.engine, counter, _ = counting_engine(tmp_path)
    client = client_of(app)
    call(client, "GET", "/api/workspace")
    assert call(client, "POST", "/api/settings", "{").status_code == 400
    call(client, "GET", "/api/workspace")
    assert store_runs(counter) == 2


def test_refresh_does_not_wait_for_a_running_store_and_its_body_is_not_cached(
    tmp_path: Path,
) -> None:
    app, _ = make_app(tmp_path)
    engine = fake_engine(tmp_path)
    release, starts = engine.root / "release", engine.root / "starts"
    (engine.root / "store.py").write_text(
        HELD_STORE.format(starts=str(starts), release=str(release))
    )
    app.engine = engine
    client = client_of(app)
    with ThreadPoolExecutor(max_workers=2) as pool:
        try:
            first = pool.submit(call, client, "GET", "/api/workspace")
            deadline = time.monotonic() + 5
            while not (starts.exists() and starts.stat().st_size == 1):
                assert time.monotonic() < deadline, "the store run never started"
                time.sleep(0.01)
            refreshed = pool.submit(call, client_of(app), "POST", "/api/refresh", "{}")
            response = refreshed.result(timeout=3)  # TimeoutError: refresh waited for the store
            assert response.status_code == 200, response.text
        finally:
            release.write_bytes(b"")  # a failure must end the held store run, not hang the pool
        body = first.result(timeout=10)
    assert body.status_code == 200 and body.text.strip() == '{"run": 1}'
    follow = call(client, "GET", "/api/workspace")
    assert follow.status_code == 200 and follow.text.strip() == '{"run": 2}', (
        "the pre-refresh body was cached: " + follow.text
    )


class Entry:
    """A DirEntry stand-in for the stat, link and junction answers a platform can give."""

    def __init__(self, entry: os.DirEntry[str], *, junction: bool = False, gone: bool = False):
        self.name, self.path = entry.name, entry.path
        self.junction, self.gone = junction, gone

    def stat(self, *, follow_symlinks: bool = True) -> os.stat_result:
        if self.gone:
            raise FileNotFoundError(2, "No such file or directory", self.path)
        return os.stat(self.path)

    def is_symlink(self) -> bool:
        return False

    def is_junction(self) -> bool:
        return self.junction


def listing_with(monkeypatch: pytest.MonkeyPatch, **kinds: bool) -> list[str]:
    """Wrap os.scandir so entries named in kinds (name -> junction?) or ending .tmp (gone) are
    presented as stand-ins; returns the directories listed."""
    real, listed = os.scandir, []

    class Listing:
        def __init__(self, path: str | os.PathLike[str]) -> None:
            listed.append(str(path))
            self.inner = real(path)

        def __enter__(self) -> list[Entry | os.DirEntry[str]]:
            entries = self.inner.__enter__()
            return [
                Entry(e, junction=True)
                if e.name in kinds
                else Entry(e, gone=True)
                if e.name.endswith(".tmp")
                else e
                for e in entries
            ]

        def __exit__(self, *exc: object) -> None:
            self.inner.__exit__(*exc)

    monkeypatch.setattr(os, "scandir", Listing)
    return listed


def test_the_fingerprint_walk_does_not_descend_a_directory_junction(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    put(tmp_path, "runs/case-a/CP-0.md", b"x")
    (tmp_path / "runs/case-a/junction").symlink_to("..", target_is_directory=True)
    assert stat.S_ISDIR(os.stat(tmp_path / "runs/case-a/junction").st_mode)
    listed = listing_with(monkeypatch, junction=True)
    lines = server_module.tree_files(tmp_path, "runs")
    assert len(listed) == 2, listed  # runs and runs/case-a only
    assert [line.split("\t")[0] for line in lines] == ["runs/case-a/CP-0.md"]


def test_a_regular_file_named_like_a_tree_is_described(tmp_path: Path) -> None:
    put(tmp_path, "deliverables", b"1234")
    [line] = server_module.tree_files(tmp_path, "deliverables")
    assert line.startswith("deliverables\t4\t")


def test_an_entry_that_vanishes_during_the_walk_is_recorded_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    put(tmp_path, "runs/case-a/CP-0.md", b"x")
    put(tmp_path, "runs/case-a/status.json.tmp", b"{}")
    listing_with(monkeypatch)
    lines = server_module.tree_files(tmp_path, "runs")
    assert "runs/case-a/status.json.tmp\tmissing" in lines
    assert any(line.startswith("runs/case-a/CP-0.md\t1\t") for line in lines)


def test_report_presentation_splices_before_the_final_body_tag_in_the_original_bytes(
    tmp_path: Path,
) -> None:
    app, _ = make_app(tmp_path)
    tail = "<script>render()</script>\n<!-- font licence -->\n</BODY></html>"
    invalid = b"<html><body><p>" + b"\xff" * 40 + ("</p>" + tail).encode()
    turkish = "Türkiye İş Bankası " * 6
    cases = {
        "ascii": ("<html><body><p>Issuer</p>" + tail).encode(),
        "turkish I": ("<html><body><p>" + turkish + "</p>" + tail).encode(),
        "kelvin": ("<html><body><p>300 K</p>" + tail).encode(),
        "U+023A": ("<html><body><p>" + "Ⱥ" * 40 + "</p>" + tail).encode(),
        "invalid utf8": invalid,
        "mixed case": b"<html><body><p>x</p></BoDy></html>",
        "early body": "</body><p>İİİİİ</p>".encode(),
        "no body": "<p>İİ ".encode() + b"\xff\xff plain fragment</p>",
    }
    for label, original in cases.items():
        out = app.report_presentation(original)
        start = out.find(b"<style data-library-presentation>")
        end = out.rfind(b"</script>") + len(b"</script>")
        want = len(original)
        for i in range(len(original) - 7, -1, -1):
            if original[i : i + 7].decode("latin-1").lower() == "</body>" and original[i] == 0x3C:
                want = i
                break
        assert start == want, f"{label}: block at {start}, want {want}"
        assert out[:start] == original[:want], label
        assert out[end:] == original[want:], label


BODY_CLOSE_CASES = [
    ("", -1),
    ("</body", -1),
    ("</body>", 0),
    ("x</BODY>", 1),
    ("<p>İ</bOdY></html>", 5),
    ("</body ></html>", -1),
    ("</body\n></html>", -1),
    ("<</body>>", 1),
    ("</body></body>", 7),
    ("\xff\xff\xff</body>\xff", 3),
    ("</bödy></html>", -1),
    ("</Kody></html>", -1),
    ("<body>x</bodyx></html>", -1),
    ("<body>x</bod></html>", -1),
]


@pytest.mark.parametrize(("html", "expected"), BODY_CLOSE_CASES)
def test_review_last_body_close_boundaries(tmp_path: Path, html: str, expected: int) -> None:
    # Go cases are Go strings: "\xff" there is one raw byte, and the other runes are UTF-8.
    raw = html.encode("latin-1") if "\xff" in html else html.encode()
    want = len(raw) if expected < 0 else expected
    assert server_module.last_body_close(raw) == want
    app, _ = make_app(tmp_path)
    out = app.report_presentation(raw)
    start = out.find(b"<style data-library-presentation>")
    block = len(out) - len(raw)
    assert start == want
    assert out[:start] + out[start + block :] == raw


def test_review_last_body_close_matches_an_ascii_lowered_oracle() -> None:
    def oracle(html: bytes) -> int:
        low = bytes(c + 32 if 65 <= c <= 90 else c for c in html)
        found = low.rfind(b"</body>")
        return found if found >= 0 else len(html)

    alphabet = ["<", "/", "b", "B", "o", "O", "d", "D", "y", "Y", ">", " ", "</body>", "</BODY>"]
    alphabet += ["</bOdY", "İ", "K", "Ⱥ", "\xff", "\xc4"]
    pieces = [
        piece.encode() if piece not in ("\xff", "\xc4") else piece.encode("latin-1")
        for piece in alphabet
    ]
    state = 1
    mask = (1 << 64) - 1

    def following(n: int) -> int:
        nonlocal state
        state ^= (state << 13) & mask
        state ^= state >> 7
        state ^= (state << 17) & mask
        return state % n

    for _ in range(50000):
        html = b"".join(pieces[following(len(pieces))] for _ in range(following(12)))
        assert server_module.last_body_close(html) == oracle(html), html


def test_review_embedded_glyph_report_over_http(tmp_path: Path) -> None:
    app, root = make_app(tmp_path)
    client = client_of(app)
    report = (
        ("<!doctype html><html><body><p>" + "Ⱥ" * 40).encode()
        + b"\xff\xfe "
        + "İstanbul</p><script>render()</script>\n<!-- font licence -->\n</body></html>".encode()
    )
    view = (
        b'{"run":{"run_id":"case-a","issuer_id":"EX","issuer_name":"Example Industries",'
        b'"as_of":"2024-12-31"}}'
    )
    put(root, "deliverables/glyph/report.html", report)
    put(root, "deliverables/glyph/view.json", view)
    put_json(
        root,
        "deliverables/glyph/delivery.json",
        {"files": {"report.html": digest(report), "view.json": digest(view)}},
    )
    assert call(client, "POST", "/api/refresh", "{}").status_code == 200
    href = ""
    for run in app.catalogue.real:
        for artifact in run.artifacts:
            if artifact.folder == "deliverables/glyph" and artifact.available:
                href = artifact.href
    assert href, f"glyph delivery not available: {app.catalogue.issues}"
    shown = client.get(href + "&embedded=1")
    body = shown.content
    at = body.find(b"<style data-library-presentation>")
    assert shown.status_code == 200 and at >= 0, (shown.status_code, at)
    assert body.endswith(b"</script></body></html>"), body[-40:]
    assert body.startswith(report[: report.rfind(b"</body>")])
    csp = shown.headers["content-security-policy"]
    assert csp.startswith("sandbox allow-scripts allow-downloads;"), csp
    assert "connect-src 'none'" in csp and csp.endswith(f"frame-ancestors {ORIGIN}"), csp
    saved = client.get(href + "&download=1")
    assert saved.content == report
    assert saved.headers["content-security-policy"].endswith("frame-ancestors 'none'")


@pytest.mark.parametrize(
    ("label", "content", "ok"),
    [
        ("bom", b"\xef\xbb\xbf{W}", True),
        ("plain", b"{W}", True),
        ("bom-only", b"\xef\xbb\xbf", False),
        ("double-bom", b"\xef\xbb\xbf\xef\xbb\xbf{W}", False),
        ("bom-then-garbage", b"\xef\xbb\xbf{", False),
        ("bom-relative", b'\xef\xbb\xbf{"workspace": "relative"}', False),
        ("utf16-bom", b"\xff\xfe{W}", False),
    ],
)
@pytest.mark.parametrize("managed", [True, False])
def test_settings_accept_one_leading_byte_order_mark(
    tmp_path: Path, label: str, content: bytes, ok: bool, managed: bool
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    valid = json.dumps({"workspace": str(workspace)}).encode()
    loc = Locations(
        state=tmp_path / "state", documents=tmp_path / "documents", policy=tmp_path / "policy.json"
    )
    loc.state.mkdir()
    (loc.policy if managed else loc.state / "settings.json").write_bytes(
        content.replace(b"{W}", valid)
    )
    if not ok:
        with pytest.raises((ValueError, OSError)):
            load_config(loc)
        return
    config, locked = load_config(loc)
    assert (config.workspace, locked) == (str(workspace), managed), label


def stalled_request(app: Application, method: str, endpoint: str):
    """Run one request through the ASGI app in its own thread; its send blocks on the first body."""
    import asyncio

    path, _, query = endpoint.partition("?")
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "query_string": query.encode(),
        "root_path": "",
        "server": ("127.0.0.1", 54321),
        "client": ("127.0.0.1", 50000),
        "headers": [
            (b"host", HOST.encode()),
            (b"cookie", f"{cookie_name(HOST)}={app.session.cookie}".encode()),
            (b"x-issuer-library", b"1"),
            (b"content-type", b"application/json"),
        ],
    }
    writing, release, served = threading.Event(), threading.Event(), threading.Event()
    sent = [False]

    async def receive() -> dict[str, object]:
        if sent[0]:  # a client that stopped reading stays connected: wait for the release
            await asyncio.get_running_loop().run_in_executor(None, release.wait)
            return {"type": "http.disconnect"}
        sent[0] = True
        return {"type": "http.request", "body": b"{}", "more_body": False}

    async def send(message: dict[str, object]) -> None:
        if message["type"] == "http.response.body":
            writing.set()
            await asyncio.get_running_loop().run_in_executor(None, release.wait)

    def run() -> None:
        try:
            asyncio.run(app.asgi(scope, receive, send))  # type: ignore[arg-type]  # ASGI send is MutableMapping[str, Any] in the stub
        finally:
            served.set()

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    return writing, release, served, thread


def test_stalled_client_does_not_hold_the_catalogue_lock(tmp_path: Path) -> None:
    app, root = make_app(tmp_path)
    client = client_of(app)
    put(root, "runs/case-a/big.txt", b"a" * (1 << 20))
    call(client, "POST", "/api/refresh", "{}")
    pinned = app.catalogue.real[0].artifacts[0].href
    for method, endpoint in [
        ("GET", "/files/runs/case-a/big.txt"),
        ("GET", pinned + "&embedded=1"),
        ("GET", "/api/catalogue"),
        ("POST", "/api/refresh"),
    ]:
        writing, release, served, thread = stalled_request(app, method, endpoint)
        try:
            for _ in range(200):
                if writing.wait(0.05) or served.is_set():
                    break
            assert writing.is_set(), f"{method} {endpoint} finished without writing"
            got = app.lock.acquire(timeout=2)
            assert got, (
                f"{method} {endpoint}: the catalogue lock is held while the response is written"
            )
            app.lock.release()
        finally:
            release.set()
            thread.join(10)
        assert not thread.is_alive(), f"{method} {endpoint}: the request is still running"


def block_discovery(
    monkeypatch: pytest.MonkeyPatch, workspace: Path
) -> tuple[threading.Event, threading.Event]:
    """Make discovery of workspace wait until release is set; entered is set when it starts.
    Other folders are discovered as usual, and an earlier block stays active."""
    entered, release = threading.Event(), threading.Event()
    saved = server_module.discover
    wanted = os.path.normpath(str(workspace))

    def hold(folder: str, seeds: Catalogue) -> Catalogue:
        if os.path.normpath(folder) == wanted:
            entered.set()
            assert release.wait(10), "the blocked discovery was never released"
        return saved(folder, seeds)

    monkeypatch.setattr(server_module, "discover", hold)
    return entered, release


def lock_within(app: Application, what: str) -> None:
    got = app.lock.acquire(timeout=2)
    assert got, f"{what} holds the catalogue lock"
    app.lock.release()


def test_refresh_discovers_without_holding_the_catalogue_lock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    app, root = make_app(tmp_path)
    put(root, "runs/added/CP-0.md", b"added")
    entered, release = block_discovery(monkeypatch, root)
    with ThreadPoolExecutor(max_workers=1) as pool:
        try:
            done = pool.submit(call, client_of(app), "POST", "/api/refresh", "{}")
            assert entered.wait(10), "the refresh never started discovering"
            lock_within(app, "a refresh in discovery")
            client = client_of(app)
            during = call(client, "GET", "/api/catalogue")
            assert during.status_code == 200, during.text
            assert len(Catalogue.model_validate_json(during.content).real) == 1, during.text
            served = call(client, "GET", "/files/runs/case-a/CP-0.md")
            assert served.status_code == 200, served.status_code
        finally:
            release.set()
        response = done.result(timeout=10)
    assert response.status_code == 200, response.text
    assert len(Catalogue.model_validate_json(response.content).real) == 2, response.text


def test_workspace_switch_during_a_refresh_keeps_the_new_workspace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    app, root = make_app(tmp_path)
    other = tmp_path / "other"
    put(other, "runs/other/CP-0.md", b"other")
    new_entered, new_release = block_discovery(monkeypatch, other)
    old_entered, old_release = block_discovery(monkeypatch, root)
    with ThreadPoolExecutor(max_workers=2) as pool:
        try:
            refreshed = pool.submit(call, client_of(app), "POST", "/api/refresh", "{}")
            assert old_entered.wait(10), "the refresh never started discovering"
            body = json.dumps({"workspace": str(other)})
            switched = pool.submit(call, client_of(app), "POST", "/api/settings", body)
            old_release.set()
            refreshed.result(timeout=10)
            assert new_entered.wait(10), "the switch never started discovering"
            lock_within(app, "a workspace switch in discovery")
        finally:
            old_release.set()
            new_release.set()
        response = switched.result(timeout=10)
    assert response.status_code == 200, response.text
    with app.lock:
        workspace, catalogue_workspace = app.config.workspace, app.catalogue.workspace
    assert workspace == str(other) and catalogue_workspace == str(other), (
        f"config {workspace}, catalogue {catalogue_workspace}; want {other}"
    )
    gone = call(client_of(app), "GET", "/files/runs/case-a/CP-0.md")
    assert gone.status_code == 404, f"old workspace file still admitted: {gone.status_code}"
