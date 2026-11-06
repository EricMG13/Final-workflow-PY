"""S08 review regressions: inline-XBRL period lines appended to staged HTML text.

The TDG comparison is against retained evidence (runs/tdg-003 source preparation, an earlier
run's staged text of the same public filings), not against production output."""

from pathlib import Path

import pytest

from deploy_vii.preparation import text_content
from deploy_workflow.inline_xbrl import parse, period_lines
from deploy_workflow.run_inputs import CaseSource, RunInputError, SourceUnreadable, _case_files

ROOT = Path(__file__).resolve().parents[1]
HEAD = (b'<html><head><meta charset="%s"></head><body><div style="display:none">'
        b"<ix:header><ix:resources>")
END = b"</ix:resources></ix:header></div>"
CONTEXT = (b'<xbrli:context id="c1"><xbrli:entity><xbrli:identifier scheme="http://www.sec.gov/CIK">'
           b"0001</xbrli:identifier></xbrli:entity><xbrli:period>%s</xbrli:period></xbrli:context>")
DURATION = b"<xbrli:startDate>2024-01-01</xbrli:startDate><xbrli:endDate>2024-12-31</xbrli:endDate>"


def _doc(body: bytes, *, period: bytes = DURATION, charset: bytes = b"utf-8") -> bytes:
    return HEAD % charset + CONTEXT % period + END + body + b"</body></html>"


def _staged(raw: bytes) -> bytes:
    files, _ = _case_files([CaseSource("s1", Path("x.html"), "text/html")], [raw])
    return files[0].data


def test_period_lines_follow_the_text_without_an_empty_span():
    data = _staged(_doc(b"<p>Revenue 1,234</p><p>Net income 56</p>"))
    assert data == (
        b"Revenue 1,234\nNet income 56\n"
        b"XBRL context c1; entity 0001; scheme http://www.sec.gov/CIK; "
        b"duration 2024-01-01 through 2024-12-31\n"
    )
    assert [span.text for span in text_content(data).spans if not span.text.strip()] == []


def test_only_dimensional_contexts_append_nothing():
    segment = (b"<xbrli:segment><xbrldi:explicitMember dimension='d'>m</xbrldi:explicitMember>"
               b"</xbrli:segment>")
    raw = _doc(b"<p>Revenue 1,234</p>", period=b"<xbrli:instant>2024-12-31</xbrli:instant>")
    raw = raw.replace(b"</xbrli:identifier>", b"</xbrli:identifier>" + segment)
    assert _staged(raw) == b"Revenue 1,234\n"


def test_windows_1252_filing_is_staged_like_convert_html():
    raw = _doc(b"<p>Revenue \x96 caf\xe9 1,234</p>", charset=b"windows-1252")
    assert _staged(raw).decode("utf-8").splitlines() == [
        "Revenue – café 1,234",
        (
            "XBRL context c1; entity 0001; scheme http://www.sec.gov/CIK; "
            "duration 2024-01-01 through 2024-12-31"
        ),
    ]


def test_a_fact_without_an_id_does_not_refuse_the_source():
    fact = b'<p><ix:nonFraction name="us-gaap:Revenues" contextRef="c1" unitRef="usd">1</ix:nonFraction></p>'
    assert _staged(_doc(fact)).startswith(b"1\nXBRL context c1;")


@pytest.mark.parametrize("raw,reason", [
    (_doc(b"<p>x</p>").replace(b"</xbrli:context>", b"</xbrli:context>" + CONTEXT % DURATION),
     "duplicate source context id"),
    (_doc(b"<p>x</p>", period=b"<xbrli:startDate>2024-01-01</xbrli:startDate>"),
     "only one of its dates"),
    (_doc(b"<p>x</p>", period=b"<xbrli:instant>2024-02-30</xbrli:instant>"), "is not a date"),
])
def test_malformed_contexts_are_a_named_refusal(raw, reason):
    with pytest.raises(SourceUnreadable, match=reason) as refused:
        _staged(raw)
    assert isinstance(refused.value, RunInputError)
    assert "x.html" in str(refused.value)


def test_a_half_duration_is_refused_not_unspecified():
    with pytest.raises(ValueError, match="c1 has a duration with only one of its dates"):
        parse(_doc(b"", period=b"<xbrli:endDate>2024-12-31</xbrli:endDate>"))


@pytest.mark.parametrize("scale", [b' scale="six"', b" scale"])
def test_a_bad_fact_scale_is_a_value_error(scale):
    fact = (b'<p><ix:nonFraction id="f1" name="us-gaap:Revenues" contextRef="c1" unitRef="usd"'
            + scale + b">1</ix:nonFraction></p>")
    with pytest.raises(ValueError, match="inline fact f1 has scale"):
        parse(_doc(fact))
    assert period_lines(parse(_doc(fact), facts=False))[0].startswith("XBRL context c1;")


@pytest.mark.parametrize("name", [
    "TDG_2024-12-28_10-Q_0001260221-25-000014_tdg-20241228",
    "TDG_2024-09-30_10-K_0001260221-24-000083_tdg-20240930",
])
def test_tdg_staged_text_matches_the_retained_tdg_003_preparation(name):
    raw = (ROOT / "data/public-corpus/v1/TDG" / f"{name}.htm").read_bytes()
    retained = ROOT / "runs/tdg-003/source-preparation" / f"{name}.txt"
    assert _staged(raw) == retained.read_bytes()
