"""Recovery when the browser has lost the session cookie: a relaunch asks the idle library to quit.

The running instance's secrets are in its memory only, so a relaunch cannot sign a browser in to
it. Instead the relaunch asks it to quit through the per-user state folder: no network endpoint,
and nothing secret on disk. The request names the asking process; the answer says what is in
flight. A port of the Go build's quit.go and its platform files.
"""

from __future__ import annotations

import ctypes
import json
import logging
import os
import re
import socket
import stat
import sys
import time
from collections.abc import Callable, Sequence
from ctypes import wintypes
from pathlib import Path
from typing import TYPE_CHECKING

from .launch import ALREADY_RUNNING
from .settings import save_json

if TYPE_CHECKING:
    from .server import Application

log = logging.getLogger("issuer_library")

QUIT_REQUEST = "quit.request"
QUIT_ANSWER = "quit.answer"

# How often the running instance looks for a request and a relaunch for the outcome; how long a
# relaunch waits; how old a request or answer may be before it belongs to no waiting launch.
# Module variables so tests can shorten them.
quit_poll = 0.25
quit_wait = 10.0
quit_stale = 20.0

# The only answer a relaunch shows, so nothing else written there reaches its dialog. Used with
# fullmatch: Python's $ also matches before a trailing newline.
BUSY_ANSWER = re.compile(r"busy: [0-9]{1,6} runs?, [0-9]{1,6} reviews?")

# Refuses a review or Start once the library has agreed to quit for a relaunch.
LIBRARY_QUITTING = "Issuer Library is quitting for a new launch; use the window that launch opens."

# Windows well-known SIDs, as stored: revision 1, the number of sub-authorities, the 6-byte
# identifier authority (big endian), then each sub-authority (little endian).
SID_SYSTEM = bytes([1, 1, 0, 0, 0, 0, 0, 5, 18, 0, 0, 0])  # S-1-5-18
SID_ADMINISTRATORS = bytes([1, 2, 0, 0, 0, 0, 0, 5, 32, 0, 0, 0, 0x20, 0x02, 0, 0])  # S-1-5-32-544
SID_CREATOR_OWNER = bytes([1, 1, 0, 0, 0, 0, 0, 3, 0, 0, 0, 0])  # S-1-3-0
SID_OWNER_RIGHTS = bytes([1, 1, 0, 0, 0, 0, 0, 3, 4, 0, 0, 0])  # S-1-3-4

# Rights that let their holder put a file in a folder, replace or delete one, or take the folder
# over: add file, add subfolder, delete child, delete, write DAC, write owner, generic all and
# generic write.
FOLDER_WRITE_RIGHTS = 0x2 | 0x4 | 0x40 | 0x10000 | 0x40000 | 0x80000 | 0x10000000 | 0x40000000


class AlreadyRunning(ValueError):
    """The running instance neither quit nor answered this launch's request."""


def remove(path: Path | str) -> None:
    """Go's os.Remove: unlink a file or link (never followed), remove an empty folder; a missing
    name is not an error."""
    try:
        if stat.S_ISDIR(os.lstat(path).st_mode):
            os.rmdir(path)
        else:
            os.unlink(path)
    except FileNotFoundError:
        pass


def discard(path: Path | str) -> None:
    """Best-effort removal for a file that only tidies up; a failure is logged, not raised."""
    try:
        remove(path)
    except OSError as error:
        log.warning("Remove %s: %s", path, error)


def stale(mtime: float) -> bool:
    return abs(time.time() - mtime) > quit_stale


def count(n: int, noun: str) -> str:
    return f"1 {noun}" if n == 1 else f"{n} {noun}s"


def clear_quit_files(state: Path) -> None:
    """Remove a request or answer left by an instance or relaunch that has ended. A new instance
    calls it before it serves anything, so no relaunch is waiting on them."""
    for name in (QUIT_REQUEST, QUIT_ANSWER):
        try:
            remove(state / name)
        except OSError as error:
            log.warning("Clear %s: %s", name, error)


def listen(port: int) -> socket.socket:
    """A listening loopback socket on the port; OSError when it is taken."""
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        if os.name != "nt":
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind(("127.0.0.1", port))
        listener.listen(128)
    except OSError:
        listener.close()
        raise
    return listener


def ask_to_quit(state: Path, port: int) -> socket.socket:
    """Ask this user's running instance to quit and wait, quit_wait at most, for its port.

    Returns the port's listener once the instance has gone. Otherwise raises ValueError with the
    instance's busy answer, or AlreadyRunning when the instance neither quits nor answers."""
    try:
        private_folder(state)
    except OSError as error:
        raise ValueError(
            f"Issuer Library is already running, and this launch does not ask it to quit: "
            f"{error}. Quit the running library (Settings > Quit library, or end Issuer "
            "Library in Task Manager), then start it again."
        ) from error
    request, answer = state / QUIT_REQUEST, state / QUIT_ANSWER
    discard(answer)  # An answer to an earlier launch is not this launch's.
    mine = f"quit requested by process {os.getpid()}\n"
    placed = False
    try:
        placed = place_quit_request(request, mine)
        deadline = time.monotonic() + quit_wait
        while True:
            try:
                return listen(port)
            except OSError:
                pass  # The instance still holds the port; look for its answer.
            status = read_quit_answer(answer)
            if status is not None:
                discard(answer)
                raise ValueError(
                    f"Issuer Library is busy ({status.removeprefix('busy: ')}); "
                    "wait for it to finish, then start it again."
                )
            if time.monotonic() > deadline:
                raise AlreadyRunning(ALREADY_RUNNING)
            time.sleep(quit_poll)
    finally:
        if placed:
            withdraw(request, mine)


def withdraw(request: Path, mine: str) -> None:
    """Withdraw the request if the instance did not take it, unless another launch's replaced it."""
    try:
        text = request.read_text(encoding="utf-8")
    except FileNotFoundError:
        return  # The instance took it.
    except (OSError, ValueError) as error:
        log.warning("Withdraw quit request: %s", error)  # Unreadable: not provably ours to remove.
        return
    if text == mine:
        discard(request)


def place_quit_request(request: Path, content: str) -> bool:
    """Create the request, owner-only, and report whether this launch created it. A stale request,
    or anything at that name that is not a plain file private to this user, is removed first
    (never followed); a fresh request of another launch is left for both to wait on."""
    try:
        info = os.lstat(request)
    except OSError:
        pass  # Nothing there (or unreadable, in which case the create below reports it).
    else:
        if not owner_only(info) or stale(info.st_mtime):
            discard(request)
    try:
        descriptor = os.open(request, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        return False
    except OSError as error:
        log.warning("Quit request: %s", error)
        return False
    try:
        try:
            os.write(descriptor, content.encode("utf-8"))
        finally:
            os.close(descriptor)
    except OSError as error:
        log.warning("Quit request: %s", error)  # The file is the request; its text only names us.
    return True


def read_quit_answer(answer: Path) -> str | None:
    """The running instance's answer, if it has written a fresh, valid one."""
    try:
        info = os.lstat(answer)
        if not stat.S_ISREG(info.st_mode) or info.st_size > 256 or stale(info.st_mtime):
            return None
        descriptor = os.open(answer, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        with os.fdopen(descriptor, "rb") as stream:
            raw = stream.read(257)
        status = json.loads(raw.decode("utf-8"))
    except (OSError, ValueError):
        return None
    if isinstance(status, str) and BUSY_ANSWER.fullmatch(status):
        return status
    return None


def claim_quit(lib: Application) -> tuple[int, int]:
    """Set the library quitting when no run or review is in flight, in the same critical section
    as the check, so no Start or review can begin between the check and the stop. Returns the
    runs and reviews in flight; quitting is left unset when there is any."""
    with lib.lock:
        runs, reviews = len(lib.active_jobs), lib.reviews
        lib.quitting = runs == 0 and reviews == 0  # From here no review or Start begins.
        return runs, reviews


def answer_quit_request(lib: Application) -> bool:
    """Act on a quit request in the state folder, if there is one, and report whether the library
    is stopping for it. Nothing is done while other users can write to the folder. A request that
    is stale, or not a plain file private to this user, is removed unread (a link is removed,
    never followed). With a run or review in flight the library keeps running and answers
    "busy: ..."; otherwise it stops. A discovery or workspace change in progress defers the
    request to the next poll, so the index and settings are never cut off mid-write."""
    state = lib.loc.state
    request = state / QUIT_REQUEST
    try:
        info = os.lstat(request)
        private_folder(state)
    except OSError:
        return False  # No request, or a folder that is not private: leave everything as it is.
    if not owner_only(info) or stale(info.st_mtime):
        try:
            remove(request)
        except OSError:
            return False  # Retried every poll, so not logged each time (Go: only on success).
        log.info("Removed a stale or invalid quit request unread")
        return False
    if not lib.refreshing.acquire(blocking=False):
        return False
    runs, reviews = claim_quit(lib)
    if runs > 0 or reviews > 0:
        lib.refreshing.release()
        status = f"busy: {count(runs, 'run')}, {count(reviews, 'review')}"
        try:
            save_json(state / QUIT_ANSWER, status)
        except OSError as error:
            log.warning("Quit request answer: %s", error)
        discard(request)
        log.info("A new launch asked the library to quit; it keeps running (%s)", status)
        return False
    discard(request)
    log.info("A new launch asked the idle library to quit; stopping")
    lib.stop()
    return True  # lib.refreshing stays held: no discovery starts while the library stops.


def hold_refreshing(lib: Application) -> bool:
    """Take lib.refreshing for a discovery or workspace change. After an idle quit it stays held
    for good, so a waiter gives up (False) once the library is quitting."""
    while not lib.refreshing.acquire(timeout=0.05):
        if lib.quitting:
            return False
    return True


def watch_quit_requests(lib: Application, stopped: Callable[[], bool], every: float) -> None:
    """Answer quit requests, looking every interval, until stopped() or the library stops for
    one."""
    while not stopped():
        time.sleep(every)
        if not stopped() and answer_quit_request(lib):
            return


def private_folder(state: Path) -> None:
    """Raise OSError unless state is a folder of this user's that no other user can write to."""
    if sys.platform == "win32":
        windows_private_folder(state)
        return
    info = os.stat(state)
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid():
        raise OSError(f"the state folder {state} does not belong to this user")
    if info.st_mode & 0o022:
        raise OSError(f"other users can write to the state folder {state}")


def windows_private_folder(state: Path) -> None:
    """Raise OSError unless only this user, SYSTEM and Administrators may write to the folder,
    according to its access-control list (permission bits do not describe access on Windows).
    The per-user local application data folder is private this way by default."""
    if sys.platform != "win32":
        raise OSError("the Windows access list is read on Windows only")
    advapi, kernel = ctypes.WinDLL("advapi32"), ctypes.WinDLL("kernel32")
    # Without argtypes ctypes converts a Python int as a 32-bit C long on Windows, and the 64-bit
    # pseudo handle from GetCurrentProcess raises ArgumentError (not OSError). So every Win32
    # function called here declares both its argument and its result types.
    pointer, dword, handle = ctypes.c_void_p, wintypes.DWORD, wintypes.HANDLE
    kernel.GetCurrentProcess.argtypes = []
    kernel.GetCurrentProcess.restype = handle
    kernel.CloseHandle.argtypes = [handle]
    kernel.CloseHandle.restype = wintypes.BOOL
    kernel.LocalFree.argtypes = [pointer]
    kernel.LocalFree.restype = pointer
    advapi.GetNamedSecurityInfoW.argtypes = [
        wintypes.LPCWSTR,
        ctypes.c_int,
        dword,
        pointer,
        pointer,
        ctypes.POINTER(pointer),
        pointer,
        ctypes.POINTER(pointer),
    ]
    advapi.GetNamedSecurityInfoW.restype = dword
    advapi.OpenProcessToken.argtypes = [handle, dword, ctypes.POINTER(handle)]
    advapi.OpenProcessToken.restype = wintypes.BOOL
    advapi.GetTokenInformation.argtypes = [
        handle,
        ctypes.c_int,
        pointer,
        dword,
        ctypes.POINTER(dword),
    ]
    advapi.GetTokenInformation.restype = wintypes.BOOL
    advapi.GetLengthSid.argtypes = [pointer]
    advapi.GetLengthSid.restype = dword
    dacl, descriptor = pointer(), pointer()
    # GetNamedSecurityInfoW(name, SE_FILE_OBJECT, DACL_SECURITY_INFORMATION, ...)
    result = advapi.GetNamedSecurityInfoW(
        str(state), 1, 4, None, None, ctypes.byref(dacl), None, ctypes.byref(descriptor)
    )
    if result != 0:
        raise OSError(
            f"the state folder's permissions cannot be read: {ctypes.FormatError(result).strip()}"
        )
    try:
        if dacl.value is None:  # A null DACL gives everyone full access.
            raise OSError(f"everyone can write to the state folder {state}")
        size = int.from_bytes(ctypes.string_at(dacl.value, 4)[2:], "little")
        acl = ctypes.string_at(dacl.value, size)
    finally:
        kernel.LocalFree(descriptor)
    token = handle()
    # OpenProcessToken(process, TOKEN_QUERY, &token)
    if not advapi.OpenProcessToken(kernel.GetCurrentProcess(), 8, ctypes.byref(token)):
        raise ctypes.WinError()
    try:
        needed = dword()
        advapi.GetTokenInformation(token, 1, None, 0, ctypes.byref(needed))
        buffer = ctypes.create_string_buffer(needed.value)
        # GetTokenInformation(token, TokenUser, ...): the TOKEN_USER starts with the SID pointer.
        if not advapi.GetTokenInformation(token, 1, buffer, needed.value, ctypes.byref(needed)):
            raise ctypes.WinError()
        sid = ctypes.cast(buffer, ctypes.POINTER(pointer))[0]
        user = ctypes.string_at(sid, advapi.GetLengthSid(sid))
    finally:
        kernel.CloseHandle(token)
    trusted = [user, SID_SYSTEM, SID_ADMINISTRATORS, SID_CREATOR_OWNER, SID_OWNER_RIGHTS]
    if others_may_write(acl, trusted):
        raise OSError(f"other users can write to the state folder {state}")


def owner_only(info: os.stat_result) -> bool:
    """Whether info describes a plain file of this user's that only they can read or write, as a
    relaunch creates its quit request. On Windows, a plain file (not a link or other reparse
    point): its access comes from the state folder, which private_folder has checked."""
    if sys.platform == "win32":
        reparse = 0x400  # FILE_ATTRIBUTE_REPARSE_POINT
        return stat.S_ISREG(info.st_mode) and not info.st_file_attributes & reparse
    return stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid() and not info.st_mode & 0o077


def others_may_write(acl: bytes, trusted: Sequence[bytes]) -> bool:
    """Whether a Windows access-control list, as stored (an 8-byte header, then its entries),
    grants FOLDER_WRITE_RIGHTS to any SID not in trusted. A deny entry grants nothing. An allow
    entry of another kind (callback, object) is not judged here and a malformed list is not
    trusted, so both count as writable by others."""
    if len(acl) < 8:
        return True
    entries = acl[8:]
    for _ in range(int.from_bytes(acl[4:6], "little")):
        if len(entries) < 4:
            return True
        kind, size = entries[0], int.from_bytes(entries[2:4], "little")
        if size < 4 or size > len(entries):
            return True
        entry, entries = entries[:size], entries[size:]
        if kind == 1:  # ACCESS_DENIED_ACE_TYPE
            continue
        # ACCESS_ALLOWED_ACE_TYPE: the 4-byte header, the access mask, then the SID.
        if kind != 0 or size < 16 or size < 16 + 4 * entry[9]:
            return True
        sid = entry[8 : 16 + 4 * entry[9]]
        if int.from_bytes(entry[4:8], "little") & FOLDER_WRITE_RIGHTS and sid not in trusted:
            return True
    return False
