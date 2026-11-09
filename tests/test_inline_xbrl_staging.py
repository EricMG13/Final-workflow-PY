"""Spec-valid inline XBRL stages without aborting the run; a malformed one is a typed refusal."""

from pathlib import Path

import pytest

from deploy_workflow.html_text import convert_html
from deploy_workflow.inline_xbrl import parse, period_lines
from deploy_workflow.run_inputs import CaseSource, SourceUnreadable, _case_files

_DOC = """<html xmlns:ix="http://www.xbrl.org/2013/inlineXBRL"><head>
<meta charset="{charset}"></head><body><div style="display:none"><ix:header><ix:resources>
<xbrli:context id="c1"><xbrli:entity>
<xbrli:identifier scheme="http://www.sec.gov/CIK">0000001</xbrli:identifier></xbrli:entity>
<xbrli:period><xbrli:startDate>{start}</xbrli:startDate>
<xbrli:endDate>2024-12-31</xbrli:endDate></xbrli:period></xbrli:context>
<xbrli:unit id="usd"><xbrli:measure>iso4217:USD</xbrli:measure></xbrli:unit>
</ix:resources></ix:header></div><p>Revenue {fact}</p></body></html>"""
_LINE = (
    "XBRL context c1; entity 0000001; scheme http://www.sec.gov/CIK; "
    "duration 2024-01-01 through 2024-12-31"
)


def _fact(attrs: str) -> str:
    return (
        f'<ix:nonFraction {attrs} name="us-gaap:Revenues" contextRef="c1" unitRef="usd" '
        'scale="6" format="ixt:num-dot-decimal">1,234</ix:nonFraction>'
    )


def _doc(*, charset: str = "utf-8", start: str = "2024-01-01", fact: str = "") -> str:
    return _DOC.format(charset=charset, start=start, fact=fact)


def test_fact_without_optional_id_is_kept_with_an_empty_id() -> None:
    document = parse(_doc(fact=_fact("")).encode())
    # 1,234 at scale 6 is 1,234,000,000 (hand-derived); the absent id stays absent, not invented.
    assert [(f.fact_id, f.amount()) for f in document.facts] == [("", 1234000000)]
    assert period_lines(document) == (_LINE,)


def test_duplicate_fact_id_still_refused() -> None:
    raw = _doc(fact=_fact('id="f1"') + _fact('id="f1"')).encode()
    with pytest.raises(ValueError, match="duplicate inline fact id"):
        parse(raw)


def test_declared_windows_1252_reads_the_same_text_as_convert_html() -> None:
    raw = _doc(charset="windows-1252", fact=_fact('id="f1"') + " company\x92s").encode("latin-1")
    assert "company’s" in convert_html(raw).text  # 0x92 is a right single quote in cp1252
    assert period_lines(parse(raw)) == (_LINE,)


def _stage(tmp_path: Path, raw: bytes) -> bytes:
    path = tmp_path / "filing.htm"
    path.write_bytes(raw)
    files, _ = _case_files([CaseSource("filing", path, "text/html")], [raw])
    return files[0].data


def test_staging_appends_context_dates_for_a_spec_valid_document(tmp_path: Path) -> None:
    raw = _doc(charset="windows-1252", fact=_fact("") + " company\x92s").encode("latin-1")
    assert _stage(tmp_path, raw).decode().endswith(f"\n\n{_LINE}\n")


def test_malformed_context_date_is_a_typed_refusal(tmp_path: Path) -> None:
    with pytest.raises(SourceUnreadable, match="inline XBRL"):
        _stage(tmp_path, _doc(start="2024-13-01").encode())


def test_several_facts_without_ids_are_all_kept() -> None:
    # Two id-less facts must not collide on the empty id; a duplicate refusal needs a real id.
    document = parse(_doc(fact=_fact("") + _fact("") + _fact('id="f1"')).encode())
    assert [f.fact_id for f in document.facts] == ["", "", "f1"]
    assert [f.amount() for f in document.facts] == [1234000000] * 3


def test_a_bom_with_a_declared_charset_reads_as_utf8_like_convert_html() -> None:
    raw = b"\xef\xbb\xbf" + _doc(charset="windows-1252", fact="company’s").encode("utf-8")
    assert "company’s" in convert_html(raw).text
    assert period_lines(parse(raw)) == (_LINE,)


def test_a_declared_charset_that_cannot_decode_is_a_value_error() -> None:
    # 0x81 is unassigned in windows-1252: convert_html and parse refuse it the same way.
    raw = _doc(charset="windows-1252", fact="x\x81").encode("latin-1")
    for read in (convert_html, parse):
        with pytest.raises(ValueError, match="windows-1252"):
            read(raw)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda d: d.replace('scale="6"', 'scale="six"'),
        lambda d: d.replace("<xbrli:entity>", '<xbrli:context id="inner"><xbrli:entity>', 1),
        lambda d: d.replace(
            '<xbrli:unit id="usd">', '<xbrli:unit id="usd"></xbrli:unit><xbrli:unit id="usd">'
        ),
    ],
)
def test_other_malformed_inline_xbrl_is_a_typed_refusal(tmp_path: Path, mutate) -> None:
    with pytest.raises(SourceUnreadable, match="inline XBRL"):
        _stage(tmp_path, mutate(_doc(fact=_fact('id="f1"'))).encode())
