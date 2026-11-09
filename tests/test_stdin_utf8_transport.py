"""S02-C02: a non-UTF-8 byte on the owner JSON-lines transport is answered, not a crash."""

import io
import json

import pytest
from test_financial_workflow import make_pack

from deploy_workflow.owner_workflow import OwnerWorkflow, serve_json_lines


# Expected (hand-derived): the line that cannot be decoded is answered bad_arguments and the
# stream ends. A TextIOWrapper decodes in chunks, so a bad byte on line 2 already fails the
# readline for line 1; both raw inputs therefore get exactly one bad_arguments answer.
@pytest.mark.parametrize(
    "raw",
    [b'\xff{"operation":"nope"}\n', b'{"operation":"nope"}\n{"operation":"\xff"}\n'],
)
def test_non_utf8_line_is_answered_bad_arguments(tmp_path, raw):
    workflow = OwnerWorkflow.create(
        tmp_path / "store", make_pack(), publication_directory=tmp_path / "model"
    )
    out = io.StringIO()
    serve_json_lines(
        workflow,
        io.TextIOWrapper(io.BytesIO(raw), encoding="utf-8"),
        out,
        destination=tmp_path / "r.json",
        participant="p",
    )
    assert [json.loads(x) for x in out.getvalue().splitlines()] == [
        {"status": "refused", "error_code": "bad_arguments"}
    ]


class _Pipe(io.RawIOBase):
    """A participant's pipe that hands over one line per read, as an interactive participant who
    waits for each answer does (a BytesIO hands over everything in one chunk)."""

    def __init__(self, lines: list[bytes]) -> None:
        self._lines = list(lines)

    def readable(self) -> bool:
        return True

    def readinto(self, buffer) -> int:  # type: ignore[no-untyped-def,override]
        if not self._lines:
            return 0
        line = self._lines.pop(0)
        buffer[: len(line)] = line
        return len(line)


def test_lines_before_a_bad_line_are_answered_and_the_stream_ends_at_it(tmp_path):
    # Review of S02-C02. Expected (hand-derived): line 1 is a well-formed request for an unknown
    # operation, answered not_permitted before line 2 is read; line 2 cannot be decoded, so it is
    # answered bad_arguments and the stream ends; line 3 is never read or answered.
    workflow = OwnerWorkflow.create(
        tmp_path / "store", make_pack(), publication_directory=tmp_path / "model"
    )
    out = io.StringIO()
    lines = [b'{"operation":"nope"}\n', b'{"operation":"\xff"}\n', b'{"operation":"nope"}\n']
    reader = io.TextIOWrapper(io.BufferedReader(_Pipe(lines)), encoding="utf-8")
    serve_json_lines(workflow, reader, out, destination=tmp_path / "r.json", participant="p")
    assert [json.loads(x) for x in out.getvalue().splitlines()] == [
        {"status": "refused", "error_code": "not_permitted"},
        {"status": "refused", "error_code": "bad_arguments"},
    ]


# Followups of S02-C02: the source (workflow) and financial servers answer a non-UTF-8 line too.
def _servers(tmp_path):
    from test_financial_workflow import start
    from test_source_workflow import make_pack as source_pack

    from deploy_workflow import financial_workflow, owner_workflow, workflow

    source = workflow.SourceWorkflow.create(tmp_path / "source-store", source_pack())
    financial, _ = start(tmp_path)
    owner = OwnerWorkflow.create(
        tmp_path / "owner-store", make_pack(), publication_directory=tmp_path / "model"
    )
    return {
        "source": (workflow, source),
        "financial": (financial_workflow, financial),
        "owner": (owner_workflow, owner),
    }


def _serve(tmp_path, kind, lines):
    module, instance = _servers(tmp_path)[kind]
    out = io.StringIO()
    raw = io.BytesIO(b"".join(lines)) if len(lines) == 1 else io.BufferedReader(_Pipe(lines))
    reader = io.TextIOWrapper(raw, encoding="utf-8")
    module.serve_json_lines(instance, reader, out, destination=tmp_path / "r.json", participant="p")
    return [json.loads(x) for x in out.getvalue().splitlines()]


_BAD = {"status": "refused", "error_code": "bad_arguments"}
_NOPE = {"status": "refused", "error_code": "not_permitted"}


@pytest.mark.parametrize("kind", ["source", "financial"])
def test_bad_line_after_a_good_one_is_answered_after_it(tmp_path, kind):
    # Expected (hand-derived): line 1 is an unknown operation -> not_permitted, answered first;
    # line 2 is not UTF-8 -> bad_arguments and the stream ends; line 3 is never read.
    lines = [b'{"operation":"nope"}\n', b'{"operation":"\xff"}\n', b'{"operation":"nope"}\n']
    assert _serve(tmp_path, kind, lines) == [_NOPE, _BAD]


@pytest.mark.parametrize("kind", ["source", "financial"])
def test_bad_line_alone_is_answered_once(tmp_path, kind):
    assert _serve(tmp_path, kind, [b'\xff{"operation":"nope"}\n']) == [_BAD]


@pytest.mark.parametrize("kind", ["source", "financial"])
def test_overlong_line_with_bad_tail_is_answered_once(tmp_path, kind):
    # Expected: the over-length line (10 bytes past MAX_LINE of valid text, then a bad byte) gets
    # one bad_arguments answer, not two; the stream ends at the undecodable byte. The bad byte is in
    # the 8 KiB chunk the first read decodes, so the first read meets it (the drain case is below).
    from deploy_workflow import financial_workflow, workflow

    module = {"source": workflow, "financial": financial_workflow}[kind]
    line = b"a" * (module.MAX_LINE + 10) + b"\xff\n"
    assert _serve(tmp_path, kind, [line]) == [_BAD]


@pytest.mark.parametrize("kind", ["source", "financial"])
def test_bom_line_and_paired_surrogate_are_not_decode_errors(tmp_path, kind):
    # Expected: a BOM or an astral character (a valid pair, U+1F600) is valid UTF-8, so each line is
    # parsed normally: the BOM line is not JSON -> bad_arguments; the astral line is an unknown
    # operation -> not_permitted. A \ud800 escape is plain ASCII on the wire and also not an error.
    lines = [
        b'\xef\xbb\xbf{"operation":"nope"}\n',
        '{"operation":"\U0001f600"}\n'.encode(),
        b'{"operation":"\\ud800"}\n',
    ]
    assert _serve(tmp_path, kind, lines) == [_BAD, _NOPE, _NOPE]


@pytest.mark.parametrize("kind", ["source", "financial", "owner"])
def test_bad_byte_met_while_reading_on_past_the_limit_ends_the_stream(tmp_path, kind):
    # Review of the followups. The bad byte sits two text-reader chunks past the first read, so it
    # is met while the rest of the over-length line is read (the drain). Expected (hand-derived):
    # the line is answered bad_arguments once and the stream ends; the over-length line's own last
    # piece, {"operation":"nope"} opening a new chunk, and the whole line after it are never
    # answered. Before the review the reader went on at an unknown position and answered both
    # (not_permitted twice): the tail of a refused line was dispatched as a request.
    from deploy_workflow import financial_workflow, owner_workflow, workflow

    module = {"source": workflow, "financial": financial_workflow, "owner": owner_workflow}[kind]
    chunk = io.TextIOWrapper(io.BytesIO())._CHUNK_SIZE
    head = b"a" * (module.MAX_LINE + 2 * chunk + 5) + b"\xff"
    request = b'{"operation":"nope"}\n'
    stream = head + b"b" * (-len(head) % chunk) + request + request
    assert _serve(tmp_path, kind, [stream]) == [_BAD]
