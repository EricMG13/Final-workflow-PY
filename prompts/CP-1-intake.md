# CP-1 — bounded handoff intake

This checks communication from CP-0, not full CP-1 execution. Run it only after
CP-0 has written its handoff. Input: `runs/tdg-001/CP-0.md`.

1. Read that handoff. Resolve its source and text-aid paths, verify the source
   hash, and open all five primary statement pages from its page map. Carry its
   scope and gap IDs forward. Do not use a historical CP-1 answer as evidence.
2. From the located source pages, retain a small sample: FY2024 net sales,
   FY2024 earnings per share, FY2024 weighted-average basic/diluted shares,
   cash at September 30, 2024, the common shares issued at that date, and FY2024
   operating cash flow. Keep amount, source label, quantity, unit, date/period,
   page and whether the value is reported or calculated. No new calculations.
3. Record inability to resolve a path, a date/unit conflict or an unreadable
   required page as a failed intake. Otherwise report intake success only.
4. Write `runs/tdg-001/CP-1-intake.md`. Explicitly distinguish this same-session
   handoff check from an independent model call, complete CP-1 result, automated
   module invocation or final deliverable.
