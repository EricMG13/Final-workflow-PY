"""Delivery integrity checks; actual handoffs are retained host-model outputs."""

import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from deploy_workflow.handoff_delivery import deliver, mapped_module, prepare, section, table

RUN = Path(__file__).resolve().parents[1] / "runs" / "tdg-002"


def copy_job(tmp_path: Path) -> Path:
    job = json.loads((RUN / "snapshot-inputs.json").read_text())
    for spec in job["handoffs"].values():
        (tmp_path / spec["path"]).write_bytes((RUN / spec["path"]).read_bytes())
    path = tmp_path / "inputs.json"
    path.write_text(json.dumps(job))
    return path


def test_table_preserves_sign_missingness_and_separates_later_tables() -> None:
    headers, rows = table(
        list(
            enumerate(
                [
                    "intro",
                    "| Measure | FY2024 |",
                    "|---|---:|",
                    "| Dividend | (2,038) |",
                    "| Prior | — |",
                    r"| Literal | a\|b |",
                    "other paragraph",
                    "| Other | Columns |",
                    "|---|---|",
                    "| x | y |",
                ],
                1,
            )
        )
    )
    assert headers == ["Measure", "FY2024"]
    assert [row[2] for row in rows] == [["Dividend", "(2,038)"], ["Prior", "—"], ["Literal", "a|b"]]


def test_malformed_table_and_ambiguous_sections_refuse() -> None:
    with pytest.raises(ValueError, match="row does not match"):
        table([(1, "| A | B |"), (2, "|---|---|"), (3, "| one | two | three |")])
    with pytest.raises(ValueError, match="Expected one"):
        section(["## Findings", "one", "## Findings", "two"], "Findings")


def test_section_keeps_blank_table_boundary() -> None:
    rows = section(
        [
            "## Findings",
            "| A | B |",
            "|---|---|",
            "| one | two |",
            "",
            "| C | D |",
            "|---|---|",
            "| three | four |",
        ],
        "Findings",
    )
    assert table(rows) == (["A", "B"], [(4, "| one | two |", ["one", "two"])])


def test_actual_handoffs_populate_existing_five_sections_and_exact_sources() -> None:
    view, report, copies = prepare(RUN / "snapshot-inputs.json")
    assert len(report.blocks) == 5
    assert all(block.state in {"populated", "collapsed"} for block in report.blocks)
    assert view.mode == "candidate"
    assert view.analytical_qualification == "unrun"
    model = next(m for m in view.modules if m.module_id == "CP-MODEL")
    assert model.status == "blocked" and not model.facts and model.artifact_sha256 is None
    source_lines = {
        s.source_id: {span.locator: span.text for span in s.spans} for s in view.sources
    }
    for module in view.modules:
        for fact in module.facts:
            for cite in fact.citations:
                assert cite.quote == source_lines[cite.source_id][cite.locator]
                assert (
                    cite.source_sha256
                    == hashlib.sha256(copies[module.module_id + ".md"]).hexdigest()
                )
    cp1 = next(m for m in view.modules if m.module_id == "CP-1")
    observed = {(f.label, f.field): f.text for f in cp1.facts}
    assert observed[("Capital expenditures", "c0")] == "(165)"
    assert observed[("Operating cash less capex", "c0")] == "1,880"
    assert (
        observed[("Total debt carrying value incl. separately shown securitization", "c2")]
        == "Not reconstructed"
    )
    cp1a = next(m for m in view.modules if m.module_id == "CP-1A")
    events = next(t for t in cp1a.tables if t.table_id == "events_timeline")
    assert all("Governance" not in r.label and "---" not in r.label for r in events.rows)
    transactions = next(b for b in report.blocks if b.block_id == "transaction-summary")
    rendered_text = json.dumps(transactions.model_dump(mode="json"), ensure_ascii=False)
    assert "Period / status: July 31, 2024 — Completed" in rendered_text
    assert "Period / status: May 8, 2023 — Completed" in rendered_text
    assert "Date / period: October 2024" in rendered_text


def test_business_row_ids_preserve_literal_content_and_ambiguous_company_refuses() -> None:
    job = json.loads((RUN / "snapshot-inputs.json").read_text())
    raw = (RUN / job["handoffs"]["CP-1A"]["path"]).read_text()
    labels = (
        "Company description",
        "Product mix",
        "Revenue-channel estimate",
        "Aftermarket margin/stability characterization",
        "End markets / concentration",
    )
    for i, label in enumerate(labels, 1):
        raw = raw.replace("| " + label + " |", f"| C{i:02} {label} |")
    module, source = mapped_module("CP-1A", raw.encode())
    mix = next(t for t in module.tables if t.table_id == "revenue_business_mix")
    assert {r.label for r in mix.rows} == {f"C{i:02} {v}" for i, v in enumerate(labels, 1) if i > 1}
    company = next(f for f in module.facts if f.table_id == "company_description")
    assert company.label == "C01 Company description"
    assert company.citations[0].quote.startswith("| C01 Company description |")
    assert company.citations[0].quote in {s.text for s in source.spans}
    row = next(line for line in raw.splitlines() if line.startswith("| C01 Company description |"))
    duplicate = raw.replace(row, row + "\n" + row.replace("C01", "C99", 1))
    with pytest.raises(ValueError, match="company-description row"):
        mapped_module("CP-1A", duplicate.encode())


@pytest.mark.parametrize("token", ["", "   ", "** **", "0", "—"])
def test_dashboard_blank_is_missing_and_zero_or_dash_stays_literal(
    tmp_path: Path, token: str
) -> None:
    """Synthetic cell controls over a retained actual handoff, including rendering."""
    path = copy_job(tmp_path)
    job = json.loads(path.read_text())
    source = tmp_path / job["handoffs"]["CP-1"]["path"]
    raw = source.read_text()
    row = next(
        line
        for line in raw.splitlines()
        if line.startswith("| Total debt carrying value incl. separately shown securitization |")
    )
    cells = row.split("|")
    cells[4] = " " + token + " "
    source.write_text(raw.replace(row, "|".join(cells), 1))
    job["handoffs"]["CP-1"]["sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
    path.write_text(json.dumps(job))
    view, _, _ = prepare(path)
    fact = next(
        f
        for module in view.modules
        if module.module_id == "CP-1"
        for f in module.facts
        if f.label == "Total debt carrying value incl. separately shown securitization"
        and f.field == "c2"
    )
    missing = token in {"", "   ", "** **"}
    assert fact.status == ("missing" if missing else "known")
    assert fact.text == (None if missing else token)
    assert bool(fact.limitation) == missing
    assert fact.amount is None
    assert fact.citations[0].quote == "|".join(cells)
    assert deliver(path, tmp_path / "out").is_file()


def test_changed_handoff_and_foreign_issuer_refuse_before_export(tmp_path: Path) -> None:
    path = copy_job(tmp_path)
    job = json.loads(path.read_text())
    source = tmp_path / job["handoffs"]["CP-2"]["path"]
    source.write_text(source.read_text() + "changed")
    with pytest.raises(ValueError, match="Changed handoff"):
        deliver(path, tmp_path / "out")
    assert not (tmp_path / "out").exists()
    job["handoffs"]["CP-2"]["sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
    job["run"]["issuer_name"] = "A different issuer"
    path.write_text(json.dumps(job))
    with pytest.raises(ValueError, match="Issuer name"):
        prepare(path)


@pytest.mark.parametrize(
    "wrapped_name",
    [
        "TransDigm\nGroup Incorporated",
        "TransDigm\r\nGroup\tIncorporated",
        "TransDigm  Group Incorporated",
    ],
)
def test_issuer_word_wrapping_preserves_original_handoff_bytes(
    tmp_path: Path, wrapped_name: str
) -> None:
    path = copy_job(tmp_path)
    job = json.loads(path.read_text())
    source = tmp_path / job["handoffs"]["CP-2"]["path"]
    raw = source.read_bytes().replace(b"TransDigm Group Incorporated", wrapped_name.encode())
    assert b"TransDigm Group Incorporated" not in raw
    source.write_bytes(raw)
    expected = hashlib.sha256(raw).hexdigest()
    job["handoffs"]["CP-2"]["sha256"] = expected
    path.write_text(json.dumps(job))
    view, _, copies = prepare(path)
    assert copies["CP-2.md"] == raw
    assert next(s for s in view.sources if s.source_id == "CP-2-handoff").sha256 == expected


def test_issuer_name_inside_another_word_does_not_establish_the_issuer(tmp_path: Path) -> None:
    # "Digm" is the middle of "TransDigm": a name embedded in a longer word is not a match.
    path = copy_job(tmp_path)
    job = json.loads(path.read_text())
    job["run"]["issuer_name"] = "Digm"
    path.write_text(json.dumps(job))
    with pytest.raises(ValueError, match="Issuer name"):
        prepare(path)


def test_whitespace_only_issuer_refuses_before_export(tmp_path: Path) -> None:
    path = copy_job(tmp_path)
    job = json.loads(path.read_text())
    job["run"]["issuer_name"] = " \t\n "
    path.write_text(json.dumps(job))
    with pytest.raises(ValueError, match="Issuer name"):
        deliver(path, tmp_path / "out")
    assert not (tmp_path / "out").exists()


def test_delivery_preserves_files_escapes_text_and_refuses_overwrite(tmp_path: Path) -> None:
    path = copy_job(tmp_path)
    job = json.loads(path.read_text())
    source = tmp_path / job["handoffs"]["CP-2"]["path"]
    attack = "</script><script>window.BAD=1</script>"
    source.write_text(source.read_text().replace("**Assessment —", attack + "\n\n**Assessment —"))
    job["handoffs"]["CP-2"]["sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
    path.write_text(json.dumps(job))
    destination = tmp_path / "out"
    report = deliver(path, destination)
    assert attack not in report.read_text()
    assert attack.replace("<", r"\u003c") in report.read_text()
    assert "Manual delivery" in report.read_text()
    record = json.loads((destination / "delivery.json").read_text())
    assert record["analytical_runtime_executed"] is False
    for name, expected in record["files"].items():
        assert hashlib.sha256((destination / name).read_bytes()).hexdigest() == expected
    assert (destination / "CP-2.md").read_bytes() == source.read_bytes()
    before = report.read_bytes()
    with pytest.raises(FileExistsError):
        deliver(path, destination)
    assert report.read_bytes() == before


def test_export_failure_never_writes_completion_record(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = Path.write_bytes

    def fail_report(path: Path, content: bytes) -> int:
        if path.name == "report.html":
            raise OSError("simulated disk failure")
        return original(path, content)

    monkeypatch.setattr(Path, "write_bytes", fail_report)
    destination = tmp_path / "out"
    with pytest.raises(OSError, match="simulated disk failure"):
        deliver(RUN / "snapshot-inputs.json", destination)
    assert not (destination / "delivery.json").exists()
    with pytest.raises(FileExistsError):
        deliver(RUN / "snapshot-inputs.json", destination)


def test_concurrent_export_has_one_complete_writer(tmp_path: Path) -> None:
    destination = tmp_path / "out"

    def attempt() -> str:
        try:
            deliver(RUN / "snapshot-inputs.json", destination)
        except FileExistsError:
            return "refused"
        return "written"

    with ThreadPoolExecutor(max_workers=2) as workers:
        assert sorted(workers.map(lambda _: attempt(), range(2))) == ["refused", "written"]
    record = json.loads((destination / "delivery.json").read_text())
    for name, expected in record["files"].items():
        assert hashlib.sha256((destination / name).read_bytes()).hexdigest() == expected


def test_cp2_key_risks_line_is_kept_with_its_materiality_ratings() -> None:
    """The handoff's `**Key risks:**` line (CP-2, runs/tdg-002 line 76) carries the (Material) and
    (Critical evidence gap) ratings; mapping it away would leave a report that omits them."""
    view, _, _ = prepare(RUN / "snapshot-inputs.json")
    cp2 = next(m for m in view.modules if m.module_id == "CP-2")
    kept = [text for text in cp2.limitations if text.startswith("Key risks")]
    assert len(kept) == 1
    for rating in (
        "(Material) refinancing access at the FY2028–FY2029 maturity concentration",
        "(Material) cash depletion through distributions and acquisitions alongside debt service",
        (
            "(Critical evidence gap) current unrestricted liquidity, covenant headroom and legal "
            "capacity cannot be established"
        ),
    ):
        assert rating in kept[0]
