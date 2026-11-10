"""The release version stamped by the package build; standard library only."""

from pathlib import Path


def app_version() -> str:
    """The text of VERSION beside src/ in a release, or "dev" in the repository."""
    stamp = Path(__file__).resolve().parents[2] / "VERSION"
    return stamp.read_text(encoding="utf-8").strip() if stamp.is_file() else "dev"
