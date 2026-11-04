"""Write cases/column-periods/SHC.json and TDG.json: the column -> period oracle (CP1H-R23, F1).

Run from the repo root: python3 -I cases/column-periods/make_column_periods.py

For every statement unit (BS, IS, CFS) of cases/statement-rows (frozen CP1H-R18 key, branch
claude/cp1h-t16-impl) for SHC and TDG, the columns in printed order, each with the header text as
printed and the period it names. The preparer read the header lines of the converted filing text
(title line, then the 'As of' / 'Months Ended' line, then the date line) and wrote the periods by
hand. No product parser or locator was read or run.

Locator key: "<source_id>|<kind>|<start>-<end>" with start/end the unit's `line:N` bounds in
cases/statement-rows (line numbers of the repo's convert_html output).

Period kinds: instant (balance sheet date, start null), quarter (three months or thirteen weeks),
half (six months or twenty-six weeks), nine_months (thirty-nine weeks), year (twelve months).

TDG fiscal quarters are counted in weeks. The filing prints no start date, and week counts back from
the end date conflict with the October 1 fiscal-year start for some columns, so a week-based column
has start null with "uncertain". Tests compare kind and end only.
"""

import json
from datetime import date
from pathlib import Path

OUT = Path("cases") / "column-periods"

NO_START = "start not printed; week counts back from the end date conflict with the October 1 fiscal-year start for some columns"


def inst(text, end):
    return {"header_text": text, "period": {"kind": "instant", "start": None, "end": end}}


def per(text, kind, start, end):
    return {"header_text": text, "period": {"kind": kind, "start": start, "end": end}}


def weeks(text, kind, end, why=NO_START):
    col = {"header_text": text, "period": {"kind": kind, "start": None, "end": end}}
    col["uncertain"] = why
    return col


def weeks39(text, end):
    col = weeks(text, "nine_months", end)
    return col


def unit(source_id, kind, start, end, columns, note=None):
    key = f"{source_id}|{kind}|{start}-{end}"
    entry = {"source_id": source_id, "kind": kind, "start": start, "end": end, "columns": columns}
    if note:
        entry["header_lines"] = note
    return key, entry


SHC_Q = "SHC_2025-06-30_10-Q_0001822479-25-000044_shc-20250630"
SHC_K = "SHC_2024-12-31_10-K_0001822479-25-000015_shc-20241231"

SHC = dict(
    [
        unit(
            SHC_Q,
            "BS",
            "line:33",
            "line:81",
            [
                inst("June 30, 2025", "2025-06-30"),
                inst("December 31, 2024", "2024-12-31"),
            ],
            "line 34 'As of'; line 35 'June 30, 2025 December 31, 2024'",
        ),
        unit(
            SHC_Q,
            "IS",
            "line:82",
            "line:114",
            [
                per("Three Months Ended June 30, 2025", "quarter", "2025-04-01", "2025-06-30"),
                per("Three Months Ended June 30, 2024", "quarter", "2024-04-01", "2024-06-30"),
                per("Six Months Ended June 30, 2025", "half", "2025-01-01", "2025-06-30"),
                per("Six Months Ended June 30, 2024", "half", "2024-01-01", "2024-06-30"),
            ],
            "line 83 'Three Months Ended June 30, Six Months Ended June 30,'; line 84 '2025 2024 2025 2024'",
        ),
        unit(
            SHC_Q,
            "CFS",
            "line:115",
            "line:162",
            [
                per("Six Months Ended June 30, 2025", "half", "2025-01-01", "2025-06-30"),
                per("Six Months Ended June 30, 2024", "half", "2024-01-01", "2024-06-30"),
            ],
            "line 116 'Six Months Ended June 30,'; line 117 '2025 2024'",
        ),
        unit(
            SHC_K,
            "BS",
            "line:217",
            "line:266",
            [
                inst("December 31, 2024", "2024-12-31"),
                inst("December 31, 2023", "2023-12-31"),
            ],
            "line 218 'As of December 31,'; line 219 '2024 2023'",
        ),
        unit(
            SHC_K,
            "IS",
            "line:267",
            "line:305",
            [
                per("Year Ended December 31, 2024", "year", "2024-01-01", "2024-12-31"),
                per("Year Ended December 31, 2023", "year", "2023-01-01", "2023-12-31"),
                per("Year Ended December 31, 2022", "year", "2022-01-01", "2022-12-31"),
            ],
            "line 268 'Year Ended December 31,'; line 269 '2024 2023 2022'",
        ),
        unit(
            SHC_K,
            "CFS",
            "line:306",
            "line:357",
            [
                per("Year Ended December 31, 2024", "year", "2024-01-01", "2024-12-31"),
                per("Year Ended December 31, 2023", "year", "2023-01-01", "2023-12-31"),
                per("Year Ended December 31, 2022", "year", "2022-01-01", "2022-12-31"),
            ],
            "line 307 'Year Ended December 31,'; line 308 '2024 2023 2022'",
        ),
    ]
)

W13_26 = "Thirteen Week Periods Ended"
W26 = "Twenty-Six Week Periods Ended"
W13 = "Thirteen Week Periods Ended"
W39 = "Thirty-Nine Week Periods Ended"
FY = "Fiscal Years Ended September 30,"

TDG = dict(
    [
        # Q2 FY24 10-Q (quarter ended March 30, 2024)
        unit(
            "Q2FY24",
            "BS",
            "line:42",
            "line:77",
            [
                inst("March 30, 2024", "2024-03-30"),
                inst("September 30, 2023", "2023-09-30"),
            ],
            "line 43 'March 30, 2024 September 30, 2023'",
        ),
        unit(
            "Q2FY24",
            "IS",
            "line:78",
            "line:100",
            [
                weeks(f"{W13_26} March 30, 2024", "quarter", "2024-03-30"),
                weeks(f"{W13_26} April 1, 2023", "quarter", "2023-04-01"),
                weeks(f"{W26} March 30, 2024", "half", "2024-03-30"),
                weeks(f"{W26} April 1, 2023", "half", "2023-04-01"),
            ],
            "line 79 'Thirteen Week Periods Ended Twenty-Six Week Periods Ended'; line 80 'March 30, 2024 April 1, 2023 March 30, 2024 April 1, 2023'",
        ),
        unit(
            "Q2FY24",
            "CFS",
            "line:171",
            "line:215",
            [
                weeks(f"{W26} March 30, 2024", "half", "2024-03-30"),
                weeks(f"{W26} April 1, 2023", "half", "2023-04-01"),
            ],
            "line 172 'Twenty-Six Week Periods Ended'; line 173 'March 30, 2024 April 1, 2023'",
        ),
        # Q3 FY24 10-Q (quarter ended June 29, 2024)
        unit(
            "Q3FY24",
            "BS",
            "line:40",
            "line:74",
            [
                inst("June 29, 2024", "2024-06-29"),
                inst("September 30, 2023", "2023-09-30"),
            ],
            "line 41 'June 29, 2024 September 30, 2023'",
        ),
        unit(
            "Q3FY24",
            "IS",
            "line:75",
            "line:97",
            [
                weeks(f"{W13} June 29, 2024", "quarter", "2024-06-29"),
                weeks(f"{W13} July 1, 2023", "quarter", "2023-07-01"),
                weeks39(f"{W39} June 29, 2024", "2024-06-29"),
                weeks39(f"{W39} July 1, 2023", "2023-07-01"),
            ],
            "line 76 'Thirteen Week Periods Ended Thirty-Nine Week Periods Ended'; line 77 'June 29, 2024 July 1, 2023 June 29, 2024 July 1, 2023'",
        ),
        unit(
            "Q3FY24",
            "CFS",
            "line:186",
            "line:235",
            [
                weeks39(f"{W39} June 29, 2024", "2024-06-29"),
                weeks39(f"{W39} July 1, 2023", "2023-07-01"),
            ],
            "line 187 'Thirty-Nine Week Periods Ended'; line 188 'June 29, 2024 July 1, 2023'",
        ),
        # FY24 10-K (fiscal year ended September 30, 2024)
        unit(
            "K24",
            "BS",
            "line:898",
            "line:933",
            [
                inst("2024", "2024-09-30"),
                inst("2023", "2023-09-30"),
            ],
            "title line 898 'AS OF SEPTEMBER 30, 2024 AND 2023'; line 899 '2024 2023'",
        ),
        unit(
            "K24",
            "IS",
            "line:934",
            "line:960",
            [
                per(f"{FY} 2024", "year", "2023-10-01", "2024-09-30"),
                per(f"{FY} 2023", "year", "2022-10-01", "2023-09-30"),
                per(f"{FY} 2022", "year", "2021-10-01", "2022-09-30"),
            ],
            "line 935 'Fiscal Years Ended September 30,'; line 936 '2024 2023 2022'. Fiscal years end on September 30 (the balance sheet dates and the equity roll-forward balances at September 30), so each starts on October 1 of the prior year.",
        ),
        unit(
            "K24",
            "CFS",
            "line:1015",
            "line:1067",
            [
                per(f"{FY} 2024", "year", "2023-10-01", "2024-09-30"),
                per(f"{FY} 2023", "year", "2022-10-01", "2023-09-30"),
                per(f"{FY} 2022", "year", "2021-10-01", "2022-09-30"),
            ],
            "line 1016 'Fiscal Years Ended September 30,'; line 1017 '2024 2023 2022'",
        ),
        # Q1 FY25 10-Q (quarter ended December 28, 2024)
        unit(
            "Q1FY25",
            "BS",
            "line:40",
            "line:75",
            [
                inst("December 28, 2024", "2024-12-28"),
                inst("September 30, 2024", "2024-09-30"),
            ],
            "line 41 'December 28, 2024 September 30, 2024'",
        ),
        unit(
            "Q1FY25",
            "IS",
            "line:76",
            "line:97",
            [
                weeks(f"{W13} December 28, 2024", "quarter", "2024-12-28"),
                weeks(f"{W13} December 30, 2023", "quarter", "2023-12-30"),
            ],
            "line 77 'Thirteen Week Periods Ended'; line 78 'December 28, 2024 December 30, 2023'",
        ),
        unit(
            "Q1FY25",
            "CFS",
            "line:150",
            "line:195",
            [
                weeks(f"{W13} December 28, 2024", "quarter", "2024-12-28"),
                weeks(f"{W13} December 30, 2023", "quarter", "2023-12-30"),
            ],
            "line 151 'Thirteen Week Periods Ended'; line 152 'December 28, 2024 December 30, 2023'",
        ),
    ]
)


def check(doc: dict) -> None:
    for key, u in doc.items():
        for c in u["columns"]:
            p = c["period"]
            e = date.fromisoformat(p["end"])
            if p["start"] is not None:
                assert date.fromisoformat(p["start"]) < e, key
            if p["kind"] == "instant":
                assert p["start"] is None, key
            elif p["start"] is None:
                assert "uncertain" in c, (key, c["header_text"])
            assert p["kind"] in {"instant", "quarter", "half", "year", "nine_months"}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, doc in (("SHC", SHC), ("TDG", TDG)):
        check(doc)
        (OUT / f"{name}.json").write_text(
            json.dumps(doc, indent=1, ensure_ascii=False) + "\n", "utf-8"
        )
        print(name, len(doc), "units", sum(len(u["columns"]) for u in doc.values()), "columns")


main()
