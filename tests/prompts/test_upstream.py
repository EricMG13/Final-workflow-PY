"""T15 (CP1H-R19): a step with ``inputs == "none"`` is sent each retained earlier step of its
attempt as a ``<<<SOURCE id=step:<producer> ...>>>`` block (Deploy VII's ``_upstream`` form), so
CP-1 financials can bind the entity and scopes ``source_context`` declared. The answer key below is
live run 3's sol-medium store; the tests copy it and never open the shared directory."""

import hashlib
import shutil
from pathlib import Path

import pytest
from prompt_support import request_for

from deploy_vii.execution import Execution
from deploy_vii.live.prompts import PromptError, UpstreamInput
from deploy_vii.preparation import PreparedPack, load_pack
from deploy_workflow.owner_workflow import OWNER_SPECS, OwnerBinding
from deploy_workflow.prompts.compose import compose
from deploy_workflow.prompts.factory import prompt_factory
from deploy_workflow.prompts.fence import FenceError

RUN = Path(
    "/Users/ericguei/Documents/Deploy Workflow/artifacts/model-testing/cp1h-live-3/"
    "pilot-sol-medium-earnings_update-4"
)
# ticket -> (source_context content hash, retained output sha256, body chars, holds shc_group)
KEY = {
    "6fe71b92-f370-4e43-a688-f088998c3e94": (
        "2d48f81e72037af57477fa496f0844f65fe126812798dedb8c443693ce423a2b",
        "1642c165127c025fd2a7570954aaad4d77bc7eb3a065c940722ec5cece60cb83",
        62_586,
        True,
    ),
    "38e9cf8b-1f09-4037-8c6a-5707b923f21a": (
        "34b24d0643e641f2e3e519d624e98abe7c67e4ab7dc23844835b889da8de5e7a",
        "f83f6e86d851103d5b281b1021dc06850f16493bd816c962ef99ce2aa3b63f10",
        65_671,
        False,
    ),
}
# ticket -> the snapshot where that ticket's financials was open, as the live loop saw it (the
# store's `current` closes every attempt, so the copy's pointer is moved to this digest)
OPEN_SNAPSHOT = {
    "6fe71b92-f370-4e43-a688-f088998c3e94": (
        "80d645fa448301781cf52c414cc0fd1450d621188a5e5f5811a3d7ba92c26fa8"
    ),
    "38e9cf8b-1f09-4037-8c6a-5707b923f21a": (
        "604e93b70c0f36b4c71c83ca44facfb7e4077b055ab903af30661535e1f5d9f1"
    ),
}
SOURCE_ID = "id=step:source_context"


@pytest.fixture
def run_copy(tmp_path: Path) -> Path:
    if not RUN.is_dir():
        pytest.skip("live run 3 sol-medium store is absent")
    copy = tmp_path / "run"
    copy.mkdir()
    for name in ("execution", "pack", "sources"):
        if (RUN / name).exists():
            shutil.copytree(RUN / name, copy / name, symlinks=True)
    return copy


def _binding(store: Execution, ticket_id: str) -> OwnerBinding:
    snapshot = store.read()
    attempt = next(a for a in snapshot.attempts if a.ticket_id == ticket_id)
    return OwnerBinding(
        run_id=snapshot.run.run_id,
        issuer_id=snapshot.run.issuer_id,
        as_of=snapshot.run.as_of.isoformat(),
        method_version=snapshot.run.method_version,
        pack_sha256=snapshot.pack_sha256,
        snapshot_sha256=snapshot.content_hash(),
        module_id=attempt.module_id,
        step_id="financials",
        ticket_id=ticket_id,
        attempt=attempt.number,
        inputs=attempt.inputs,
    )


@pytest.mark.parametrize("ticket_id", sorted(KEY))
def test_financials_opening_carries_the_source_context_block(
    run_copy: Path, ticket_id: str
) -> None:
    content_hash, output_sha, chars, has_shc = KEY[ticket_id]
    pointer = run_copy / "execution" / "current"
    pointer.write_text(OPEN_SNAPSHOT[ticket_id] + "\n", encoding="ascii")
    store = Execution(run_copy / "execution")
    pack = load_pack(run_copy / "pack")
    spec = next(s for s in OWNER_SPECS["CP-1"].steps if s.step_id == "financials")
    messages = prompt_factory(pack, store)(_binding(store, ticket_id), spec, ())
    user = messages[1].text
    assert user.count(SOURCE_ID) == 1
    header = f"<<<SOURCE {SOURCE_ID} sha256={content_hash} projection=full>>>\n"
    assert header in user
    body = user.split(header, 1)[1].split("\n<<<END>>>", 1)[0]
    assert hashlib.sha256(body.encode()).hexdigest() == output_sha
    assert len(body) == chars
    assert ("shc_group" in user) is has_shc
    # placed after the data blocks and before any REPAIR block
    assert user.index(header) > user.index("<<<CONTEXT")


def _upstream(text: str = '{"entity": "x"}') -> UpstreamInput:
    return UpstreamInput(
        input_id="step:source_context",
        sha256=hashlib.sha256(b"step").hexdigest(),
        text=text,
        projection="full",
    )


def test_the_upstream_block_comes_before_repair(pack: PreparedPack) -> None:
    request = request_for(
        "financials", pack, upstream=(_upstream(),), issues=("fix the thing",)
    )
    user = compose(request)[1].text
    assert user.count("<<<SOURCE id=step:source_context") == 1
    assert user.index("<<<SOURCE id=step:source_context") < user.index("<<<REPAIR")
    assert user.index("<<<CONTEXT") < user.index("<<<SOURCE id=step:source_context")
    assert (
        f"<<<SOURCE id=step:source_context sha256={hashlib.sha256(b'step').hexdigest()} "
        'projection=full>>>\n{"entity": "x"}\n<<<END>>>'
    ) in user


def test_an_upstream_on_a_step_that_reads_inputs_is_refused(pack: PreparedPack) -> None:
    with pytest.raises(PromptError):
        compose(request_for("narrative", pack, upstream=(_upstream(),)))


def test_an_upstream_body_holding_a_delimiter_is_refused(pack: PreparedPack) -> None:
    assert issubclass(FenceError, PromptError)
    with pytest.raises(FenceError):
        compose(request_for("financials", pack, upstream=(_upstream("a <<<END>>> b"),)))


def test_no_upstream_leaves_the_prompt_unchanged(pack: PreparedPack) -> None:
    user = compose(request_for("financials", pack))[1].text
    assert "<<<SOURCE" not in user
