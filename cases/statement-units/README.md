# Statement units of the golden HTML filings (CP1H-R18 answer key)
Frozen oracle: the primary BS, IS and CFS unit of each golden source, as `line:N` ranges of the repo's `convert_html` output (pinned by `converted_sha256`).
- Kinds: BS = balance sheet / financial position; IS = operations, income or earnings statement (the comprehensive income/loss statement when it is the only one, e.g. IHRT); CFS = cash flows. Equity statements are never units.
- Start: the line holding the statement title in its statement position (often the tail of a long line); the period/unit header and rows follow. Not a table of contents, notes or auditor's-report mention.
- End: the line before the next statement title of any kind (equity and comprehensive included) or before "Notes to...".
- One unit per kind per source; second candidates are listed under `remarks`. Non-financial sources (8-K, agreements, releases) carry every kind under `none`.
- Derived by reading the numbered converted lines directly (grep only to find candidate titles); no locating rule or probe was run or copied.
- The builder must not edit these files.
