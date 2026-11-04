"""Focused checks for the example's evidence and output boundary."""

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from build import admit_catalog, render_page, verify_artifact


class CatalogueTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.page_dir = self.root / "examples" / "library"
        self.page_dir.mkdir(parents=True)
        self.source = self.root / "runs" / "a" / "answer.md"
        self.source.parent.mkdir(parents=True)
        self.source.write_text("| Cash | 0 |\n")
        self.data = {
            "sources": {
                "s": {
                    "path": "runs/a/answer.md",
                    "sha256": hashlib.sha256(self.source.read_bytes()).hexdigest(),
                    "line": 1,
                    "quote": "| Cash | 0 |",
                }
            },
            "real": [],
            "illustrative": [],
        }

    def test_pins_and_relative_link(self):
        result = admit_catalog(self.data, self.root, self.page_dir)
        self.assertEqual(result["sources"]["s"]["href"], "../../runs/a/answer.md")
        self.assertNotIn("href", self.data["sources"]["s"])

    def test_changed_source_and_quote_refuse(self):
        self.source.write_text("| Cash | 9 |\n")
        with self.assertRaisesRegex(ValueError, "Changed source"):
            admit_catalog(self.data, self.root, self.page_dir)
        self.source.write_text("| Cash | 0 |\n")
        self.data["sources"]["s"]["quote"] = "| Cash | 7 |"
        with self.assertRaisesRegex(ValueError, "Source excerpt"):
            admit_catalog(self.data, self.root, self.page_dir)

    def test_escape_outside_project_refuses(self):
        self.data["sources"]["s"]["path"] = "../outside.md"
        with self.assertRaisesRegex(ValueError, "outside project"):
            admit_catalog(self.data, self.root, self.page_dir)

    def test_unverified_real_completion_refuses(self):
        self.data["real"] = [{"id": "a", "completion": 100, "checkpoints": None}]
        with self.assertRaisesRegex(ValueError, "Real completeness"):
            admit_catalog(self.data, self.root, self.page_dir)

    def test_bundle_corruption_disables_report(self):
        folder = self.root / "deliverables" / "a"
        folder.mkdir(parents=True)
        (folder / "report.html").write_text("changed")
        view = b'{"run":{"issuer_id":"TDG"}}'
        (folder / "view.json").write_bytes(view)
        (folder / "delivery.json").write_text(
            json.dumps(
                {
                    "files": {
                        "report.html": hashlib.sha256(b"original").hexdigest(),
                        "view.json": hashlib.sha256(view).hexdigest(),
                    }
                }
            )
        )
        self.data["real"] = [
            {
                "id": "a",
                "issuer": "TDG",
                "completion": None,
                "checkpoints": None,
                "metrics": {},
                "handoff": "runs/a/answer.md",
                "artifacts": [{"folder": "deliverables/a"}],
            }
        ]
        result = admit_catalog(self.data, self.root, self.page_dir)
        self.assertFalse(result["real"][0]["artifacts"][0]["available"])
        self.assertIsNone(result["real"][0]["artifacts"][0]["href"])
        self.assertIn("Changed delivery file", result["real"][0]["artifacts"][0]["issue"])

    def test_wrong_issuer_report_is_not_linked(self):
        folder = self.root / "deliverables" / "foreign"
        folder.mkdir(parents=True)
        content = {"report.html": b"report", "view.json": b'{"run":{"issuer_id":"OTHER"}}'}
        for name, raw in content.items():
            (folder / name).write_bytes(raw)
        (folder / "delivery.json").write_text(
            json.dumps(
                {"files": {name: hashlib.sha256(raw).hexdigest() for name, raw in content.items()}}
            )
        )
        result = verify_artifact(
            {"folder": "deliverables/foreign"}, self.root, self.page_dir, "TDG"
        )
        self.assertFalse(result["available"])
        self.assertIsNone(result["href"])
        self.assertIn("issuer", result["issue"])

    def test_malformed_bundle_stays_unavailable(self):
        folder = self.root / "deliverables" / "malformed"
        folder.mkdir(parents=True)
        (folder / "delivery.json").write_text('{"files":[]}')
        result = verify_artifact(
            {"folder": "deliverables/malformed"}, self.root, self.page_dir, "TDG"
        )
        self.assertFalse(result["available"])
        self.assertIsNone(result["href"])

    def test_inline_data_cannot_break_script(self):
        output = render_page("<script>/*DATA*/</script>", {"name": "</script><script>bad()"}, {})
        self.assertNotIn("</script><script>bad()", output)
        self.assertIn("\\u003c/script>", output)

    def test_real_snapshot_values_and_semantics(self):
        data = json.loads(Path(__file__).with_name("catalog.json").read_text())
        rows = {r["id"]: r for r in data["real"]}
        self.assertEqual(len(rows), 7)
        self.assertEqual(rows["tdg-002"]["metrics"]["leverage"]["value"], "5.96")
        self.assertEqual(rows["tdg-002"]["metrics"]["cashflow"]["value"], "1880")
        self.assertIn("proxy", rows["tdg-002"]["metrics"]["cashflow"]["basis"])
        self.assertIsNone(rows["tdg-003"]["metrics"]["leverage"])
        self.assertEqual(rows["tdg-003"]["metrics"]["cash"]["value"], "2459")
        self.assertEqual(rows["ford-otosan-2024-001"]["metrics"]["coverage"]["value"], "8.2")
        self.assertEqual(rows["ford-otosan-2024-001"]["currency"], "TRY")
        self.assertTrue(all(r["completion"] is None for r in rows.values()))
        self.assertTrue(all(not r["artifacts"] for r in data["illustrative"]))


if __name__ == "__main__":
    unittest.main()
