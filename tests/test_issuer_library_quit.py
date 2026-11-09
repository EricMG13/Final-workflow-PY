"""The relaunch quit protocol, ported case for case from the Go tests.

Expected values come from final-workflow's quit_test.go at the pinned sha dd3dfa18 (answer key in
.superpowers/sdd/2026-11-08-python-build/answer-key/), never from running this code. The
docstring of each test is the Go comment's "Expected by hand".
"""

from __future__ import annotations

import ast
import http.client
import json
import os
import re
import socket
import stat
import subprocess
import sys
import threading
import time
from collections.abc import Callable
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from issuer_library_support import POST_HEADERS, call, client_of, fake_engine, make_app
from test_issuer_library_jobs import review_request, wait_idle

import issuer_library.quit as quit_module
import issuer_library.server as server_module
from issuer_library.launch import ALREADY_RUNNING
from issuer_library.model import Catalogue
from issuer_library.server import Application

WINDOWS = sys.platform == "win32"
SRC = Path(quit_module.__file__).resolve().parents[1]
GUARD = "deferred: needs Task 1.5 guard; the later of 1-D4 and S3's PR un-skips"
A07 = "deferred: needs Task 1.5 A07; the later of 1-D4 and S3's PR un-skips"
BUSY = "Issuer Library is busy ({}); wait for it to finish, then start it again."


@pytest.fixture
def short_quit_times(monkeypatch: pytest.MonkeyPatch) -> None:
    """The running instance and a relaunch poll every 10 ms; a test sets the wait it needs."""
    monkeypatch.setattr(quit_module, "quit_poll", 0.01)


def wait_at_most(monkeypatch: pytest.MonkeyPatch, seconds: float) -> None:
    monkeypatch.setattr(quit_module, "quit_wait", seconds)


def absent(name: Path) -> bool:
    return not os.path.lexists(name)


def age(name: Path, seconds: float) -> None:
    """Move the file's times by seconds (negative: into the past)."""
    moved = time.time() + seconds
    os.utime(name, (moved, moved), follow_symlinks=False)


def held_listener() -> socket.socket:
    """Go's `held`: a bound, listening loopback socket, as a running instance's port is."""
    held = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    held.bind(("127.0.0.1", 0))
    held.listen(5)
    return held


def test_the_quit_request_is_owner_only_and_names_only_the_process(tmp_path: Path) -> None:
    """Mode 0600 and exactly the given text; a second launch while it is fresh joins it (false,
    text unchanged); a stale one is replaced; a link at the name is removed, not followed (its
    target keeps its content) and a plain file is placed."""
    request = tmp_path / quit_module.QUIT_REQUEST

    def read() -> str:
        return request.read_text()

    assert quit_module.place_quit_request(request, "quit requested by process 4242\n")
    assert read() == "quit requested by process 4242\n"
    if not WINDOWS:
        assert os.lstat(request).st_mode & 0o777 == 0o600
    assert not quit_module.place_quit_request(request, "quit requested by process 4343\n")
    assert read() == "quit requested by process 4242\n", "a fresh request was replaced"
    age(request, -3600)
    assert quit_module.place_quit_request(request, "quit requested by process 4343\n")
    assert read() == "quit requested by process 4343\n", "a stale request was kept"
    if WINDOWS:
        return
    outside = tmp_path / "elsewhere" / "target"
    outside.parent.mkdir()
    outside.write_text("kept")
    request.unlink()
    request.symlink_to(outside)
    assert os.path.islink(request)
    assert quit_module.place_quit_request(request, "quit requested by process 4444\n")
    assert read() == "quit requested by process 4444\n", "through a link"
    assert outside.read_text() == "kept"
    assert os.path.isfile(request) and not os.path.islink(request), "request is not a plain file"


def test_only_a_fresh_well_formed_busy_answer_is_shown(tmp_path: Path) -> None:
    """The three well-formed answers are read; text after the counts, a bare string, plain text,
    a stale answer, a link to a valid answer and an answer over 256 bytes are not."""
    answer = tmp_path / quit_module.QUIT_ANSWER
    for text in [
        '"busy: 1 run, 0 reviews"',
        '"busy: 0 runs, 1 review"',
        '"busy: 12 runs, 3 reviews"\n',
    ]:
        answer.write_text(text)
        assert quit_module.read_quit_answer(answer) == text.strip().strip('"'), text
    for text in [
        '"busy: 1 run, 0 reviews; open http://x"',
        '"Issuer Library is busy"',
        "busy: 1 run, 0 reviews",
        '"busy: 1 run, 0 reviews' + " " * 300 + '"',
    ]:
        answer.write_text(text)
        assert quit_module.read_quit_answer(answer) is None, f"{text!r} was shown"
    answer.write_text('"busy: 1 run, 0 reviews"')
    age(answer, -3600)
    assert quit_module.read_quit_answer(answer) is None, "a stale answer was shown"
    if not WINDOWS:
        valid = tmp_path / "elsewhere" / "valid"
        valid.parent.mkdir()
        valid.write_text('"busy: 1 run, 0 reviews"')
        answer.unlink()
        answer.symlink_to(valid)
        assert quit_module.read_quit_answer(answer) is None, "an answer behind a link was shown"


def test_a_relaunch_that_gets_no_answer_withdraws_its_request(
    tmp_path: Path, short_quit_times: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A running instance that neither quits nor answers (an older build, or one that is hung):
    after the wait (300 ms here) the relaunch raises AlreadyRunning and withdraws its own
    request."""
    wait_at_most(monkeypatch, 0.3)
    with held_listener() as held:
        began = time.monotonic()
        with pytest.raises(quit_module.AlreadyRunning) as raised:
            quit_module.ask_to_quit(tmp_path, held.getsockname()[1])
        elapsed = time.monotonic() - began
    assert str(raised.value) == ALREADY_RUNNING
    assert 0.3 <= elapsed <= 5, f"waited {elapsed}"
    assert absent(tmp_path / quit_module.QUIT_REQUEST), "the unanswered request was left behind"


@pytest.mark.skipif(WINDOWS, reason="links are judged by Unix rules here")
def test_relaunch_side_planted_answers_and_links(
    tmp_path: Path, short_quit_times: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A fresh, well-formed busy answer left in the folder before the relaunch (nobody is running
    to write it) is deleted at the start, so the relaunch waits its 300 ms and reports
    AlreadyRunning rather than busy; a link at quit.answer is deleted, never followed; a link at
    quit.request is replaced by a plain file of this launch (the link's target keeps its
    content); a hard link to an old file is judged stale, removed, and its other name is
    untouched."""
    wait_at_most(monkeypatch, 0.3)
    state = tmp_path / "state"
    state.mkdir(mode=0o700)
    answer, request = state / quit_module.QUIT_ANSWER, state / quit_module.QUIT_REQUEST
    outside = tmp_path / "outside"
    outside.write_text("kept")
    with held_listener() as held:
        port = held.getsockname()[1]
        answer.write_text('"busy: 9 runs, 9 reviews"')
        with pytest.raises(quit_module.AlreadyRunning):
            quit_module.ask_to_quit(state, port)
        answer.symlink_to(outside)
        with pytest.raises(quit_module.AlreadyRunning):
            quit_module.ask_to_quit(state, port)
        assert absent(answer), "a linked answer was not removed"
    request.symlink_to(outside)
    assert quit_module.place_quit_request(request, "quit requested by process 1\n")
    assert os.path.isfile(request) and not os.path.islink(request), "request after a link"
    request.unlink()
    old = tmp_path / "old"
    old.write_text("kept")
    age(old, -3600)
    os.link(old, request)
    assert quit_module.place_quit_request(request, "quit requested by process 1\n")
    assert old.read_text() == "kept", "the hard link's other name changed"
    assert outside.read_text() == "kept", "the link target changed"


def sid(text: str) -> bytes:
    """A SID's stored form from its string form, by hand rather than with quit.py."""
    parts = text.split("-")
    authority = int(parts[2])
    raw = bytearray([1, len(parts) - 3])
    raw += authority.to_bytes(6, "big")
    for part in parts[3:]:
        raw += int(part).to_bytes(4, "little")
    return bytes(raw)


def entry(kind: int, flags: int, mask: int, who: bytes) -> bytes:
    """An access-control entry: type, flags, size, mask, SID."""
    size = 8 + len(who)
    return bytes([kind, flags]) + size.to_bytes(2, "little") + mask.to_bytes(4, "little") + who


def acl(count: int, *entries: bytes) -> bytes:
    """A stored access-control list (revision 2) of entries; count overrides the entry count
    when it is not negative."""
    body = b"".join(entries)
    if count < 0:
        count = len(entries)
    size = 8 + len(body)
    return bytes([2, 0]) + size.to_bytes(2, "little") + count.to_bytes(2, "little") + b"\0\0" + body


def test_windows_access_list_judgement() -> None:
    """The state folder's access-control list decides. Masks by hand: full control 0x1F01FF,
    modify 0x1301BF, read and execute 0x1200A9, add file 0x2, generic write 0x40000000.
    Expected: the default local application data list (SYSTEM, Administrators and the user with
    full control, inherited with OI|CI 0x13) is private, also with Users reading and an empty
    list; Users with modify, Everyone with generic write, Authenticated Users adding files,
    another user with full control, a callback allow entry, a short list, an entry count past
    the list and a SID past its entry are not. A deny entry grants nothing."""
    for text, want in {
        "S-1-5-18": quit_module.SID_SYSTEM,
        "S-1-5-32-544": quit_module.SID_ADMINISTRATORS,
        "S-1-3-0": quit_module.SID_CREATOR_OWNER,
        "S-1-3-4": quit_module.SID_OWNER_RIGHTS,
    }.items():
        assert sid(text) == want, f"{text}: {want.hex(' ')}, want {sid(text).hex(' ')}"
    user = sid("S-1-5-21-1004336348-1177238915-682003330-1001")
    trusted = [
        user,
        quit_module.SID_SYSTEM,
        quit_module.SID_ADMINISTRATORS,
        quit_module.SID_CREATOR_OWNER,
        quit_module.SID_OWNER_RIGHTS,
    ]
    system, administrators, users = sid("S-1-5-18"), sid("S-1-5-32-544"), sid("S-1-5-32-545")
    standard = [
        entry(0, 0x13, 0x1F01FF, system),
        entry(0, 0x13, 0x1F01FF, administrators),
        entry(0, 0x13, 0x1F01FF, user),
    ]

    def with_(*extra: bytes) -> bytes:
        return acl(-1, *standard, *extra)

    cases: dict[str, tuple[bytes, bool]] = {
        "default": (with_(), False),
        "users read and execute": (with_(entry(0, 0x13, 0x1200A9, users)), False),
        "empty list": (acl(-1), False),
        "creator owner inherit-only": (with_(entry(0, 0x1B, 0x10000000, sid("S-1-3-0"))), False),
        "users denied, then allowed": (
            with_(entry(1, 0, 0x1301BF, users), entry(0, 0, 0x1200A9, users)),
            False,
        ),
        "users modify": (with_(entry(0, 0x13, 0x1301BF, users)), True),
        "everyone generic write": (with_(entry(0, 0, 0x40000000, sid("S-1-1-0"))), True),
        "authenticated users add": (with_(entry(0, 0, 0x2, sid("S-1-5-11"))), True),
        "another user full control": (
            with_(entry(0, 0, 0x1F01FF, sid("S-1-5-21-1004336348-1177238915-682003330-1002"))),
            True,
        ),
        "callback allow entry": (with_(entry(9, 0, 0x1200A9, user)), True),
        "short header": (bytes([2, 0, 8, 0]), True),
        "count past the list": (acl(4, *standard), True),
        "SID past its entry": (
            acl(-1, entry(0, 0, 0x1200A9, bytes([1, 5, 0, 0, 0, 0, 0, 5, 18, 0, 0, 0]))),
            True,
        ),
        "entry size below its header": (acl(1, bytes([0, 0, 2, 0])), True),
    }
    for label, (stored, others) in cases.items():
        got = quit_module.others_may_write(stored, trusted)
        assert got == others, f"{label}: others may write {got}, want {others}"


def plant_request(state: Path) -> None:
    """A fresh quit request as a relaunch writes it."""
    descriptor = os.open(
        state / quit_module.QUIT_REQUEST, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600
    )
    with os.fdopen(descriptor, "w") as stream:
        stream.write("quit requested by process 1\n")
    os.chmod(state / quit_module.QUIT_REQUEST, 0o600)


def answer_of(state: Path) -> str:
    """The busy answer the instance left, or "" when there is none."""
    return quit_module.read_quit_answer(state / quit_module.QUIT_ANSWER) or ""


def counted_stop(lib: Application) -> list[int]:
    """Replace lib.stop with a counter; its length is the number of stops."""
    stops: list[int] = []
    lib.stop = lambda: stops.append(1)
    return stops


# Relaunches through the executable, as it runs: BROWSER is the stand-in for Go's launchBrowser.


def opener_script(tmp_path: Path) -> tuple[Path, Path]:
    """A BROWSER command that appends each URL it is given to a file; returns (command, file)."""
    opened, opener = tmp_path / "opened.txt", tmp_path / "opener.sh"
    opener.write_text(f'#!/bin/sh\necho "$@" >> "{opened}"\n')
    opener.chmod(opener.stat().st_mode | stat.S_IXUSR)
    return opener, opened


def launcher(
    tmp_path: Path, opener: Path, port: int, state: Path, name: str
) -> subprocess.Popen[str]:
    workspace = tmp_path / "workspace"
    workspace.mkdir(exist_ok=True)
    return subprocess.Popen(
        [
            sys.executable,
            "-m",
            "issuer_library",
            "--state-dir",
            str(state),
            "--port",
            str(port),
            "--workspace",
            str(workspace),
        ],
        stdout=subprocess.PIPE,
        stderr=(tmp_path / f"stderr-{name}.txt").open("wb"),
        env={**os.environ, "BROWSER": str(opener), "PYTHONPATH": str(SRC)},
        text=True,
    )  # fmt: skip  (argument list kept one flag pair per line)


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def wait_opened(opened: Path, number: int, process: subprocess.Popen[str]) -> str:
    """The number-th link a launch opens, failing if the launch ends first."""
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        links = opened.read_text().split() if opened.exists() else []
        if len(links) >= number:
            return links[number - 1]
        assert process.poll() is None, f"the launch ended before opening a link: {process.poll()}"
        time.sleep(0.05)
    raise AssertionError("the launch opened no link")


def send(method: str, port: int, path: str, cookie: str | None = None) -> tuple[int, list[str]]:
    """A request as the app's page makes it (a POST with the custom header, JSON and Origin),
    with cookie when given; returns the status and the Set-Cookie values."""
    headers = dict(POST_HEADERS, Origin=f"http://127.0.0.1:{port}") if method == "POST" else {}
    if cookie is not None:
        headers["Cookie"] = cookie
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    try:
        connection.request(method, path, body="{}" if method == "POST" else None, headers=headers)
        response = connection.getresponse()
        response.read()
        return response.status, response.headers.get_all("Set-Cookie") or []
    finally:
        connection.close()


def exchange(port: int, link: str) -> str:
    """Open a launch link as the browser does and return the session cookie it receives."""
    status, cookies = send("GET", port, link.removeprefix(f"http://127.0.0.1:{port}"))
    assert status == 303 and len(cookies) == 1, f"exchange: {status} {cookies}"
    return cookies[0].split(";")[0]


def test_relaunch_asks_an_idle_library_to_quit_and_opens_a_fresh_link(tmp_path: Path) -> None:
    """S18 ruling 1, through the executable as it runs. A request and an answer left from a crash
    are cleared when the first launch starts (it keeps running); that launch opens
    http://127.0.0.1:<port>/launch?ticket=<64 hex> and the browser then loses its cookie (403). A
    relaunch places the request, the idle instance removes it and stops (exit 0), and the
    relaunch takes the port and opens a different link whose cookie works while the old one gets
    403. Each launch prints only the address; no quit file is left, and neither launch's ticket
    or session is in any state file, library.log included."""
    opener, opened = opener_script(tmp_path)
    state, port = tmp_path / "state", free_port()
    base = f"http://127.0.0.1:{port}"
    state.mkdir(mode=0o700)
    plant_request(state)
    (state / quit_module.QUIT_ANSWER).write_text('"busy: 9 runs, 9 reviews"')
    request, answer = state / quit_module.QUIT_REQUEST, state / quit_module.QUIT_ANSWER
    first = launcher(tmp_path, opener, port, state, "first")
    second: subprocess.Popen[str] | None = None
    try:
        first_link = wait_opened(opened, 1, first)
        pattern = re.compile("^" + re.escape(base) + r"/launch\?ticket=[0-9a-f]{64}$")
        assert pattern.match(first_link), f"first link {first_link!r}"
        assert absent(request) and absent(answer), "the files left from a crash were not cleared"
        first_cookie = exchange(port, first_link)
        time.sleep(1.3)  # five polls: the cleared request did not stop the instance
        assert send("GET", port, "/api/catalogue", first_cookie)[0] == 200
        assert send("GET", port, "/api/catalogue")[0] == 403, "the cookie is lost, but it opened"
        second = launcher(tmp_path, opener, port, state, "second")
        assert first.wait(timeout=10) == 0, "the idle library did not quit for the relaunch"
        second_link = wait_opened(opened, 2, second)
        assert pattern.match(second_link) and second_link != first_link, f"second {second_link!r}"
        second_cookie = exchange(port, second_link)
        assert send("GET", port, "/api/catalogue", second_cookie)[0] == 200, "the fresh session"
        assert send("GET", port, "/api/catalogue", first_cookie)[0] == 403, "the old session"
        assert absent(request) and absent(answer), "a quit file was left behind"
        assert send("POST", port, "/api/quit", second_cookie)[0] == 200
        assert second.wait(timeout=10) == 0, "the second instance did not stop"
        for process in (first, second):
            assert process.stdout is not None
            assert process.stdout.read() == f"Issuer Library: {base}\n"
    finally:
        for process in (first, second):
            if process is not None and process.poll() is None:
                process.kill()
                process.wait()
    prefix = base + "/launch?ticket="
    secrets = [
        first_link.removeprefix(prefix),
        first_cookie.partition("=")[2],
        second_link.removeprefix(prefix),
        second_cookie.partition("=")[2],
    ]
    for name in state.rglob("*"):
        if name.is_file():
            for secret in secrets:
                assert secret not in name.read_text(errors="replace"), f"{name} holds a secret"
    logged = (state / "library.log").read_text()
    assert "A new launch asked the idle library to quit; stopping" in logged, logged


@pytest.mark.skip(reason=A07)
def test_relaunch_is_told_a_run_keeps_the_library_busy(tmp_path: Path) -> None:
    """S18 ruling 1 with a run in flight (a job an earlier instance left running, whose worker
    still holds its lock). Expected by hand: the relaunch returns exactly "Issuer Library is busy
    (1 run, 0 reviews); wait for it to finish, then start it again.", the instance keeps running
    with its session, and no quit file is left. Once the worker ends, a relaunch quits the idle
    instance and opens a fresh link."""
    import fcntl  # a worker's lock is a flock; Windows has its own

    opener, opened = opener_script(tmp_path)
    state, port = tmp_path / "state", free_port()
    workspace = tmp_path / "workspace"
    # Go's writeJob (jobs_test.go:595): intake/<id> (0700) holding status.json (0600) with just
    # the state, its times set to now.
    job = workspace / "intake" / ("web-" + "b" * 32)
    job.mkdir(parents=True, mode=0o700)
    (job / "status.json").write_text('{"state":"running"}')
    (job / "status.json").chmod(0o600)  # written just now, as Go's Chtimes(now) leaves it
    # S3's worker lock replaces this when A07 lands.
    lock = open(job / "worker.lock", "w")  # noqa: SIM115  (held until the worker "ends")
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    first = launcher(tmp_path, opener, port, state, "first")
    relaunched: list[subprocess.Popen[str]] = []
    try:
        link = wait_opened(opened, 1, first)
        cookie = exchange(port, link)
        busy = launcher(tmp_path, opener, port, state, "busy")
        assert busy.wait(timeout=20) == 1
        error = (tmp_path / "stderr-busy.txt").read_text().strip()
        assert error == BUSY.format("1 run, 0 reviews"), f"relaunch beside a run: {error}"
        assert first.poll() is None, "the busy library stopped"
        assert send("GET", port, "/api/catalogue", cookie)[0] == 200, "the busy library's session"
        assert absent(state / quit_module.QUIT_REQUEST)
        assert absent(state / quit_module.QUIT_ANSWER), "a quit file was left behind"
        lock.close()
        # The instance notices the worker has ended within a few polls; until then a relaunch is
        # told it is busy, then one quits it.
        attempt = 0
        while True:
            process = launcher(tmp_path, opener, port, state, f"again-{attempt}")
            relaunched.append(process)
            while first.poll() is None and process.poll() is None:
                time.sleep(0.02)
            if first.poll() is not None:
                assert first.returncode == 0, f"first instance: {first.returncode}"
                break
            reason = (tmp_path / f"stderr-again-{attempt}.txt").read_text()
            not_busy = not reason.startswith("Issuer Library is busy (")
            assert not (attempt > 100 or process.returncode == 0 or not_busy), reason
            time.sleep(0.02)
            attempt += 1
        assert first.wait(timeout=10) == 0
        fresh = exchange(port, wait_opened(opened, 2, relaunched[-1]))
        assert send("POST", port, "/api/quit", fresh)[0] == 200
        assert relaunched[-1].wait(timeout=10) == 0
    finally:
        lock.close()
        for process in [first, *relaunched]:
            if process.poll() is None:
                process.kill()
                process.wait()


def test_quit_request_is_answered_busy_while_a_review_or_run_is_in_flight(tmp_path: Path) -> None:
    """In process. Expected by hand: with one review in flight the answer is "busy: 0 runs, 1
    review"; with two runs as well "busy: 2 runs, 1 review"; with one "busy: 1 run, 1 review".
    Each time the library keeps running (no stop) and the request is removed. Once nothing is in
    flight the next request stops it (one stop, request removed, no answer)."""
    lib, _ = make_app(tmp_path)
    stops = counted_stop(lib)
    state = lib.loc.state
    request = state / quit_module.QUIT_REQUEST
    with lib.lock:
        lib.reviews = 1  # a review in flight; S3 owns the code that changes it
    for jobs, want in [
        ([], "busy: 0 runs, 1 review"),
        (["web-a", "web-b"], "busy: 2 runs, 1 review"),
        (["web-a"], "busy: 1 run, 1 review"),
    ]:
        with lib.lock:
            lib.active_jobs = set(jobs)
        plant_request(state)
        assert not quit_module.answer_quit_request(lib) and not stops, f"{jobs}: it stopped"
        assert answer_of(state) == want and absent(request), f"{jobs}: answer {answer_of(state)!r}"
    with lib.lock:
        lib.active_jobs = set()
        lib.reviews = 0
    (state / quit_module.QUIT_ANSWER).unlink()
    plant_request(state)
    assert quit_module.answer_quit_request(lib) and len(stops) == 1
    assert absent(request) and answer_of(state) == "", f"idle: answer {answer_of(state)!r}"


@pytest.mark.skip(reason=GUARD)
def test_quit_request_is_answered_busy_while_a_review_or_run_is_in_flight_tail(
    tmp_path: Path,
) -> None:
    """From the idle stop on, a review or Start is refused with 503 and the quitting message."""
    lib, _ = make_app(tmp_path)
    lib.engine = fake_engine(tmp_path)
    client = client_of(lib)
    counted_stop(lib)
    plant_request(lib.loc.state)
    assert quit_module.answer_quit_request(lib)
    refused = review_request(client, '["annual.txt"]')
    assert refused.status_code == 503 and refused.text == quit_module.LIBRARY_QUITTING + "\n"
    start = '{"id":"web-' + "c" * 32 + '","review_id":"x","confirm":true}'
    refused = call(client, "POST", "/api/runs/start", start)
    assert refused.status_code == 503 and refused.text == quit_module.LIBRARY_QUITTING + "\n"


def test_stale_or_invalid_quit_requests_are_removed_unread(tmp_path: Path) -> None:
    """Adversarial requests. Expected by hand: each of these is removed unread, never followed,
    and does not stop the library or write an answer: an hour old, an hour in the future,
    readable or writable by others, a link to a file elsewhere (which keeps its content), a
    dangling link, a folder, and (as root) a file of another user."""
    if WINDOWS:
        pytest.skip("permission bits and links are judged by Unix rules here")
    lib, _ = make_app(tmp_path)
    stops = counted_stop(lib)
    state = lib.loc.state
    request, answer = state / quit_module.QUIT_REQUEST, state / quit_module.QUIT_ANSWER
    outside = tmp_path / "elsewhere" / "target"
    outside.parent.mkdir()
    outside.write_text("kept")

    def planted(change: Callable[[], None]) -> Callable[[], None]:
        def plant() -> None:
            plant_request(state)
            change()

        return plant

    cases: dict[str, Callable[[], None]] = {
        "an hour old": planted(lambda: age(request, -3600)),
        "an hour ahead": planted(lambda: age(request, 3600)),
        "readable by others": planted(lambda: os.chmod(request, 0o644)),
        "writable by group": planted(lambda: os.chmod(request, 0o620)),
        "a link elsewhere": lambda: request.symlink_to(outside),
        "a dangling link": lambda: request.symlink_to(state / "missing"),
        "a folder": lambda: request.mkdir(mode=0o700),
    }
    if os.getuid() == 0:
        cases["another user's file"] = planted(lambda: os.chown(request, 12345, 12345))
    for label, plant in cases.items():
        plant()
        assert not quit_module.answer_quit_request(lib), f"{label}: the library stopped"
        assert absent(request) and absent(answer), f"{label}: request or answer left"
    assert outside.read_text() == "kept" and not stops
    with lib.lock:
        assert not lib.quitting, "an invalid request set the library quitting"


def test_a_state_folder_other_users_can_write_is_refused(tmp_path: Path) -> None:
    """A state folder other users can write to, or that is not this user's, is refused by both
    sides. Expected by hand: for modes 0770, 0720, 0702 and 0777 private_folder names the folder
    as writable by others; a fresh valid request there is left untouched (no stop, no answer); a
    relaunch raises the refusal before placing a request. Modes 0700, 0750 and 0755 are
    accepted, and back at 0700 the same request stops the library."""
    if WINDOWS:
        pytest.skip(
            "permission bits do not describe access on Windows; see TestWindowsAccessListJudgement"
        )
    lib, _ = make_app(tmp_path)
    stops = counted_stop(lib)
    state = lib.loc.state
    request = state / quit_module.QUIT_REQUEST
    try:
        for mode in (0o770, 0o720, 0o702, 0o777):
            os.chmod(state, mode)
            with pytest.raises(OSError) as refusal:
                quit_module.private_folder(state)
            assert str(refusal.value) == f"other users can write to the state folder {state}"
            plant_request(state)
            acted = quit_module.answer_quit_request(lib)
            assert not acted and not absent(request), f"{mode:o}: acted on"
            assert absent(state / quit_module.QUIT_ANSWER), f"{mode:o}: answered"
            request.unlink()
            with pytest.raises(ValueError) as relaunch:
                quit_module.ask_to_quit(state, 1)
            assert (
                "this launch does not ask it to quit: other users can write to the state folder "
                f"{state}. Quit the running library" in str(relaunch.value)
            ) and absent(request), f"{mode:o}: relaunch {relaunch.value}, request placed"
        for mode in (0o700, 0o750, 0o755):
            os.chmod(state, mode)
            quit_module.private_folder(state)  # no error
        os.chmod(state, 0o700)
        if os.getuid() == 0:
            os.chown(state, 12345, 12345)
            with pytest.raises(OSError) as foreign:
                quit_module.private_folder(state)
            assert str(foreign.value) == f"the state folder {state} does not belong to this user"
            os.chown(state, 0, 0)
        plant_request(state)
        assert quit_module.answer_quit_request(lib) and len(stops) == 1
    finally:
        os.chmod(state, 0o700)


def test_two_relaunches_at_once(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Two relaunches at once against an idle instance (its port held, its watcher running).
    Expected by hand: the instance stops once; exactly one relaunch gets the port and the other
    raises AlreadyRunning after its wait; no request is left."""
    monkeypatch.setattr(quit_module, "quit_poll", 0.01)
    wait_at_most(monkeypatch, 1.0)
    lib, _ = make_app(tmp_path)
    held = held_listener()
    port = held.getsockname()[1]
    stops: list[int] = []

    def stop() -> None:
        stops.append(1)
        held.close()

    lib.stop = stop
    ended = threading.Event()
    watcher = threading.Thread(
        target=quit_module.watch_quit_requests, args=(lib, ended.is_set, 0.01), daemon=True
    )
    watcher.start()
    outcomes: list[socket.socket | BaseException] = []

    def relaunch() -> None:
        try:
            outcomes.append(quit_module.ask_to_quit(lib.loc.state, port))
        except BaseException as error:  # noqa: BLE001  (the test classifies every outcome)
            outcomes.append(error)

    threads = [threading.Thread(target=relaunch) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=15)
    ended.set()
    watcher.join(timeout=5)
    ports = [o for o in outcomes if isinstance(o, socket.socket)]
    refused = [o for o in outcomes if isinstance(o, quit_module.AlreadyRunning)]
    other = [o for o in outcomes if o not in ports and o not in refused]
    for listener in ports:
        listener.close()  # The winner keeps the port, as the new instance does.
    assert not other, f"relaunch: {other}"
    assert len(ports) == 1 and len(refused) == 1 and len(stops) == 1
    assert absent(lib.loc.state / quit_module.QUIT_REQUEST), "a request is left"


def quit_during_discovery(label: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """One label of the discovery test: label "refresh" holds POST /api/refresh, anything else
    holds a POST /api/settings to another folder."""
    lib, _ = make_app(tmp_path / "app")
    stops = counted_stop(lib)
    client = client_of(lib)
    entered, release = threading.Event(), threading.Event()
    other = tmp_path / "other"
    other.mkdir()
    real_discover = server_module.discover

    def held(workspace: str, seed: Catalogue) -> Catalogue:
        entered.set()
        assert release.wait(timeout=10)
        return real_discover(workspace, seed)

    codes: list[int] = []

    def work() -> None:
        if label == "refresh":
            codes.append(call(client, "POST", "/api/refresh").status_code)
        else:
            body = json.dumps({"workspace": str(other)})
            codes.append(call(client, "POST", "/api/settings", body).status_code)

    monkeypatch.setattr(server_module, "discover", held)
    thread = threading.Thread(target=work)
    thread.start()
    assert entered.wait(timeout=10)
    plant_request(lib.loc.state)
    acted = quit_module.answer_quit_request(lib)
    gone = absent(lib.loc.state / quit_module.QUIT_REQUEST)
    assert not acted and not stops and not gone, f"{label}: acted on during the discovery"
    release.set()
    thread.join(timeout=10)
    monkeypatch.setattr(server_module, "discover", real_discover)
    assert codes == [200], f"{label}: {codes}"
    assert quit_module.answer_quit_request(lib) and len(stops) == 1, f"{label}: after"


def test_a_quit_request_waits_for_a_discovery_in_progress(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A request that arrives during a discovery (the periodic refresh) or a workspace switch
    waits for it. Expected by hand: while the discovery is held the request stays and the library
    keeps running; once it ends (the switch answering 200) the next poll stops the library."""
    for label in ["refresh", "workspace switch"]:
        quit_during_discovery(label, tmp_path / label.replace(" ", "-"), monkeypatch)


def race_round(
    lib: Application, client: TestClient, root: Path, round_: int, stops: list[int]
) -> None:
    """One round of Start racing the quit watcher; the asserts are the test's expected pairs."""
    state = lib.loc.state
    response = review_request(client, '["annual.txt"]')
    assert response.status_code == 200, f"round {round_}: review {response.status_code}"
    job_id = response.json()["id"]
    plant_request(state)
    before = len(stops)
    gate = threading.Event()
    result: dict[str, object] = {}
    body = json.dumps({"id": job_id, "review_id": "review-fingerprint", "confirm": True})

    def start() -> None:
        gate.wait()
        result["code"] = call(client, "POST", "/api/runs/start", body).status_code

    def watch() -> None:
        gate.wait()
        time.sleep((round_ % 8) * 0.0001)
        result["stopped"] = quit_module.answer_quit_request(lib)

    threads = [threading.Thread(target=start), threading.Thread(target=watch)]
    for thread in threads:
        thread.start()
    gate.set()
    for thread in threads:
        thread.join()
    code, stopped = result["code"], result["stopped"]
    claim = not absent(root / "intake" / job_id / "start.claim")
    if code == 202 and not stopped:
        assert answer_of(state) == "busy: 1 run, 0 reviews" and len(stops) == before, round_
        wait_idle(lib)
    elif code == 503 and stopped:
        started = root / "intake" / job_id / "synthetic-starts.txt"
        assert not claim and absent(started) and len(stops) == before + 1, round_
        lib.refreshing.release()  # The test's stand-in for the process ending.
    else:
        raise AssertionError(f"round {round_}: Start {code}, library stopped {stopped}")
    (state / quit_module.QUIT_ANSWER).unlink(missing_ok=True)
    with lib.lock:
        lib.quitting = False


@pytest.mark.skip(reason=GUARD)
def test_start_racing_a_quit_request_never_orphans_a_worker(tmp_path: Path) -> None:
    """Start racing the quit watcher. Expected by hand, whichever runs first: either Start gets
    202 and the watcher then sees one run (it keeps running, answers "busy: 1 run, 0 reviews",
    and has not asked the app to stop), or the watcher wins (it stops) and Start gets 503 with no
    claim and no worker, so nothing is orphaned. Any other pair is a defect."""
    lib, root = make_app(tmp_path)
    lib.engine = fake_engine(tmp_path)
    client = client_of(lib)
    stops = counted_stop(lib)
    for round_ in range(40):
        race_round(lib, client, root, round_, stops)


def test_quit_claims_the_shutdown_guard_before_a_start_can_begin(tmp_path: Path) -> None:
    """Codex review of ac22d9d (P1). Expected by hand: Quit with a run or a review in flight
    answers 409 and leaves the library not quitting; Quit when idle answers 200."""
    lib, _ = make_app(tmp_path)
    client = client_of(lib)
    stopped = threading.Event()
    lib.stop = stopped.wait  # hold the stop, so a Start would race an unfinished quit
    try:
        for busy in [
            lambda: setattr(lib, "active_jobs", {"web-a"}),
            lambda: setattr(lib, "reviews", 1),
        ]:
            with lib.lock:
                lib.active_jobs, lib.reviews = set(), 0
                busy()
            response = call(client, "POST", "/api/quit", "{}")
            assert response.status_code == 409, f"Quit with work in flight: {response.text!r}"
            with lib.lock:
                assert not lib.quitting, "a refused Quit set the library quitting"
        with lib.lock:
            lib.active_jobs, lib.reviews = set(), 0
        assert call(client, "POST", "/api/quit", "{}").status_code == 200
        with lib.lock:
            assert lib.quitting
    finally:
        stopped.set()


@pytest.mark.skip(reason=GUARD)
def test_quit_claims_the_shutdown_guard_before_a_start_can_begin_tail(tmp_path: Path) -> None:
    """From an idle Quit's 200 on, a Start is refused with 503 and the quitting message, before
    the asynchronous stop runs."""
    lib, _ = make_app(tmp_path)
    client = client_of(lib)
    stopped = threading.Event()
    lib.stop = stopped.wait
    try:
        assert call(client, "POST", "/api/quit", "{}").status_code == 200
        start = '{"id":"web-' + "c" * 32 + '","review_id":"x","confirm":true}'
        response = call(client, "POST", "/api/runs/start", start)
        assert response.status_code == 503, f"Start after Quit: {response.status_code}"
        assert response.text == quit_module.LIBRARY_QUITTING + "\n"
    finally:
        stopped.set()


def test_every_windows_call_declares_its_argument_and_result_types() -> None:
    """Fix round 1, reading the cause at the source. Expected by reading quit.py: a ctypes call
    with no argtypes converts a Python int as a 32-bit C long on Windows, so the 64-bit pseudo
    handle from GetCurrentProcess raises ctypes.ArgumentError (not OSError). So every
    `<dll>.<Name>(...)` call in windows_private_folder, where <dll> is a ctypes.WinDLL, must have
    both `<dll>.<Name>.argtypes = ...` and `<dll>.<Name>.restype = ...` assigned before it."""
    parsed = ast.parse(Path(quit_module.__file__).read_text())
    function = next(
        node
        for node in ast.walk(parsed)
        if isinstance(node, ast.FunctionDef) and node.name == "windows_private_folder"
    )
    dlls = {
        target.id
        for node in ast.walk(function)
        if isinstance(node, ast.Assign) and "ctypes.WinDLL(" in ast.unparse(node.value)
        for target in ast.walk(node.targets[0])
        if isinstance(target, ast.Name)
    }
    for dll in ("advapi", "kernel"):
        assert dll in dlls, f"{dll} is not a WinDLL in windows_private_folder"
    declared = {
        ast.unparse(target): node.lineno
        for node in ast.walk(function)
        if isinstance(node, ast.Assign)
        for target in node.targets
    }
    called = [
        node
        for node in ast.walk(function)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id in dlls
    ]
    assert len(called) >= 6, "the Win32 calls were not found"
    for node in called:
        name = ast.unparse(node.func)
        for kind in ("argtypes", "restype"):
            line = declared.get(f"{name}.{kind}")
            assert line is not None and line < node.lineno, f"{name} has no {kind} before use"


def test_a_refresh_or_settings_request_after_an_idle_quit_is_refused_not_blocked(
    tmp_path: Path,
) -> None:
    """Fix round 1. After the idle stop refreshing stays held (Go parity), so a discovery request
    admitted afterwards must not wait for it for ever: expected by hand, POST /api/refresh and
    POST /api/settings each answer 503 with Go's libraryQuitting text and a newline within 5 s."""
    lib, _ = make_app(tmp_path)
    counted_stop(lib)
    client = client_of(lib)
    plant_request(lib.loc.state)
    assert quit_module.answer_quit_request(lib)
    replies: list[tuple[int, str]] = []
    for endpoint, body in [
        ("/api/refresh", ""),
        ("/api/settings", json.dumps({"workspace": str(tmp_path)})),
    ]:
        replies.clear()

        def post(endpoint: str = endpoint, body: str = body) -> None:
            reply = call(client, "POST", endpoint, body)
            replies.append((reply.status_code, reply.text))

        thread = threading.Thread(target=post, daemon=True)
        thread.start()
        thread.join(timeout=5)
        assert not thread.is_alive(), f"{endpoint} is blocked on the held refreshing lock"
        want = "Issuer Library is quitting for a new launch; use the window that launch opens.\n"
        assert replies == [(503, want)], endpoint
