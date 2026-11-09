"""`Execution._atomic_write` survives Windows refusing a replace over a file another reader holds.

Windows raises PermissionError from `os.replace` while a scanner or a concurrent `read()` has the
target open (Python opens files without FILE_SHARE_DELETE). `platform_io.replace` waits that out;
the execution store's pointer and blob writes must use it, as `cpos_status` and the runner do.
"""

import os
from pathlib import Path

import pytest

from deploy_vii.execution import _atomic_write


def test_atomic_write_retries_a_replace_windows_refuses_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "current"
    target.write_bytes(b"old\n")
    real = os.replace
    calls: list[int] = []

    def refuse_first(source: str | Path, destination: str | Path) -> None:
        calls.append(1)
        if len(calls) == 1:
            raise PermissionError(13, "The process cannot access the file")
        real(source, destination)

    monkeypatch.setattr(os, "replace", refuse_first)
    _atomic_write(target, b"new\n")
    assert target.read_bytes() == b"new\n"
    assert len(calls) == 2
    assert sorted(p.name for p in tmp_path.iterdir()) == ["current"]  # no .tmp- file left behind
