"""The run API: review stages an upload and validates it offline; Start launches one worker, once."""

from __future__ import annotations

import functools
import importlib.util
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import threading
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING, Any

from fastapi import HTTPException, Response
from starlette.datastructures import FormData, UploadFile

from .desktop import WORKER_FLAGS
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
WINDOWS_RESERVED = {"CON", "PRN", "AUX", "NUL"} | {
    f"{device}{number}" for device in ("COM", "LPT") for number in "123456789"
}
PACKAGE = Path(__file__).resolve().parent


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
        """The workspace's handoffs parsed for the app; the catalogue names what to show."""
        store: dict[str, Any] = load_store(self.root / "store.py").workspace_store(
            Path(workspace), catalogue
        )
        return store

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
    return Engine(root=engine_root())


def json_response(value: Any, status: int = 200) -> Response:
    return Response(json.dumps(value, ensure_ascii=False), status, media_type=JSON)


def valid_source_path(name: str) -> bool:
    """A folder-relative path as the browser reports it, refused unless it stays inside sources/."""
    if not name or name.startswith("/") or "\\" in name or "\x00" in name:
        return False
    parts = name.split("/")
    if any(part in ("", ".", "..") for part in parts):
        return False
    if os.name == "nt":
        if ":" in name:
            return False
        if any(part.split(".")[0].upper() in WINDOWS_RESERVED for part in parts):
            return False
    return True


def read_status(folder: Path) -> dict[str, Any] | None:
    try:
        value = json.loads((folder / "status.json").read_bytes())
    except (OSError, ValueError):
        return None
    return value if isinstance(value, dict) else None


def run_available(workspace: str, job_id: str) -> bool:
    return (Path(workspace) / "runs" / job_id).is_dir()


def recent_jobs(workspace: str) -> list[dict[str, Any]]:
    """The newest 30 intake folders that hold a readable status beyond review."""
    try:
        names = sorted(os.listdir(Path(workspace) / "intake"))
    except OSError:
        names = []
    recent: list[dict[str, Any]] = []
    for job_id in reversed(names):
        if len(recent) == 30:
            break
        if not JOB_ID.fullmatch(job_id):
            continue
        status = read_status(Path(workspace) / "intake" / job_id)
        if status is None or status.get("state") == "reviewed":
            continue
        status["id"] = job_id
        status["run_available"] = run_available(workspace, job_id)
        recent.append(status)
    return recent


def job_status(workspace: str, job_id: str) -> Response:
    if not JOB_ID.fullmatch(job_id):
        raise HTTPException(404, "Not Found")
    folder = Path(workspace) / "intake" / job_id
    if not (folder / "status.json").is_file():
        raise HTTPException(404, "Not Found")
    status = read_status(folder)
    if status is None:
        raise HTTPException(500, "Run status is unreadable")
    # This file contains only module/step names, not provider messages.
    try:
        progress = json.loads((Path(workspace) / "runs" / job_id / "progress.json").read_bytes())
    except (OSError, ValueError):
        progress = None
    if isinstance(progress, dict):
        status["progress"] = progress
    status["id"] = job_id
    status["run_available"] = run_available(workspace, job_id)
    return json_response(status)


def text(form: FormData, key: str) -> str:
    value = form.get(key)
    return value if isinstance(value, str) else ""


def create(path: Path, raw: bytes) -> None:
    """A new file only: a repeated upload path or a planted file is refused, never replaced."""
    handle = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(handle, "wb") as stream:
        stream.write(raw)


def review_run(lib: Application, form: FormData) -> Response:
    """Stage the upload under intake/<id>, then ask the engine to review it offline."""
    try:
        paths = json.loads(text(form, "source_paths"))
    except ValueError:
        paths = None
    if not isinstance(paths, list) or not all(isinstance(name, str) for name in paths):
        raise HTTPException(400, "Source paths are invalid")
    files = [item for item in form.getlist("sources") if isinstance(item, UploadFile)]
    context = text(form, "context")
    if not files or len(files) > 500 or len(paths) != len(files) or len(context) > 1 << 20:
        raise HTTPException(400, "Choose a folder of 1–500 files and complete the context")
    for name in paths:
        if not valid_source_path(name):
            raise HTTPException(400, f"Source path is not inside the chosen folder: {name}")
    modules = text(form, "modules").split()
    for module in modules:
        if not MODULE_CODE.fullmatch(module):
            raise HTTPException(400, f"Modules are CP codes separated by spaces: {module}")
    max_turns = DEFAULT_TURNS
    if turns := text(form, "max_turns"):
        try:
            max_turns = int(turns)
        except ValueError:
            max_turns = 0
        if not 1 <= max_turns <= 200:
            raise HTTPException(400, "Max turns must be between 1 and 200")
    with lib.lock:
        workspace = lib.config.workspace
    job: dict[str, Any] = {
        "id": f"web-{secrets.token_hex(16)}",
        "workspace": workspace,
        "config": text(form, "config"),
        "cap_usd": text(form, "cap_usd"),
        "modules": modules,
        "max_turns": max_turns,
        "sources": [],
    }
    root = Path(workspace)
    if not root.is_dir():
        raise HTTPException(400, "Choose an available workspace folder first")
    try:
        for name in ("intake", "runs", "deliverables"):
            os.makedirs(root / name, mode=0o700, exist_ok=True)
        folder = root / "intake" / job["id"]
        folder.mkdir(mode=0o700)
    except OSError as error:
        raise HTTPException(400, "The workspace is not writable") from error
    valid = False
    try:
        try:
            create(folder / "context.json", context.encode())
        except OSError as error:
            raise HTTPException(500, "Could not retain context") from error
        # Every chosen file is kept, so the launcher itself reports the ones no module can read.
        for name, upload in zip(paths, files, strict=True):
            if (upload.size or 0) > SOURCE_LIMIT:
                raise HTTPException(400, f"Files must be up to 64 MiB each: {name}")
            try:
                upload.file.seek(0)
                raw = upload.file.read(SOURCE_LIMIT + 1)
            except OSError as error:
                raise HTTPException(400, "Source upload could not be read") from error
            if len(raw) > SOURCE_LIMIT:
                raise HTTPException(400, f"Source upload is too large or unreadable: {name}")
            target = folder / "sources" / name
            try:
                os.makedirs(target.parent, mode=0o700, exist_ok=True)
            except OSError as error:
                raise HTTPException(500, "Could not retain source") from error
            try:
                create(target, raw)
            except FileExistsError as error:
                raise HTTPException(400, f"Could not retain source: {name}") from error
            except OSError as error:
                raise HTTPException(500, "Could not retain source") from error
            job["sources"].append({"path": name, "sha256": digest(raw)})
        try:
            save_json(folder / "job.json", job)
        except OSError as error:
            raise HTTPException(500, "Could not save run request") from error
        try:
            result = lib.engine.review(folder)
        except RuntimeError as error:
            raise HTTPException(503, str(error)) from error
        review = json.loads(result)
        if not isinstance(review, dict) or not isinstance(review.get("ok"), bool):
            raise HTTPException(500, "Invalid validation response")
        if review["ok"]:
            try:
                save_json(folder / "review.json", review)
            except OSError as error:
                raise HTTPException(500, "Could not retain review") from error
            status = {
                "state": "reviewed",
                "message": "Reviewed; no model call has been made.",
                "id": job["id"],
            }
            try:
                save_json(folder / "status.json", status)
            except OSError as error:
                raise HTTPException(500, "Could not retain run status") from error
            valid = True
    finally:
        if not valid:
            shutil.rmtree(folder, ignore_errors=True)
    return Response(result, media_type="application/json")


def start_run(lib: Application, raw: bytes) -> Response:
    """Launch the worker for a reviewed run once; a duplicate request makes no second call."""
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
    with lib.lock:
        if lib.active_jobs:
            raise HTTPException(409, "A CP-OS run is already active; wait for it to finish")
        folder = Path(lib.config.workspace) / "intake" / job_id
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
        try:
            create(folder / "start.claim", b"")
        except FileExistsError as error:
            raise HTTPException(
                409, "This run has already been started; no additional call was made"
            ) from error
        except OSError as error:
            raise HTTPException(500, "Could not retain the start authorisation") from error
        running = {
            "state": "running",
            "message": "CP-OS is validating the reviewed inputs and starting the selected workflow.",
            "id": job_id,
        }
        try:
            save_json(folder / "status.json", running)
        except OSError as error:
            raise HTTPException(500, "Could not retain start state") from error
        try:
            process = lib.engine.start(folder)
        except OSError as error:
            failed = {"state": "failed", "message": "CP-OS runtime could not start."}
            try:
                save_json(folder / "status.json", failed)
            except OSError:
                pass
            raise HTTPException(503, "CP-OS runtime could not start") from error
        lib.active_jobs.add(job_id)
    threading.Thread(target=watch, args=(lib, job_id, folder, process), daemon=True).start()
    return json_response({"state": "running", "message": "Run started.", "id": job_id}, 202)


def watch(lib: Application, job_id: str, folder: Path, process: subprocess.Popen[bytes]) -> None:
    """When the worker exits without a final status, say so; never retry a paid run."""
    process.wait()
    status = read_status(folder)
    if status is not None and status.get("state") == "running":
        interrupted = {
            "state": "interrupted",
            "message": "The worker exited without a final result. Retained evidence remains "
            "available; no automatic paid retry was made.",
        }
        try:
            save_json(folder / "status.json", interrupted)
        except OSError:
            pass
    with lib.lock:
        lib.active_jobs.discard(job_id)
        lib.refresh_locked()
