"""Write the PDF page fixtures: tests/fixtures/pdf_pages/<DOC>/pNNN.txt and manifest.json.

Run: python3 -I cases/pdf-units/make_pages.py <dir holding <DOC>.source.json> [<repo root>]

Each file is the exact `text` of span `page:N` of the product intake (deploy_vii preparation,
pypdf 6.21.2), written as UTF-8 bytes with no change. The page choice below comes from the
preparer's own reading of each document: every primary-statement page, the page before and after
each statement, and the pages that look like a statement but are not (index, MD&A, notes, parent
company). Nothing here reads product code.
"""

import hashlib
import json
import sys
from pathlib import Path

# DOC -> page numbers (PDF page index, as in the span locator "page:N")
PAGES = {
    # 62: Item 15 index; 101: F-pages index; 104: auditor's report (page before BS);
    # 105-109: BS, IS, CI, SE, CFS; 110: notes (page after CFS)
    "TDG": [62, 101, 104, 105, 106, 107, 108, 109, 110],
    # 53: Item 8 index; 55: auditor's report; 56-61: BS, IS, CI, SE, CFS (60-61); 62: notes;
    # 101: Item 15 index
    "CZR": [53, 55, 56, 57, 58, 59, 60, 61, 62, 101],
    # 4: MD&A contents; 104: Item 15 list; 114: notes before; 115: IS and CI; 116: BS;
    # 117: CFS; 118: SE; 119: notes contents after
    "FUN": [4, 104, 114, 115, 116, 117, 118, 119],
    # 86: Item 8 index; 92: auditor's report tail; 93-97: BS, IS, CI, SE, CFS; 98: note 1;
    # 160: Item 15 index
    "SIX22": [86, 92, 93, 94, 95, 96, 97, 98, 160],
    # 2: contents; 3: divider; 4-5: SFP; 6: P&L; 7: CI; 8: SE; 9-10: CFS; 11: note 1
    "VMO2Q3": [2, 3, 4, 5, 6, 7, 8, 9, 10, 11],
    # 2: contents; 34: Financial Review cash flow summary; 106: contents of the FS section;
    # 107: P&L; 108: CI; 109-110: SFP; 111: SE; 112-113: CFS; 114: note 1;
    # 172-173: parent-company statements
    "VMED25": [2, 34, 106, 107, 108, 109, 110, 111, 112, 113, 114, 172, 173],
}


def main() -> None:
    src_dir = Path(sys.argv[1])
    root = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(".")
    for doc, pages in PAGES.items():
        src = json.loads((src_dir / f"{doc}.source.json").read_text("utf-8"))
        text = {s["locator"]: s["text"] for s in src["spans"]}
        out = root / "tests" / "fixtures" / "pdf_pages" / doc
        out.mkdir(parents=True, exist_ok=True)
        digests = {}
        for n in pages:
            raw = text[f"page:{n}"].encode("utf-8")
            (out / f"p{n:03d}.txt").write_bytes(raw)
            digests[f"{n:03d}"] = hashlib.sha256(raw).hexdigest()
        manifest = {
            "source_name": src["name"],
            "source_sha256": src["sha256"],
            "extractor": src["extractor"],
            "pages": digests,
        }
        (out / "manifest.json").write_text(
            json.dumps(manifest, indent=1, ensure_ascii=False) + "\n", "utf-8"
        )
        print(doc, len(pages), "pages")


main()
