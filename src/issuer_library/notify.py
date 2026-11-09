"""The native notice for a finished run: when to send it, what it says, and how it is shown."""

from __future__ import annotations

import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

from . import events
from .desktop import WORKER_FLAGS

if TYPE_CHECKING:
    from .server import Application

log = logging.getLogger("issuer_library")

# How long finish_job waits, after a run finishes, for a run-list request that proves a tab is
# open. The app-wide watcher polls /api/runs/list every 5 s while a run is running, but Chrome and
# Edge throttle a hidden tab to about one poll a minute, so the wait covers one such poll.
TAB_GRACE = 75.0
TAB_POLL_STEP = 1.0
TOAST_TIMEOUT = 20.0

# The variables the PowerShell child inherits, matched case-insensitively: what PowerShell and
# WinRT need to start, and no credentials.
TOAST_ENV_NAMES = (
    "SystemRoot",
    "windir",
    "SystemDrive",
    "USERPROFILE",
    "APPDATA",
    "LOCALAPPDATA",
    "TEMP",
    "TMP",
    "PATH",
    "PATHEXT",
    "ProgramData",
    "ProgramFiles",
    "COMPUTERNAME",
    "USERNAME",
    "PROCESSOR_ARCHITECTURE",
)

# The fixed words for a reason the worker records in status.json. Only these words are ever shown;
# a reason outside the table is dropped rather than echoed.
STOP_REASON_WORDS = {
    "budget": "spending cap reached",
    "checker": "a handoff did not pass its check",
    "provider": "provider error or unknown charge",
    "interrupted": "interrupted",
    "ruling": "a provider ruling or pause is in force",
}

# The fixed PowerShell program for the Windows notice, Go's toastScript byte for byte. The text
# arrives only through the two environment variables and is set as XML text nodes, never
# concatenated.
TOAST_SCRIPT = (
    r"$ErrorActionPreference = 'Stop'"
    "\n"
    r"$null = [Windows.UI.Notifications.ToastNotificationManager, "
    r"Windows.UI.Notifications, ContentType = WindowsRuntime]"
    "\n"
    r"$null = [Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, "
    r"ContentType = WindowsRuntime]"
    "\n"
    r"$xml = New-Object Windows.Data.Xml.Dom.XmlDocument"
    "\n"
    r"$xml.LoadXml('<toast><visual><binding template="
    r'"ToastGeneric"'
    r"><text/><text/></binding></visual></toast>')"
    "\n"
    r"$texts = $xml.GetElementsByTagName('text')"
    "\n"
    r"$null = $texts.Item(0).AppendChild($xml.CreateTextNode($env:ISSUER_LIBRARY_TOAST_TITLE))"
    "\n"
    r"$null = $texts.Item(1).AppendChild($xml.CreateTextNode($env:ISSUER_LIBRARY_TOAST_BODY))"
    "\n"
    r"$toast = [Windows.UI.Notifications.ToastNotification]::new($xml)"
    "\n"
    r"[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("
    r"'{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\WindowsPowerShell\v1.0\powershell.exe')"
    r".Show($toast)"
    "\n"
)


class ToastFailed(subprocess.CalledProcessError, OSError):
    """PowerShell exited nonzero; its text is Go's exec.ExitError text, "exit status N"."""

    def __str__(self) -> str:
        return f"exit status {self.returncode}"


def tab_watching(lib: Application) -> bool:
    """Whether a run-list request arrived after the finish time in lib.finished.

    Waits up to TAB_GRACE after that time for one. A request made before the finish does not
    count: a tab closed since then leaves only such a request. It holds no lock.
    """
    finished = lib.finished
    grace = int(TAB_GRACE * 1_000_000_000)
    while True:
        if lib.watched > finished:
            return True
        if lib.now() - finished >= grace:
            return False
        lib.pause(TAB_POLL_STEP)


def fold_equal(left: str, right: str) -> bool:
    """Go's strings.EqualFold: the same length in characters, each pair equal under case folding.

    Folding is per character, so a character that folds to several (a ligature) never matches
    a plain letter, while the long s and the Kelvin sign fold onto s and k as in Go.
    """
    return len(left) == len(right) and all(
        one == two or one.casefold() == two.casefold() for one, two in zip(left, right, strict=True)
    )


def toast_env(environ: list[str], title: str, body: str) -> list[str]:
    """The child environment: the allowed names in input order, then the two notice variables."""
    kept = [
        entry
        for entry in environ
        if any(fold_equal(entry.partition("=")[0], name) for name in TOAST_ENV_NAMES)
    ]
    return [*kept, f"ISSUER_LIBRARY_TOAST_TITLE={title}", f"ISSUER_LIBRARY_TOAST_BODY={body}"]


def read_record(path: Path) -> dict[str, list[Any]] | None:
    """The members of a JSON file as Go's json.Unmarshal into a struct reads them.

    None when the file is unreadable, is not a regular file (a FIFO would block the finish
    thread) or is undecodable.
    """
    try:
        with events.open_regular(path) as stream:
            return events.go_record(stream.read())
    except (OSError, ValueError):
        return None


def finish_notice(folder: Path) -> tuple[str, str] | None:
    """The native notice text for a finished run, or None when there is nothing to say.

    It carries the state word, the issuer when known and, for a run that did not complete, its
    recorded reason in fixed words. It never carries the status message, which may hold redacted
    provider text. Both files decode as Go's structs do: keys match without regard to case, a null
    leaves a field as it was, invalid UTF-8 becomes U+FFFD, and a wrong type is undecodable.
    """
    status = read_record(folder / "status.json")
    if status is None:
        return None
    try:
        state: str = events.go_value(status, "state", events.go_text)
    except ValueError:
        return None
    if state in ("", "running"):
        return None
    issuer = ""
    review = read_record(folder / "review.json")  # An unreadable review only drops the issuer.
    if review is not None:
        try:
            issuer = events.go_value(review, "issuer", events.go_text)
        except ValueError:
            issuer = ""
    text = f"{issuer} run {state}" if issuer else f"Run {state}"
    # Go's Reason is `any`: a null resets it and a reason that is not a string is dropped.
    reason = events.go_value(status, "reason", lambda value: value, nil_resets=True)
    words = STOP_REASON_WORDS.get(reason) if isinstance(reason, str) else None
    if words is not None and state != "complete" and words != state:
        text += f": {words}"
    return "Credit OS", text


def system_directory() -> str:
    """The Windows system folder from GetSystemDirectoryW, not from the environment."""
    if sys.platform == "win32":
        import ctypes

        buffer = ctypes.create_unicode_buffer(260)
        length = ctypes.windll.kernel32.GetSystemDirectoryW(buffer, len(buffer))
        if 0 < length < len(buffer):
            return buffer.value
    raise OSError("Windows system folder lookup failed")


def powershell_path() -> str:
    """The system PowerShell by absolute path; there is no PATH fallback."""
    path = Path(system_directory()) / "WindowsPowerShell" / "v1.0" / "powershell.exe"
    if not path.is_file():
        raise FileNotFoundError(f"{path} does not exist")
    return str(path)


def toast(title: str, body: str) -> None:
    """Show a native notice. Off Windows there is none: say so in the log.

    It raises OSError only: ToastFailed ("exit status N") for a nonzero exit, and a plain OSError,
    chained to the cause, for a timeout, a NUL in the text or a failed start.
    """
    if sys.platform != "win32":
        log.info("No tab is open; native run notices are Windows-only (%s)", body)
        return
    # close_fds stays at its default so the child never inherits a worker.lock handle.
    try:
        result = subprocess.run(
            [
                powershell_path(),
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                TOAST_SCRIPT,
            ],
            env=dict(
                entry.partition("=")[::2]
                for entry in toast_env([f"{k}={v}" for k, v in os.environ.items()], title, body)
            ),
            creationflags=WORKER_FLAGS,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=TOAST_TIMEOUT,
            check=False,
        )
    except (subprocess.TimeoutExpired, ValueError) as error:
        raise OSError(f"PowerShell notice failed: {error}") from error
    if result.returncode != 0:
        log.warning("PowerShell toast output: %s", result.stdout.decode("utf-8", "replace"))
        raise ToastFailed(result.returncode, "powershell", result.stdout)
