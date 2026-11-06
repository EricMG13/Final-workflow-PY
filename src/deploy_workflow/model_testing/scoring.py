"""Module scorer: compares one module result with its golden facts through the mapping
(spec 7.4, 9a, 10.3). Python owns the arithmetic; every comparison is ``Decimal``."""

from __future__ import annotations

import re
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Context, Decimal, InvalidOperation
from typing import Any, Literal, cast, get_args

from pydantic import Field

from deploy_vii.contracts import Contract, Fact, Module
from deploy_vii.cp5_integrity import UNIT_SCALE
from deploy_workflow.model_testing.cases import GoldenCase, checker
from deploy_workflow.model_testing.mapping import Locator, Mapping, MappingEntry

Outcome = Literal[
    "match",
    "mismatch",
    "missing_in_output",
    "invented",
    "gap_ok",
    "conflict_ok",
    "unmapped",
    "inherited",
]
HeadStatus = Literal["accepted", "restricted", "blocked", "refused", "absent"]

JUDGMENT_MODULES = frozenset({"CP-5", "CP-6", "CP-MODEL", "CP-2A"})
# Golden statuses that carry no value: the module should show a gap, not a figure.
_NO_VALUE_STATUSES = frozenset({"missing", "not_applicable"})

# Wide enough that scaling and quantising never round before the comparison does.
_CTX = Context(prec=120, rounding=ROUND_HALF_UP)
_PERCENT_TYPES = ("percent", "bps")
# Fact.unit semantics (display.py "percent takes a decimal fraction"; cp5_integrity.UNIT_SCALE):
# fractions hold 0.922 for 92.2 percent; decimal_percent holds points; basis_points holds bps.
_FRACTION_UNITS = frozenset({"PERCENT", "decimal_fraction"})
_POINT_UNITS = frozenset({"decimal_percent", "pp"})
_BPS_UNITS = frozenset({"basis_points"})
_RATIO_UNITS = _FRACTION_UNITS | _POINT_UNITS | _BPS_UNITS
# A currency amount (golden unit "USD", a financial_gold currency): scaled amount units, the
# statement registers' "currency" unit (report_view._MIXABLE_UNITS), or a currency code itself.
_AMOUNT_UNITS = frozenset({"UNITS", "THOUSANDS", "MILLIONS", "currency"})
_CURRENCY_CODE = re.compile(r"[A-Z]{3}", re.ASCII)  # check.py CURRENCY
# Outcomes a dependent fact inherits from: a wrong value, or one that is itself inherited.
_PASSED_UPSTREAM = frozenset({"mismatch", "inherited"})
_PRINTED_NUMBER = re.compile(r"\d[\d,]*(\.\d+)?")
_SCALE_WORD = re.compile(r"\s*(thousand|million|billion)s?\b", re.IGNORECASE)
_SCALE_WORD_EXP = {"thousand": 3, "million": 6, "billion": 9}
_DATE_FORMATS = ("%Y-%m-%d", "%B %d, %Y", "%b %d, %Y", "%d %B %Y", "%d %b %Y")


class FactScore(Contract):
    fact_id: str = Field(min_length=1)
    outcome: Outcome
    expected: str | None
    observed: str | None


class ModuleScore(Contract):
    module_id: str = Field(min_length=1)
    head_status: HeadStatus
    facts: tuple[FactScore, ...]
    untraced: tuple[str, ...]
    unscored: int = Field(ge=0)
    judgment: bool
    passed: bool


def _text(value: str) -> str:
    return str(checker().normalise(value)).casefold()


def _nonblank(items: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(x for x in items if x.strip())


def _parse_date(text: str) -> date | None:
    cleaned = str(checker().normalise(text))
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(cleaned, fmt).date()
        except ValueError:
            continue
    return None


def _is_numeric(golden: Any) -> bool:
    return bool(golden["value_type"] in checker().NUMERIC_TYPES)


def _golden_decimal(golden: Any) -> Decimal:
    return Decimal(golden["value"])


def _golden_units(golden: Any) -> Decimal:
    """Golden value in units; percent points and bps as stored."""
    value = _golden_decimal(golden)
    if golden["value_type"] in _PERCENT_TYPES:
        return value
    return value.scaleb(checker().SCALE_EXP[golden["scale"]], _CTX)


def _currency_problem(fact: Fact, currency: str) -> str | None:
    """Why the fact is not an amount in ``currency``, or None. A currency amount is a scaled
    amount unit (``UNITS``/``THOUSANDS``/``MILLIONS``, or the statement registers' ``currency``)
    or a currency code as the unit; its currency is ``Fact.currency`` and any code unit, which
    must name the golden's currency and nothing else."""
    unit = fact.unit or ""
    code = unit if _CURRENCY_CODE.fullmatch(unit) else None
    if code is None and unit not in _AMOUNT_UNITS:
        return f"unit {unit or 'none'} is not a {currency} amount"
    named = sorted({c for c in (fact.currency, code) if c})
    if named != [currency]:
        return f"currency {'/'.join(named) or 'none'} is not {currency}"
    return None


def _unit_problem(fact: Fact, golden: Any) -> str | None:
    """Why the fact's unit cannot be compared with the golden, or None."""
    unit = fact.unit or ""
    expected_scale = UNIT_SCALE.get(unit)
    if fact.amount is not None and expected_scale is not None and fact.scale != expected_scale:
        return f"unit {unit} expects scale {expected_scale}, fact has scale {fact.scale}"
    vtype = golden["value_type"]
    currency = golden.get("unit")
    if vtype == "decimal" and isinstance(currency, str) and _CURRENCY_CODE.fullmatch(currency):
        return _currency_problem(fact, currency)
    if vtype == "percent":
        ok = unit in _FRACTION_UNITS | _POINT_UNITS
    elif vtype == "bps":
        ok = unit in _BPS_UNITS
    elif currency is None and vtype == "decimal":
        ok = unit not in _POINT_UNITS | _BPS_UNITS  # a unitless ratio may be a fraction unit
    else:
        ok = unit not in _RATIO_UNITS
    if not ok:
        return f"unit {unit or 'none'} is not a {vtype} unit"
    return None


def _module_units(fact: Fact, golden: Any) -> Decimal | None:
    """Module value in the golden's terms: units, percent points or bps."""
    if fact.amount is None:
        return None
    value = _CTX.multiply(fact.amount, fact.scale)
    if fact.unit in _FRACTION_UNITS and golden["value_type"] == "percent":
        value = _CTX.multiply(value, Decimal(100))
    return value


def _numbers_equal(golden: Any, module_units: Decimal) -> bool:
    """Exact equality; a golden with fewer decimal places quantises the module value first."""
    gold = _golden_decimal(golden)
    exp = 0 if golden["value_type"] in _PERCENT_TYPES else checker().SCALE_EXP[golden["scale"]]
    in_golden_scale = module_units.scaleb(-exp, _CTX)
    gold_exp = gold.as_tuple().exponent
    if not isinstance(gold_exp, int):
        return False
    try:
        quantised = in_golden_scale.quantize(Decimal(1).scaleb(min(gold_exp, 0)), context=_CTX)
    except InvalidOperation:
        return False
    return quantised == gold


def _expected_text(golden: Any) -> str | None:
    if golden["value"] is None:
        return None
    if _is_numeric(golden):
        return format(_golden_units(golden), "f")
    return str(golden["value"])


def _observed_text(fact: Fact | None, golden: Any) -> str | None:
    if fact is None:
        return None
    if fact.amount is not None:
        units = _module_units(fact, golden)
        return None if units is None else format(units.normalize(_CTX), "f")
    return fact.text


def _resolve_periods(module: Module, loc: Locator) -> list[str | None]:
    """The periods a locator names: its literal one, or the ``id_field`` text of every row of
    the referenced register whose ``match`` cells all equal the reference (spec: model-declared
    period ids, e.g. CP-1 T4.14/T4.15)."""
    ref = loc.period_ref
    if ref is None:
        return [loc.period]
    # ponytail: O(facts) per entry; index by table if scoring ever becomes slow.
    in_table = [f for f in module.facts if f.table_id == ref.table_id]
    periods: list[str | None] = []
    for row in dict.fromkeys(f.row_id for f in in_table):
        cells = [f for f in in_table if f.row_id == row and f.text is not None]
        if all(
            any(c.field == k and _text(str(c.text)) == _text(v) for c in cells)
            for k, v in ref.match.items()
        ):
            periods.extend(c.text for c in cells if c.field == ref.id_field)
    return periods


def _locate(module: Module | None, entry: MappingEntry, golden: Any) -> list[Fact]:
    if module is None:
        return []
    loc = entry.locator
    if loc.period_ref is None:
        return _locate_at(module, loc, golden)
    found: list[Fact] = []
    for period in _resolve_periods(module, loc):
        found.extend(_locate_at(module, loc.model_copy(update={"period": period}), golden))
    return found


def _locate_at(module: Module, loc: Locator, golden: Any) -> list[Fact]:
    rk = loc.row_key
    if rk is None:
        key = (loc.table_id, loc.row_id, loc.field, loc.period)
        return [f for f in module.facts if (f.table_id, f.row_id, f.field, f.period) == key]
    candidates = {_text(str(golden["subject"]))} | {_text(a) for a in rk.aliases}
    rows = {
        f.row_id
        for f in module.facts
        if f.table_id == loc.table_id
        and f.field == rk.field
        and f.text is not None
        and _text(f.text) in candidates
    }
    return [
        f
        for f in module.facts
        if f.table_id == loc.table_id
        and f.row_id in rows
        and f.field == loc.field
        and f.period == loc.period
    ]


def _has_value(fact: Fact | None) -> bool:
    return fact is not None and fact.status == "known"


def _equal(fact: Fact, golden: Any, entry: MappingEntry) -> bool:
    vtype = golden["value_type"]
    if _is_numeric(golden):
        units = _module_units(fact, golden)
        return units is not None and _numbers_equal(golden, units)
    if fact.text is None:
        return False
    if vtype == "date":
        expected = _parse_date(str(golden["value"]))
        observed = _parse_date(fact.text)
        return expected is not None and observed == expected
    accepted = [str(golden["value"])]
    if vtype == "text":
        accepted.extend(entry.subject_aliases)
    return _text(fact.text) in {_text(x) for x in accepted}


def _printed_number(printed: str) -> Decimal | None:
    match = _PRINTED_NUMBER.search(printed)
    if match is None:
        return None
    value = Decimal(match.group().replace(",", ""))
    stripped = printed.strip()
    if (stripped.startswith("(") and stripped.endswith(")")) or stripped.startswith("-"):
        value = -value
    word = _SCALE_WORD.match(printed, match.end())
    if word is not None:
        value = value.scaleb(_SCALE_WORD_EXP[word.group(1).lower()], _CTX)
    return value


def _printed_matches(printed: str, fact: Fact, golden: Any) -> bool:
    """Whether a conflicting golden's evidenced ``printed`` value is the module's value,
    read by the golden's value_type."""
    vtype = golden["value_type"]
    if vtype == "date":
        if fact.text is None:
            return False
        if _text(fact.text) == _text(printed):
            return True
        want = _parse_date(printed)
        return want is not None and _parse_date(fact.text) == want
    if vtype not in checker().NUMERIC_TYPES:
        return fact.text is not None and _text(fact.text) == _text(printed)
    if fact.amount is None or _unit_problem(fact, golden) is not None:
        return False
    units = _module_units(fact, golden)
    want_number = _printed_number(printed)
    return units is not None and want_number is not None and want_number == units


Located = tuple[MappingEntry, list[Fact], int]  # an entry, its facts, its period_ref row count
Scored = tuple[Outcome, str | None]  # the outcome, and what to show in place of the value


def _ambiguous(facts: list[Fact], period_rows: int, status: str) -> Scored | None:
    """Two or more facts at the locator, or period rows matching its period_ref (ambiguous even
    if one holds the fact): invented where the golden has no value, else a mismatch."""
    found = max(len(facts), period_rows)
    if found <= 1:
        return None
    seen = (
        f"{found} period rows match period_ref"
        if len(facts) < period_rows
        else f"{found} facts at one locator"
    )
    if status in _NO_VALUE_STATUSES and any(_has_value(f) for f in facts):
        return "invented", seen
    return "mismatch", seen


def _conflicting(fact: Fact | None, golden: Any, module: Module) -> Outcome:
    """A conflicting golden: met by a conflicting fact, or by a limited fact holding one of the
    printed values; an omitted fact is forgiven like any omitted fact."""
    if fact is not None and fact.status == "conflicting":
        return "conflict_ok"
    if fact is None or not _has_value(fact):
        return "missing_in_output"
    limited = bool((fact.limitation or "").strip() or _nonblank(module.limitations))
    printed = (str(ev.get("printed", "")) for ev in golden.get("evidence") or ())
    if limited and any(_printed_matches(p, fact, golden) for p in printed):
        return "conflict_ok"
    return "mismatch"


def _valued(entry: MappingEntry, fact: Fact, golden: Any, upstream: frozenset[str]) -> Scored:
    """A known golden against a fact with a value. A unit or currency problem is a mismatch
    that shows the problem and is never excused as inherited."""
    if _is_numeric(golden) and fact.amount is not None:
        problem = _unit_problem(fact, golden)
        if problem is not None:
            return "mismatch", problem
    if _equal(fact, golden, entry):
        return "match", None
    inherited = bool((set(entry.depends_on) - {entry.fact_id}) & upstream)
    return ("inherited" if inherited else "mismatch"), None


def _outcome(located: Located, golden: Any, module: Module, upstream: frozenset[str]) -> Scored:
    entry, facts, period_rows = located
    status = golden["status"]
    fact = facts[0] if facts else None
    ambiguous = _ambiguous(facts, period_rows, status)
    if ambiguous is not None:
        return ambiguous
    if status in _NO_VALUE_STATUSES:
        return ("invented" if _has_value(fact) else "gap_ok"), None
    if status == "conflicting":
        return _conflicting(fact, golden, module), None
    if fact is None or not _has_value(fact):
        return "missing_in_output", None
    return _valued(entry, fact, golden, upstream)


def _score_entry(
    located: Located, golden: Any, module: Module, upstream: frozenset[str]
) -> FactScore:
    entry, facts, _ = located
    outcome, seen = _outcome(located, golden, module, upstream)
    return FactScore(
        fact_id=entry.fact_id,
        outcome=outcome,
        expected=_expected_text(golden),
        observed=_observed_text(facts[0] if facts else None, golden) if seen is None else seen,
    )


def _traced(fact: Fact) -> bool:
    return bool(fact.citations) or fact.calculation_id is not None


def upstream_ids(score: ModuleScore) -> frozenset[str]:
    """The fact ids a dependent fact can inherit an error from: each mismatch, and each fact
    that is itself inherited (its error came from further up the chain)."""
    return frozenset(f.fact_id for f in score.facts if f.outcome in _PASSED_UPSTREAM)


def _census(live: Module, located: list[Located]) -> tuple[tuple[str, ...], int]:
    """Known amount facts without a citation or calculation (untraced), and traced ones at no
    mapped locator (unscored)."""
    mapped = {(f.table_id, f.row_id, f.field, f.period) for _, facts, _ in located for f in facts}
    untraced: list[str] = []
    unscored = 0
    for fact in live.facts:
        if fact.status != "known" or fact.amount is None:
            continue
        if not _traced(fact):
            untraced.append(fact.fact_id)
        elif (fact.table_id, fact.row_id, fact.field, fact.period) not in mapped:
            unscored += 1
    return tuple(untraced), unscored


def _score_located(
    located: list[Located], case: GoldenCase, live: Module, upstream: frozenset[str]
) -> list[FactScore]:
    """Score every entry. The module's own mismatched and inherited facts join the upstream set
    and the entries are scored again until it stops growing, so a dependency inside one module
    can score ``inherited`` whatever the mapping's entry order."""
    known = upstream
    while True:
        scores = [_score_entry(x, case.facts[x[0].fact_id], live, known) for x in located]
        grown = known | {s.fact_id for s in scores if s.outcome in _PASSED_UPSTREAM}
        if grown == known:
            return scores
        known = grown


def _no_result(golden: Any, fid: str) -> FactScore:
    """An entry of a module with no result to read: a golden gap is met, a value is missing."""
    outcome: Outcome = "gap_ok" if golden["status"] in _NO_VALUE_STATUSES else "missing_in_output"
    return FactScore(fact_id=fid, outcome=outcome, expected=_expected_text(golden), observed=None)


def _unmapped_scores(case: GoldenCase, mapping: Mapping, module_id: str) -> list[FactScore]:
    scores: list[FactScore] = []
    listed = {e.fact_id for e in mapping.entries if e.module == module_id}
    for u in mapping.unmapped:
        if u.fact_id in case.facts and case.facts[u.fact_id]["module"] == module_id:
            scores.append(_unmapped(case, u.fact_id))
            listed.add(u.fact_id)
    for fid in sorted(mapping.pending(case)):
        if case.facts[fid]["module"] == module_id and fid not in listed:
            scores.append(_unmapped(case, fid))
    return scores


def _passed(
    module: Module | None, head: HeadStatus, refused_honestly: bool, score: ModuleScore
) -> bool:
    """Whether the module passes, from its scores (``score.passed`` is not read)."""
    outcomes = {s.outcome for s in score.facts}
    bad = "invented" in outcomes or bool(score.untraced)
    if refused_honestly:
        # the module named what it lacked: pass only if it invented nothing
        return not bad and "mismatch" not in outcomes
    if module is None or head == "absent" or head == "refused":
        return False  # no usable module result never passes
    if score.judgment:
        return not bad  # no value facts required
    # The module itself declares the limit (spec 10.3): blocked or restricted only.
    honest_gap = head in ("blocked", "restricted") and bool(_nonblank(module.limitations))
    return (
        not bad
        and "mismatch" not in outcomes
        and ("missing_in_output" not in outcomes or honest_gap)
    )


def score_module(
    module: Module | None,
    module_id: str,
    head_status: str,
    case: GoldenCase,
    mapping: Mapping,
    upstream_mismatches: frozenset[str],
    refusal_missing: tuple[str, ...] = (),
) -> ModuleScore:
    """Score one module. ``upstream_mismatches`` holds the ``upstream_ids`` of the modules
    scored before it; a fact depending on one of them, or on a mismatched or inherited fact of
    this module, scores ``inherited`` instead of ``mismatch``."""
    if head_status not in get_args(HeadStatus):
        raise ValueError(f"head_status {head_status!r} is not one of {get_args(HeadStatus)}")
    head = cast(HeadStatus, head_status)
    entries = [e for e in mapping.entries if e.module == module_id]
    refusal = _nonblank(refusal_missing)
    refused_honestly = head == "refused" and bool(refusal)
    # An absent head, or a refusal naming nothing, has no module result to read.
    usable = head != "absent" and (head != "refused" or refused_honestly)
    live = module if usable else None
    untraced: tuple[str, ...] = ()
    unscored = 0
    if live is None:
        scores = [_no_result(case.facts[e.fact_id], e.fact_id) for e in entries]
    else:
        located: list[Located] = [
            (
                e,
                _locate(live, e, case.facts[e.fact_id]),
                len(_resolve_periods(live, e.locator)) if e.locator.period_ref is not None else 0,
            )
            for e in entries
        ]
        untraced, unscored = _census(live, located)
        scores = _score_located(located, case, live, upstream_mismatches)
    if refused_honestly:
        observed = "refused: " + ", ".join(refusal)
        scores = [
            s.model_copy(update={"outcome": "gap_ok", "observed": observed})
            if live is None or s.outcome == "missing_in_output"
            else s
            for s in scores
        ]
    score = ModuleScore(
        module_id=module_id,
        head_status=head,
        facts=(*scores, *_unmapped_scores(case, mapping, module_id)),
        untraced=untraced,
        unscored=unscored,
        judgment=module_id in JUDGMENT_MODULES,
        passed=False,
    )
    return score.model_copy(update={"passed": _passed(module, head, refused_honestly, score)})


def _unmapped(case: GoldenCase, fid: str) -> FactScore:
    return FactScore(
        fact_id=fid, outcome="unmapped", expected=_expected_text(case.facts[fid]), observed=None
    )
