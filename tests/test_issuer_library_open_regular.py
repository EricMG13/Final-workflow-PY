"""`events.open_regular(name, dir_fd=...)` reads a regular file relative to a folder fd."""

from __future__ import annotations

import errno
import os
from pathlib import Path

import pytest

from issuer_library.events import open_regular

pytestmark = pytest.mark.skipif(
    os.open not in os.supports_dir_fd, reason="no dir_fd on this platform"
)


def folder_fd(path: Path) -> int:
    return os.open(path, os.O_RDONLY | os.O_DIRECTORY)


def test_reads_a_regular_file_by_name_under_the_fd(tmp_path):
    (tmp_path / "a.txt").write_bytes(b"hello")
    fd = folder_fd(tmp_path)
    try:
        with open_regular(Path("a.txt"), dir_fd=fd) as stream:
            assert stream.read() == b"hello"
    finally:
        os.close(fd)


def test_refuses_a_link_under_the_fd(tmp_path):
    (tmp_path / "real.txt").write_bytes(b"x")
    (tmp_path / "a.txt").symlink_to(tmp_path / "real.txt")
    fd = folder_fd(tmp_path)
    try:
        with pytest.raises(OSError) as err:
            open_regular(Path("a.txt"), dir_fd=fd)
        assert err.value.errno in (errno.ELOOP, errno.EMLINK)
    finally:
        os.close(fd)


def test_missing_name_is_file_not_found_and_a_fifo_is_refused(tmp_path):
    os.mkfifo(tmp_path / "pipe")
    fd = folder_fd(tmp_path)
    try:
        with pytest.raises(FileNotFoundError):
            open_regular(Path("none"), dir_fd=fd)
        with pytest.raises(OSError, match="not a regular file"):
            open_regular(Path("pipe"), dir_fd=fd)
    finally:
        os.close(fd)
