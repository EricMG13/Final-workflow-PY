"""S10 review: both JSON-lines transports answer undecodable request bytes `bad_arguments`
(G7), both CLIs serve strict UTF-8 stdio, and the financial transport parses and faults as the
owner's does. Synthetic transport probes over a real (financial) or stub (owner) workflow; no
participant or model evidence."""

from __future__ import annotations

import importlib
import io
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from deploy_workflow import financial_workflow as fin
from deploy_workflow import owner_workflow as owner
from deploy_workflow.workflow import WorkflowError

fw: Any = importlib.import_module("test_financial_workflow")

BAD_ARGUMENTS = {"status": "refused", "error_code": "bad_arguments"}
# A short, terminated request whose quoted value is the byte 0xFF: not UTF-8.
UNDECODABLE = b'{"operation":"read_inputs","x":"\xff"}\n'


def _stub(root: Path) -> SimpleNamespace:
    return SimpleNamespace(
        _calls=[], _submissions=[], _reads=[], _session=None, _store=SimpleNamespace(directory=root)
    )


def _answers(serve: Any, workflow: Any, reader: Any, root: Path) -> list[dict[str, Any]]:
    out = io.StringIO()
    serve(workflow, reader, out, destination=root / "receipt.json", participant="probe")
    return [json.loads(line) for line in out.getvalue().splitlines()]


@pytest.mark.parametrize("serve", [owner.serve_json_lines, fin.serve_json_lines])
def test_an_undecodable_short_request_answers_bad_arguments(serve: Any, tmp_path: Path) -> None:
    reader = io.TextIOWrapper(io.BytesIO(UNDECODABLE), encoding="utf-8")  # strict
    assert _answers(serve, _stub(tmp_path), reader, tmp_path) == [BAD_ARGUMENTS]


@pytest.mark.parametrize("serve", [owner.serve_json_lines, fin.serve_json_lines])
def test_the_stream_continues_after_an_undecodable_request(serve: Any, tmp_path: Path) -> None:
    """The decoder's buffered chunk is lost with the error; the next chunk is served."""
    later = b'{"operation":"no_such_operation"}\n'
    raw = UNDECODABLE + b" " * (16 * 1024) + b"\n" + later
    reader = io.TextIOWrapper(io.BytesIO(raw), encoding="utf-8")
    answers = _answers(serve, _stub(tmp_path), reader, tmp_path)
    assert answers[0] == BAD_ARGUMENTS
    assert answers[-1] == {"status": "refused", "error_code": "not_permitted"}


@pytest.mark.parametrize("module", [owner, fin])
def test_main_serves_strict_utf8_stdio_whatever_the_locale(
    module: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A Windows pipe defaults to the ANSI code page (simulated here as cp1252)."""
    stdin = io.TextIOWrapper(io.BytesIO(), encoding="cp1252")
    stdout = io.TextIOWrapper(io.BytesIO(), encoding="cp1252")
    monkeypatch.setattr(sys, "stdin", stdin)
    monkeypatch.setattr(sys, "stdout", stdout)
    seen: list[tuple[str, str, str, str]] = []

    def serve(workflow: Any, reader: Any, writer: Any, **kwargs: Any) -> None:
        seen.append((reader.encoding, reader.errors, writer.encoding, writer.errors))

    pack = tmp_path / "pack.json"
    pack.write_bytes(fw.make_pack().model_dump_json().encode())
    monkeypatch.setattr(module, "serve_json_lines", serve)
    output = "--model-directory" if module is fin else "--publication-directory"
    argv = ["prog", "--directory", str(tmp_path / "store"), "--pack", str(pack)]
    argv += [output, str(tmp_path / "model"), "--receipt", str(tmp_path / "r.json")]
    monkeypatch.setattr(sys, "argv", [*argv, "--participant", "probe"])
    module.main()
    assert seen == [("utf-8", "surrogateescape", "utf-8", "strict")]


@pytest.mark.parametrize("serve", [owner.serve_json_lines, fin.serve_json_lines])
def test_undecodable_bytes_on_cli_stdin_lose_no_later_request(serve: Any, tmp_path: Path) -> None:
    """The stdin `main` serves (UTF-8, `surrogateescape`): the bad line alone is refused."""
    later = b'{"operation":"no_such_operation"}\n'
    reader = io.TextIOWrapper(
        io.BytesIO(UNDECODABLE + later), encoding="utf-8", errors="surrogateescape"
    )
    assert _answers(serve, _stub(tmp_path), reader, tmp_path) == [
        BAD_ARGUMENTS,
        {"status": "refused", "error_code": "not_permitted"},
    ]


def test_an_escaped_surrogate_is_still_the_hosts_to_refuse(tmp_path: Path) -> None:
    """Only raw undecodable-byte marks are refused by the line reader; a JSON escape is text."""
    line = '{"operation":"invoke","tool":"search_pack","arguments":{"query":"\\udcff"}}\n'
    workflow, _ = fw.start(tmp_path)
    (answer,) = _answers(fin.serve_json_lines, workflow, io.StringIO(line), tmp_path)
    assert (answer["status"], answer["error_code"]) == ("refused", "bad_arguments")
    assert answer["arguments"] == {}  # the host's refusal receipt, retained as a call
    assert len(workflow._calls) == 1


@pytest.mark.parametrize(
    "line",
    [
        '{"operation":"invoke","tool":"read_pages","arguments":{"x":1e999}}',
        '{"operation":"invoke","tool":"read_pages","arguments":{"x":-1e999}}',
        "[" * 200_000,
        '{"operation":"invoke","tool":"t","arguments":{"k":' + "[" * 300 + "]" * 300 + "}}",
    ],
    ids=["inf", "-inf", "recursion", "past-depth-bound"],
)
def test_financial_parser_refuses_what_the_owner_parser_refuses(line: str, tmp_path: Path) -> None:
    with pytest.raises(WorkflowError) as caught:
        owner._request_of(line)
    assert caught.value.code == "bad_arguments"
    workflow, _ = fw.start(tmp_path)
    assert _answers(fin.serve_json_lines, workflow, io.StringIO(line + "\n"), tmp_path) == [
        BAD_ARGUMENTS
    ]
    assert workflow._calls == []


def _faults(root: Path) -> list[dict[str, Any]]:
    directory = root / "store" / "financial-slice-audit" / "faults"
    return [json.loads(p.read_bytes()) for p in sorted(directory.iterdir())]


@pytest.mark.parametrize("error", [ValueError("internal x"), RuntimeError("internal y")])
def test_financial_internal_error_is_a_fault_and_ends_the_stream(
    error: Exception, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """G7 parity with the owner transport: not relabelled `bad_arguments`/`internal_error`."""
    workflow, _ = fw.start(tmp_path)

    def projection(*args: Any, **kwargs: Any) -> Any:
        raise error

    monkeypatch.setattr(fin, "_projection", projection)
    request = '{"operation":"read_inputs"}\n'
    out = io.StringIO()
    with pytest.raises(type(error)) as caught:
        fin.serve_json_lines(
            workflow,
            io.StringIO(request + request),
            out,
            destination=tmp_path / "receipt.json",
            participant="probe",
        )
    assert caught.value is error
    assert out.getvalue() == ""
    assert _faults(tmp_path) == [
        {
            "schema_version": "financial-fault/1",
            "code": "InternalError",
            "operation": "read_inputs",
            "error_type": type(error).__name__,
            "detail": str(error),
        }
    ]


def test_financial_refusals_are_not_faults(tmp_path: Path) -> None:
    workflow, _ = fw.start(tmp_path)
    answers = _answers(
        fin.serve_json_lines,
        workflow,
        io.StringIO('{"operation":"publish_model"}\n{"operation":"write_receipt"}\n'),
        tmp_path,
    )
    assert answers == [{"status": "refused", "error_code": "not_permitted"}] * 2
    assert not (tmp_path / "store" / "financial-slice-audit" / "faults").exists()


def test_financial_known_operation_with_extra_keys_is_bad_arguments(tmp_path: Path) -> None:
    workflow, _ = fw.start(tmp_path)
    line = '{"operation":"read_inputs","extra":1}\n'
    answers = _answers(fin.serve_json_lines, workflow, io.StringIO(line), tmp_path)
    assert answers == [BAD_ARGUMENTS]
