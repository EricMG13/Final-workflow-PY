"""The independent data-flow checker, over a synthetic two-module run in the real layout."""

import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "library_flow_check", ROOT / "apps/issuer-library/designs/flow_check.py"
)
flow = importlib.util.module_from_spec(spec)
spec.loader.exec_module(flow)

CP0 = "# CP-0\n\nRevenue was 7,940.0 and margin 12%.\n"
CP1 = "# CP-1\n\nLeverage (1,234) against 7,940 and 4.2x.\n"
SOURCE = "Revenue 7,940.0. Margin 12%. Leverage (1,234). Multiple 4.2x.\n"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def make_run(tmp_path: Path) -> tuple[Path, Path]:
    run, sources = tmp_path / "run", tmp_path / "issuer"
    sources.mkdir()
    (sources / "annual.txt").write_text(SOURCE)
    (run / "inputs").mkdir(parents=True)
    (run / "inputs" / sha(SOURCE.encode())).write_text(SOURCE)
    handoffs = {"CP-0": CP0, "CP-1": CP1}
    for module, text in handoffs.items():
        (run / f"requests/{module}/fp").mkdir(parents=True)
        (run / f"requests/{module}/fp/1.response.md").write_text(text)
        (run / "deliveries/d1").mkdir(parents=True, exist_ok=True)
        (run / f"deliveries/d1/{module}.md").write_text(text)
    modules = {m: f"requests/{m}/fp/1.response.md" for m in handoffs}
    (run / "completed-abc.json").write_text(
        json.dumps({"kind": "cpos-markdown-delivery/1", "modules": modules})
    )
    for module, upstream in (("CP-0", {}), ("CP-1", {"CP-0": CP0})):
        folder = run / "live/modules" / sha(module.encode())
        folder.mkdir(parents=True)
        request = {
            "module_id": module,
            "sources": {"annual.txt": sha(SOURCE.encode())},
            "handoffs": {
                u: {"sha256": sha(t.encode()), "markdown": t} for u, t in upstream.items()
            },
        }
        (folder / "0.request.json").write_text(
            json.dumps({"messages": [{}, {"text": json.dumps(request)}]})
        )
        tools = [{"call_id": "1", "name": "read_pages", "text": SOURCE}]
        tools.append({"call_id": "2", "name": "write_handoff", "text": "999,999"})
        (folder / "0.tools.json").write_text(json.dumps(tools))
        (folder / "1.draft.md").write_text(handoffs[module])
        (folder / "1.review.json").write_text(json.dumps({"issues": []}))
    return run, sources


def set_handoff(run: Path, module: str, text: str, *, draft: bool = True) -> None:
    """Replace a module's accepted handoff and its delivered copy; its draft follows by default."""
    (run / f"requests/{module}/fp/1.response.md").write_text(text)
    (run / f"deliveries/d1/{module}.md").write_text(text)
    if draft:
        (run / "live/modules" / sha(module.encode()) / "1.draft.md").write_text(text)


def add_calls(run: Path, module: str, calls: list[tuple[str, list[str], str]]) -> None:
    """Record calculate calls as the real layout does: the result in N.tools.json, the arguments in
    the assistant message of the next request."""
    folder = run / "live/modules" / sha(module.encode())
    tools = json.loads((folder / "0.tools.json").read_text())
    tools += [
        {"call_id": cid, "name": "calculate", "text": json.dumps({"value": out, "reason": None})}
        for cid, _, out in calls
    ]
    (folder / "0.tools.json").write_text(json.dumps(tools))
    assistant = {
        "role": "assistant",
        "tool_calls": [
            {
                "call_id": cid,
                "name": "calculate",
                "arguments": {"operation": "sum", "values": values},
            }
            for cid, values, _ in calls
        ],
    }
    (folder / "1.request.json").write_text(json.dumps({"messages": [{}, {}, assistant]}))


def test_numbers_normalises_and_ignores_digests_and_dates() -> None:
    assert flow.numbers("7,940.0") == {"7940"}
    assert flow.numbers("(1,234)") == {"1234"}
    assert flow.numbers("-3.50") == {"3.5"}
    assert flow.numbers("12%") == {"12"}
    assert flow.numbers("leverage 4.2x") == {"4.2"}
    assert (
        flow.numbers(
            "sha256 " + "ab12" * 16 + " on 2024-09-30 in report-v2.md and tdg-20240930.htm"
        )
        == set()
    )
    # Identifiers and lists are not quantities: run-20261105, a page list, a leading-zero label.
    assert flow.numbers("run-20261105 pp.38,54,106,109 OP01-02 057") == set()
    assert flow.numbers("1,198 | 1,057 and 2.5-3.0x") == {"1198", "1057", "2.5"}
    assert flow.numbers("see pp.3,105\u2013109,131,146 and p.35") == set()
    assert flow.numbers("sum(980,161)=1141 and Pp.52\u201354,106,109,142") == {"980", "161", "1141"}
    assert flow.numbers("as of 31 March 2025 and Mar 31, 2025 and 2,025") == {"2025"}
    assert flow.numbers("7 and 0.0 and 12") == {"12"}


def test_clean_synthetic_run_has_no_faults(tmp_path: Path) -> None:
    run, sources = make_run(tmp_path)
    assert flow.run_faults(run, sources) == []


def test_number_absent_from_what_the_module_read_is_a_fault(tmp_path: Path) -> None:
    run, sources = make_run(tmp_path)
    set_handoff(run, "CP-1", CP1 + "Planted 7,941.\n")
    faults = flow.run_faults(run, sources)
    assert len(faults) == 1 and "CP-1" in faults[0] and "7941" in faults[0]


def test_write_handoff_text_is_not_evidence(tmp_path: Path) -> None:
    run, sources = make_run(tmp_path)
    set_handoff(run, "CP-1", CP1 + "Only in the draft 999,999.\n")
    assert any("999999" in f for f in flow.run_faults(run, sources))


def test_upstream_hash_mismatch_is_a_fault(tmp_path: Path) -> None:
    run, sources = make_run(tmp_path)
    for file in (run / "live/modules").glob("*/0.request.json"):
        outer = json.loads(file.read_text())
        request = json.loads(outer["messages"][1]["text"])
        if request["module_id"] == "CP-1":
            request["handoffs"]["CP-0"]["sha256"] = "0" * 64
            outer["messages"][1]["text"] = json.dumps(request)
            file.write_text(json.dumps(outer))
    faults = flow.run_faults(run, sources)
    assert len(faults) == 1 and "CP-1" in faults[0] and "CP-0" in faults[0]


def test_source_hash_mismatch_is_a_fault(tmp_path: Path) -> None:
    run, sources = make_run(tmp_path)
    (sources / "annual.txt").write_text(SOURCE + "changed\n")
    (run / "inputs" / sha(SOURCE.encode())).unlink()
    faults = flow.run_faults(run, sources)
    assert faults and all("annual.txt" in f for f in faults)


def test_delivered_copy_that_differs_is_a_fault(tmp_path: Path) -> None:
    run, sources = make_run(tmp_path)
    (run / "deliveries/d1/CP-0.md").write_text(CP0 + "edited\n")
    faults = flow.run_faults(run, sources)
    assert len(faults) == 1 and "CP-0" in faults[0]


def test_report_number_not_in_handoffs_is_a_fault() -> None:
    faults = flow.report_faults("Revenue 7,941 and 7,940", [CP0, CP1])
    assert len(faults) == 1 and "7941" in faults[0]


def test_report_numbers_from_handoffs_pass() -> None:
    assert flow.report_faults("Revenue 7,940 margin 12% 2030", [CP0], "year 2030") == []


def test_main_exits_1_and_prints_count(tmp_path: Path, capsys) -> None:
    run, sources = make_run(tmp_path)
    assert flow.main([str(run), "--sources", str(sources)]) == 0
    assert "flow: 0 fault(s)" in capsys.readouterr().out
    (run / "deliveries/d1/CP-0.md").write_text("edited")
    assert flow.main([str(run), "--sources", str(sources)]) == 1
    assert "flow: 1 fault(s)" in capsys.readouterr().out


def test_superseded_attempt_is_not_checked_against_the_accepted_upstream(tmp_path: Path) -> None:
    run, sources = make_run(tmp_path)
    stale = run / "live/modules" / sha(b"stale")
    stale.mkdir()
    request = {
        "module_id": "CP-1",
        "sources": {},
        "handoffs": {"CP-0": {"sha256": "0" * 64, "markdown": "old"}},
    }
    (stale / "0.request.json").write_text(
        json.dumps({"messages": [{}, {"text": json.dumps(request)}]})
    )
    (stale / "0.tools.json").write_text("[]")
    (run / "live/modules" / sha(b"CP-1") / "1.draft.md").unlink()
    faults = flow.run_faults(run, sources)
    assert len(faults) == 1 and "not a draft the model submitted" in faults[0]
    (run / "live/modules" / sha(b"CP-1") / "1.draft.md").write_text(CP1)
    assert flow.run_faults(run, sources) == []  # the draft CP-1 was accepted from names its attempt


def test_rounded_long_results_cover_their_printed_roundings_only() -> None:
    long = "4.5068296189791516894320632638389647735"
    known = flow.rounded(flow.numbers(long))
    assert {"4.51", "4.507", "4.5068"} <= known
    assert "4.52" not in known and "4.6" not in known
    assert flow.rounded({"4.51"}) == {"4.51"}  # a reported two-decimal figure is not expanded
    assert flow.report_faults("ratio 4.51x and 4.52x", [long]) == [
        "report: number 4.52 is not in the handoffs or context"
    ]


def test_input_whose_contents_no_longer_match_its_hash_is_a_fault(tmp_path: Path) -> None:
    run, _ = make_run(tmp_path)
    with (run / "inputs" / sha(SOURCE.encode())).open("a") as handle:
        handle.write("x")
    faults = flow.run_faults(run)
    assert faults and all("annual.txt" in f for f in faults)


def test_unicode_minus_in_call_args_keeps_each_addend_checked() -> None:
    got = flow.numbers("sum(2456,18,999,1,\u221213)=3461")
    assert got - flow.numbers("2456 18 1 13 3461") == {"999"}
    assert "375" not in flow.numbers("2,045/1,375")  # no false figure from the digit-comma form


def test_unit_suffixes_are_stripped_not_truncated() -> None:
    assert flow.numbers("$12.6bn") == {"12.6"}
    assert flow.numbers("a $451m loan") == {"451"}
    assert flow.numbers("EUR 1,250.5mm and 40K and 5M") == {"1250.5", "40"}
    assert flow.numbers("12.6xyz 3.5.1") == set()


def test_written_dates_are_month_names_only_and_slugs_are_lowercase() -> None:
    assert flow.numbers("as of September 30, 2024 and 31 Mar. 2025") == set()
    assert flow.numbers("Facility 45, 7940 drawn") == {"45", "7940"}
    assert flow.numbers("across 3 Tranches 7940 drawn") == {"7940"}
    assert flow.numbers("Term Loan B-12 and EUR-1,250 and run-20261105") == {"12", "1250"}


def test_module_missing_from_an_existing_delivery_is_a_fault(tmp_path: Path) -> None:
    run, sources = make_run(tmp_path)
    (run / "deliveries/d1/CP-1.md").unlink()
    faults = flow.run_faults(run, sources)
    assert len(faults) == 1 and "CP-1" in faults[0] and "d1" in faults[0]


def test_manual_delivery_may_omit_a_module(tmp_path: Path) -> None:
    run, sources = make_run(tmp_path)
    record = next(run.glob("completed-*.json"))
    data = json.loads(record.read_text())
    record.write_text(json.dumps({**data, "kind": "cpos-handoff-snapshot/1"}))
    (run / "deliveries/d1/CP-0.md").unlink()
    assert flow.run_faults(run, sources) == []
    (run / "deliveries/d1/CP-1.md").write_text("edited")  # copies it does hold are still compared
    assert len(flow.run_faults(run, sources)) == 1


def test_corrupted_input_is_a_fault_and_not_evidence_even_with_a_good_sources_copy(
    tmp_path: Path,
) -> None:
    run, sources = make_run(tmp_path)
    (run / "inputs" / sha(SOURCE.encode())).write_text(SOURCE + "Planted 31,337.\n")
    set_handoff(run, "CP-1", CP1 + "Planted 31,337.\n")
    faults = flow.run_faults(run, sources)
    assert any("annual.txt" in f and "inputs" in f for f in faults)
    assert any("CP-1: number 31337" in f for f in faults)


def test_handoff_altered_after_the_model_wrote_it_is_a_fault(tmp_path: Path) -> None:
    run, sources = make_run(tmp_path)
    set_handoff(run, "CP-1", CP1.replace("against 7,940", "against 1,234"), draft=False)
    faults = flow.run_faults(run, sources)
    assert len(faults) == 1
    assert (
        "CP-1" in faults[0]
        and "not a draft the model submitted and the checker accepted" in faults[0]
    )


def test_handoff_equal_only_to_a_draft_with_open_review_issues_is_a_fault(tmp_path: Path) -> None:
    run, sources = make_run(tmp_path)
    review = run / "live/modules" / sha(b"CP-1") / "1.review.json"
    review.write_text(json.dumps({"issues": ["Use the current registry recipient role"]}))
    assert any("CP-1" in f and "not a draft" in f for f in flow.run_faults(run, sources))
    review.unlink()  # no review record: acceptance cannot be shown
    assert any("CP-1" in f and "not a draft" in f for f in flow.run_faults(run, sources))


def test_invented_operand_does_not_launder_a_calculate_result(tmp_path: Path) -> None:
    run, sources = make_run(tmp_path)
    add_calls(run, "CP-1", [("c1", ["5000", "2941"], "7941")])  # 2941 is nowhere
    set_handoff(run, "CP-1", CP1 + "Adjusted 7,941 (calculated).\n")
    faults = flow.run_faults(run, sources)
    assert len(faults) == 1 and "number 7941" in faults[0]


def test_calculate_over_evidenced_operands_is_evidence_and_chains(tmp_path: Path) -> None:
    run, sources = make_run(tmp_path)
    add_calls(
        run,
        "CP-1",
        [
            ("c1", ["7940", "1234"], "9174"),
            ("c2", ["9174", "1234"], "10408"),
            ("c3", ["10408", "7940"], "18348"),
        ],
    )
    set_handoff(run, "CP-1", CP1 + "Total 18,348 (calculated).\n")
    assert flow.run_faults(run, sources) == []
    add_calls(run, "CP-1", [("c4", ["18348", "777"], "19125")])  # 777 is nowhere: stops the chain
    set_handoff(run, "CP-1", CP1 + "Total 19,125.\n")
    assert any("number 19125" in f for f in flow.run_faults(run, sources))


def test_calculate_result_without_recorded_arguments_is_not_evidence(tmp_path: Path) -> None:
    run, sources = make_run(tmp_path)
    add_calls(run, "CP-1", [("c1", ["7940", "1234"], "9174")])
    (run / "live/modules" / sha(b"CP-1") / "1.request.json").unlink()
    set_handoff(run, "CP-1", CP1 + "Total 9,174.\n")
    assert any("number 9174" in f for f in flow.run_faults(run, sources))


def test_run_with_no_accepted_handoff_is_a_fault_and_exits_1(tmp_path: Path, capsys) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    assert flow.run_faults(empty) == [f"no accepted handoff found in {empty}"]
    assert flow.main([str(empty)]) == 1
    assert flow.main([str(tmp_path / "nope")]) == 1
    assert "flow: 1 fault(s)" in capsys.readouterr().out


def test_module_must_have_received_every_module_accepted_before_it(tmp_path: Path) -> None:
    run, sources = make_run(tmp_path)
    folder = run / "live/modules" / sha(b"CP-1")
    request = json.loads(json.loads((folder / "0.request.json").read_text())["messages"][1]["text"])
    request["handoffs"] = {}
    (folder / "0.request.json").write_text(
        json.dumps({"messages": [{}, {"text": json.dumps(request)}]})
    )
    faults = flow.run_faults(run, sources)
    assert (
        len(faults) == 1
        and "CP-1" in faults[0]
        and "CP-0" in faults[0]
        and "never received" in faults[0]
    )


def test_only_sources_the_requests_name_are_evidence(tmp_path: Path) -> None:
    run, sources = make_run(tmp_path)
    (sources / "_scratch.txt").write_text("working figure 31,337\n")
    set_handoff(run, "CP-1", CP1 + "Planted 31,337.\n")
    assert any("number 31337" in f for f in flow.run_faults(run, sources))
    assert any("number 31337" in f for f in flow.run_faults(run, None))


def test_converted_source_name_maps_to_its_original_file(tmp_path: Path) -> None:
    run, sources = make_run(tmp_path)
    (sources / "filing.htm").write_text("only in the filing 31,337\n")
    for file in (run / "live/modules").glob("*/0.request.json"):
        outer = json.loads(file.read_text())
        request = json.loads(outer["messages"][1]["text"])
        request["sources"]["filing.htm.jsonl"] = "0" * 64  # the converted copy the module was given
        outer["messages"][1]["text"] = json.dumps(request)
        file.write_text(json.dumps(outer))
    set_handoff(run, "CP-1", CP1 + "Planted 31,337.\n")
    faults = flow.run_faults(run, sources)
    assert not any("number 31337" in f for f in faults)


def test_edit_handoff_reply_is_not_evidence(tmp_path: Path) -> None:
    run, sources = make_run(tmp_path)
    folder = run / "live/modules" / sha(b"CP-1")
    tools = json.loads((folder / "0.tools.json").read_text())
    tools.append({"call_id": "e", "name": "edit_handoff", "text": "REJECTED\nFigure 7,941"})
    (folder / "0.tools.json").write_text(json.dumps(tools))
    set_handoff(run, "CP-1", CP1 + "Planted 7,941.\n")
    assert any("number 7941" in f for f in flow.run_faults(run, sources))


def test_thousands_figure_in_call_arguments_stays_whole() -> None:
    assert flow.numbers("sum(7,941)") == {"7941"}
    assert flow.numbers("ratio(7,941, 1,234)") == {"7941", "1234"}
    assert flow.numbers("sum(980,161)") == {"980", "161"}  # not the one figure 980161


def test_thousands_figures_in_a_call_written_with_comma_space_stay_whole() -> None:
    # Verbatim from a retained live CP-3 handoff: ", " separates the arguments.
    line = (
        "| Term loans/secured notes share of gross principal | ratio(19,702, 25,228); CP-1 C3 | "
        "0.78095766608530204534644046297764388774 | 0.780958 fraction; "
        "not percentage or recovery |"
    )
    got = flow.numbers(line)
    assert {"19702", "25228"} <= got
    assert not got & {"19", "702", "25", "228"}


def test_duration_word_glued_by_pdf_extraction_is_a_unit() -> None:
    # The sol-medium filing text reads "Operating leases ..... 5.4years".
    assert flow.numbers("lease term 5.4years and 18months, 30days") == {"5.4", "18", "30"}
    assert flow.numbers("12.6xyz 5.4yearsago") == set()


def test_completed_record_without_modules_is_a_fault(tmp_path: Path) -> None:
    run, sources = make_run(tmp_path)
    record = next(run.glob("completed-*.json"))
    record.write_text(json.dumps({"kind": "cpos-markdown-delivery/1"}))
    assert flow.run_faults(run, sources) == [f"completed record {record.name} has no modules"]


def c1_rounding_run(tmp_path: Path, printed: str, *, calculated: bool = True) -> list[str]:
    """CP-1 read 767 and 200; optionally calculated 3.835; its handoff prints `printed`."""
    run, sources = make_run(tmp_path)
    folder = run / "live/modules" / sha(b"CP-1")
    tools = json.loads((folder / "0.tools.json").read_text())
    tools.append({"call_id": "r2", "name": "read_pages", "text": "Debt 767. EBITDA 200."})
    if not calculated:
        tools.append({"call_id": "r3", "name": "read_pages", "text": "Ratio 3.835."})
    (folder / "0.tools.json").write_text(json.dumps(tools))
    if calculated:
        add_calls(run, "CP-1", [("c1", ["767", "200"], "3.835")])
    set_handoff(
        run, "CP-1", CP1 + f"Proposed debt / EBITDA: 767 / 200 = 3.835, displayed {printed}.\n"
    )
    return flow.run_faults(run, sources)


def test_calculate_result_covers_its_two_decimal_rounding(tmp_path: Path) -> None:
    faults = c1_rounding_run(tmp_path, "3.84")
    assert not any("number 3.84" in f for f in faults)


def test_calculate_result_does_not_cover_a_wrong_rounding(tmp_path: Path) -> None:
    faults = c1_rounding_run(tmp_path, "3.83")
    assert any("number 3.83" in f for f in faults)


def test_calculate_result_covers_itself(tmp_path: Path) -> None:
    faults = c1_rounding_run(tmp_path, "3.835")
    assert not any("number 3.835" in f for f in faults)


def test_reported_three_decimal_figure_is_not_expanded(tmp_path: Path) -> None:
    faults = c1_rounding_run(tmp_path, "3.84", calculated=False)
    assert any("number 3.84" in f for f in faults)


ROUNDINGS = [
    ("0.0828320662783500246", "0.082832066278350024600441220816734648531"),
    ("0.2853008794070834874", "0.28530087940708348740373948971881481005"),
    ("1.5382407917", "1.5382407917290375621446797949322516346"),
    ("1.7156817882", "1.7156817882155848386371216057952580022"),
    ("1.8702504944", "1.8702504943968358602504943968358602505"),
    ("1.989848385", "1.9898483849703361898483849703361898484"),
    ("10.4730259931", "10.473025993133889161353604708190289358"),
    ("11.4556197246", "11.455619724566859173700577521101732563"),
    ("2.21434202", "2.2143420200270044565158007289642308023"),
    ("2.3159137264", "2.3159137263719144972457320892286443863"),
    ("2.3559437121", "2.3559437120981526142030953663162331125"),
    ("2.4094624761", "2.4094624761109415902484462074614161594"),
]


def calc_run(tmp_path: Path, result: str, text: str, operands: tuple[str, str]) -> list[str]:
    """CP-1 read the two operands, calculated `result` from them; its handoff holds `text`."""
    run, sources = make_run(tmp_path)
    folder = run / "live/modules" / sha(b"CP-1")
    tools = json.loads((folder / "0.tools.json").read_text())
    tools.append(
        {"call_id": "r2", "name": "read_pages", "text": f"Values {operands[0]} and {operands[1]}."}
    )
    (folder / "0.tools.json").write_text(json.dumps(tools))
    add_calls(run, "CP-1", [("c1", list(operands), result)])
    set_handoff(run, "CP-1", CP1 + text + "\n")
    return flow.run_faults(run, sources)


@pytest.mark.parametrize(("printed", "result"), ROUNDINGS, ids=[r[0] for r in ROUNDINGS])
def test_long_calculate_roundings_trace(tmp_path: Path, printed: str, result: str) -> None:
    faults = calc_run(tmp_path, result, f"The ratio is {printed}.", ("1234", "567"))
    assert not any(f"number {printed}" in f for f in faults)


@pytest.mark.parametrize(("printed", "result"), ROUNDINGS, ids=[r[0] for r in ROUNDINGS])
def test_long_calculate_rounding_with_changed_last_digit_is_flagged(
    tmp_path: Path, printed: str, result: str
) -> None:
    wrong = printed[:-1] + str((int(printed[-1]) + 1) % 10)
    faults = calc_run(tmp_path, result, f"The ratio is {wrong}.", ("1234", "567"))
    assert any(f"number {wrong}" in f for f in faults)


PCT_RESULT = "0.2853008794070834874"
PCT_OPERANDS = ("17746", "62201")
C1N_CP1_LINE193 = (
    "Calculated H1 exclusions total 17,746 versus 5,219 in the prior H1; reported EBITDA fell "
    "by 806 while exclusions rose by 12,527, producing the 11,721 increase in Adjusted EBITDA. "
    "Exclusions equal 28.5301% of current-H1 EBITDA versus 8.2832% in prior H1. This is the "
    "principal earnings-definition risk: adjusted growth does not demonstrate improvement in "
    "the unadjusted earnings available to absorb acquisition and implementation costs."
)


def pct_run(tmp_path: Path, text: str) -> list[str]:
    """The two C1n CP-1 calculate calls (17746/62201 and 5219/63007) over evidenced operands."""
    run, sources = make_run(tmp_path)
    folder = run / "live/modules" / sha(b"CP-1")
    tools = json.loads((folder / "0.tools.json").read_text())
    tools.append(
        {"call_id": "r2", "name": "read_pages", "text": "Values 17746, 62201, 5219 and 63007."}
    )
    (folder / "0.tools.json").write_text(json.dumps(tools))
    add_calls(
        run,
        "CP-1",
        [
            ("c1", ["17746", "62201"], PCT_RESULT),
            ("c2", ["5219", "63007"], "0.0828320662783500246"),
        ],
    )
    set_handoff(run, "CP-1", CP1 + text + "\n")
    return flow.run_faults(run, sources)


def test_1f_x_c1n_line193_percent_pair_traces(tmp_path: Path) -> None:
    faults = pct_run(tmp_path, C1N_CP1_LINE193)
    assert not any("number 28.5301" in f or "number 8.2832" in f for f in faults)


@pytest.mark.parametrize("marker", ["%", " percent", " per cent", " pct"])
def test_1f_y_percent_marker_traces(tmp_path: Path, marker: str) -> None:
    faults = pct_run(tmp_path, f"Exclusions equal 28.53{marker} of EBITDA.")
    assert not any("number 28.53" in f for f in faults)


def test_1f_z_unmarked_percent_is_flagged(tmp_path: Path) -> None:
    faults = pct_run(tmp_path, "Exclusions equal 28.53 of EBITDA.")
    assert any("number 28.53" in f for f in faults)


def test_1f_z2_marked_and_unmarked_is_flagged(tmp_path: Path) -> None:
    faults = pct_run(tmp_path, "Exclusions equal 28.53% of EBITDA. Elsewhere 28.53 appears bare.")
    assert any("number 28.53" in f for f in faults)


def test_1f_k_no_other_scaling(tmp_path: Path) -> None:
    faults = pct_run(tmp_path, "Exclusions equal 285.3% of EBITDA.")
    assert any("number 285.3" in f for f in faults)


# --- Answer key: units (R-ALIVE flow_check H1/H2, R-C2-4). Lines are quoted from the retained
# A-live (TDG 2024) and C2 (Mattress Firm 2014) runs; the fixtures carry only the source text the
# rule reads.


def units_run(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    source: str,
    handoff: str,
    **extra: Any,
) -> set[str]:
    """The numbers CP-1 is flagged for. Optional `extra`: `calls`, a list of (id, operation,
    operands, printed result), and `instruction`, text added to the request."""
    calls, instruction = extra.pop("calls", ()), extra.pop("instruction", None)
    assert not extra, extra
    monkeypatch.setattr(sys.modules[__name__], "SOURCE", SOURCE + source + "\n")
    run, _ = make_run(tmp_path)
    set_handoff(run, "CP-1", handoff)
    folder = run / "live/modules" / sha(b"CP-1")
    if calls:
        add_calls(run, "CP-1", [(c, o, r) for c, _, o, r in calls])
        request = json.loads((folder / "1.request.json").read_text())
        for call, (_, operation, _, _) in zip(request["messages"][2]["tool_calls"], calls):
            call["arguments"]["operation"] = operation
        (folder / "1.request.json").write_text(json.dumps(request))
    if instruction:
        outer = json.loads((folder / "0.request.json").read_text())
        inner = json.loads(outer["messages"][1]["text"]) | {"instructions": instruction}
        outer["messages"][1]["text"] = json.dumps(inner)
        (folder / "0.request.json").write_text(json.dumps(outer))
    found = re.findall(r"CP-1: number (\S+) in the handoff", "\n".join(flow.run_faults(run)))
    return set(found)


BPS_CASES = [
    # CP-1.md:266 and :268 (A-live); the source prints "Term SOFR plus 2.50%" (10-K page 59).
    ("Term SOFR + 250 bps", "Term SOFR plus 2.50%"),
    ("Term SOFR + 250 bps", "Term SOFR plus 2.5%"),
    ("spread of 250 basis points", "Term SOFR plus 2.50%"),
    # CP-1.md:269-270 rows. In the retained source these passed only by coincidence: 225 is
    # "Total liabilities assumed 164 61 225" (and "$225 million"), 145 is the JSON key "page": 145,
    # 275 is "290 275 586 517" in a table. The fixtures keep the percent and drop that coincidence.
    ("Draws: Term SOFR + 225 bps", "Term SOFR plus 2.25%"),
    ("Term SOFR + 145 bps", "Term SOFR plus 1.45%"),
    ("Term SOFR + 275 bps", "Term SOFR plus 2.75%"),
]


@pytest.mark.parametrize(("line", "source"), BPS_CASES)
def test_h1_bps_is_sourced_by_its_percent(tmp_path, monkeypatch, line: str, source: str) -> None:
    assert units_run(tmp_path, monkeypatch, source=source, handoff=f"# CP-1\n\n{line}\n") == set()


@pytest.mark.parametrize(
    ("line", "source"),
    [
        ("Term SOFR + 250 bps", "Term SOFR plus 2.0%"),  # a different percent
        ("Term SOFR + 250 bps", "margin 2.50 on the schedule"),  # 2.50 is not marked a percent
        ("Term SOFR + 250 bps", "Term SOFR plus 25.0%"),  # 250 / 10 is no conversion
        ("Term SOFR + 250 bps", "Term SOFR plus 0.25%"),  # nor 250 / 1000
        ("Term SOFR + 250 bps", "Term SOFR plus 2.51%"),  # exact decimal equality only
    ],
)
def test_h1_bps_without_its_exact_percent_is_flagged(tmp_path, monkeypatch, line, source) -> None:
    flagged = units_run(tmp_path, monkeypatch, source=source, handoff=f"# CP-1\n\n{line}\n")
    assert flagged == {"250"}


def test_h1_percent_converts_only_for_bps(tmp_path, monkeypatch) -> None:
    flagged = units_run(
        tmp_path, monkeypatch, source="Term SOFR plus 2.50%", handoff="# CP-1\n\nfee 250 per year\n"
    )
    assert flagged == {"250"}


@pytest.mark.parametrize(
    "line",
    ["x / 100", "x / 1000", "step-up / 10000", "ratio 233.1 ÷ 1000", "y / 0.001"],
)
def test_h2_unit_divisors_are_not_figures(tmp_path, monkeypatch, line: str) -> None:
    # CP-3C.md:159 "whole principal payable × step-up / 10000".
    handoff = f"# CP-1\n\n- Added annual cash interest = {line}.\n"
    # The dividend 233.1 is sourced, so only the divisor is under test.
    assert units_run(tmp_path, monkeypatch, source="LP 233.1", handoff=handoff) == set()


@pytest.mark.parametrize(
    ("line", "flagged"),
    [
        ("x / 50", {"50"}),
        ("x / 1000.5", {"1000.5"}),
        ("x ÷ 0.01", {"0.01"}),
        ("x / 10000.0", set()),  # 10000.0 is exactly 10000
        ("x / 100 and 100 outstanding", {"100"}),  # only the divisor occurrence is exempt
        ("x / 10000 and 10000 drawn", {"10000"}),
        ("Net debt / 100.5m", {"100.5"}),  # a glued unit does not shorten the figure to 100
        ("Net debt / 1000.25x", {"1000.25"}),
        ("Net debt \u00f7 10000.7bn", {"10000.7"}),
    ],
)
def test_h2_other_divisors_and_plain_figures_stay_flagged(
    tmp_path, monkeypatch, line: str, flagged: set[str]
) -> None:
    handoff = f"# CP-1\n\n{line}\n"
    assert units_run(tmp_path, monkeypatch, source="", handoff=handoff) == flagged


def test_instruction_text_admits_nothing(tmp_path, monkeypatch) -> None:
    flagged = units_run(
        tmp_path,
        monkeypatch,
        source="",
        handoff="# CP-1\n\n4321 / 50, 250 bps\n",
        instruction="divide by 50; quote 4321 and 250 bps; 2.50%",
    )
    assert flagged == {"4321", "50", "250"}


@pytest.mark.parametrize(
    "line",
    [
        "ASC 842 leases",  # CP-1D.md:118, :304, :337
        "IFRS 16 and IAS 17",
        "ASU 2016-02, SFAS 157",
        "under ASC 842, the lessee",
    ],
)
def test_standard_names_are_not_figures(tmp_path, monkeypatch, line: str) -> None:
    assert units_run(tmp_path, monkeypatch, source="", handoff=f"# CP-1\n\n{line}\n") == set()


@pytest.mark.parametrize(
    ("line", "flagged"),
    [
        ("lease fee 842 due", {"842"}),
        ("Section 842 applies", {"842"}),
        ("ASC topics cover 842", {"842"}),  # not directly after the prefix
        ("ASC leases, effective 842", {"842"}),
        ("ASC 842 and also 842 drawn", {"842"}),  # the bare occurrence still counts
        ("ASCENT 842", {"842"}),  # a prefix is a whole word
        ("Adjusted per ASC\n\n5678 total", {"5678"}),  # the prefix does not reach the next line
    ],
)
def test_standard_prefix_must_directly_precede_the_number(
    tmp_path, monkeypatch, line: str, flagged: set[str]
) -> None:
    assert units_run(tmp_path, monkeypatch, source="", handoff=f"# CP-1\n\n{line}\n") == flagged


E_LINES = "# CP-1\n\n767 / 0.001 = 767000 USD thousands; 233.1 / 0.001 = 233100 USD thousands\n"
E_CALLS = [
    ("c1", "ratio", ["767", "0.001"], "7.67E+5"),  # CP-2 tools 3 (#12)
    ("c2", "ratio", ["233.1", "0.001"], "2.331E+5"),  # #13
]


def test_e_notation_calculate_results_read_as_exact_decimals(tmp_path, monkeypatch) -> None:
    flagged = units_run(
        tmp_path, monkeypatch, source="Total Debt $767 and 216.3 + 16.8 = 233.1",
        handoff=E_LINES, calls=E_CALLS,
    )  # fmt: skip
    assert flagged == set()


def test_e_notation_result_is_still_checked_like_any_calculate_result(
    tmp_path, monkeypatch
) -> None:
    # An unsourced operand (999) keeps the result 999000 flagged; a wrong exponent is no match.
    flagged = units_run(
        tmp_path, monkeypatch, source="Total Debt $767",
        handoff="# CP-1\n\n767 / 0.001 = 76700; 999 / 0.001 = 999000\n",
        calls=[("c1", "ratio", ["767", "0.001"], "7.67E+5"),
               ("c2", "ratio", ["999", "0.001"], "9.99E+5")],
    )  # fmt: skip
    assert flagged == {"76700", "999", "999000"}


def test_hand_rescales_and_their_sums_stay_flagged(tmp_path, monkeypatch) -> None:
    # #5-#9: "$98.4 million" and "$77.1 million" written as 98400 and 77100 (USD thousands).
    flagged = units_run(
        tmp_path, monkeypatch, source="$98.4 million and $77.1 million and 18,143 and 22,878",
        handoff="# CP-1\n\n98400 and 77100 (USD thousands); 116543 and 99978\n",
        calls=[("c1", "sum", ["18143", "98400"], "116543"),
               ("c2", "sum", ["22878", "77100"], "99978")],
    )  # fmt: skip
    assert flagged == {"98400", "77100", "116543", "99978"}


def test_hand_rescales_survive_a_divisor_in_the_same_module(tmp_path, monkeypatch) -> None:
    # #14-#19: LP 10.0 / 0.6 / 16.8, calculate 21.7 and 33.4, written x1000, unit stated.
    flagged = units_run(
        tmp_path, monkeypatch,
        source="LP 10.0 0.6 16.8 and 20.0 1.7 and 30.0 3.4 and 2500",
        handoff=("# CP-1\n\nUSD thousands: 10000, 600, 16800; 21700; 33400; 38500\n"
                 "ratio 767 / 1000 and 0.6 / 0.001\n"),
        calls=[("c1", "sum", ["20.0", "1.7"], "21.7"), ("c2", "sum", ["30.0", "3.4"], "33.4"),
               ("c3", "sum", ["10000", "2500", "600", "16800"], "38500")],
    )  # fmt: skip
    assert flagged == {"10000", "600", "16800", "21700", "33400", "38500", "767"}


def copy_runs() -> list[tuple[Path, Path]]:
    """The retained runs, when present on this machine: (run directory, sources folder)."""
    notes = Path.home() / "Library/Application Support/Claude/side-session-notes"
    alive = notes / "local_6dd3c4fd-b818-4b8a-8cbd-10a4368bbb28/sb2/logs/alive-copy"
    c2 = ROOT.parent / "s2-launch-quit-933fbe/.superpowers/sdd/plan-3/c2-assess/run"
    out = []
    for copy in (alive, c2):
        runs = sorted((copy / "ws/runs").glob("web-*")) if copy.is_dir() else []
        out += [(runs[0], copy / "sources")] if runs else []
    return out


def test_retained_runs_keep_only_the_real_faults() -> None:
    copies = {run.name[:8]: (run, sources) for run, sources in copy_runs()}
    if not copies:
        pytest.skip("retained A-live and C2 copies are not on this machine")
    if "web-58d0" in copies:  # A-live: 250 bps now sourced, "/ 10000" not a figure
        assert flow.run_faults(*copies["web-58d0"]) == []
    if "web-f126" in copies:  # C2: names, divisor and E-notation clear; hand rescales remain
        left = {f.split("number ")[1].split(" ")[0] for f in flow.run_faults(*copies["web-f126"])}
        assert left == {
            "98400", "77100", "99978", "110050", "116543", "10000", "600", "16800", "21700",
            "33400", "38500",
        }  # fmt: skip


def test_e_notation_one_e3_result_is_read_as_1000(tmp_path, monkeypatch) -> None:
    flagged = units_run(
        tmp_path, monkeypatch, source="Total Debt $767", handoff="# CP-1\n\n767 x 1000 = 1000\n",
        calls=[("c1", "sum", ["767"], "1e3")],
    )  # fmt: skip
    assert flagged == set()


def test_ratio_with_a_unit_dividend_is_not_exempt(tmp_path, monkeypatch) -> None:
    result = "1.3037809647979139"  # 1000 / 767: the unit is the dividend, so 1000 is no divisor
    flagged = units_run(
        tmp_path, monkeypatch, source="Total Debt $767", handoff=f"# CP-1\n\nresult {result}\n",
        calls=[("c1", "ratio", ["1000", "767"], result)],
    )  # fmt: skip
    assert flagged == {result}


def test_ratio_divisor_written_1e3_is_the_unit_1000(tmp_path, monkeypatch) -> None:
    flagged = units_run(
        tmp_path, monkeypatch, source="Total Debt $767", handoff="# CP-1\n\n767 / 1000 = 0.767\n",
        calls=[("c1", "ratio", ["767", "1E3"], "0.767")],
    )  # fmt: skip
    assert flagged == set()
