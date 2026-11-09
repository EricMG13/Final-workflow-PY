"""Write the issuer library's `issuer-library-run/1` manifest for a finished app run.

Values are copied as written; nothing is calculated or converted, and a value that cannot be
pinned to exactly one source line is omitted with its field. Missing is never zero.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any, NamedTuple

SCHEMA = "issuer-library-run/1"
Json = dict[str, Any]
_NUMBER = re.compile(r"-?\d[\d,]*(\.\d+)?")
_KEY = re.compile(r'^("(?:[^"\\]|\\.)*"):\s*(.*)$')
_TERM_FIELDS = (
    ("tenor_years", "years"),
    ("talk_spread_bps_low", "bps"),
    ("talk_spread_bps_high", "bps"),
    ("talk_oid_low", "price"),
    ("talk_oid_high", "price"),
    ("floor_pct", "%"),
    ("coupon_pct", "%"),
    ("margin_bps", "bps"),
)
_QUOTE_FIELDS = (
    ("bid", "price"),
    ("ask", "price"),
    ("price", "price"),
    ("yield_pct", "%"),
    ("spread_bps", "bps"),
)
_TABLES = {
    "cp1_leverage": (
        "leverage",
        "x",
        (("leverage", "Total debt / EBITDA"), ("net_leverage", "Net debt / EBITDA")),
    ),
    "cp1_coverage": ("interest cover", "x", (("coverage", "EBITDA / cash interest"),)),
    "cp1_liquidity": (
        "liquidity",
        "US$m",
        (("cash", "Cash"), ("undrawn", "Undrawn committed facilities")),
    ),
}
_HEADINGS = {f"### Chart data: {t[0]}": k for k, t in _TABLES.items()}
_BASIS_USER = "Entered by the user in the run context"


class ManifestError(ValueError):
    """A required input of the manifest is missing or malformed."""


_Item = tuple[str, "_Doc | None", int | None]


class _Doc(NamedTuple):
    rel: str
    sha: str
    lines: list[str]


class _Row(NamedTuple):
    line: int
    cells: dict[str, str]


class _Delivery(NamedTuple):
    folder: Path
    doc: _Doc
    files: dict[str, str]
    report: _Doc | None


def _doc(root: Path, rel: str) -> _Doc:
    path = root / rel
    if not path.is_file():
        raise ManifestError(f"{rel} is missing")
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as err:
        raise ManifestError(f"{rel} is not UTF-8") from err
    return _Doc(rel, hashlib.sha256(raw).hexdigest(), text.replace("\r\n", "\n").split("\n"))


def _doc_if(root: Path, rel: str) -> _Doc | None:
    return _doc(root, rel) if (root / rel).is_file() else None


def _pin(doc: _Doc, line: int) -> Json:
    return {"path": doc.rel, "sha256": doc.sha, "line": line, "quote": doc.lines[line - 1]}


def _load(root: Path, rel: str) -> tuple[_Doc, Json]:
    doc = _doc(root, rel)
    try:
        data = json.loads("\n".join(doc.lines))
    except ValueError as err:
        raise ManifestError(f"{rel} is not valid JSON: {err}") from err
    if not isinstance(data, dict):
        raise ManifestError(f"{rel} must hold a JSON object")
    return doc, data


def _need(obj: Json, key: str, kind: type, where: str) -> Any:
    value = obj.get(key)
    if not isinstance(value, kind):
        raise ManifestError(f"{where}: '{key}' must be a {kind.__name__}")
    return value


def _rows(obj: Json, key: str, where: str) -> list[Json]:
    rows = _need(obj, key, list, where)
    if not all(isinstance(row, dict) for row in rows):
        raise ManifestError(f"{where}: '{key}' must hold objects")
    return list(rows)


def _key_paths(lines: list[str]) -> dict[tuple[Any, ...], list[int]]:
    """Map each key path of 2-space-indented JSON (one key per line) to its 1-based lines."""
    found: dict[tuple[Any, ...], list[int]] = {}
    stack: list[list[Any]] = []  # [path component, is array, next element index]
    for number, raw in enumerate(lines, 1):
        text = raw.strip().rstrip(",")
        top = stack[-1] if stack else None
        if text in ("}", "]"):
            stack.pop()
            continue
        match = None if top and top[1] else _KEY.match(text)
        if match:
            part, opener = json.loads(match[1]), match[2]
            path = tuple(f[0] for f in stack if f[0] is not None) + (part,)
            found.setdefault(path, []).append(number)
        else:
            part, opener = None, text
            if top and top[1]:  # an array element: its index is its path component
                part, top[2] = top[2], top[2] + 1
        if opener in ("{", "["):
            stack.append([part, opener == "[", 0])
    return found


def _only[T](items: list[T]) -> T | None:
    return items[0] if len(items) == 1 else None


def _line_of(doc: _Doc, *path: Any) -> int | None:
    return _only(_key_paths(doc.lines).get(path, []))


class _Sink:
    """The manifest's `sources`, plus the context snapshot its fields are pinned to."""

    def __init__(self, context: _Doc, as_of: str) -> None:
        self.sources: Json = {}
        self.as_of = as_of
        self._context = context
        self._paths = _key_paths(context.lines)

    def pin(self, key: str, doc: _Doc, line: int | None) -> str | None:
        if line is None:
            return None
        self.sources[key] = _pin(doc, line)
        return key

    def ctx(self, key: str, *path: Any) -> str | None:
        return self.pin(key, self._context, _only(self._paths.get(path, [])))

    def evidence(self, items: list[_Item]) -> list[str]:
        """Pin every item and return the keys; no evidence at all if any cannot be pinned."""
        if not items or any(doc is None or line is None for _, doc, line in items):
            return []
        return [str(self.pin(key, doc, line)) for key, doc, line in items if doc]


def _chosen_row(rows: list[_Row], as_of: str, current_period: str, needs_ltm: bool) -> _Row | None:
    # R-24: the chart-row rule awaits an owner ruling, so no row is chosen and no metric written.
    return None


def _chart_rows(doc: _Doc) -> dict[str, list[_Row]]:
    tables: dict[str, list[_Row]] = {}
    current, header = "", None
    for number, line in enumerate(doc.lines, 1):
        text = line.strip()
        if text.startswith("#"):
            current, header = _HEADINGS.get(text, ""), None
            if current:
                tables[current] = []
        elif current and text.startswith("|"):
            cells = [c.strip() for c in text.strip("|").split("|")]
            if header is None:
                header = cells
            elif len(cells) == len(header) and not all(re.fullmatch(r":?-+:?", c) for c in cells):
                tables[current].append(_Row(number, dict(zip(header, cells, strict=True))))
    return tables


def _row_metrics(table: str, row: _Row) -> Json:
    _, unit, fields = _TABLES[table]
    period, basis = row.cells.get("Period"), row.cells.get("Basis and limitation")
    if row.cells.get("Reporting unit") != unit or period is None or basis is None:
        return {}
    out: Json = {}
    for name, column in fields:
        cell = row.cells.get(column, "")
        if _NUMBER.fullmatch(cell) and not cell.startswith("-"):
            out[name] = {"value": cell.replace(",", ""), "unit": unit, "period": period}
            out[name] |= {"basis": basis, "source": table, "provenance": "calculated"}
    return out


def _chart_metrics(doc: _Doc | None, as_of: str, period: str, sink: _Sink) -> Json:
    metrics: Json = {}
    for table, rows in (_chart_rows(doc) if doc else {}).items():
        interim = not period.startswith("fy-") and table != "cp1_liquidity"
        row = _chosen_row(rows, as_of, period, interim)
        found = _row_metrics(table, row) if doc and row else {}
        if found and doc and row:
            sink.pin(table, doc, row.line)
            metrics |= found
    return metrics


def _user_terms(sink: _Sink, row: Json, fields: Any, prefix: str, path: tuple[Any, ...]) -> Json:
    terms: Json = {}
    for name, unit in fields:
        source = sink.ctx(f"{prefix}_{name}", *path, name) if row.get(name) else None
        if source:
            terms[name] = {"value": row[name], "unit": unit}
            terms[name] |= {"period": row.get("as_of") or sink.as_of, "basis": _BASIS_USER}
            terms[name] |= {"source": source, "provenance": "user"}
    return terms


def _facility(fid: str, deals: list[Json], quotes: list[Json], sink: _Sink, cur: str) -> Json:
    terms: Json = {}
    for i, deal in enumerate(deals):
        if deal.get("facility_id") == fid:
            fields = (("size_m", f"{deal.get('currency') or cur} m"), *_TERM_FIELDS)
            terms = _user_terms(sink, deal, fields, f"ctx_term_{i}", ("deal_terms", i))
            break
    shown = [
        {
            "kind": q.get("kind", ""),
            "terms": _user_terms(sink, q, _QUOTE_FIELDS, f"ctx_quote_{j}", ("quotes", j)),
        }
        for j, q in enumerate(quotes)
        if q.get("facility_id") == fid
    ]
    return {"facility_id": fid, "terms": terms, "quotes": shown}


def _facilities(ctx: Json, sink: _Sink, currency: str) -> list[Json]:
    deals, quotes = _rows(ctx, "deal_terms", "context"), _rows(ctx, "quotes", "context")
    ids = dict.fromkeys(r["facility_id"] for r in deals + quotes if r.get("facility_id"))
    return [_facility(fid, deals, quotes, sink, currency) for fid in ids]


def _ratings(ctx: Json, sink: _Sink) -> list[Json]:
    return [
        {
            "label": r["rating"],
            "date": r.get("as_of", ""),
            "agency": r.get("agency", ""),
            "scope": r.get("scope", ""),
            "source": src,
        }
        for i, r in enumerate(_rows(ctx, "ratings", "context"))
        if r.get("rating") and (src := sink.ctx(f"ctx_rating_{i}", "ratings", i, "rating"))
    ]


def _gaps(expectations: Json, published: bool) -> list[str]:
    by_id: Json = {}
    for item in _rows(expectations, "expectations", "expectations"):
        by_id.setdefault(str(item.get("id")), item)
    counted = _need(expectations, "counted", list, "expectations")
    gaps = [_need(by_id[i], "reason", str, "expectation") for i in counted if i in by_id]
    if not published:
        gaps.append("HTML Model not published by app runs")
    return list(dict.fromkeys(gaps))


def _receipt(root: Path, base: str) -> tuple[_Doc, Json] | None:
    found = sorted((root / base).glob("completed-*.json"))
    if len(found) > 1:
        raise ManifestError(f"{base}: more than one completion receipt")
    if not found:
        return None
    doc, data = _load(root, found[0].relative_to(root).as_posix())
    _need(data, "scope", str, doc.rel)
    _need(data, "report_sha256", str, doc.rel)
    return doc, data


def _deliveries(root: Path, base: str) -> list[_Delivery]:
    out = []
    for path in sorted((root / base / "deliveries").glob("*/delivery.json")):
        doc, data = _load(root, path.relative_to(root).as_posix())
        files = _need(data, "files", dict, doc.rel)
        out.append(_Delivery(path.parent, doc, files, _doc_if(path.parent, "report.html")))
    return out


def _chosen(deliveries: list[_Delivery], receipt_sha: str | None) -> _Delivery | None:
    if receipt_sha is None:
        return deliveries[0] if len(deliveries) == 1 else None
    return _only([d for d in deliveries if d.files.get("report.html") == receipt_sha])


def _requirement(rid: str, stage: str, evidence: list[str]) -> Json:
    return {"id": rid, "stage": stage, "done": bool(evidence), "evidence": evidence}


def _downstream(chosen: _Delivery | None, handoffs: dict[str, _Doc | None]) -> list[_Item]:
    items: list[_Item] = []
    for module, handoff in handoffs.items():
        if chosen is None:
            break
        copy = _doc_if(chosen.folder, f"{module}.md")
        ok = handoff and copy and chosen.files.get(f"{module}.md") == handoff.sha == copy.sha
        line = _line_of(chosen.doc, "files", f"{module}.md") if ok else None
        items.append((f"delivery_{module}", chosen.doc, line))
    return items


def _requirements(
    sink: _Sink,
    sources: list[str],
    handoffs: dict[str, _Doc | None],
    receipt: tuple[_Doc, Json] | None,
    chosen: _Delivery | None,
) -> list[Json]:
    reqs = [_requirement("sources", "sources", sources)]
    for module, handoff in handoffs.items():
        found: list[_Item] = [(f"handoff_{module}", handoff, 1)] if handoff else []
        reqs.append(_requirement(f"analysis-{module}", "analysis", sink.evidence(found)))
    report = chosen.report if chosen else None
    verified = receipt and report and receipt[1]["report_sha256"] == report.sha
    found = (
        [("receipt_report", receipt[0], _line_of(receipt[0], "report_sha256"))]
        if verified and receipt
        else []
    )
    reqs.append(_requirement("verification", "verification", sink.evidence(found)))
    reqs.append(
        _requirement("downstream", "downstream", sink.evidence(_downstream(chosen, handoffs)))
    )
    shipped = chosen and report and chosen.files.get("report.html") == report.sha
    found = (
        [("delivery_report", chosen.doc, _line_of(chosen.doc, "files", "report.html"))]
        if shipped and chosen
        else []
    )
    reqs.append(_requirement("delivery", "delivery", sink.evidence(found)))
    return reqs


def _identity(ctx: Json, sink: _Sink, run: Json) -> Json:
    ident = _need(ctx, "identity", dict, "context")
    name = _need(ident, "issuer_name", str, "context identity")
    source = sink.ctx("ctx_identity", "identity", "issuer_name")
    if source is None:
        raise ManifestError("context: issuer_name is not on exactly one line")
    out: Json = {"issuer": _need(ident, "issuer_id", str, "context identity")}
    out |= {"name": name, "identity_source": source}
    sector = ident.get("sector") or ""
    source = sink.ctx("ctx_sector", "identity", "sector") if sector else None
    out["sector"] = sector if source else "Unclassified"
    if source:
        out["sector_source"] = source
    grade = ident.get("issue_classification")
    if grade in ("investment_grade", "high_yield") and (
        src := sink.ctx("ctx_classification", "identity", "issue_classification")
    ):
        out |= {"classification": grade, "classification_source": src}
    if run["case_kind"] == "private" and (src := sink.ctx("ctx_private", "run", "case_kind")):
        out |= {"private_side": True, "private_side_source": src}
    return out


def build(workspace: Path, run_id: str) -> Json:
    """Return the `issuer-library-run/1` manifest of `runs/<run_id>/`; raise `ManifestError`."""
    if not run_id or run_id in (".", "..") or Path(run_id).name != run_id:
        raise ManifestError(f"invalid run id {run_id!r}")
    base = f"runs/{run_id}"
    ctx_doc, ctx = _load(workspace, f"{base}/context.json")
    expectations = _load(workspace, f"{base}/expectations.json")[1]
    wf_doc, wf = _load(workspace, f"{base}/workflow.json")
    ctx_run = _need(ctx, "run", dict, "context")
    for key in ("pathway", "as_of", "current_period", "reporting_currency", "case_kind"):
        _need(ctx_run, key, str, "context run")
    modules = _need(_need(wf, "run", dict, "workflow"), "requested_modules", list, "workflow")
    first = next(iter(_need(wf, "sources", dict, "workflow")), None)
    receipt = _receipt(workspace, base)
    chosen = _chosen(_deliveries(workspace, base), receipt[1]["report_sha256"] if receipt else None)
    handoffs = {m: _doc_if(workspace, f"{base}/{m}.md") for m in modules}
    cp1 = _doc_if(workspace, f"{base}/CP-1.md")
    sink = _Sink(ctx_doc, ctx_run["as_of"])
    period, as_of = ctx_run["current_period"], ctx_run["as_of"]
    text = ctx_run["pathway"].replace("_", " ")
    workflow = text[:1].upper() + text[1:]
    run: Json = {"id": run_id} | _identity(ctx, sink, ctx_run)
    run |= {"workflow": workflow, "title": f"{workflow} as of {as_of}", "date": as_of}
    run |= {"period": period, "period_kind": "Annual" if period.startswith("fy-") else "Interim"}
    run["currency"] = ctx_run["reporting_currency"]
    run["summary"] = receipt[1]["scope"] if receipt else "No completion receipt for this run."
    if handoff := cp1 or next((d for d in handoffs.values() if d), None):
        run["handoff"] = handoff.rel
    published = bool(receipt and receipt[1].get("cp_model_published") is True)
    run |= {"gaps": _gaps(expectations, published), "artifacts": []}
    run["ratings"] = _ratings(ctx, sink)
    run["facilities"] = _facilities(ctx, sink, ctx_run["reporting_currency"])
    run["metrics"] = _chart_metrics(cp1, as_of, period, sink)
    line = _line_of(wf_doc, "sources", first, "sha256") if first else None
    sources = sink.evidence([("wf_source_0", wf_doc, line)] if first else [])
    scope = f"App run {run_id}: requested modules and delivery"
    checklist = {
        "scope": scope,
        "requirements": _requirements(sink, sources, handoffs, receipt, chosen),
    }
    return {"schema": SCHEMA, "run": run, "sources": sink.sources, "checklist": checklist}


def write(workspace: Path, run_id: str) -> Path:
    """Write `build(...)` to `runs/<run_id>/library.json` atomically and return the path."""
    text = json.dumps(build(workspace, run_id), indent=2, ensure_ascii=False) + "\n"
    target = workspace / "runs" / run_id / "library.json"
    handle, temp = tempfile.mkstemp(dir=target.parent, prefix=".library-", suffix=".tmp")
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="") as out:
            out.write(text)
        os.replace(temp, target)
    except BaseException:
        Path(temp).unlink(missing_ok=True)
        raise
    return target
