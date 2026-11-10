"""Write the issuer library's `issuer-library-run/1` manifest for a finished app run.

Values are copied as written; nothing is calculated or converted, and a value that cannot be
pinned to exactly one source line is omitted with its field. Missing is never zero.

Standard library plus this repo's `issuer_library.events.open_regular`, which reads a workspace
file without following a link or blocking on a FIFO.
"""

from __future__ import annotations

import datetime
import errno
import hashlib
import json
import os
import re
import secrets
import stat
import sys
from pathlib import Path
from typing import Any, NamedTuple

HERE = Path(__file__).resolve().parent
ENGINE_SRC = HERE / "src" if (HERE / "src").is_dir() else HERE.parents[2] / "src"
sys.path.insert(0, str(ENGINE_SRC))

from issuer_library import discovery, events
from issuer_library.events import open_regular
from issuer_library.model import Catalogue, Manifest, Metric, Source

SCHEMA = "issuer-library-run/1"
Json = dict[str, Any]
_DATE = r"(?P<date>[0-9]{4}-[0-9]{2}-[0-9]{2})"
_KINDS = r"(?P<kind>FY[0-9]{4}|LTM|H[12] [0-9]{4}|9M [0-9]{4}|Q[1-4] [0-9]{4})"
_RATIO_PERIOD = re.compile(_KINDS + " ended " + _DATE)
_PERIODS = {
    "cp1_leverage": _RATIO_PERIOD,
    "cp1_coverage": _RATIO_PERIOD,
    "cp1_liquidity": re.compile(_DATE + r"(?P<kind>)"),
}
_FORMAT_GAP = "CP-1 chart periods are not in the fixed format"
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


class _Absent(ManifestError):
    """A folder on the way to an optional file does not exist."""


_Item = tuple[str, "_Doc | None", int | None]


class _Doc(NamedTuple):
    rel: str
    sha: str
    lines: list[str]


class _Row(NamedTuple):
    line: int
    cells: dict[str, str]


class _Delivery(NamedTuple):
    root: Path
    folder: str
    doc: _Doc
    files: dict[str, str]
    report: _Doc | None


def _read(root: Path, rel: str) -> bytes | None:
    """The file's bytes, or None when it is absent; a link or non-regular file is refused."""
    try:
        # A test that replaces `os.open` fails this check and takes the fallback below.
        if os.open in os.supports_dir_fd:
            return _read_pinned(root, Path(rel))
        # ponytail: no dir_fd (Windows): folders are checked then opened by path, so a link
        # swapped in between can be followed. Ceiling: the POSIX path above.
        for parent in reversed(Path(rel).parents):
            if parent.parts and (root / parent).is_symlink():
                raise ManifestError(f"{rel} is under a link ({parent.as_posix()})")
        with open_regular(root / rel) as stream:
            return stream.read()
    except _Absent:
        return None
    except FileNotFoundError:
        return None
    except OSError as err:
        if err.errno in (errno.ELOOP, errno.EMLINK):
            raise ManifestError(f"{rel} is a link") from err
        if err.errno in (None, errno.EOPNOTSUPP, errno.ENXIO):  # None: open_regular; others: socket
            raise ManifestError(f"{rel} is not a regular file") from err
        raise ManifestError(f"{rel} cannot be read: {err.strerror}") from err


def _read_pinned(root: Path, rel: Path) -> bytes:
    """Read `rel` through folder fds opened one name at a time, so no link is followed."""
    fds = _walk(root, rel.parts[:-1], rel.as_posix())
    try:
        with events.open_regular(Path(rel.name), dir_fd=fds[-1]) as stream:
            return stream.read()
    finally:
        _close(fds)


def _doc(root: Path, rel: str) -> _Doc:
    doc = _doc_if(root, rel)
    if doc is None:
        raise ManifestError(f"{rel} is missing")
    return doc


def _doc_if(root: Path, rel: str) -> _Doc | None:
    raw = _read(root, rel)
    if raw is None:
        return None
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as err:
        raise ManifestError(f"{rel} is not UTF-8") from err
    return _Doc(rel, hashlib.sha256(raw).hexdigest(), text.replace("\r\n", "\n").split("\n"))


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


def _chosen_row(table: str, rows: list[_Row], as_of: str) -> _Row | None:
    """R-26: the latest row on or before `as_of`; FY beats LTM on a tie; no row when ambiguous."""
    eligible: list[tuple[str, str, _Row]] = []
    for row in rows:
        found = _PERIODS[table].fullmatch(row.cells["Period"])
        kind = found["kind"] if found else "H1"
        # Liquidity has no kind and competes as one pool; interim kinds never compete.
        pool = "fy" if kind.startswith("FY") else "ltm" if kind in ("LTM", "") else ""
        if found and pool and found["date"] <= as_of:
            eligible.append((found["date"], pool, row))
    latest = max((date for date, _, _ in eligible), default="")
    fy = [r for date, pool, r in eligible if date == latest and pool == "fy"]
    ltm = [r for date, pool, r in eligible if date == latest and pool == "ltm"]
    return None if len(fy) > 1 or len(ltm) > 1 else next(iter(fy or ltm), None)


def _real_date(text: str) -> bool:
    try:
        datetime.date.fromisoformat(text)
    except ValueError:
        return False
    return True


def _period_ok(table: str, cell: str) -> bool:
    found = _PERIODS[table].fullmatch(cell)
    return found is not None and _real_date(found["date"])


def _header(table: str) -> list[str]:
    """The one header a readable chart table has: Period, its value columns, unit, basis."""
    columns = [column for _, column in _TABLES[table][2]]
    return ["Period", *columns, "Reporting unit", "Basis and limitation"]


def _scan(doc: _Doc) -> tuple[dict[str, list[_Row]], bool]:
    """Readable chart tables by key, and whether a table was dropped for an off-format Period.

    A table is unreadable when its heading repeats, its header is not exactly `_header`, or a
    row has the wrong cell count (checked first): none of these adds the gap. A row with the
    right count and a Period outside the fixed format also makes it unreadable, with the gap.
    """
    tables: dict[str, list[_Row]] = {}
    seen: set[str] = set()
    bad: set[str] = set()
    off_format = False
    current, header, exact = "", None, False
    for number, line in enumerate(doc.lines, 1):
        text = line.strip()
        if text.startswith("#"):
            current, header = _HEADINGS.get(text, ""), None
            if current:
                (bad if current in seen else seen).add(current)
                tables[current] = []
        elif current and text.startswith("|"):
            cells = [c.strip() for c in text.strip("|").split("|")]
            if header is None:
                header = cells
                exact = cells == _header(current)
                if not exact:
                    bad.add(current)
            elif not exact or all(re.fullmatch(r":?-+:?", c) for c in cells):
                continue
            elif len(cells) != len(header):
                bad.add(current)
            else:
                row = _Row(number, dict(zip(header, cells, strict=True)))
                if not _period_ok(current, row.cells.get("Period", "")):
                    bad.add(current)
                    off_format = True
                tables[current].append(row)
    return {k: v for k, v in tables.items() if k not in bad}, off_format


def _chart_rows(doc: _Doc) -> dict[str, list[_Row]]:
    return _scan(doc)[0]


def _number(cell: str) -> bool:
    """The cell is, by discovery's own reader, exactly one non-negative number."""
    return discovery.stated_numbers(cell) == [cell.replace(",", "")] and cell[0] != "-"


def _row_metrics(table: str, row: _Row) -> Json:
    _, unit, fields = _TABLES[table]
    period, basis = row.cells.get("Period"), row.cells.get("Basis and limitation")
    if row.cells.get("Reporting unit") != unit or not period or not basis:
        return {}
    out: Json = {}
    for name, column in fields:
        cell = row.cells.get(column, "")
        if _number(cell):
            out[name] = {"value": cell.replace(",", ""), "unit": unit, "period": period}
            out[name] |= {"basis": basis, "source": table, "provenance": "calculated"}
    return out


def _readable_metrics(found: Json, pin: Json) -> Json:
    """Keep the metrics discovery would admit from the pinned line, as it reads that line."""
    kept: Json = {}
    for name, metric in found.items():
        try:
            discovery.check_metric(Metric(**metric), {metric["source"]: Source(**pin)})
        except ValueError:
            continue
        kept[name] = metric
    return kept


def _chart_metrics(doc: _Doc | None, as_of: str, sink: _Sink) -> tuple[Json, bool]:
    metrics: Json = {}
    tables, off_format = _scan(doc) if doc else ({}, False)
    for table, rows in tables.items():
        row = _chosen_row(table, rows, as_of)
        found = (
            _readable_metrics(_row_metrics(table, row), _pin(doc, row.line)) if row and doc else {}
        )
        if found and doc and row:
            sink.pin(table, doc, row.line)
            metrics |= found
    return metrics, off_format


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
        folder = path.parent.relative_to(root).as_posix()
        files = _need(data, "files", dict, doc.rel)
        out.append(_Delivery(root, folder, doc, files, _doc_if(root, f"{folder}/report.html")))
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
        copy = _doc_if(chosen.root, f"{chosen.folder}/{module}.md")
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


def _check_module(name: object) -> None:
    if not isinstance(name, str) or not re.fullmatch(r"CP-[A-Z0-9]+(?:-[A-Z0-9]+)*", name):
        raise ManifestError(f"workflow: requested module {name!r} is not a plain name")


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
    for module in modules:
        _check_module(module)
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
    metrics, off_format = _chart_metrics(cp1, as_of, sink)
    gaps = _gaps(expectations, published) + ([_FORMAT_GAP] if off_format else [])
    run |= {"gaps": gaps, "artifacts": []}
    run["ratings"] = _ratings(ctx, sink)
    run["facilities"] = _facilities(ctx, sink, ctx_run["reporting_currency"])
    run["metrics"] = metrics
    line = _line_of(wf_doc, "sources", first, "sha256") if first else None
    sources = sink.evidence([("wf_source_0", wf_doc, line)] if first else [])
    scope = f"App run {run_id}: requested modules and delivery"
    checklist = {
        "scope": scope,
        "requirements": _requirements(sink, sources, handoffs, receipt, chosen),
    }
    return {"schema": SCHEMA, "run": run, "sources": sink.sources, "checklist": checklist}


def _is_link(part: str, parent: int | None) -> bool:
    """macOS reports a link under O_DIRECTORY|O_NOFOLLOW as ENOTDIR; tell the two apart."""
    try:
        return stat.S_ISLNK(os.stat(part, dir_fd=parent, follow_symlinks=False).st_mode)
    except OSError:
        return False


class _Fault(Exception):
    """Why one folder could not be opened: `kind` is link, folder, missing or `detail` text."""

    def __init__(self, kind: str, detail: str = "") -> None:
        super().__init__(kind)
        self.kind, self.detail = kind, detail


def _open_dir(part: str, parent: int | None) -> int:
    """Open one folder name under `parent` without following a link; raise `_Fault`."""
    try:
        return os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
    except OSError as err:
        if err.errno in (errno.ELOOP, errno.EMLINK) or (
            err.errno in (errno.ENOTDIR, errno.ENOENT) and _is_link(part, parent)
        ):
            raise _Fault("link") from err
        if err.errno == errno.ENOTDIR:
            raise _Fault("folder") from err
        if err.errno == errno.ENOENT:
            raise _Fault("missing") from err
        raise _Fault("other", err.strerror or "") from err


def _refusal(fault: _Fault, shown: str, file: str | None) -> ManifestError:
    """The typed error for a folder fault, naming the folder and the file being read."""
    if fault.kind == "link":
        return ManifestError(f"{file} is under a link ({shown})" if file else f"{shown} is a link")
    if fault.kind == "folder":
        return ManifestError(f"{shown} is not a folder")
    if fault.kind == "missing":
        return _Absent(f"{shown} is missing")
    return ManifestError(f"{shown} cannot be opened: {fault.detail}")


def _walk(workspace: Path, parts: tuple[str, ...], file: str | None = None) -> list[int]:
    """Open the workspace root, then each folder name under it; every fd is closed on failure."""
    fds: list[int] = []
    shown = str(workspace)
    try:
        fds.append(_open_dir(shown, None))
        for part in parts:
            shown = f"{shown}/{part}" if len(fds) > 1 else part
            fds.append(_open_dir(part, fds[-1]))
    except _Fault as fault:
        _close(fds)
        raise _refusal(fault, shown, file) from fault.__cause__
    except BaseException:
        _close(fds)
        raise
    return fds


def _close(fds: list[int]) -> None:
    for fd in reversed(fds):
        os.close(fd)


def _close_if_unowned(fd: int, ours: os.stat_result) -> None:
    """Close `fd` after a failed `os.fdopen` only if it is still our temp file: when the file
    layer had taken it, that layer already closed it and a second close would raise EBADF over
    the original error (or close a descriptor number reused since)."""
    try:
        now = os.fstat(fd)
    except OSError:  # EBADF: already closed by the file layer.
        return
    if (now.st_dev, now.st_ino) == (ours.st_dev, ours.st_ino):
        os.close(fd)


def _publish(workspace: Path, run_id: str, text: str) -> None:
    """Write `library.json` through folder fds; a link swapped in after `build` is not followed."""
    fds = _walk(workspace, ("runs", run_id))
    try:
        _admit(workspace, run_id, text)
    except BaseException:
        _close(fds)
        raise
    temp = f".library-{secrets.token_hex(8)}.tmp"
    made = False
    try:
        run_fd = fds[-1]
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
        handle = os.open(temp, flags, 0o600, dir_fd=run_fd)
        made = True
        ours = os.fstat(handle)
        try:
            out = os.fdopen(handle, "w", encoding="utf-8", newline="")
        except BaseException:
            _close_if_unowned(handle, ours)
            raise
        with out:
            out.write(text)
        os.replace(temp, "library.json", src_dir_fd=run_fd, dst_dir_fd=run_fd)
        made = False
    except BaseException as err:
        if made:
            try:
                os.unlink(temp, dir_fd=fds[-1])
            except OSError as cleanup:
                err.add_note(f"temp file {temp} was not removed: {cleanup}")
        raise
    finally:
        _close(fds)


def _admit(workspace: Path, run_id: str, text: str) -> None:
    """Run discovery's admission on the manifest text; raise `ManifestError` with its reason."""
    try:
        manifest = Manifest.model_validate_json(text)
        if manifest.schema_ != discovery.MANIFEST_SCHEMA:
            raise ValueError("unsupported run manifest schema")
        discovery.admit_run(workspace, manifest, run_id, Catalogue(workspace=str(workspace)))
    except (OSError, ValueError) as err:
        raise ManifestError(f"discovery rejects this manifest: {discovery.describe(err)}") from err


def write(workspace: Path, run_id: str) -> Path:
    """Write `build(...)` to `runs/<run_id>/library.json` atomically and return the path."""
    text = json.dumps(build(workspace, run_id), indent=2, ensure_ascii=False) + "\n"
    target = workspace / "runs" / run_id / "library.json"
    # A test that replaces `os.open` fails this membership test and runs the by-path fallback.
    if os.open not in os.supports_dir_fd:
        # ponytail: no dir_fd (Windows), so the folder path is not pinned; a link swapped in
        # between build() and this write can redirect library.json. Ceiling: the POSIX path above.
        _admit(workspace, run_id, text)
        temp = target.with_name(f".library-{secrets.token_hex(8)}.tmp")
        try:
            temp.write_text(text, encoding="utf-8", newline="")
            os.replace(temp, target)
        except BaseException:
            temp.unlink(missing_ok=True)
            raise
        return target
    _publish(workspace, run_id, text)
    return target
