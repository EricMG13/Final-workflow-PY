"""The run API: review stages an upload and validates it offline; Start launches one worker once."""

from __future__ import annotations

import contextlib
import functools
import importlib.util
import json
import logging
import ntpath
import os
import re
import secrets
import shutil
import subprocess
import sys
import threading
import time
from collections.abc import Callable, Iterator
from concurrent.futures import Future
from concurrent.futures import TimeoutError as FutureTimeout
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING, Any

from fastapi import HTTPException, Response
from starlette.datastructures import FormData, UploadFile

from deploy_workflow.platform_io import regular_open

from .desktop import WORKER_FLAGS, process_alive
from .model import digest
from .settings import save_json

if TYPE_CHECKING:
    from .server import Application

JOB_ID = re.compile(r"web-[a-f0-9]{32}")
MODULE_CODE = re.compile(r"CP-[A-Z0-9]+")
JSON = "application/json; charset=utf-8"
SOURCE_LIMIT = 64 << 20
UPLOAD_LIMIT = 512 << 20
UPLOAD_MESSAGE = "Upload is too large or malformed (512 MiB total maximum)"
REQUEST_LIMIT = 8192
DEFAULT_TURNS = 32  # The launcher's default.
WORKER_OPTIONS = ("-I", "-B", "-X", "utf8")
RECENT_LIMIT = 30
STORE_TIMEOUT = 120.0
STORE_TIMEOUT_MESSAGE = (
    "the workspace store did not finish within {seconds:g} seconds; check that the workspace "
    "folder is available locally, then reload"
)
ORPHAN_POLL = 2.0
WORKER_RECORD = "worker.json"
INTERRUPTED = (
    "The worker exited without a final result. Retained evidence remains "
    "available; no automatic paid retry was made."
)
PACKAGE = Path(__file__).resolve().parent
# One store read at a time: a read that never returns holds this, so later reads time out
# instead of each leaving another thread behind.
STORE_SLOT = threading.Lock()

log = logging.getLogger("issuer_library")


class StoreTimeout(RuntimeError):
    """The workspace store did not answer in time; the message is shown to the reader."""


def engine_root() -> Path:
    """The engine folder: under apps/ in the repository, or the folder holding src/ in a package."""
    repository = PACKAGE.parents[1] / "apps" / "issuer-library" / "engine"
    return repository if repository.is_dir() else PACKAGE.parents[1]


@functools.cache
def load_store(path: Path) -> ModuleType:
    """store.py imports only the standard library, so a page load does not pay for the engine."""
    spec = importlib.util.spec_from_file_location("issuer_library_store", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"store is unavailable: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@dataclass(frozen=True)
class Engine:
    """The CP-OS bridge beside the server; the worker runs under the same interpreter."""

    root: Path
    python: str = sys.executable

    def command(self, operation: str, folder: Path) -> list[str]:
        return [self.python, *WORKER_OPTIONS, str(self.root / "bridge.py"), operation, str(folder)]

    def library(self, workspace: str, catalogue: dict[str, Any]) -> dict[str, Any]:
        """The workspace's handoffs parsed for the app, within STORE_TIMEOUT seconds."""
        read: Callable[[Path, dict[str, Any]], dict[str, Any]] = load_store(
            self.root / "store.py"
        ).workspace_store
        deadline = time.monotonic() + STORE_TIMEOUT
        refusal = STORE_TIMEOUT_MESSAGE.format(seconds=STORE_TIMEOUT)
        if not STORE_SLOT.acquire(timeout=STORE_TIMEOUT):
            raise StoreTimeout(refusal)
        result: Future[dict[str, Any]] = Future()

        def work() -> None:
            try:
                result.set_result(read(Path(workspace), catalogue))
            except Exception as error:  # noqa: BLE001 -- handed to the caller through the future
                result.set_exception(error)
            finally:
                STORE_SLOT.release()

        # A daemon thread: a store stuck on a slow share must not keep Quit from exiting.
        threading.Thread(target=work, name="workspace-store", daemon=True).start()
        try:
            return result.result(timeout=max(deadline - time.monotonic(), 0.0))
        except FutureTimeout as error:
            raise StoreTimeout(refusal) from error

    def review(self, folder: Path) -> bytes:
        failure = "CP-OS validation could not complete; check the runtime installation"
        try:
            # The launcher reads every file in the folder, so a large one takes minutes.
            done = subprocess.run(
                self.command("review", folder),
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                timeout=600,
                creationflags=WORKER_FLAGS,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            raise RuntimeError(failure) from error
        output: bytes = done.stdout
        if len(output) > 1 << 20:
            raise RuntimeError(failure)
        try:
            result = json.loads(output)
        except ValueError as error:
            raise RuntimeError(failure) from error
        # A refusal exits nonzero with an object whose ok is false; anything else is broken.
        if done.returncode != 0 and (
            not isinstance(result, dict) or result.get("ok", False) is not False
        ):
            raise RuntimeError("CP-OS validator failed")
        return output

    def start(self, folder: Path) -> subprocess.Popen[bytes]:
        # Discard worker output; structured, redacted status is the only browser contract.
        return subprocess.Popen(
            self.command("start", folder),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=WORKER_FLAGS,
        )


def local_engine() -> Engine:
    # ISSUER_LIBRARY_ENGINE_ROOT lets an offline check serve a fake engine; the launcher sets it.
    override = os.environ.get("ISSUER_LIBRARY_ENGINE_ROOT")
    return Engine(root=Path(override) if override else engine_root())


def json_response(value: Any, status: int = 200) -> Response:
    return Response(json.dumps(value, ensure_ascii=False), status, media_type=JSON)


def valid_source_path(name: str) -> bool:
    """A folder-relative path as the browser reports it, refused unless it stays inside sources/."""
    if not name or name.startswith("/") or "\\" in name or "\x00" in name:
        return False
    parts = name.split("/")
    if any(part in ("", ".", "..") for part in parts):
        return False
    if os.name != "nt":
        return True
    # isreserved reads "b:c" as drive b: and the name c, so a stream or drive is refused first.
    # It covers devices (CONIN$, COM¹), invalid characters and names Windows trims ("a.", "a ").
    return ":" not in name and not any(ntpath.isreserved(part) for part in parts)


def run_available(workspace: str, job_id: str) -> bool:
    return (Path(workspace) / "runs" / job_id).is_dir()


def read_object(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_bytes())
    except (OSError, ValueError):
        return None
    return value if isinstance(value, dict) else None


def job_view(workspace: str, job_id: str) -> dict[str, Any] | None:
    """A job's own files: status, the app-written review and the module/step progress.

    None of them holds provider text. The review gives only what names the run and its modules.
    """
    status = read_object(Path(workspace) / "intake" / job_id / "status.json")
    if status is None:
        return None
    review = read_object(Path(workspace) / "intake" / job_id / "review.json")
    if review is not None:
        for key in ("issuer", "pathway", "as_of", "modules", "module_details"):
            if key in review:
                status[key] = review[key]
    progress = read_object(Path(workspace) / "runs" / job_id / "progress.json")
    if progress is not None:
        status["progress"] = progress
    status["id"] = job_id
    status["run_available"] = run_available(workspace, job_id)
    return status


def job_ids(workspace: str) -> list[str]:
    try:
        names = os.listdir(Path(workspace) / "intake")
    except OSError:
        return []
    return [name for name in names if JOB_ID.fullmatch(name)]


def status_changed(workspace: str, job_id: str) -> int:
    """When the job's status last changed; a job without a status sorts last."""
    try:
        return (Path(workspace) / "intake" / job_id / "status.json").stat().st_mtime_ns
    except OSError:
        return -1


def recent_jobs(workspace: str) -> list[dict[str, Any]]:
    """The 30 most recently changed jobs beyond review, newest first; a running job always shows.

    Job ids are random, so the order comes from each status file's modification time.
    """
    names = sorted(
        job_ids(workspace), key=lambda job_id: (status_changed(workspace, job_id), job_id)
    )
    recent: list[dict[str, Any]] = []
    for job_id in reversed(names):
        status = job_view(workspace, job_id)
        if status is None or status.get("state") == "reviewed":
            continue
        if len(recent) < RECENT_LIMIT or status.get("state") == "running":
            recent.append(status)
    return recent


def job_status(workspace: str, job_id: str) -> Response:
    if not JOB_ID.fullmatch(job_id):
        raise HTTPException(404, "Not Found")
    status = job_view(workspace, job_id)
    if status is None:
        if not (Path(workspace) / "intake" / job_id / "status.json").exists():
            raise HTTPException(404, "Not Found")
        raise HTTPException(500, "Run status is unreadable")
    return json_response(status)


def text(form: FormData, key: str) -> str:
    value = form.get(key)
    return value if isinstance(value, str) else ""


def create(path: Path, raw: bytes) -> None:
    """A new file only: a repeated upload path or a planted file is refused, never replaced.

    regular_open adds O_BINARY, so Windows writes the bytes whose SHA-256 the job records.
    """
    handle = regular_open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL)
    with os.fdopen(handle, "wb") as stream:
        stream.write(raw)


@contextlib.contextmanager
def retaining(message: str) -> Iterator[None]:
    """A file the app must keep could not be written: a server fault, named by message."""
    try:
        yield
    except OSError as error:
        raise HTTPException(500, message) from error


@dataclass(frozen=True)
class ReviewForm:
    paths: list[str]
    files: list[UploadFile]
    context: str
    modules: list[str]
    max_turns: int
    config: str
    cap_usd: str


def source_paths(form: FormData) -> list[str]:
    """The folder-relative paths, each inside the folder and none both a file and a folder."""
    try:
        paths = json.loads(text(form, "source_paths"))
    except ValueError:
        paths = None
    if not isinstance(paths, list) or not all(isinstance(name, str) for name in paths):
        raise HTTPException(400, "Source paths are invalid")
    return paths


def check_source_paths(paths: list[str]) -> None:
    for name in paths:
        if not valid_source_path(name):
            raise HTTPException(400, f"Source path is not inside the chosen folder: {name}")
    folders: set[str] = set()
    for name in paths:
        parts = name.split("/")
        folders.update("/".join(parts[:end]) for end in range(1, len(parts)))
    if clash := sorted(folders.intersection(paths)):
        raise HTTPException(400, f"Source path is both a file and a folder: {clash[0]}")


def max_turns(form: FormData) -> int:
    turns = text(form, "max_turns")
    if not turns:
        return DEFAULT_TURNS
    try:
        value = int(turns)
    except ValueError:
        value = 0
    if not 1 <= value <= 200:
        raise HTTPException(400, "Max turns must be between 1 and 200")
    return value


def parse_review_form(form: FormData) -> ReviewForm:
    paths = source_paths(form)
    files = [item for item in form.getlist("sources") if isinstance(item, UploadFile)]
    context = text(form, "context")
    if not files or len(files) > 500 or len(paths) != len(files) or len(context) > 1 << 20:
        raise HTTPException(400, "Choose a folder of 1–500 files and complete the context")
    check_source_paths(paths)
    modules = text(form, "modules").split()
    for module in modules:
        if not MODULE_CODE.fullmatch(module):
            raise HTTPException(400, f"Modules are CP codes separated by spaces: {module}")
    return ReviewForm(
        paths=paths,
        files=files,
        context=context,
        modules=modules,
        max_turns=max_turns(form),
        config=text(form, "config"),
        cap_usd=text(form, "cap_usd"),
    )


def job_folder(root: Path, job_id: str) -> Path:
    if not root.is_dir():
        raise HTTPException(400, "Choose an available workspace folder first")
    try:
        for name in ("intake", "runs", "deliverables"):
            os.makedirs(root / name, mode=0o700, exist_ok=True)
        folder = root / "intake" / job_id
        folder.mkdir(mode=0o700)
    except OSError as error:
        raise HTTPException(400, "The workspace is not writable") from error
    return folder


def upload_bytes(name: str, upload: UploadFile) -> bytes:
    if (upload.size or 0) > SOURCE_LIMIT:
        raise HTTPException(400, f"Files must be up to 64 MiB each: {name}")
    try:
        upload.file.seek(0)
        raw = upload.file.read(SOURCE_LIMIT + 1)
    except OSError as error:
        raise HTTPException(400, "Source upload could not be read") from error
    if len(raw) > SOURCE_LIMIT:
        raise HTTPException(400, f"Source upload is too large or unreadable: {name}")
    return raw


def stage_sources(folder: Path, paths: list[str], files: list[UploadFile]) -> list[dict[str, str]]:
    """Every chosen file is kept, so the launcher itself reports the ones no module can read."""
    sources: list[dict[str, str]] = []
    for name, upload in zip(paths, files, strict=True):
        raw = upload_bytes(name, upload)
        target = folder / "sources" / name
        try:
            os.makedirs(target.parent, mode=0o700, exist_ok=True)
            create(target, raw)
        except (FileExistsError, NotADirectoryError) as error:
            # A repeated path, or one Windows sees as the same file or folder as another.
            raise HTTPException(400, f"Could not retain source: {name}") from error
        except OSError as error:
            raise HTTPException(500, "Could not retain source") from error
        sources.append({"path": name, "sha256": digest(raw)})
    return sources


def engine_review(lib: Application, folder: Path) -> tuple[bytes, dict[str, Any]]:
    try:
        result = lib.engine.review(folder)
    except RuntimeError as error:
        raise HTTPException(503, str(error)) from error
    review = json.loads(result)
    if not isinstance(review, dict) or not isinstance(review.get("ok"), bool):
        raise HTTPException(500, "Invalid validation response")
    return result, review


def record_review(folder: Path, job_id: str, review: dict[str, Any]) -> None:
    with retaining("Could not retain review"):
        save_json(folder / "review.json", review)
    status = {
        "state": "reviewed",
        "message": "Reviewed; no model call has been made.",
        "id": job_id,
    }
    with retaining("Could not retain run status"):
        save_json(folder / "status.json", status)


def review_run(lib: Application, form: FormData) -> Response:
    """Stage the upload under intake/<id>, then ask the engine to review it offline."""
    request = parse_review_form(form)
    with lib.lock:
        workspace = lib.config.workspace
    job: dict[str, Any] = {
        "id": f"web-{secrets.token_hex(16)}",
        "workspace": workspace,
        "config": request.config,
        "cap_usd": request.cap_usd,
        "modules": request.modules,
        "max_turns": request.max_turns,
        "sources": [],
    }
    folder = job_folder(Path(workspace), job["id"])
    valid = False
    try:
        with retaining("Could not retain context"):
            create(folder / "context.json", request.context.encode())
        job["sources"] = stage_sources(folder, request.paths, request.files)
        with retaining("Could not save run request"):
            save_json(folder / "job.json", job)
        result, review = engine_review(lib, folder)
        if review["ok"]:
            record_review(folder, job["id"], review)
            valid = True
    finally:
        if not valid:
            shutil.rmtree(folder, ignore_errors=True)
    return Response(result, media_type="application/json")


def parse_start(raw: bytes) -> tuple[str, str]:
    refusal = "Explicit confirmation of a reviewed run is required"
    try:
        request = json.loads(raw) if len(raw) <= REQUEST_LIMIT else None
    except ValueError:
        request = None
    if not isinstance(request, dict) or set(request) - {"id", "review_id", "confirm"}:
        raise HTTPException(400, refusal)
    job_id, review_id = request.get("id", ""), request.get("review_id", "")
    if (
        not isinstance(job_id, str)
        or not isinstance(review_id, str)
        or request.get("confirm", False) is not True
        or not JOB_ID.fullmatch(job_id)
    ):
        raise HTTPException(400, refusal)
    return job_id, review_id


def approve_review(folder: Path, review_id: str) -> None:
    try:
        review = json.loads((folder / "review.json").read_bytes())
    except OSError as error:
        raise HTTPException(409, "Review this run before starting") from error
    except ValueError:
        review = None
    if (
        not isinstance(review, dict)
        or review.get("review_id") != review_id
        or review.get("provider_ready") is not True
    ):
        raise HTTPException(409, "Review is invalid or the provider is not configured")


def claim_start(folder: Path) -> None:
    try:
        create(folder / "start.claim", b"")
    except FileExistsError as error:
        raise HTTPException(
            409, "This run has already been started; no additional call was made"
        ) from error
    except OSError as error:
        raise HTTPException(500, "Could not retain the start authorisation") from error


def launch(lib: Application, folder: Path) -> subprocess.Popen[bytes]:
    """Spawn the worker and record its process id, so a restarted library still sees it."""
    try:
        process = lib.engine.start(folder)
    except OSError as error:
        failed = {
            "state": "failed",
            "message": "CP-OS runtime could not start; no model call was made.",
        }
        with contextlib.suppress(OSError):
            save_json(folder / "status.json", failed)
        raise HTTPException(503, "CP-OS runtime could not start") from error
    try:
        save_json(folder / WORKER_RECORD, {"pid": process.pid})
    except OSError as error:
        log.warning("Worker record for %s: %s", folder.name, error)
    return process


def start_run(lib: Application, raw: bytes) -> Response:
    """Launch the worker for a reviewed run once; a duplicate request makes no second call."""
    job_id, review_id = parse_start(raw)
    with lib.lock:
        if lib.active_jobs:
            raise HTTPException(409, "A CP-OS run is already active; wait for it to finish")
        folder = Path(lib.config.workspace) / "intake" / job_id
        approve_review(folder, review_id)
        claim_start(folder)
        running = {
            "state": "running",
            "message": "CP-OS is validating the reviewed inputs and starting the selected "
            "workflow.",
            "id": job_id,
        }
        try:
            with retaining("Could not retain start state"):
                save_json(folder / "status.json", running)
            process = launch(lib, folder)
        except HTTPException:
            # Nothing was launched, so the one-shot claim is released for another Start.
            with contextlib.suppress(OSError):
                (folder / "start.claim").unlink(missing_ok=True)
            raise
        lib.active_jobs.add(job_id)
    threading.Thread(target=watch, args=(lib, job_id, folder, process.wait), daemon=True).start()
    return json_response({"state": "running", "message": "Run started.", "id": job_id}, 202)


def mark_interrupted(folder: Path) -> None:
    """A job still recorded as running whose worker has gone ends as interrupted."""
    status = read_object(folder / "status.json")
    if status is not None and status.get("state") == "running":
        with contextlib.suppress(OSError):
            save_json(folder / "status.json", {"state": "interrupted", "message": INTERRUPTED})


def watch(lib: Application, job_id: str, folder: Path, wait: Callable[[], object]) -> None:
    """When the worker exits without a final status, say so; never retry a paid run."""
    wait()
    mark_interrupted(folder)
    with lib.lock:
        lib.active_jobs.discard(job_id)
        lib.refresh_locked()


def worker_pid(folder: Path) -> int | None:
    record = read_object(folder / WORKER_RECORD)
    pid = record.get("pid") if record is not None else None
    return pid if isinstance(pid, int) and not isinstance(pid, bool) else None


def wait_for_exit(pid: int) -> None:
    while process_alive(pid):
        time.sleep(ORPHAN_POLL)


def adopt_running_jobs(lib: Application) -> None:
    """Hold the one-run guard for a worker an earlier library process started; caller locks.

    A running job whose recorded worker is alive stays active until that process exits. One
    with no live worker is marked interrupted, so it neither blocks a Start nor shows as running.
    """
    workspace = lib.config.workspace
    for job_id in job_ids(workspace):
        folder = Path(workspace) / "intake" / job_id
        status = read_object(folder / "status.json")
        if job_id in lib.active_jobs or status is None or status.get("state") != "running":
            continue
        pid = worker_pid(folder)
        if pid is None or not process_alive(pid):
            mark_interrupted(folder)
            continue
        lib.active_jobs.add(job_id)
        threading.Thread(
            target=watch,
            args=(lib, job_id, folder, functools.partial(wait_for_exit, pid)),
            daemon=True,
        ).start()
