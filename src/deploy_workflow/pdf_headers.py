"""Mapping-only recovery of printed PDF period headings.

This module deliberately returns only synthetic header rows. It never edits the
extracted table or its evidence.
"""

from __future__ import annotations

import re
from datetime import date
from itertools import pairwise
from typing import Literal

_MONTH = r"January|February|March|April|May|June|July|August|September|October|November|December"
_DUR = re.compile(
    r"(?i)(three|six|nine|twelve)\s+months?\s+ended|(?:fiscal\s+)?years?\s+ended|year\s+ended"
)
_YEARS = re.compile(r"(?<!\d)(?:19|20)\d{2}(?!\d)")
_DATE = re.compile(
    rf"(?i)({_MONTH})\s+(\d{{1,2}}),?\s+(\d{{4}})|(?<!\d)(\d{{1,2}})\s+({_MONTH})\s+(\d{{4}})"
)
# The day is not followed by another digit: in "June 2024" the "20" is the start of a year.
_MONTH_DAY = re.compile(rf"(?i)({_MONTH})\s+(\d{{1,2}})(?!\d)|(?<!\d)(\d{{1,2}})\s+({_MONTH})")
_DURATION = re.compile(
    r"(?i)(?<![A-Za-z])(?:(three|six|nine|twelve)\s+months?|(?:fiscal\s+)?years?)\s+ended\b"
)
_TITLE = re.compile(
    r"(?i)^\s*(?:(?:condensed|consolidated)\s+)*(?:"
    r"balance\s+sheets?|financial\s+position|income\s+statement|"
    r"statements?\s+of\s+(?:operations|income|cash\s+flows?|"
    r"comprehensive\s+income(?:\s*\(loss\))?|financial\s+position|profit)|"
    r"statement\s+of\s+(?:operations|income|cash\s+flows?|financial\s+position))"
    r"(?:\s*\([^)]*\))?\s*$"
)
_TITLE_STEM = re.compile(r"(?i)^\s*(?:(?:condensed|consolidated)\s+)*statements?\s*$")
_TITLE_CONTINUATION = re.compile(
    r"(?i)^\s*of\s+(?:profit|financial\s+position|comprehensive\s+income|income|cash\s+flows?)\b"
)
_MONTHS = {
    m.lower(): i
    for i, m in enumerate(
        [
            "January",
            "February",
            "March",
            "April",
            "May",
            "June",
            "July",
            "August",
            "September",
            "October",
            "November",
            "December",
        ],
        1,
    )
}


def _cells(line: str) -> list[str]:
    return [part.strip() for part in re.split(r"\s{2,}", line.strip()) if part.strip()]


def _iso(month: str, day: str, year: str) -> str | None:
    try:
        return date(int(year), _MONTHS[month.lower()], int(day)).isoformat()
    except (ValueError, KeyError):
        return None


def _duration_labels(line: str) -> list[str] | None:
    """Parse whole supported duration phrases plus the adopted decorations."""
    matches = list(_DURATION.finditer(line))
    if not matches:
        return None
    residue = line
    for found in reversed(matches):
        residue = residue[: found.start()] + " " + residue[found.end() :]
    residue = re.sub(r"(?i)\bfor\s+the\b", " ", residue)
    residue = re.sub(rf"(?i)\b(?:{_MONTH})\b", " ", residue)
    residue = re.sub(r"\d+|[^A-Za-z]+", " ", residue)
    if residue.strip():
        return None
    return [match.group(1).title() if match.group(1) else "Year" for match in matches]


def _statement_title_start(lines: list[str]) -> int | None:
    """Find a recognized title, including the common two-line IFRS title."""
    titles = []
    for index, line in enumerate(lines):
        if _TITLE.fullmatch(line) or (
            _TITLE_STEM.fullmatch(line)
            and index + 1 < len(lines)
            and _TITLE_CONTINUATION.match(lines[index + 1])
        ):
            titles.append(index)
    return titles[-1] if titles else None


def mapping_headers(  # noqa: C901, PLR0911, PLR0912, PLR0915 - pre-existing (C901 52 at base, 48 now)
    page_text: str, *, first_data_line: int, statement: Literal["BS", "IS", "CFS"]
) -> tuple[str, ...] | None:
    """Recover coherent column headers from this page before its first data row."""
    lines = page_text.splitlines()[: max(0, first_data_line - 1)]
    # The unit's recognized title is the metadata boundary. A continuation
    # without a title must carry its own printed header; later row captions
    # cannot replace a valid header above them.
    title_start = _statement_title_start(lines)
    if title_start is not None:
        lines = lines[title_start:]
    candidates = []
    for line in lines:
        if (
            _DUR.search(line)
            or _YEARS.search(line)
            or _DATE.search(line)
            or _MONTH_DAY.search(line)
        ):
            candidates.append(line)
    if not candidates:
        return None
    # Most recent typed header controls flow semantics; a date-only row cannot
    # rescue a malformed or durationless income/cash-flow header.
    duration_lines = [line for line in candidates if _duration_labels(line)]
    if statement != "BS" and not duration_lines:
        return None
    years_line = next((line for line in reversed(candidates) if _YEARS.search(line)), None)
    if years_line is None:
        # Complete dates already carry their years.
        full = _DATE.findall(" ".join(candidates))
        if len(full) < 1:
            return None
        dates = []
        for match in full:
            month, day, year = (
                (match[0], match[1], match[2]) if match[0] else (match[4], match[3], match[5])
            )
            iso = _iso(month, day, year)
            if iso is None:
                return None
            dates.append(date.fromisoformat(iso).strftime("%B %d, %Y"))
        if statement == "BS":
            return (" | ".join(dates),)
        # Ensure each printed end date has a printed duration.
        span = duration_lines[-1]
        spans = _DUR.findall(span)
        if not spans:
            return None
        return (" | ".join(_canonical_duration(span, d) for d in dates),)
    years = _YEARS.findall(years_line)
    if len(years) < 2:
        return None
    year_matches = list(_YEARS.finditer(years_line))
    for left, right in pairwise(year_matches):
        residue = years_line[left.end() : right.start()]
        residue = re.sub(rf"(?i)\b(?:notes?|references?|{_MONTH})\b", " ", residue)
        if re.search(r"[A-Za-z]", residue):
            return None
    residue = years_line[year_matches[-1].end() :]
    residue = re.sub(rf"(?i)\b(?:notes?|references?|{_MONTH})\b", " ", residue)
    if re.search(r"[A-Za-z]", residue):
        return None
    if statement == "BS":
        # Bind column-specific dates in order; a single explicit AS OF date can
        # cover bare year columns only when that is what the page prints.
        dates = _DATE.findall(" ".join(candidates))
        full_dates = []
        for found in dates:
            month, day, year = (
                (found[0], found[1], found[2]) if found[0] else (found[4], found[3], found[5])
            )
            iso = _iso(month, day, year)
            if iso is None:
                return None
            full_dates.append(date.fromisoformat(iso))
        if len(full_dates) == 1 and str(full_dates[0].year) != years[0]:
            return None
        if len(full_dates) == len(years):
            return (" | ".join(d.strftime("%B %d, %Y") for d in full_dates),)
        md = []
        for candidate in candidates:
            for found in _MONTH_DAY.findall(candidate):
                md.append((found[0], found[1]) if found[0] else (found[3], found[2]))
        if len(md) == len(years):
            full = [_iso(month, day, year) for (month, day), year in zip(md, years, strict=True)]
        elif len(md) == 1:
            full = [_iso(md[0][0], md[0][1], year) for year in years]
        else:
            return None
        if any(v is None for v in full):
            return None
        return (" | ".join(date.fromisoformat(v).strftime("%B %d, %Y") for v in full if v),)
    if not duration_lines:
        return None
    dline = duration_lines[-1]
    # Normalize supported day-first and month-first span headings to the existing matcher syntax.
    normalized = re.sub(rf"(?i)(\d{{1,2}})\s+({_MONTH})", r"\2 \1", dline)
    durations = _duration_labels(dline)
    if durations is None:
        return None
    month_days = []
    # Only month/day cells following the selected duration row belong to that
    # header; earlier report banners frequently repeat the document end date.
    selected = lines.index(dline)
    for candidate in lines[selected:]:
        if candidate == years_line:
            break
        for match in _MONTH_DAY.findall(candidate):
            month_days.append((match[0], match[1]) if match[0] else (match[3], match[2]))
    if not month_days:
        fallback = _MONTH_DAY.findall(normalized)
        if fallback:
            month_days = [
                (fallback[0][0], fallback[0][1])
                if fallback[0][0]
                else (fallback[0][3], fallback[0][2])
            ]
    complete_dates = []
    for found in _DATE.findall(years_line):
        mo, day, yr = (found[0], found[1], found[2]) if found[0] else (found[4], found[3], found[5])
        if _iso(mo, day, yr) is None:
            return None
        complete_dates.append((mo, day, yr))
    explicit_span_date = _MONTH_DAY.findall(dline)
    if explicit_span_date and complete_dates:
        span_mds = [(x[0], x[1]) if x[0] else (x[3], x[2]) for x in explicit_span_date]
        for index, (month, day, _) in enumerate(complete_dates):
            if index < len(span_mds) and (month.lower(), str(int(day))) != (
                span_mds[index][0].lower(),
                str(int(span_mds[index][1])),
            ):
                return None
    if not month_days and complete_dates:
        month_days = [(m, d) for m, d, _ in complete_dates]
    if not month_days:
        return None
    span_tokens = durations
    is_year = "year" in dline.lower()
    kinds = [
        (x.title(), 12 if is_year else {"three": 3, "six": 6, "nine": 9, "twelve": 12}[x.lower()])
        for x in span_tokens
    ] or [("Year", 12)]
    if (
        complete_dates
        and len(complete_dates) < len(years)
        and len(month_days) + len(complete_dates) == len(years)
    ):
        month_days = [(m, d) for m, d, _ in complete_dates] + month_days
    elif len(complete_dates) == len(years):
        month_days = [(m, d) for m, d, _ in complete_dates]
    if len(month_days) not in (1, len(kinds), len(years)):
        return None
    if len(kinds) > 1 and len(years) % len(kinds):
        return None
    if is_year:
        ends = []
        for i, year in enumerate(years):
            month, day = (
                month_days[i]
                if len(month_days) == len(years)
                else month_days[i // max(1, len(years) // len(month_days))]
                if len(month_days) > 1
                else month_days[0]
            )
            end = _iso(month, day, year)
            if end is None:
                return None
            ends.append("FY " + end)
        return (" | ".join(ends),)
    spanrow = []
    for i in range(len(years)):
        kind, _ = kinds[min(len(kinds) - 1, i // max(1, len(years) // len(kinds)))]
        md_index = (
            i
            if len(month_days) == len(years)
            else (i // max(1, len(years) // len(month_days)) if len(month_days) > 1 else 0)
        )
        month, day = month_days[md_index]
        label = "Year Ended " if kind == "Year" else f"{kind} Months Ended "
        spanrow.append(label + month.title() + " " + day)
    span_row_text = " | ".join(spanrow)
    # One span per column permits distinct ends under a mixed year/date header.
    return (span_row_text, " | ".join(years))


def _canonical_duration(text: str, iso: str) -> str:
    month, day = date.fromisoformat(iso).strftime("%B"), date.fromisoformat(iso).day
    m = re.search(r"(?i)(three|six|nine|twelve)\s+months?", text)
    label = m.group(1).title() + " Months Ended " if m else "Year Ended "
    return label + month + " " + str(day)
