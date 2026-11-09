"""The relaunch quit protocol, ported case for case from the Go tests.

Expected values come from final-workflow's quit_test.go at the pinned sha dd3dfa18 (answer key in
.superpowers/sdd/2026-11-08-python-build/answer-key/), never from running this code. The
docstring of each test is the Go comment's "Expected by hand".
"""

from __future__ import annotations

import ast
import os
import socket
import sys
import time
from pathlib import Path

import pytest

import issuer_library.quit as quit_module
from issuer_library.launch import ALREADY_RUNNING

WINDOWS = sys.platform == "win32"


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
