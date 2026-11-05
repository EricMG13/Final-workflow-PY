"""OS file primitives used by the existing runner on Windows and Unix."""

from __future__ import annotations

import os
import stat
import time
from pathlib import Path

if os.name != "nt":
    import fcntl as locks
else:
    import msvcrt

    class _Locks:
        LOCK_SH, LOCK_EX, LOCK_NB, LOCK_UN = 1, 2, 4, 8

        @staticmethod
        def flock(file: int | object, operation: int) -> None:
            fd = file if isinstance(file, int) else file.fileno()
            position = os.lseek(fd, 0, os.SEEK_CUR)
            try:
                os.lseek(fd, 0, os.SEEK_SET)
                if operation & 8:
                    msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
                    return
                mode = msvcrt.LK_NBRLCK if operation & 1 else msvcrt.LK_NBLCK
                while True:
                    try:
                        msvcrt.locking(fd, mode, 1)
                        return
                    except OSError as error:
                        if error.errno not in (13, 36):
                            raise
                        if operation & 4:
                            raise BlockingIOError("run is locked") from error
                        time.sleep(0.05)
            finally:
                os.lseek(fd, position, os.SEEK_SET)

    locks = _Locks()


def replace(source: str | Path, target: str | Path) -> None:
    """os.replace, waiting out Windows refusing a file a scanner or another reader has open."""
    for remaining in range(39, -1, -1):
        try:
            os.replace(source, target)
            return
        except PermissionError:
            if not remaining:
                raise
            time.sleep(0.05)


def flags(*names: str) -> int:
    result = 0
    for name in names:
        result |= getattr(os, name, 0)
    return result


def fsync_directory(path: Path) -> None:
    # Windows cannot open a directory with os.open; regular file writes still fsync.
    if os.name == "nt":
        return
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def read_at(fd: int, count: int, offset: int) -> bytes:
    if hasattr(os, "pread"):
        return os.pread(fd, count, offset)
    position = os.lseek(fd, 0, os.SEEK_CUR)
    try:
        os.lseek(fd, offset, os.SEEK_SET)
        return os.read(fd, count)
    finally:
        os.lseek(fd, position, os.SEEK_SET)


def regular_open(path: Path, options: int, mode: int = 0o600) -> int:
    """Refuse a final symlink/reparse point; web uploads reside in a private job tree."""
    if os.name == "nt" and path.exists():
        before = path.lstat()
        if before.st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT:
            raise OSError("reparse points are not accepted")
    fd = os.open(path, options | flags("O_BINARY"), mode)
    if not stat.S_ISREG(os.fstat(fd).st_mode):
        os.close(fd)
        raise OSError("not a regular file")
    return fd
