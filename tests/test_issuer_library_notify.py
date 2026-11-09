"""The run notice: its text, the fixed toast script, the tab wait and the child environment."""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest

from issuer_library import notify

ORIGIN_NS = 1_794_139_200_000_000_000  # 2026-11-08T12:00:00Z
SECOND_NS = 1_000_000_000


def notice_folder(tmp_path: Path, status: str, review: str) -> Path:
    tmp_path.mkdir(exist_ok=True)
    if status:
        (tmp_path / "status.json").write_text(status)
    if review:
        (tmp_path / "review.json").write_text(review)
    return tmp_path


def test_finish_notice_text_uses_issuer_and_state(tmp_path: Path) -> None:
    folder = notice_folder(
        tmp_path,
        '{"state":"complete","message":"secret provider text"}',
        '{"issuer":"Northbridge Group"}',
    )
    assert notify.finish_notice(folder) == ("Issuer Library", "Northbridge Group run complete")
    for name, status, review in (
        ("running", '{"state":"running"}', '{"issuer":"Northbridge Group"}'),
        ("unreadable", "", ""),
    ):
        assert notify.finish_notice(notice_folder(tmp_path / name, status, review)) is None
    interrupted = notice_folder(tmp_path / "interrupted", '{"state":"interrupted"}', "")
    assert notify.finish_notice(interrupted) == ("Issuer Library", "Run interrupted")


NORTHBRIDGE = '{"issuer":"Northbridge Group"}'


@pytest.mark.parametrize(
    ("status", "review", "want"),
    [
        (
            '{"state":"stopped","reason":"budget"}',
            '{"issuer":"TransDigm Group Incorporated"}',
            "TransDigm Group Incorporated run stopped: spending cap reached",
        ),
        (
            '{"state":"stopped","reason":"checker"}',
            NORTHBRIDGE,
            "Northbridge Group run stopped: a handoff did not pass its check",
        ),
        (
            '{"state":"failed","reason":"provider"}',
            NORTHBRIDGE,
            "Northbridge Group run failed: provider error or unknown charge",
        ),
        (
            '{"state":"failed","reason":"ruling"}',
            NORTHBRIDGE,
            "Northbridge Group run failed: a provider ruling or pause is in force",
        ),
        (
            '{"state":"interrupted","reason":"interrupted"}',
            NORTHBRIDGE,
            "Northbridge Group run interrupted",
        ),
        ('{"state":"stopped"}', NORTHBRIDGE, "Northbridge Group run stopped"),
        (
            '{"state":"failed","reason":"sk-secret"}',
            NORTHBRIDGE,
            "Northbridge Group run failed",
        ),
        ('{"state":"stopped","reason":"budget"}', "", "Run stopped: spending cap reached"),
        ('{"state":"stopped","reason":5}', NORTHBRIDGE, "Northbridge Group run stopped"),
        ('{"state":"failed","reason":{"a":1}}', NORTHBRIDGE, "Northbridge Group run failed"),
        (
            '{"state":"complete","reason":"budget"}',
            NORTHBRIDGE,
            "Northbridge Group run complete",
        ),
    ],
)
def test_finish_notice_names_the_stop_reason(
    tmp_path: Path, status: str, review: str, want: str
) -> None:
    assert notify.finish_notice(notice_folder(tmp_path, status, review)) == (
        "Issuer Library",
        want,
    )


def test_a_status_whose_state_is_not_a_string_gives_no_notice(tmp_path: Path) -> None:
    # Go decodes status into a struct whose state is a string: any other type is undecodable.
    assert notify.finish_notice(notice_folder(tmp_path, '{"state":5}', NORTHBRIDGE)) is None


def test_toast_script_is_fixed_and_reads_only_the_two_variables() -> None:
    script = notify.TOAST_SCRIPT
    assert script.count("$env:") == 2
    for want in (
        "$env:ISSUER_LIBRARY_TOAST_TITLE",
        "$env:ISSUER_LIBRARY_TOAST_BODY",
        "CreateTextNode",
        "ContentType = WindowsRuntime",
        "{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}",
    ):
        assert want in script
    for bad in ("%s", "+ $env"):
        assert bad not in script


def test_tab_watching_waits_for_a_poll_after_the_finish() -> None:
    state = {"now": ORIGIN_NS}
    lib = SimpleNamespace(finished=ORIGIN_NS, watched=0, now=lambda: state["now"])

    def step(seconds: float) -> None:
        state["now"] += int(seconds * SECOND_NS)

    lib.pause = step
    app = cast(Any, lib)
    # Never polled: waits the whole 75 s, then false.
    assert not notify.tab_watching(app)
    assert state["now"] == ORIGIN_NS + 75 * SECOND_NS
    # A poll before the finish does not count.
    state["now"] = ORIGIN_NS
    lib.watched = ORIGIN_NS - SECOND_NS
    assert not notify.tab_watching(app)
    # A poll at the finish instant does not count either; only a later one does.
    state["now"] = ORIGIN_NS
    lib.watched = ORIGIN_NS
    assert not notify.tab_watching(app)

    # A poll arriving during the wait (60 s in) counts and ends the wait there.
    def late(seconds: float) -> None:
        step(seconds)
        if state["now"] == ORIGIN_NS + 60 * SECOND_NS:
            lib.watched = state["now"]

    state["now"] = ORIGIN_NS
    lib.pause = late
    assert notify.tab_watching(app)
    assert state["now"] == ORIGIN_NS + 60 * SECOND_NS


def test_toast_env_keeps_only_the_allowed_names() -> None:
    got = notify.toast_env(
        [
            "OPENAI_API_KEY=k1",
            "Path=C:\\bin",
            "systemroot=C:\\Windows",
            "GH_TOKEN=k2",
            "USERNAME=eg",
            "BAD",
        ],
        "T",
        "B",
    )
    assert got == [
        "Path=C:\\bin",
        "systemroot=C:\\Windows",
        "USERNAME=eg",
        "ISSUER_LIBRARY_TOAST_TITLE=T",
        "ISSUER_LIBRARY_TOAST_BODY=B",
    ]


# Fix round 1: expected values come from Go's encoding/json and strings.EqualFold (the 5E probes
# and the Go oracle built from key/notify.go), not from this code.
DEEP = b"[" * 100000 + b"]" * 100000
NOTICE_CASES = [
    ("State key", b'{"State":"stopped"}', None, "Run stopped"),
    ("Issuer key", b'{"state":"stopped"}', b'{"Issuer":"Northbridge Group"}', None),
    (
        "REASON key",
        b'{"state":"stopped","REASON":"budget"}',
        None,
        "Run stopped: spending cap reached",
    ),
    ("invalid UTF-8 message", b'{"state":"stopped","message":"\xff"}', None, "Run stopped"),
    ("null after state", b'{"state":"stopped","state":null}', None, "Run stopped"),
    ("state then number", b'{"state":5,"state":"stopped"}', None, False),
    ("issuer then null", b'{"state":"stopped"}', b'{"issuer":"A","issuer":null}', "A run stopped"),
    ("lone surrogate issuer", b'{"state":"stopped"}', b'{"issuer":"A\\ud800B"}', "A�B run stopped"),
    ("invalid UTF-8 issuer", b'{"state":"stopped"}', b'{"issuer":"A\xffB"}', "A�B run stopped"),
    ("NUL issuer", b'{"state":"stopped"}', b'{"issuer":"A\\u0000B"}', "A\x00B run stopped"),
    (
        "mixed-case keys",
        b'{"State":"failed","Reason":"budget"}',
        b'{"ISSUER":"N"}',
        "N run failed: spending cap reached",
    ),
    (
        "reason then null",
        b'{"state":"stopped","reason":"budget","reason":null}',
        None,
        "Run stopped",
    ),
    ("BOM", b'\xef\xbb\xbf{"state":"stopped"}', None, False),
    ("UTF-16", '{"state":"stopped"}'.encode("utf-16"), None, False),
    ("NaN", b'{"state":"stopped","reason":NaN}', None, False),
    ("NaN elsewhere", b'{"state":"stopped","x":NaN}', None, False),
    ("array status", b'["stopped"]', None, False),
    ("null status", b"null", None, False),
    ("deep status", b'{"state":"stopped","x":' + DEEP + b"}", None, False),
    ("deep review", b'{"state":"stopped"}', b'{"issuer":"A","x":' + DEEP + b"}", "Run stopped"),
]


@pytest.mark.parametrize(
    ("status", "review", "want"),
    [case[1:] for case in NOTICE_CASES],
    ids=[case[0] for case in NOTICE_CASES],
)
def test_finish_notice_decodes_as_go_does(
    tmp_path: Path, status: bytes, review: bytes | None, want: str | bool | None
) -> None:
    (tmp_path / "status.json").write_bytes(status)
    if review is not None:
        (tmp_path / "review.json").write_bytes(review)
    got = notify.finish_notice(tmp_path)
    if want is False:
        assert got is None
    elif want is None:  # Only the issuer key's case is probed.
        assert got == ("Issuer Library", "Northbridge Group run stopped")
    else:
        assert got == ("Issuer Library", want)


def test_toast_env_matches_names_by_go_equal_fold() -> None:
    entries = [
        "ANTHROPIC_API_KEY=sk",
        "path=low",
        "ſYSTEMROOT=longs",  # Go's EqualFold folds the long s onto s.
        "PROGRAMﬁLES=ligature",  # No simple fold: not ProgramFiles.
        "SYSTEMROOT\u0000=nul",
        "TEMP",
    ]
    assert notify.toast_env(entries, "T", "B") == [
        "path=low",
        "ſYSTEMROOT=longs",
        "TEMP",
        "ISSUER_LIBRARY_TOAST_TITLE=T",
        "ISSUER_LIBRARY_TOAST_BODY=B",
    ]


def test_a_review_or_status_fifo_does_not_block(tmp_path: Path) -> None:
    import os
    import threading

    (tmp_path / "status.json").write_text('{"state":"stopped"}')
    os.mkfifo(tmp_path / "review.json")
    out: list[object] = []
    worker = threading.Thread(
        target=lambda: out.append(notify.finish_notice(tmp_path)), daemon=True
    )
    worker.start()
    worker.join(3)
    assert not worker.is_alive(), "finish_notice blocked on a FIFO review.json"
    assert out == [("Issuer Library", "Run stopped")]
    os.unlink(tmp_path / "status.json")
    os.mkfifo(tmp_path / "status.json")
    out.clear()
    worker = threading.Thread(
        target=lambda: out.append(notify.finish_notice(tmp_path)), daemon=True
    )
    worker.start()
    worker.join(3)
    assert not worker.is_alive() and out == [None]


def test_a_failed_toast_logs_its_output_and_raises_the_exit_status(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    exe = tmp_path / "WindowsPowerShell" / "v1.0" / "powershell.exe"
    exe.parent.mkdir(parents=True)
    exe.write_text("#!/bin/sh\necho boom\nexit 1\n")
    exe.chmod(0o700)
    monkeypatch.setattr(notify, "sys", SimpleNamespace(platform="win32"))
    monkeypatch.setattr(notify, "system_directory", lambda: str(tmp_path))
    with caplog.at_level("INFO", logger="issuer_library"), pytest.raises(OSError) as raised:
        notify.toast("T", "B")
    assert str(raised.value) == "exit status 1"
    assert "PowerShell toast output: boom\n" in [r.getMessage() for r in caplog.records]


def fake_powershell(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, script: str) -> None:
    exe = tmp_path / "WindowsPowerShell" / "v1.0" / "powershell.exe"
    exe.parent.mkdir(parents=True)
    exe.write_text(script)
    exe.chmod(0o700)
    monkeypatch.setattr(notify, "sys", SimpleNamespace(platform="win32"))
    monkeypatch.setattr(notify, "system_directory", lambda: str(tmp_path))


def test_a_toast_timeout_raises_a_plain_oserror_chained_to_the_timeout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_powershell(tmp_path, monkeypatch, "#!/bin/sh\nsleep 5\n")
    monkeypatch.setattr(notify, "TOAST_TIMEOUT", 0.5)
    with pytest.raises(OSError) as raised:
        notify.toast("T", "B")
    assert not isinstance(raised.value, subprocess.TimeoutExpired)
    assert isinstance(raised.value.__cause__, subprocess.TimeoutExpired)


def test_a_toast_with_a_nul_in_the_text_raises_a_plain_oserror_chained_to_the_valueerror(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_powershell(tmp_path, monkeypatch, "#!/bin/sh\nexit 0\n")
    with pytest.raises(OSError) as raised:
        notify.toast("T", "A\x00B run stopped")
    assert isinstance(raised.value.__cause__, ValueError)


def test_toast_script_is_gos_byte_for_byte() -> None:
    assert len(notify.TOAST_SCRIPT) == 863
    digest = hashlib.sha256(notify.TOAST_SCRIPT.encode()).hexdigest()
    assert digest == "392cd731f1f4bb72ae64b7ec96f5438448849cbddd930dc712c428262df2d6e6"
