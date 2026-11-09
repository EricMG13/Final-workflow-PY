"""Context form, the cases P added to context-embed.test.cjs (final-workflow dd3dfa18).

The Node suite loaded context-form.html in jsdom with stub layout and talked to it with `message`
events. Here the real page opens in Chromium (ContextForm in test_issuer_library_app.py, which also
holds the cases the earlier port covered), styles are read with getComputedStyle, and the date
input is the browser's own. Synthetic data only; nothing reaches a server or a provider.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest
from issuer_library_browser import ROOT, WEB, until
from test_issuer_library_app import ContextForm

pytestmark = pytest.mark.browser

SEND = (
    "(names,source=window)=>window.dispatchEvent(new MessageEvent('message',"
    "{source,data:{type:'cpos:names',names}}))"
)
INTRO = "Name the issuer so CP-0 can confirm it and the filings can be matched."
SOURCE = {"CP-0": "Source readiness"}
HOST = "document.querySelector('#sec2 .intro')"
TALK = [
    "tenor_years",
    "talk_spread_bps_low",
    "talk_spread_bps_high",
    "talk_oid_low",
    "talk_oid_high",
]


@pytest.fixture
def forms(browser: Any) -> Iterator[Callable[[], ContextForm]]:
    opened: list[ContextForm] = []

    def make() -> ContextForm:
        opened.append(ContextForm(browser))
        return opened[-1]

    yield make
    try:
        for each in opened:
            assert each.errors == []
    finally:
        for each in opened:
            each.page.context.close()


def send_names(form: ContextForm, names: Any) -> None:
    form.page.evaluate(
        f"n=>({SEND})(n)",
        names,
    )


def facility(form: ContextForm, values: dict[str, str]) -> None:
    form.page.evaluate("document.querySelector('[data-add=\"deal\"]').click()")
    for key, value in values.items():
        set_term(form, key, value)


def set_term(form: ContextForm, key: str, value: str) -> None:
    form.page.evaluate(
        "([k,v])=>{const f=document.getElementById('rows-deal').lastElementChild"
        '.querySelector(`[data-k="${k}"]`);f.value=v;'
        "f.dispatchEvent(new Event('input',{bubbles:true}));}",
        [key, value],
    )


def term(form: ContextForm, key: str, expression: str) -> Any:
    return form.page.evaluate(
        "k=>{const f=document.getElementById('rows-deal').lastElementChild"
        f'.querySelector(`[data-k="${{k}}"]`);return {expression};}}',
        key,
    )


def deal(form: ContextForm) -> dict[str, str]:
    row: dict[str, str] = form.submit()["context"]["deal_terms"][0]
    return row


def test_the_issue_classification_is_visible_after_the_issuer_id_required_unselected(
    forms: Callable[[], ContextForm],
) -> None:
    form = forms()
    facts = form.page.evaluate(
        """()=>{const d=document,box=d.getElementById('classf');
        const cards=d.querySelector('[data-cards="legal_documents"]');
        return {details:box.closest('details'),section:box.closest('section').id,
          after:box.previousElementSibling.contains(d.getElementById('s2-issuer_id')),
          inputs:[...box.querySelectorAll('input')].map(i=>[i.value,i.checked]),text:box.textContent,
          tag:box.querySelector('legend .rtag').textContent,
          legalTag:cards.closest('fieldset').querySelector('legend .rtag').textContent,
          legalChecked:d.querySelectorAll('input[name="legal_documents"]:checked').length,
          body:d.body.textContent,cards:cards.textContent};}"""
    )
    assert facts["details"] is None and facts["section"] == "sec2" and facts["after"]
    assert facts["inputs"] == [["investment_grade", False], ["high_yield", False]]
    assert "Investment grade" in facts["text"] and "High yield" in facts["text"]
    assert (
        "Classify by the debt this run analyses; for split-rated or unrated issuers use your "
        "firm's convention. The workflow's methods are written for high-yield and "
        "leveraged-loan credit."
    ) in facts["text"]
    assert facts["tag"] == "Required" and facts["legalTag"] == "Required"
    assert facts["legalChecked"] == 0
    assert not re.search(r"CP-4 refuses them today|draft mode|Planned\s*CP-4 draft", facts["body"])
    assert "Provisional" in facts["cards"]
    problems = form.submit()["problems"]
    assert any(p.startswith("Issue classification") and p.endswith("required.") for p in problems)
    assert any(p.startswith("Legal documents") and p.endswith("required.") for p in problems)


def test_a_saved_classification_and_facility_terms_load_back_into_the_form(
    forms: Callable[[], ContextForm], tmp_path: Path
) -> None:
    form = forms()
    saved = json.loads((ROOT / "cases/context/research-minimal.json").read_text("utf-8"))
    saved["identity"]["issue_classification"] = "high_yield"
    saved["run"]["run_type"] = "secondary"
    saved["run"]["pathway"] = "relative_value"
    keys = "facility_id instrument currency size_m tenor_years talk_spread_bps_low"
    keys += " talk_spread_bps_high"
    keys += " talk_oid_low talk_oid_high floor_pct coupon_pct margin_bps maturity call_protection"
    keys += " use_of_proceeds as_of provider"
    saved["deal_terms"] = [
        dict.fromkeys(keys.split(), "")
        | {"facility_id": "tlb", "instrument": "Term loan B", "currency": "USD", "size_m": "1250"}
        | {"coupon_pct": "8.25", "margin_bps": "350", "maturity": "2031-06-30"}
    ]
    form.load(tmp_path, json.dumps(saved))
    result = form.submit()
    assert result["problems"] == []
    assert result["context"]["identity"]["issue_classification"] == "high_yield"
    terms = result["context"]["deal_terms"][0]
    assert [terms["coupon_pct"], terms["margin_bps"], terms["maturity"]] == [
        "8.25",
        "350",
        "2031-06-30",
    ]
    assert "tenor and price talk" not in form.page.evaluate(
        "document.getElementById('loadmsg').textContent"
    )


def test_the_names_message_replaces_a_visible_module_code_with_its_name_keeping_a_title(
    forms: Callable[[], ContextForm],
) -> None:
    form = forms()
    assert form.page.evaluate(f"{HOST}.textContent") == INTRO
    send_names(form, SOURCE)
    assert (
        form.page.evaluate(f"{HOST}.textContent")
        == "Name the issuer so Source readiness can confirm it and the filings can be matched."
    )
    assert form.page.evaluate(f"{HOST}.title") == "CP-0"
    assert "CP-0" not in form.page.evaluate(
        "document.getElementById('s2-borrower_name-h').textContent"
    )


def test_a_code_with_no_name_stays_a_code_and_values_and_options_keep_codes(
    forms: Callable[[], ContextForm],
) -> None:
    form = forms()
    form.page.evaluate("document.querySelector('[data-add=\"q\"]').click()")
    send_names(form, SOURCE)
    assert "CP-1 looks" in form.page.evaluate(
        "document.getElementById('s2-borrower_name-h').textContent"
    )
    option = form.page.evaluate(
        "(()=>{const o=[...document.querySelectorAll('option')].find(o=>o.textContent==='CP-0');"
        "return o&&o.value})()"
    )
    assert option == "CP-0"


def test_names_apply_again_when_the_form_rewrites_its_own_text(
    forms: Callable[[], ContextForm],
) -> None:
    form = forms()
    send_names(form, SOURCE)
    form.page.evaluate(f"{HOST}.textContent='Ask CP-0 first.'")
    until(form.page, f"{HOST}.textContent==='Ask Source readiness first.'")


def test_the_names_message_is_ignored_from_another_source_or_with_a_non_string_value(
    forms: Callable[[], ContextForm],
) -> None:
    form = forms()
    texts = form.page.evaluate(
        f"""()=>{{const f=document.createElement('iframe');document.body.append(f);
        const send={SEND};
        const seen=[];const after=()=>seen.push({HOST}.textContent);
        send({{'CP-0':'Source readiness'}},f.contentWindow);after();
        send({{'CP-0':'Source readiness'}},null);after();
        send({{'CP-0':'Source readiness','CP-1':{{toString:()=>'x'}}}});after();
        send(null);send('CP-0');after();return seen;}}"""
    )
    assert texts == [INTRO] * 4
    send_names(form, SOURCE)
    assert form.page.evaluate(f"{HOST}.title") == "CP-0"


def test_a_name_is_written_as_text_never_markup(forms: Callable[[], ContextForm]) -> None:
    form = forms()
    send_names(form, {"CP-0": "<img src=x onerror=1>"})
    assert form.page.evaluate("document.querySelector('#sec2 .intro img')") is None
    assert "<img src=x onerror=1>" in form.page.evaluate(f"{HOST}.textContent")


def test_names_leave_the_emitted_context_json_unchanged(forms: Callable[[], ContextForm]) -> None:
    before, after = forms(), forms()
    for each in (before, after):
        each.set("s2-issuer_name", "Synthetic")
        each.set("s3-reporting_currency", "EUR")
    send_names(after, {"CP-0": "Source readiness", "CP-1": "Filing intake"})
    assert "Source readiness" in after.page.evaluate(f"{HOST}.textContent")
    assert json.dumps(after.submit()["context"]) == json.dumps(before.submit()["context"])


def test_the_date_help_names_the_picker_and_keeps_the_saved_format(
    forms: Callable[[], ContextForm],
) -> None:
    help_text = forms().page.evaluate("document.getElementById('s3-as_of-h').textContent")
    assert "Choose the date; it is saved as YYYY-MM-DD." in help_text
    assert "Format YYYY-MM-DD" not in help_text


STYLE = (
    "s=>{const c=getComputedStyle(document.querySelector(s));"
    "return [c.height,c.fontSize,c.borderRadius,c.backgroundColor,c.color,"
    "c.borderTopColor,c.textTransform];}"
)


def test_the_form_uses_the_app_look_40_px_fields_16_px_text_pills_and_file_button(
    forms: Callable[[], ContextForm],
) -> None:
    form = forms()
    css = (WEB / "context-embed.css").read_text(encoding="utf-8")
    for selector in ["#s2-issuer_name", "#s3-as_of"]:
        assert form.page.evaluate(STYLE, selector)[:3] == ["40px", "16px", "8px"]
    assert form.page.evaluate(STYLE, ".f select")[0] == "40px"
    assert re.search(r'\.f select \{[^}]*background-image:url\("data:image/svg\+xml', css)
    assert "::file-selector-button" in css
    required = form.page.evaluate(STYLE, ".rtag.req")
    assert required[3:5] == ["rgb(248, 249, 251)", "rgb(58, 64, 86)"]
    recommended = form.page.evaluate(STYLE, ".rtag.rec")
    assert recommended[3] == "rgba(0, 0, 0, 0)" and recommended[5] == "rgb(207, 211, 221)"
    assert re.search(r"\.tag\.def \{[^}]*background:#F8F9FB;[^}]*color:#3A4056", css)


def test_the_default_tag_is_the_grey_pill_and_the_form_text_sizes_are_13px_and_11px(
    forms: Callable[[], ContextForm],
) -> None:
    form = forms()
    assert form.page.evaluate("Boolean(document.querySelector('.tag.def'))"), (
        "a Default tag is shown"
    )
    assert form.page.evaluate("document.querySelector('.tag.def').textContent") == "Default"
    style = form.page.evaluate(STYLE, ".tag.def")
    assert style[6] == "none" and style[3:5] == ["rgb(248, 249, 251)", "rgb(58, 64, 86)"]
    assert style[2] == "999px"
    html = (WEB / "context-form.html").read_text(encoding="utf-8")
    css = (WEB / "context-embed.css").read_text(encoding="utf-8")
    assert "--rb-fs-body: 13px;" in html and "--rb-fs-micro: 11px;" in html
    assert not re.search(r"13\.5px|10\.5px", html)
    assert (
        ".tag.def { background:#F8F9FB; border:1px solid #E4E6EC; color:#3A4056; "
        "text-transform:none;" in html
    )
    assert ".badge-gray of screen.css" in html and ".badge-gray of screen.css" in css


def test_a_host_with_several_text_nodes_titles_all_their_codes_and_loses_the_title(
    forms: Callable[[], ContextForm],
) -> None:
    form = forms()
    form.page.evaluate(
        f"()=>{{const h={HOST};h.textContent='';"
        "h.append('Ask CP-0 then ',document.createElement('br'),'CP-2 after.');}"
    )
    send_names(form, {"CP-0": "Source readiness", "CP-2": "Review"})
    assert form.page.evaluate(f"{HOST}.textContent") == "Ask Source readiness then Review after."
    assert form.page.evaluate(f"{HOST}.title") == "CP-0, CP-2"
    form.page.evaluate(f"{HOST}.textContent='No codes here.'")
    until(form.page, f"!{HOST}.hasAttribute('title')")


def test_a_title_the_host_had_before_the_script_ran_is_never_overwritten_or_removed(
    forms: Callable[[], ContextForm],
) -> None:
    form = forms()
    form.page.evaluate(f"{HOST}.title='Their own'")
    send_names(form, SOURCE)
    assert form.page.evaluate(f"{HOST}.title") == "Their own"
    # A probe edited in the same task is renamed by the same pass that would have touched the title.
    form.page.evaluate(
        f"()=>{{const p=document.createElement('p');p.id='probe';document.body.append(p);"
        f"{HOST}.textContent='None.';p.textContent='Ask CP-0.';}}"
    )
    until(form.page, "document.getElementById('probe').textContent==='Ask Source readiness.'")
    assert form.page.evaluate(f"{HOST}.title") == "Their own"


def test_facility_rows_are_available_on_every_run_type_and_required_only_for_primary(
    forms: Callable[[], ContextForm],
) -> None:
    form = forms()
    form.set("s2-issuer_name", "Synthetic")
    form.declare()
    for run_type in ["secondary", "research", "primary", "earnings"]:
        form.pick(f"run_type-{run_type}")
        assert form.page.evaluate("document.getElementById('sec4').hidden") is False, run_type
        if run_type == "earnings":
            form.set("s3-current_period", "q3-2026")
            form.set("s3-prior_period", "q2-2026")
        problems = form.submit()["problems"]
        if run_type == "primary":
            assert len(problems) == 1 and re.search(r"add at least one facility row", problems[0])
        else:
            assert problems == [], run_type
    form.pick("run_type-primary")
    facility(form, {"facility_id": "tlb", "size_m": "1250"})
    assert form.submit()["problems"] == []


def test_coupon_margin_and_maturity_are_plain_non_negative_numbers_and_a_date(
    forms: Callable[[], ContextForm],
) -> None:
    form = forms()
    form.set("s2-issuer_name", "Synthetic")
    form.declare()
    form.pick("run_type-secondary")
    facility(
        form,
        {"facility_id": "tlb", "coupon_pct": "8.25", "margin_bps": "350", "maturity": "2031-06-30"},
    )
    result = form.submit()
    assert result["problems"] == []
    terms = result["context"]["deal_terms"][0]
    assert [terms["coupon_pct"], terms["margin_bps"], terms["maturity"]] == [
        "8.25",
        "350",
        "2031-06-30",
    ]
    for key, value in [("coupon_pct", "8.25%"), ("coupon_pct", "-1"), ("margin_bps", "350bps"),
                       ("margin_bps", "1,5"), ("coupon_pct", "1e3")]:  # fmt: skip
        was = term(form, key, "f.value")
        set_term(form, key, value)
        assert len(form.submit()["problems"]) == 1, f"{key} {value}"
        set_term(form, key, was)
    set_term(form, "maturity", "not a date")
    assert term(form, "maturity", "f.type + ':' + f.value") == "date:"
    for key in ["coupon_pct", "margin_bps", "maturity"]:
        set_term(form, key, "")
    result = form.submit()
    assert result["problems"] == []
    assert result["context"]["deal_terms"][0]["coupon_pct"] == ""
    assert result["context"]["deal_terms"][0]["maturity"] == ""


def test_switching_from_primary_to_secondary_blanks_the_hidden_talk_fields_before_build(
    forms: Callable[[], ContextForm],
) -> None:
    form = forms()
    form.set("s2-issuer_name", "Synthetic")
    form.declare()
    form.pick("run_type-primary")
    talk = {"tenor_years": "7", "talk_spread_bps_low": "325", "talk_spread_bps_high": "350"}
    talk |= {"talk_oid_low": "99.0", "talk_oid_high": "99.5"}
    facility(form, {"facility_id": "tlb", "size_m": "1250", "floor_pct": "0.50"} | talk)
    for key in TALK:
        assert deal(form)[key] != "", key
    form.pick("run_type-secondary")
    for key in TALK:
        assert term(form, key, "f.closest('.f').hidden") is True, key
    assert term(form, "size_m", "f.closest('.f').hidden") is False
    result = form.submit()
    assert result["problems"] == []
    for key in TALK:
        assert deal(form)[key] == "", key
    assert deal(form)["size_m"] == "1250" and deal(form)["floor_pct"] == "0.50"
    form.pick("run_type-primary")
    assert deal(form)["tenor_years"] == "7" and deal(form)["talk_oid_high"] == "99.5"


def test_an_invalid_value_in_a_hidden_talk_field_is_not_an_error_on_a_secondary_run(
    forms: Callable[[], ContextForm],
) -> None:
    form = forms()
    form.set("s2-issuer_name", "Synthetic")
    form.declare()
    form.pick("run_type-primary")
    facility(
        form,
        {
            "facility_id": "tlb",
            "talk_spread_bps_low": "400",
            "talk_spread_bps_high": "300",
            "tenor_years": "7%",
        },
    )
    assert len(form.submit()["problems"]) > 0
    form.pick("run_type-secondary")
    result = form.submit()
    assert result["problems"] == []
    assert result["context"]["deal_terms"][0]["talk_spread_bps_low"] == ""
