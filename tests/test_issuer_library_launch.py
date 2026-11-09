"""The launch ticket, session cookie and same-site gate, ported case for case from the Go tests.

Expected values come from final-workflow's launch_test.go and launch_review_test.go at the
pinned sha dd3dfa18 (answer key in .superpowers/sdd/2026-11-08-python-build/answer-key/), never
from running this code. Requests that need exact paths, methods or header lines go straight to
the ASGI app, because httpx collapses ".." segments and rewrites some requests.
"""

from __future__ import annotations

import ast
import asyncio
import http.client
import json
import logging
import os
import re
import socket
import stat
import subprocess
import sys
import threading
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any, NamedTuple
from urllib.parse import unquote

import pytest
import uvicorn
from issuer_library_support import ORIGIN, POST_HEADERS, make_app
from starlette.types import Message, Scope

import issuer_library.server as server_module
from issuer_library import __main__ as launcher
from issuer_library import launch
from issuer_library.jobs import Engine
from issuer_library.model import digest
from issuer_library.server import Application
from issuer_library.settings import Config

LAUNCHER_ONLY = (
    "Open Credit OS from its launcher. This page is not part of the library's current "
    "session. If the library is already running, start it again: a library with no run or "
    "review in progress quits and the new launch opens a fresh window."
)
LOCAL_ONLY = "Local app requests only\n"
SRC = Path(launch.__file__).resolve().parents[1]
HEX64 = re.compile(r"^[0-9a-f]{64}$")


class Reply(NamedTuple):
    status: int
    headers: list[tuple[str, str]]
    body: bytes

    def values(self, name: str) -> list[str]:
        return [value for key, value in self.headers if key == name.lower()]

    def header(self, name: str) -> str:
        found = self.values(name)
        return found[0] if found else ""

    @property
    def text(self) -> str:
        return self.body.decode("utf-8", "replace")


def drive(
    app: Application,
    method: str,
    target: str,
    *,
    headers: Sequence[tuple[str, str | bytes]] = (),
    body: bytes = b"",
) -> Reply:
    """One request straight into the ASGI app; target is the path and optional query, unmodified."""
    path, _, query = target.partition("?")
    raw: list[tuple[bytes, bytes]] = []
    if not any(key.lower() == "host" for key, _ in headers):
        raw.append((b"host", app.host.encode("latin-1")))
    for key, value in headers:
        raw.append(
            (
                key.lower().encode("latin-1"),
                value.encode("latin-1") if isinstance(value, str) else value,
            )
        )
    scope: Scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": path,
        "raw_path": path.encode("latin-1"),
        "query_string": query.encode("latin-1"),
        "root_path": "",
        "headers": raw,
        "client": ("127.0.0.1", 50000),
        "server": ("127.0.0.1", 54321),
    }
    sent: list[Message] = []

    async def receive() -> Message:
        return {"type": "http.request", "body": body, "more_body": False}

    async def send(message: Message) -> None:
        sent.append(message)

    asyncio.run(app.asgi(scope, receive, send))
    start = next(message for message in sent if message["type"] == "http.response.start")
    answer = [
        (key.decode("latin-1").lower(), value.decode("latin-1")) for key, value in start["headers"]
    ]
    payload = b"".join(m.get("body", b"") for m in sent if m["type"] == "http.response.body")
    return Reply(start["status"], answer, payload)


def launch_request(app: Application, method: str, query: str) -> Reply:
    """The launch path with the given raw query, as the browser does (no cookie, no Origin)."""
    return drive(app, method, "/launch" + query)


def cookie_of(app: Application) -> tuple[str, str]:
    return ("Cookie", f"{launch.cookie_name(app.host)}={app.session.cookie}")


def call(app: Application, method: str, endpoint: str, body: str = "") -> Reply:
    """A request as the app's own page sends it: session cookie and, for a POST, its headers."""
    headers = [cookie_of(app)]
    if method == "POST":
        headers += list(POST_HEADERS.items())
    return drive(app, method, endpoint, headers=headers, body=body.encode())


def build_app(tmp_path: Path, name: str = "app") -> Application:
    return make_app(tmp_path / name)[0]


# C03: the ticket is exchanged once for the session cookie, and the redirect drops it. Expected by
# hand: 303 to "/" with exactly `issuer-library-54321=<session>; Path=/; HttpOnly;
# SameSite=Strict` (no Secure on plain loopback HTTP, no expiry); the same ticket then gets the
# 403 page and no cookie, and the cookie opens /api/catalogue.
def test_launch_ticket_is_exchanged_once_and_the_redirect_drops_it(tmp_path: Path) -> None:
    """Expected by hand: 303 to "/" with exactly
    `issuer-library-54321=<session>; Path=/; HttpOnly; SameSite=Strict` (no Secure on plain
    loopback HTTP, no expiry); the same ticket then gets the 403 page and no cookie, and the
    cookie opens /api/catalogue."""
    app = build_app(tmp_path)
    ticket, session = app.session.ticket(), app.session.cookie
    assert launch.LAUNCHER_ONLY == LAUNCHER_ONLY
    assert HEX64.match(ticket) and HEX64.match(session) and ticket != session
    assert launch.launch_link(app.host, ticket) == "http://127.0.0.1:54321/launch?ticket=" + ticket
    first = launch_request(app, "GET", "?ticket=" + ticket)
    assert first.status == 303 and first.header("Location") == "/"
    assert first.values("Set-Cookie") == [
        f"issuer-library-54321={session}; Path=/; HttpOnly; SameSite=Strict"
    ]
    assert ticket not in first.text and session not in first.text
    again = launch_request(app, "GET", "?ticket=" + ticket)
    assert again.status == 403 and again.header("Set-Cookie") == ""
    assert again.text == LAUNCHER_ONLY + "\n"
    exchanged = first.header("Set-Cookie").split(";")[0]
    assert drive(app, "GET", "/api/catalogue", headers=[("Cookie", exchanged)]).status == 200


def test_tampered_tickets_are_refused_without_spending_the_real_one(tmp_path: Path) -> None:
    """A tampered or misplaced ticket gets the 403 page and no cookie, and does not spend the
    real one, which still works afterwards. A HEAD or POST to the launch path neither exchanges
    nor spends."""
    app = build_app(tmp_path)
    ticket = app.session.ticket()
    flip = "1" if ticket[63] == "0" else "0"
    for query in [
        "",
        "?ticket=",
        "?ticket=" + ticket[:63],
        "?ticket=" + ticket + "0",
        "?ticket=" + ticket[:63] + flip,
        "?ticket=" + ticket.upper(),
        "?ticket=" + app.session.cookie,
        "?Ticket=" + ticket,
        "?t=" + ticket,
        "?ticket=x&ticket=" + ticket,  # only the first value counts
    ]:
        w = launch_request(app, "GET", query)
        assert w.status == 403 and w.header("Set-Cookie") == "", query
    for method in ["HEAD", "POST", "PUT"]:
        w = launch_request(app, method, "?ticket=" + ticket)
        assert w.status == 405 and w.header("Set-Cookie") == "", method
    for path in ["/launch/", "/launch/x", "/Launch", "/api/catalogue", "/"]:
        w = drive(app, "GET", path + "?ticket=" + ticket)
        assert w.status == 403 and w.header("Set-Cookie") == "", path
    assert launch_request(app, "GET", "?ticket=" + ticket).status == 303


def test_every_app_request_needs_the_session_cookie(tmp_path: Path) -> None:
    """Every request that reads the workspace, changes it, starts or spends needs the cookie.
    Expected by hand: without it 403 with the launcher text and no side effect (workspace, quit,
    intake unchanged); with it each endpoint answers as before (for the bodies used here: 200,
    the unknown run 404, the missing runtime 503, the malformed start and review 400). /health
    alone answers without it."""
    app, root = make_app(tmp_path)
    app.engine = Engine(root=tmp_path / "missing-engine", python=str(tmp_path / "missing-python"))
    quits: list[int] = []
    stopped = threading.Event()  # app.stop runs on its own thread

    def stop() -> None:
        quits.append(1)
        stopped.set()

    app.stop = stop
    other = tmp_path / "other-workspace"
    other.mkdir()
    settings = Config(workspace=str(other)).model_dump_json()
    cases: list[tuple[str, str, str, int]] = [
        ("GET", "/", "", 200),
        ("GET", "/index.html", "", 200),
        ("GET", "/screen.js", "", 200),
        ("GET", "/context-form.html", "", 200),
        ("GET", "/fonts/RedHatText-Regular.woff2", "", 200),
        ("GET", "/api/catalogue", "", 200),
        ("HEAD", "/api/catalogue", "", 200),
        ("GET", "/api/workspace", "", 503),
        ("GET", "/api/runs/list", "", 200),
        ("GET", "/api/runs/status?id=web-" + "a" * 32, "", 404),
        ("GET", "/files/deliverables/report/report.html", "", 200),
        ("HEAD", "/files/deliverables/report/report.html", "", 200),
        ("GET", "/files/runs/case-a/CP-0.md?download=1", "", 200),
        ("POST", "/api/refresh", "{}", 200),
        ("POST", "/api/runs/start", '{"id":"x"}', 400),
        ("POST", "/api/runs/review", "{}", 400),
        ("POST", "/api/quit", "{}", 200),
        ("POST", "/api/settings", settings, 200),
    ]
    for method, endpoint, body, expected in cases:
        headers = [*POST_HEADERS.items(), ("Origin", ORIGIN)]
        w = drive(app, method, endpoint, headers=headers, body=body.encode())
        assert w.status == 403 and w.text == LAUNCHER_ONLY + "\n", (method, endpoint, w.text)
        assert w.header("Content-Type").startswith("text/plain")
        assert app.config.workspace == str(root), f"{method} {endpoint} had an effect"
        assert not list((root / "intake").glob("*")), f"{method} {endpoint} created intake"
        got = call(app, method, endpoint, body)
        assert got.status == expected, (method, endpoint, got.status, got.text)
    assert stopped.wait(5)
    assert len(quits) == 1 and app.config.workspace == str(other)
    health = drive(app, "GET", "/health")
    value = json.loads(health.body)
    assert health.status == 200 and value == {
        "application": "finalworkflow-issuer-library/1",
        "instance": digest(str(app.loc.state).encode()),
    }


def test_secret_comparisons_are_constant_time() -> None:
    """The secret checks use secrets.compare_digest. Expected by reading launch.py: exchange and
    valid each call secrets.compare_digest on the secret, and no ==, !=, is, is not, in or not in
    compares anything naming a secret except against a literal constant."""
    source = Path(launch.__file__).read_text()
    parsed = ast.parse(source)
    secret = re.compile(r"cookie|ticket|session|value|query")
    forbidden = (ast.Eq, ast.NotEq, ast.Is, ast.IsNot, ast.In, ast.NotIn)
    want = {"exchange": "self._ticket", "valid": "self.cookie"}
    for function in ast.walk(parsed):
        if not isinstance(function, ast.FunctionDef) or function.name not in want:
            continue
        compared = False
        for node in ast.walk(function):
            text = ast.get_source_segment(source, node) or ""
            if isinstance(node, ast.Call):
                called = ast.get_source_segment(source, node.func)
                if called == "secrets.compare_digest" and want[function.name] in text:
                    compared = True
            elif isinstance(node, ast.Compare) and any(isinstance(o, forbidden) for o in node.ops):
                sides = [node.left, *node.comparators]
                literal = any(isinstance(side, ast.Constant) for side in sides)
                assert literal or not secret.search(text), f"{function.name}: {text}"
        assert compared, f"{function.name} does not compare {want[function.name]}"
        del want[function.name]
    assert not want, f"functions not found: {want}"


def test_requests_without_this_launchs_session_are_refused(tmp_path: Path) -> None:
    """Cookies of another port or instance, a wrong or truncated value, the ticket in a Referer,
    cookie or header, a cross-site or same-site request carrying the valid cookie, path tricks on
    /files and on the two exempt paths, and a shadowing cookie. Expected by hand: 403 for each,
    except the last (the valid cookie is among those sent), and the ticket is still unspent at
    the end."""
    app = build_app(tmp_path, "a")
    other = build_app(tmp_path, "b")
    other.host = "127.0.0.1:54322"
    ticket = app.session.ticket()
    session = app.session.cookie
    name = launch.cookie_name(app.host)
    other_name = launch.cookie_name(other.host)
    swap = "1" if session[63] == "0" else "0"

    def cookie(cookie_name: str, value: str) -> list[tuple[str, str]]:
        return [("Cookie", f"{cookie_name}={value}")]

    refused: dict[str, list[tuple[str, str]]] = {
        "other port's cookie": cookie(other_name, other.session.cookie),
        "this value, other port's name": cookie(other_name, session),
        "other instance's value": cookie(name, other.session.cookie),
        "name in another case": cookie(name.upper(), session),
        "one character changed": cookie(name, session[:63] + swap),
        "truncated value": cookie(name, session[:32]),
        "value plus a byte": cookie(name, session + "0"),
        "empty value": cookie(name, ""),
        "ticket as the cookie": cookie(name, ticket),
        "ticket in a Referer": [("Referer", f"http://{app.host}/launch?ticket={ticket}")],
        "ticket in the custom header": [("X-Issuer-Library", ticket)],
        "session in an Authorization": [("Authorization", "Bearer " + session)],
    }
    for label, headers in refused.items():
        assert drive(app, "GET", "/api/catalogue", headers=headers).status == 403, label
    valid = cookie(name, session)
    foreign: dict[str, list[tuple[str, str]]] = {
        "cross-site fetch": valid + [("Sec-Fetch-Site", "cross-site")],
        "same-site fetch": valid + [("Sec-Fetch-Site", "same-site")],
        "foreign Origin": valid + [("Origin", "http://attacker.invalid")],
        "another port's Origin": valid + [("Origin", "http://127.0.0.1:54322")],
        "sandboxed Origin": valid + [("Origin", "null")],
        "rebound Host": valid + [("Host", "attacker.invalid:54321")],
        "localhost Host": valid + [("Host", "localhost:54321")],
    }
    for label, headers in foreign.items():
        w = drive(app, "GET", "/api/catalogue", headers=headers)
        assert w.status == 403 and w.text == LOCAL_ONLY, f"{label} with the valid cookie"
    for path in [
        "/files/../secret",
        "/files/%2e%2e/%2e%2e/etc/passwd",
        "/files//etc/passwd",
        "/files/deliverables/report/../../AGENTS.md",
        "/files/runs/case-a/CP-0.md?sha256=x&download=1",
        "/FILES/runs/case-a/CP-0.md",
        "/health/../api/catalogue",
        "/health/",
        "/launch/../api/catalogue",
        "/api/runs/list",
        "//api/catalogue",
    ]:
        # httpx-free: the server sees the decoded path, as Go's URL.Path holds it.
        decoded, _, query = path.partition("?")
        w = drive(app, "GET", unquote(decoded) + ("?" + query if query else ""))
        assert w.status == 403 and w.text == LAUNCHER_ONLY + "\n", f"{path} without a cookie"
    shadowed = [
        ("Cookie", f"{name}=planted; {other_name}={other.session.cookie}; {name}={session}")
    ]
    assert drive(app, "GET", "/api/catalogue", headers=shadowed).status == 200
    for site in ["cross-site", "same-site"]:
        w = drive(app, "GET", "/launch?ticket=" + ticket, headers=[("Sec-Fetch-Site", site)])
        assert w.status == 403 and w.header("Set-Cookie") == "", f"{site} launch"
    assert launch_request(app, "GET", "?ticket=" + ticket).status == 303


def serve_over_loopback(app: Application) -> tuple[int, Callable[[], None]]:
    """Serve the app with uvicorn on 127.0.0.1:0; returns the port and a stop function."""
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(("127.0.0.1", 0))
    listener.listen(16)
    port = listener.getsockname()[1]
    app.host = f"127.0.0.1:{port}"
    server = uvicorn.Server(
        uvicorn.Config(app.asgi, log_config=None, access_log=False, lifespan="off")
    )
    thread = threading.Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
    thread.start()

    def stop() -> None:
        server.should_exit = True
        thread.join(10)
        listener.close()

    return port, stop


def test_head_requests_over_loopback(tmp_path: Path) -> None:
    """A HEAD is refused without the cookie and answers with no body with it; a HEAD to the launch
    path neither sets the cookie nor spends the ticket."""
    app = build_app(tmp_path)
    port, stop = serve_over_loopback(app)
    try:

        def request(
            method: str, path: str, signed: bool = False
        ) -> tuple[http.client.HTTPResponse, bytes]:
            connection = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
            headers = dict([cookie_of(app)]) if signed else {}
            connection.request(method, path, headers=headers)
            response = connection.getresponse()
            raw = response.read()
            connection.close()
            return response, raw

        assert request("HEAD", "/api/catalogue")[0].status == 403
        response, body = request("HEAD", "/api/catalogue", True)
        assert response.status == 200 and body == b""
        assert request("HEAD", "/files/runs/case-a/CP-0.md")[0].status == 403
        ticket = app.session.ticket()
        response, _ = request("HEAD", "/launch?ticket=" + ticket)
        assert response.status == 405 and response.getheader("Set-Cookie") is None
        response, _ = request("GET", "/launch?ticket=" + ticket)
        assert response.status == 303 and len(response.headers.get_all("Set-Cookie") or []) == 1
    finally:
        stop()


def test_the_secrets_appear_only_in_the_cookie(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """Neither secret is in a log line, a response body, a header other than Set-Cookie, or a
    state or workspace file, across a launch exchange and every endpoint, refused or not."""
    caplog.set_level(logging.DEBUG)
    app, root = make_app(tmp_path)
    ticket, session = app.session.ticket(), app.session.cookie
    responses = [
        launch_request(app, "GET", "?ticket=" + ticket),
        launch_request(app, "GET", "?ticket=" + ticket),
        launch_request(app, "HEAD", "?ticket=x"),
    ]
    for endpoint in [
        "/",
        "/boot.js",
        "/health",
        "/api/catalogue",
        "/api/workspace",
        "/api/runs/list",
        "/files/deliverables/report/report.html?embedded=1",
        "/files/missing",
        "/nothing",
    ]:
        responses.append(call(app, "GET", endpoint))
        responses.append(drive(app, "GET", endpoint))
    for endpoint in ["/api/refresh", "/api/runs/start", "/api/settings"]:
        responses.append(call(app, "POST", endpoint, "{}"))
    for i, w in enumerate(responses):
        assert ticket not in w.text and session not in w.text, f"response {i} body"
        for key, value in w.headers:
            if key != "set-cookie":
                assert ticket not in value and session not in value, f"response {i} header {key}"
    cookie = responses[0].header("Set-Cookie")
    assert session in cookie and ticket not in cookie
    assert ticket not in caplog.text and session not in caplog.text
    for folder in [app.loc.state, root]:
        for name in Path(folder).rglob("*"):
            if name.is_file():
                raw = name.read_bytes()
                assert ticket.encode() not in raw and session.encode() not in raw, str(name)


def free_port() -> int:
    """A loopback port that was free a moment ago."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def test_no_browser_launch_prints_the_link_on_standard_output_only(tmp_path: Path) -> None:
    """--no-browser: the launch link goes to standard output only, for whoever started the
    library; nothing is opened and library.log does not hold it."""
    state, port = tmp_path / "state", free_port()
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    opened = tmp_path / "opened.txt"
    opener = tmp_path / "opener.sh"
    opener.write_text(f'#!/bin/sh\necho "$@" >> "{opened}"\n')
    opener.chmod(opener.stat().st_mode | stat.S_IXUSR)
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "issuer_library",
            "--state-dir",
            str(state),
            "--port",
            str(port),
            "--no-browser",
            "--workspace",
            str(workspace),
        ],
        stdout=subprocess.PIPE,
        stderr=(tmp_path / "stderr.txt").open("wb"),
        env={**os.environ, "BROWSER": str(opener), "PYTHONPATH": str(SRC)},
        text=True,
    )  # fmt: skip  (argument list kept one flag pair per line)
    try:
        assert process.stdout is not None
        line = process.stdout.readline()
        base = f"http://127.0.0.1:{port}"
        pattern = r"^Issuer Library: " + re.escape(base) + r"/launch\?ticket=[0-9a-f]{64}\n$"
        assert re.match(pattern, line), line
        link = line.removeprefix("Issuer Library: ").strip()

        def send(
            method: str, target: str, headers: dict[str, str] | None = None, body: str | None = None
        ) -> http.client.HTTPResponse:
            connection = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
            connection.request(method, target, body=body, headers=headers or {})
            response = connection.getresponse()
            response.read()
            connection.close()
            return response

        target = link.removeprefix(base)
        exchange = send("GET", target)
        cookies = exchange.headers.get_all("Set-Cookie") or []
        assert exchange.status == 303 and len(cookies) == 1
        assert send("GET", target).status == 403, "the printed link worked twice"
        quit_headers = {"X-Issuer-Library": "1", "Content-Type": "application/json"}
        quit_headers["Origin"] = base
        assert send("POST", "/api/quit", quit_headers, "{}").status == 403
        signed = {**quit_headers, "Cookie": cookies[0].split(";")[0]}
        assert send("POST", "/api/quit", signed, "{}").status == 200
        assert process.wait(10) == 0
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()
    ticket = link.removeprefix(base + "/launch?ticket=")
    assert ticket not in (state / "library.log").read_text()
    assert not opened.exists(), "a browser was started"


def test_only_same_origin_or_user_initiated_requests_are_served(tmp_path: Path) -> None:
    """Sec-Fetch-Site is accepted only as same-origin (the app's own page), none (an address the
    user or the launcher opened) or absent. same-site is refused: a page on another 127.0.0.1
    port is the same site, and the Strict cookie goes with its requests. Expected by hand, with
    the valid cookie on each: absent, same-origin and none get the endpoint's own answer (200;
    the launch 303); same-site, cross-site, an empty value, another letter case, an unknown
    value, and same-origin followed by same-site get 403 "Local app requests only", and the
    launch ticket stays unspent until the accepted "none" launch spends it."""
    app = build_app(tmp_path)
    ticket = app.session.ticket()

    def send(method: str, path: str, sites: list[str]) -> Reply:
        headers = [cookie_of(app), *(("Sec-Fetch-Site", site) for site in sites)]
        if method == "POST":
            headers += list(POST_HEADERS.items())
        return drive(app, method, path, headers=headers, body=b"{}")

    endpoints = [
        ("GET", "/"),
        ("GET", "/api/catalogue"),
        ("GET", "/files/deliverables/report/report.html?embedded=1"),
        ("GET", "/files/runs/case-a/CP-0.md?download=1"),
        ("GET", "/context-form.html"),
        ("POST", "/api/refresh"),
    ]
    for sites in [[], ["same-origin"], ["none"]]:
        for method, path in endpoints:
            assert send(method, path, sites).status == 200, (sites, method, path)
    refused = [
        ["same-site"],
        ["cross-site"],
        [""],
        ["Same-Origin"],
        ["same-origin-ish"],
        ["same-origin", "same-site"],
    ]
    for sites in refused:
        for method, path in [*endpoints, ("GET", "/launch?ticket=" + ticket)]:
            w = send(method, path, sites)
            assert w.status == 403 and w.text == LOCAL_ONLY, (sites, method, path)
            assert w.header("Set-Cookie") == "", (sites, method, path)
    assert send("GET", "/launch?ticket=" + ticket, ["none"]).status == 303


def test_the_launch_ticket_expires_120_seconds_after_start(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The ticket expires 120 seconds after start, counted from when the library is ready (after
    its first discovery, which here moves the test clock 30 s). Expected by hand: ready at
    T = start+30 s, so the ticket works until T+120 s: at T+120 s-1 ns it is exchanged (303 with
    the cookie). On fresh apps, at exactly T+120 s and at T+120 s+1 ns it gets the 403 launcher
    page with no cookie, and moving the clock back to T+1 s afterwards does not revive it."""
    start = 1000.0
    current = [start]
    monkeypatch.setattr(launch, "clock", lambda: current[0])
    real_discover = server_module.discover

    def slow(workspace: str, seed: Any) -> Any:
        current[0] += 30.0
        return real_discover(workspace, seed)

    monkeypatch.setattr(server_module, "discover", slow)
    ready = start + 30.0
    app = build_app(tmp_path, "first")
    assert app.session.expires == ready + 120.0
    current[0] = ready + 120.0 - 1e-9
    w = launch_request(app, "GET", "?ticket=" + app.session.ticket())
    assert w.status == 303 and len(w.values("Set-Cookie")) == 1
    for after in [0.0, 1e-9]:
        current[0] = start
        late = build_app(tmp_path, f"late-{after}")
        ticket = late.session.ticket()
        current[0] = ready + 120.0 + after
        w = launch_request(late, "GET", "?ticket=" + ticket)
        assert w.status == 403 and w.header("Set-Cookie") == "", after
        assert w.text == LAUNCHER_ONLY + "\n", after
        current[0] = ready + 1.0
        w = launch_request(late, "GET", "?ticket=" + ticket)
        assert w.status == 403 and w.header("Set-Cookie") == "", f"{after}: the ticket was revived"


def test_review_concurrent_launch_spends_once(tmp_path: Path) -> None:
    """Hand-derived: 64 concurrent valid-ticket GETs: exactly one 303 with a cookie, 63 are 403
    without."""
    app = build_app(tmp_path)
    ticket = app.session.ticket()
    barrier = threading.Barrier(64)
    replies: list[Reply] = []
    guard = threading.Lock()

    def one() -> None:
        barrier.wait(10)
        reply = launch_request(app, "GET", "?ticket=" + ticket)
        with guard:
            replies.append(reply)

    threads = [threading.Thread(target=one) for _ in range(64)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(30)
    assert len(replies) == 64  # a thread that raised never answered
    ok = sum(1 for r in replies if r.status == 303)
    refused = sum(1 for r in replies if r.status == 403)
    cookies = sum(1 for r in replies if r.header("Set-Cookie") != "")
    assert (ok, refused, cookies) == (1, 63, 1)


def test_review_gate_covers_methods_and_paths(tmp_path: Path) -> None:
    """Every method on every path shape without the cookie: 403 (or 405 only for /launch
    non-GET), never a 404/200/405 from behind the gate; with the cookie the gate lets it through
    (anything but the launcher text)."""
    app = build_app(tmp_path)
    ticket = app.session.ticket()
    session = app.session.cookie
    paths = [
        "/",
        "/nope",
        "/launch/",
        "//launch",
        "/LAUNCH",
        "/health/",
        "/health/x",
        "/files/",
        "/files/../x",
        "/api/",
        "/api/runs",
        "/api/runs/",
        "/api/runs/status",
        "/api/catalogue/",
        "/%2e%2e/etc",
        "/launch%2f",
        "/api/quit",
        "/api/settings",
        "/favicon.ico",
        "/web/index.html",
    ]  # fmt: skip  (the path table is packed, as in Go's launch_review_test.go)
    methods = ["GET", "HEAD", "OPTIONS", "POST", "PUT", "DELETE", "PATCH", "TRACE", "FOO"]
    for path in paths:
        for method in methods:
            w = drive(app, method, path)
            marked = "Open Credit OS from its launcher" in w.text
            assert w.status == 403 and (marked or method == "HEAD"), (method, path, w.status)
            assert session not in w.text and ticket not in w.text, (method, path)
    # /launch with other methods: never spends, never sets a cookie.
    for method in ["HEAD", "POST", "OPTIONS", "PUT"]:
        w = launch_request(app, method, "?ticket=" + ticket)
        assert w.status == 405 and w.header("Set-Cookie") == "", method
        assert app.session.ticket() != "", method
    # Host/Origin checks come first: a wrong host with a valid ticket is refused, not spent.
    w = drive(app, "GET", "/launch?ticket=" + ticket, headers=[("Host", "evil.example")])
    assert w.status == 403 and app.session.ticket() != "" and "Local app requests only" in w.text
    w = drive(app, "GET", "/launch?ticket=" + ticket, headers=[("Sec-Fetch-Site", "cross-site")])
    assert w.status == 403 and app.session.ticket() != ""
    # Responses never carry a secret in any header except the one Set-Cookie of a launch.
    w = launch_request(app, "GET", "?ticket=" + ticket)
    for key, value in w.headers:
        assert key == "set-cookie" or session not in value, key
    # /health: only the two fields, no secret, with and without the cookie.
    for with_cookie in [False, True]:
        w = drive(app, "GET", "/health", headers=[cookie_of(app)] if with_cookie else [])
        assert w.status == 200 and session not in w.text
        assert str(app.loc.state) not in w.text and w.text.count(":") == 2


def test_non_ascii_secrets_are_refused_not_errors(tmp_path: Path) -> None:
    """Python-only: secrets.compare_digest raises on non-ASCII str, so a non-ASCII query or
    cookie must be refused with 403, never a 500."""
    app = build_app(tmp_path)
    name = launch.cookie_name(app.host)
    w = drive(app, "GET", "/launch?ticket=%C3%A9%FF")
    assert w.status == 403 and w.header("Set-Cookie") == ""
    w = drive(app, "GET", "/launch", headers=[("Cookie", f"{name}=caf\xe9")])
    assert w.status == 403
    w = drive(app, "GET", "/api/catalogue", headers=[("Cookie", name.encode() + b"=caf\xc3\xa9")])
    assert w.status == 403
    assert launch_request(app, "GET", "?ticket=" + app.session.ticket()).status == 303


_GO124 = (
    "not applicable: mkdirAllIn is the Go 1.24 stand-in for os.Root.MkdirAll used by jobs.go "
    "intake staging; Python has no os.Root, and intake staging is jobs.py (Task 1.5)"
)


@pytest.mark.skip(reason=_GO124)
def test_mkdir_all_in_creates_nested_and_accepts_existing() -> None:
    """Go go124_test.go TestMkdirAllInCreatesNestedAndAcceptsExisting."""


@pytest.mark.skip(reason=_GO124)
def test_mkdir_all_in_refuses_files_and_escapes() -> None:
    """Go go124_test.go TestMkdirAllInRefusesFilesAndEscapes."""


def test_an_authorised_head_answers_as_get_without_a_body(tmp_path: Path) -> None:
    """Go's net/http answers an authorised HEAD from the GET route: same status and headers
    (Content-Length included), no body."""
    app = build_app(tmp_path)
    got = drive(app, "GET", "/api/catalogue", headers=[cookie_of(app)])
    head = drive(app, "HEAD", "/api/catalogue", headers=[cookie_of(app)])
    assert got.status == 200 and len(got.body) > 0
    assert head.status == 200 and head.body == b""
    assert head.header("content-length") == str(len(got.body))


def test_browser_launch_opens_the_link_and_reports_a_failure_without_the_ticket(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Go main.go: without --no-browser, standard output holds `Issuer Library: <address>` only
    and the browser gets the launch link; when it fails, the log line is `Open browser: <error>`
    (no ticket) and the error dialog says `Open this link in your browser within 2 minutes; it
    works once:\n<link>\n<error>`."""
    address = "http://127.0.0.1:54321"
    link = address + "/launch?ticket=" + "ab" * 32
    opened: list[str] = []
    shown: list[str] = []
    done = threading.Event()

    def open_browser(url: str) -> None:
        opened.append(url)
        raise OSError("no browser could be started")

    def show_error(message: str) -> None:
        shown.append(message)
        done.set()

    monkeypatch.setattr(launcher, "open_browser", open_browser)
    monkeypatch.setattr(launcher, "show_error", show_error)
    caplog.set_level(logging.DEBUG)
    launcher.announce(link=link, address=address, browse=True)
    assert done.wait(10)
    assert capsys.readouterr().out == "Issuer Library: " + address + "\n"
    assert opened == [link]
    assert shown == [
        "Open this link in your browser within 2 minutes; it works once:\n"
        + link
        + "\nno browser could be started"
    ]
    assert "Open browser: no browser could be started" in caplog.text
    assert "ab" * 32 not in caplog.text
