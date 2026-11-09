"""The verification record stays short; older entries live in the archive."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / "VERIFICATION.md"
ARCHIVE = ROOT / "docs" / "VERIFICATION-ARCHIVE.md"


def _headings(path: Path) -> set[str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    return {line for line in lines if line.startswith("## ")}


def test_the_record_is_short_and_points_at_the_archive() -> None:
    text = RECORD.read_text(encoding="utf-8")
    assert len(text.splitlines()) <= 1000
    assert "docs/VERIFICATION-ARCHIVE.md" in text
    assert ARCHIVE.read_text(encoding="utf-8").startswith("# Verification archive")


def test_no_entry_is_in_both_files() -> None:
    assert _headings(RECORD).isdisjoint(_headings(ARCHIVE))
