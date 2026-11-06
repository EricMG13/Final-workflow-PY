"""S06 review fixes in delivery: one publish helper writes and hashes the same UTF-8 bytes,
and the page shell reads its assets as UTF-8 whatever the locale."""

import hashlib
import io
import json
import pathlib
from pathlib import Path
from typing import Any

import pytest
import test_connect_cp2d as tc

from deploy_vii import cp1_render, delivery, register_view, render
from deploy_vii.execution import Execution


def _windows_text_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    """``Path.write_text`` as Windows text mode does it: every newline becomes CRLF."""

    def write_text(self: Path, data: str, encoding: str | None = None, **_: Any) -> int:
        with open(self, "w", encoding=encoding, newline="\r\n") as stream:
            return stream.write(data)

    monkeypatch.setattr(pathlib.Path, "write_text", write_text)


def _on_disk(folder: Path) -> dict[str, str]:
    return {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(folder.iterdir())
        if path.name != "complete.json"
    }


def test_published_hashes_are_the_bytes_on_disk(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _windows_text_mode(monkeypatch)
    payloads = {"view.json": '{\n  "a": "∅ G1"\n}', "page.html": "<p>\n€\n</p>\n"}
    receipt = delivery.publish_bundle(tmp_path / "out", payloads, {"schema_version": "x/1"})
    complete = json.loads((tmp_path / "out" / "complete.json").read_bytes())
    assert complete == receipt
    assert receipt["files"] == _on_disk(tmp_path / "out")
    assert receipt["files"] == {
        "view.json": hashlib.sha256('{\n  "a": "∅ G1"\n}'.encode()).hexdigest(),
        "page.html": hashlib.sha256("<p>\n€\n</p>\n".encode()).hexdigest(),
    }
    assert b"\r\n" not in (tmp_path / "out" / "complete.json").read_bytes()
    assert list(receipt) == ["schema_version", "files"]


def test_the_receipt_cannot_be_a_payload(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="complete.json is the receipt"):
        delivery.publish_bundle(tmp_path / "out", {"complete.json": "{}"}, {})
    assert not (tmp_path / "out").exists()


def test_the_cp1_render_receipt_hashes_its_page_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = Execution.create(tmp_path / "store", tc.PACK)
    tc._settle(store, "CP-0")
    _windows_text_mode(monkeypatch)
    receipt = cp1_render.render_cp1_envelope(store, tmp_path / "no-envelope", tmp_path / "page")
    assert receipt["envelope"] == "refused"
    assert receipt["files"] == _on_disk(tmp_path / "page")
    assert list(receipt["files"]) == ["refused.html"]  # type: ignore[call-overload]
    assert json.loads((tmp_path / "page" / "complete.json").read_bytes()) == receipt


def test_every_bundle_writer_shares_the_one_helper() -> None:
    assert cp1_render.publish_bundle is register_view.publish_bundle is delivery.publish_bundle


def test_the_shell_reads_its_text_assets_as_utf8(monkeypatch: pytest.MonkeyPatch) -> None:
    asked: list[str | None] = []
    real = pathlib.Path.read_text

    def read_text(self: Path, encoding: str | None = None, errors: str | None = None) -> str:
        asked.append(encoding)
        if encoding is None:  # the locale's code page, cp1252 on Windows
            return io.TextIOWrapper(io.BytesIO(self.read_bytes()), encoding="cp1252").read()
        return real(self, encoding=encoding, errors=errors)

    monkeypatch.setattr(pathlib.Path, "read_text", read_text)
    shell = render._shell.__wrapped__()
    assert asked == ["utf-8"] * 5
    assert "∅" in shell.script and "â" not in shell.script
