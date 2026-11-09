"""Phase 5 Task 6 (B17 item 4): the model-facing CP-4 text names draft sources on a draft run.

Wording only. The answer key is the imported `methods/cp4.md` and `live/context.py` sha256 the
D12 records pin as their prior (preflight P5-P12): putting the old words back must give exactly
those files, so no other sentence changed.
"""

import hashlib
import re
from pathlib import Path

import deploy_vii.live.context as live_context
from deploy_vii.live.prompts import CP4_METHOD

SRC = Path(__file__).resolve().parents[1] / "src" / "deploy_vii"
PHRASE = "executed, filed or, on a draft-documents run, draft"
OLD_CP4_SHA = "99ec34c7a8257e15325456eb5466388eeb656fa01cf30db91e8474334bb39ff0"
# S13 C01 restated the kpi evidence line (period_basis_id); S09 C06 passes the caller's
# python_checks to integrity_projection (integrity_scope); S14-C06 passes an already-built
# pack to the source scopes (`session_scope`); S13-vii-canonical-context-A07 adds the
# narrative `financial_dimensions` context line (narrative_evidence). The pin is the CURRENT file
# less the phrase, so it follows every later edit of context.py; it no longer pins the imported
# text.
CONTEXT_WITHOUT_PHRASE_SHA = "54ffb55c5b1c77255b4ab8d464d9bfb4de14da7303a72c1901d091c1fc8fd78e"


def flat(text: str) -> str:
    return re.sub(r"\s+", " ", text)


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def test_cp4_md_names_draft_sources_in_both_places() -> None:
    text = flat((SRC / "methods" / "cp4.md").read_text(encoding="utf-8"))
    assert f"(CP-0 classes them {PHRASE})" in text
    assert f"Sources: only {PHRASE} sources are cited" in text
    assert text.count(PHRASE) == 2


def test_the_cp4_method_the_model_is_sent_carries_the_phrase() -> None:
    assert PHRASE in flat(CP4_METHOD)


def test_the_context_docstring_names_draft_sources() -> None:
    assert f"CP-4 is sent the ready sources CP-0 classes {PHRASE}" in flat(
        live_context.__doc__ or ""
    )


def test_cp4_md_differs_from_the_imported_text_only_by_the_two_phrases() -> None:
    text = (SRC / "methods" / "cp4.md").read_text(encoding="utf-8")
    new_one = "(CP-0 classes them executed,\nfiled or, on a draft-documents run, draft);"
    new_two = (
        "- Sources: only executed, filed or, on a draft-documents run, draft sources are cited, "
        "whole documents\n  as the pack holds them (ruling 1)."
    )
    old_two = (
        "- Sources: only executed and filed sources are cited, whole documents as the pack holds "
        "them\n  (ruling 1)."
    )
    assert text.count(new_one) == 1 and text.count(new_two) == 1
    old = text.replace(new_one, "(CP-0 classes them executed\nor filed);")
    assert sha(old.replace(new_two, old_two)) == OLD_CP4_SHA


def test_context_py_without_the_phrase_matches_the_pin_of_the_current_file() -> None:
    """The current context.py, phrase restored to the imported wording, hashes to the pin; the
    pin was moved by S13-C01, S09-C06, S14-C06 and S13-A07, so this is not the imported text."""
    text = (SRC / "live" / "context.py").read_text(encoding="utf-8")
    new = "classes executed, filed or,\non a draft-documents run, draft, CP-3"
    assert text.count(new) == 1
    assert sha(text.replace(new, "classes executed or filed, CP-3")) == CONTEXT_WITHOUT_PHRASE_SHA
