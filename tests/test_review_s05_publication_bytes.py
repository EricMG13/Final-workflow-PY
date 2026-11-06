"""S05 review: CP-MODEL's publication and the interface preview write the exact UTF-8 bytes
their receipts hash (a newline-translating text write, as on Windows, would not), and a
CP-MODEL publication whose finish fails leaves no receipt naming an unsettled head."""

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from deploy_vii import cp_model_workflow as cpm
from deploy_vii.execution import text_sha256
from deploy_vii.interface_view import _write_preview

PAGE = "<p>café</p>\n<p>two</p>\n"
CALCULATION = '{"a": 1}\n'


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@pytest.fixture
def windows_text(monkeypatch: pytest.MonkeyPatch) -> None:
    """`Path.write_text` as on Windows: newline=None writes each '\\n' as '\\r\\n'."""

    def write_text(self: Path, data: str, encoding: str | None = None, **_: Any) -> int:
        with self.open("w", encoding=encoding, newline="\r\n") as handle:
            return handle.write(data)

    monkeypatch.setattr(Path, "write_text", write_text)


@pytest.mark.usefixtures("windows_text")
def test_cp_model_files_are_the_hashed_bytes(tmp_path: Path) -> None:
    output = tmp_path / "model"
    cpm._write(output, {cpm.PAGE: PAGE, cpm.CALCULATION: CALCULATION})
    assert (output / cpm.PAGE).read_bytes() == PAGE.encode("utf-8")
    assert _sha((output / cpm.PAGE).read_bytes()) == text_sha256(PAGE)
    assert (output / cpm.CALCULATION).read_bytes() == b'{"a": 1}\n'


@pytest.mark.usefixtures("windows_text")
def test_interface_preview_receipt_hashes_the_bytes_on_disk(tmp_path: Path) -> None:
    destination = tmp_path / "preview"
    _write_preview(destination, {"tables.md": "# T\n\nrow\n"}, {"schema_version": "x"})
    written = (destination / "tables.md").read_bytes()
    assert written == b"# T\n\nrow\n"
    complete = json.loads((destination / "complete.json").read_bytes())
    assert complete == {"schema_version": "x", "files": {"tables.md": _sha(b"# T\n\nrow\n")}}
    assert b"\r" not in (destination / "complete.json").read_bytes()


class _Store:
    """begin/finish/interrupt/read of a journal whose finish refuses the inputs."""

    def __init__(self) -> None:
        self.interrupted: list[str] = []

    def begin(self, module_id: str) -> Any:
        return SimpleNamespace(ticket_id="t1", module_id=module_id)

    def finish(self, *_: object, **__: object) -> Any:
        raise ValueError("Inputs changed since the attempt began")

    def interrupt(self, ticket_id: str, reason: str) -> None:
        self.interrupted.append(reason)


def test_a_failed_finish_leaves_no_receipt(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    files = {cpm.PAGE: PAGE, cpm.CALCULATION: CALCULATION, cpm.RECEIPT: '{"head": "h"}\n'}
    monkeypatch.setattr(cpm, "_basis", lambda store: object())
    monkeypatch.setattr(cpm, "_prepare", lambda store, attempt, basis: ("{}", object(), files))
    store: Any = _Store()
    output = tmp_path / "model"
    with pytest.raises(cpm.CpModelRefused, match="Inputs changed since the attempt began"):
        cpm.publish_cp_model(store, output=output)
    assert store.interrupted == [
        "CP-MODEL publication failed: Inputs changed since the attempt began"
    ]
    assert sorted(p.name for p in output.iterdir()) == [cpm.CALCULATION, cpm.PAGE]


def test_a_journal_write_error_at_finish_leaves_no_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    files = {cpm.PAGE: PAGE, cpm.RECEIPT: '{"head": "h"}\n'}
    monkeypatch.setattr(cpm, "_basis", lambda store: object())
    monkeypatch.setattr(cpm, "_prepare", lambda store, attempt, basis: ("{}", object(), files))
    store: Any = _Store()

    def unavailable(*_: object, **__: object) -> None:
        raise OSError("journal write failed")

    store.finish = unavailable
    output = tmp_path / "model"
    with pytest.raises(OSError, match="journal write failed"):
        cpm.publish_cp_model(store, output=output)
    assert [p.name for p in output.iterdir()] == [cpm.PAGE]
