"""Where the application keeps its state on each OS, and how it reaches the person at the desk."""

from __future__ import annotations

import ctypes
import os
import sys
import webbrowser
from pathlib import Path

from .settings import Locations

LOCAL_APP_DATA = "{F1B32785-6FBA-4FCF-9D55-7B8E7F157091}"
PROGRAM_DATA = "{62AB5D82-FDC1-4DC3-A9DD-070D1D495D97}"
DOCUMENTS = "{FDD39AD0-238F-46AF-ADB4-6C85480369C7}"
# CREATE_NO_WINDOW: a worker never opens a console beside the browser.
WORKER_FLAGS = 0x08000000 if os.name == "nt" else 0
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
STILL_ACTIVE = 259
ERROR_ACCESS_DENIED = 5


def known_folder(identifier: str) -> Path:
    """A Windows known folder, honouring folder redirection, through SHGetKnownFolderPath."""
    windll = ctypes.windll  # type: ignore[attr-defined]
    guid = (ctypes.c_ubyte * 16)()
    if windll.ole32.CLSIDFromString(identifier, ctypes.byref(guid)):
        raise OSError(f"Windows known folder identifier is invalid: {identifier}")
    pointer = ctypes.c_wchar_p()
    result = windll.shell32.SHGetKnownFolderPath(ctypes.byref(guid), 0, None, ctypes.byref(pointer))
    if result:
        raise OSError(f"Windows known folder lookup failed: 0x{result & 0xFFFFFFFF:x}")
    try:
        return Path(pointer.value or "")
    finally:
        windll.ole32.CoTaskMemFree(pointer)


def platform_locations() -> Locations:
    if os.name == "nt":
        local = known_folder(LOCAL_APP_DATA)
        common = known_folder(PROGRAM_DATA)
        return Locations(
            state=local / "FinalWorkflow" / "IssuerLibrary",
            documents=known_folder(DOCUMENTS),
            policy=common / "FinalWorkflow" / "IssuerLibrary" / "settings.json",
        )
    home = Path.home()
    if sys.platform == "darwin":
        config = home / "Library" / "Application Support"
    else:
        config = Path(os.environ.get("XDG_CONFIG_HOME") or home / ".config")
    return Locations(state=config / "FinalWorkflow" / "IssuerLibrary", documents=home / "Documents")


def windows_process_alive(pid: int) -> bool:
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)  # type: ignore[attr-defined]
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return bool(ctypes.get_last_error() == ERROR_ACCESS_DENIED)  # type: ignore[attr-defined]
    try:
        code = ctypes.c_ulong()
        return not kernel32.GetExitCodeProcess(handle, ctypes.byref(code)) or (
            code.value == STILL_ACTIVE
        )
    finally:
        kernel32.CloseHandle(handle)


def process_alive(pid: int) -> bool:
    """Whether a process with this id exists; one this user may not inspect counts as alive."""
    if pid <= 0:
        return False
    if os.name == "nt":
        return windows_process_alive(pid)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def open_browser(url: str) -> None:
    if not webbrowser.open(url):
        raise OSError("no browser could be started")


def show_error(message: str) -> None:
    if os.name == "nt":
        windll = ctypes.windll  # type: ignore[attr-defined]
        windll.user32.MessageBoxW(None, message, "Issuer Library", 0x10)
        return
    print(message, file=sys.stderr)
