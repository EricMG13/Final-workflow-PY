"""The independent data-flow checker, over a synthetic two-module run in the real layout."""

import hashlib
import importlib.util
import json
from pathlib import Path

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
