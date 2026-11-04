"""CP1H-R18 rows answer key, derived mechanically: for every unit of the frozen statement-units key
(fc93c39d) except BGS (F1: one cell per line), run DVII's extract_statement_lines on the cell-marked
re-conversion (td/th boundaries -> ' | ' cells). Never uses the DW tokenizer. Writes one JSON per
case to OUT. Run with the lane venv from the units-oracle worktree (py.sh).

This file documents the method that produced the sibling JSON files. It is not run by tests."""

import hashlib
import json
import re
from pathlib import Path

from deploy_vii.statement_extract import extract_statement_lines
from deploy_workflow import html_text as ht

CORPUS = Path("/Users/ericguei/Documents/Deploy Workflow/artifacts/public-corpus/v1")
M = ""
PIPE = " " + chr(124) + " "


class Marked(ht._Lines):
    def _break(self, tag):
        if tag in ("td", "th"):
            self.parts.append(M)
        else:
            super()._break(tag)


def marked(raw):
    decoded, _ = ht._decode(raw)
    p = Marked()
    p.feed(decoded)
    p.close()
    out = []
    for x in "".join(p.parts).split("\n"):
        x = x.translate(ht._ZERO_WIDTH)
        if ht._normalise(x.replace(M, " ")):
            out.append(x)
    return out


def _cells(x):
    return [c for c in (re.sub(r"\s+", " ", c).strip() for c in x.split(M)) if c]


def opt_i(x):
    return PIPE.join(_cells(x))


UNITS = Path("cases/statement-units")
OUT = Path("cases/statement-rows")
OUT.mkdir(exist_ok=True)
total = 0
MERGED: list[tuple[str, int]] = []
for path in sorted(UNITS.glob("*.json")):
    key = json.loads(path.read_text("utf-8"))
    if key["case"].startswith("bgs"):
        continue
    sources = []
    for src in key["sources"]:
        if not src["units"]:
            continue
        raw = (CORPUS / src["file"]).read_bytes()
        ev = ht.convert_html(raw).text.splitlines()
        sha = hashlib.sha256("".join(x + "\n" for x in ev).encode()).hexdigest()
        assert sha == src["converted_sha256"], src["source_id"]
        mk = marked(raw)
        assert len(mk) == len(ev), src["source_id"]
        assert all(ht._normalise(a.replace(M, " ")) == b for a, b in zip(mk, ev, strict=True))
        units = []
        for unit in src["units"]:
            start = int(unit["start"].removeprefix("line:"))
            end = int(unit["end"].removeprefix("line:"))
            table = extract_statement_lines(
                "\n".join(opt_i(mk[k]) for k in range(start - 1, end)), "x"
            )
            rows = []
            for r in table.lines:
                line = start + r.line_no - 1
                # Review H1: each <tr> is one line here, so DVII's continuation merge only glues a
                # separate heading row onto the label; the label is the row's own label cell.
                own = _cells(mk[line - 1])[0]
                if r.label != own:
                    assert r.label.endswith(" " + own), (src["source_id"], line)
                    MERGED.append((src["source_id"], line))
                rows.append({"line": line, "label": own, "raw_values": list(r.raw_values)})
            total += len(rows)
            units.append(
                {"kind": unit["kind"], "start": unit["start"], "end": unit["end"], "rows": rows}
            )
        sources.append(
            {
                "source_id": src["source_id"],
                "file": src["file"],
                "converted_sha256": sha,
                "units": units,
            }
        )
    out = {
        "schema": "statement-rows/1",
        "case": key["case"],
        "method": "DVII extract_statement_lines over each unit of cases/statement-units (fc93c39d), "
        "on a cell-marked re-conversion of the filing (td/th boundaries joined by ' | '); "
        "line-aligned with convert_html's text (asserted). A row's label is its own "
        "label cell (review H1: each <tr> is one line, so DVII's continuation merge "
        "would glue a heading row on). Headers are not part of the key (review L1). "
        "BGS excluded (CP1H-R18 F1).",
        "sources": sources,
    }
    (OUT / path.name).write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n", "utf-8")
    print(
        key["case"],
        [(s["source_id"], [(u["kind"], len(u["rows"])) for u in s["units"]]) for s in sources],
    )
print("rows", total, "labels un-merged", len(MERGED), MERGED)
