"""The run API: review stages an upload and validates it offline; Start launches one worker, once."""

from __future__ import annotations

import errno
import functools
import hashlib
import importlib.util
import json
import logging
import os
import re
import secrets
import shutil
import stat
import subprocess
import sys
import threading
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING, Any

from fastapi import HTTPException, Response
from starlette.datastructures import FormData, UploadFile

from . import events, notify
from .desktop import WORKER_FLAGS
from .quit import LIBRARY_QUITTING
from .settings import save_json

if TYPE_CHECKING:
    from .server import Application

if sys.platform == "win32":
    import _winapi
else:
    import fcntl

log = logging.getLogger("issuer_library")

JOB_ID = re.compile(r"web-[a-f0-9]{32}")
MODULE_CODE = re.compile(r"CP-[A-Z0-9]+")
JSON = "application/json; charset=utf-8"
SOURCE_LIMIT = 64 << 20
UPLOAD_LIMIT = 512 << 20
UPLOAD_MESSAGE = "Upload is too large or malformed (512 MiB total maximum)"
REQUEST_LIMIT = 8192
DEFAULT_TURNS = 32  # The launcher's default.
MAX_TURNS = 64  # What the CP-OS loop allows.
WORKER_OPTIONS = ("-I", "-B", "-X", "utf8")
WINDOWS_RESERVED = {"CON", "PRN", "AUX", "NUL"} | {
    f"{device}{number}" for device in ("COM", "LPT") for number in "123456789"
}
PACKAGE = Path(__file__).resolve().parent
WORKER_POLL = 5.0  # Seconds between checks of a worker this instance did not start.
REVIEW_TIMEOUT = 600.0  # Seconds a review may take; the launcher reads every file in the folder.
COPY_CHUNK = 1 << 20
NOT_STARTED = "no run was started and no model call was made. Start can be tried again."


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
            done = subprocess.run(
                self.command("review", folder),
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                timeout=REVIEW_TIMEOUT,
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

    def start(self, folder: Path, lock: int) -> subprocess.Popen[bytes]:
        # Discard worker output; structured, redacted status is the only browser contract.
        return subprocess.Popen(
            self.command("start", folder),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=WORKER_FLAGS,
            **inherit_lock(lock),
        )


def refuse_non_regular(path: Path) -> None:
    """Windows stand-in for O_NOFOLLOW: OSError for a link or other non-regular file."""
    if not stat.S_ISREG(path.lstat().st_mode):
        raise OSError(f"not a regular file: {path.name}")


def refuse_non_regular_descriptor(descriptor: int, path: Path) -> None:
    """Close the descriptor and raise OSError when it is not a regular file."""
    if not stat.S_ISREG(os.fstat(descriptor).st_mode):
        os.close(descriptor)
        raise OSError(f"not a regular file: {path.name}")


if sys.platform == "win32":

    def hold_worker_lock(path: Path) -> int:
        """Open the lock file shared for reading only, so a second open for writing is refused."""
        try:
            refuse_non_regular(path)
        except FileNotFoundError:
            pass  # CreateFile below creates it.
        handle: int = _winapi.CreateFile(str(path), 0x80000000, 1, 0, 4, 0x80, 0)
        try:
            os.set_handle_inheritable(handle, True)
        except OSError:
            _winapi.CloseHandle(handle)
            raise
        return handle

    def release_lock(lock: int) -> None:
        _winapi.CloseHandle(lock)

    def inherit_lock(lock: int) -> dict[str, Any]:
        info = subprocess.STARTUPINFO()
        info.lpAttributeList = {"handle_list": [lock]}
        return {"startupinfo": info, "close_fds": True}

    def worker_alive(path: Path) -> bool:
        """Whether a worker holds the lock; OSError when that cannot be checked."""
        try:
            refuse_non_regular(path)
            _winapi.CloseHandle(_winapi.CreateFile(str(path), 0x40000000, 3, 0, 3, 0x80, 0))
        except FileNotFoundError:  # The file is absent: no worker ever held it.
            return False
        except OSError as error:
            if error.winerror == 32:  # A sharing violation: the worker holds it.
                return True
            raise
        return False

    @contextmanager
    def dead_worker_proof(path: Path) -> Iterator[Callable[[], bool] | None]:
        """Yield a still-valid check when no worker holds the lock, else None (also if unknown)."""
        try:
            alive = worker_alive(path)
        except OSError as error:
            log.warning("The run lock %s cannot be checked: %s", path, error)
            alive = True
        yield None if alive else (lambda: True)

else:

    def hold_worker_lock(path: Path) -> int:
        """Lock the file exclusively; the worker inherits the descriptor and so keeps the lock."""
        flags = os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK
        descriptor = os.open(path, flags, 0o600)
        refuse_non_regular_descriptor(descriptor, path)
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            os.close(descriptor)
            raise
        return descriptor

    def release_lock(lock: int) -> None:
        os.close(lock)

    def inherit_lock(lock: int) -> dict[str, Any]:
        return {"pass_fds": (lock,)}

    def worker_alive(path: Path) -> bool:
        """Whether a worker holds the lock; OSError when that cannot be checked.

        A lock won on an unlinked inode proves nothing (a failed start removed the file the
        path named when we opened it), so the path is reopened; a few tries, then OSError.
        """
        for _ in range(3):
            try:
                descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
            except FileNotFoundError:
                return False
            refuse_non_regular_descriptor(descriptor, path)
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
                if os.fstat(descriptor).st_nlink:
                    return False
            except BlockingIOError:
                return True
            finally:
                os.close(descriptor)
        raise OSError(f"The run lock {path} was replaced repeatedly; its holder is unknown")

    @contextmanager
    def dead_worker_proof(path: Path) -> Iterator[Callable[[], bool] | None]:
        """Hold the lock of a gone worker; yield a check that the file is still the path's.

        None (nothing is proven, so nothing may be settled) when a worker holds the lock or the
        path is unusable. A missing file is created, as hold_worker_lock does, so that no start
        can take the lock while the caller decides (a start then refuses; none is paid for).
        The check, made after the caller's read, catches a lock file removed and replaced
        meanwhile, which holding the old inode alone does not prevent.
        """
        flags = os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK
        try:
            descriptor = os.open(path, flags, 0o600)
        except FileNotFoundError:  # The run folder itself is gone.
            yield None
            return
        except OSError as error:
            log.warning("The run lock %s cannot be checked: %s", path, error)
            yield None
            return
        try:
            refuse_non_regular_descriptor(descriptor, path)
        except OSError as error:  # The descriptor is closed.
            log.warning("The run lock %s cannot be checked: %s", path, error)
            yield None
            return
        try:
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                yield None
                return

            def still_the_path() -> bool:
                try:
                    named, held = os.lstat(path), os.fstat(descriptor)
                except OSError:
                    return False
                return (named.st_dev, named.st_ino) == (held.st_dev, held.st_ino) and bool(
                    held.st_nlink
                )

            yield still_the_path
        finally:
            os.close(descriptor)


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
    if os.name == "nt":
        if ":" in name:
            return False
        if any(part.split(".")[0].upper() in WINDOWS_RESERVED for part in parts):
            return False
    return True


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
        for key in (
            "issuer",
            "pathway",
            "as_of",
            "modules",
            "module_details",
            "resume_of",
            "retained_modules",
        ):
            if key in review:
                status[key] = review[key]
    folder = Path(workspace) / "runs" / job_id
    if (progress := events.progress(folder)) is not None:
        status["progress"] = progress
    if started := events.started(folder):
        status["started_at"] = started
    status["id"] = job_id
    status["run_available"] = run_available(workspace, job_id)
    return status


def recent_candidate(workspace: str, name: str) -> tuple[int, str, bool] | None:
    """(write time ns, id, running) of an intake folder that holds a run's status, else None."""
    if not JOB_ID.fullmatch(name):
        return None
    file = Path(workspace) / "intake" / name / "status.json"
    try:
        written = file.stat().st_mtime_ns
        state = events.state_of(file.read_bytes())
    except (OSError, ValueError):
        return None
    if state is None or state == "reviewed":
        return None
    return written, name, state == "running"


def recent_jobs(workspace: str, limit: int = 30) -> list[dict[str, Any]]:
    """Every running job plus the most recently written others, newest first, up to limit rows.

    Job ids are random, so recency is the modification time of status.json, never the folder
    name; ties fall back to the id, descending. Reviewed-only drafts are not runs.
    """
    try:
        names = os.listdir(Path(workspace) / "intake")
    except OSError:
        names = []
    found = [item for name in names if (item := recent_candidate(workspace, name))]
    found.sort(reverse=True)
    room = limit - sum(1 for _, _, running in found if running)  # Places left for finished jobs.
    recent: list[dict[str, Any]] = []
    for _, name, running in found:
        if not running:
            if room <= 0:
                continue
            room -= 1
        if (status := job_view(workspace, name)) is not None:
            recent.append(status)
    return recent


def run_events(workspace: str, job_id: str) -> Response:
    """The run's events; [] when it has no log yet, 404 when it has neither log nor status."""
    if not JOB_ID.fullmatch(job_id):
        raise HTTPException(404, "Not Found")
    try:
        listed, complete = events.read_events(Path(workspace) / "runs" / job_id)
    except FileNotFoundError as error:
        if not (Path(workspace) / "intake" / job_id / "status.json").exists():
            raise HTTPException(404, "Not Found") from error
        listed, complete = [], True
    except OSError as error:
        raise HTTPException(500, "Run events are unreadable") from error
    return json_response({"events": listed, "complete": complete})


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
    """A new file only: a repeated upload path or a planted file is refused, never replaced."""
    handle = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(handle, "wb") as stream:
        stream.write(raw)


def review_form(form: FormData) -> tuple[list[str], list[UploadFile], str, list[str], int]:
    """The upload's source paths, files, context, module codes and turn bound, validated."""
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
        if not 1 <= max_turns <= MAX_TURNS:
            raise HTTPException(400, f"Max turns must be between 1 and {MAX_TURNS}")
    return paths, files, context, modules, max_turns


def retain_source(upload: UploadFile, target: Path, name: str) -> str:
    """Copy the upload into a new file and a sha256 together, reading at most SOURCE_LIMIT + 1
    bytes in bounded chunks; the partial file of a refusal goes with the intake folder."""
    try:
        os.makedirs(target.parent, mode=0o700, exist_ok=True)
    except OSError as error:
        raise HTTPException(500, "Could not retain source") from error
    try:
        handle = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as error:
        raise HTTPException(400, f"Could not retain source: {name}") from error
    except OSError as error:
        raise HTTPException(500, "Could not retain source") from error
    hasher = hashlib.sha256()
    size = 0
    try:
        with os.fdopen(handle, "wb") as stream:
            try:
                upload.file.seek(0)
            except OSError as error:
                raise HTTPException(400, "Source upload could not be read") from error
            while size <= SOURCE_LIMIT:
                chunk = upload.file.read(min(COPY_CHUNK, SOURCE_LIMIT + 1 - size))
                if not chunk:
                    break
                stream.write(chunk)
                hasher.update(chunk)
                size += len(chunk)
    except OSError as error:
        raise HTTPException(500, "Could not retain source") from error
    if size > SOURCE_LIMIT:
        raise HTTPException(400, f"Source upload is too large or unreadable: {name}")
    return hasher.hexdigest()


def stage_sources(folder: Path, paths: list[str], files: list[UploadFile]) -> list[dict[str, str]]:
    """Keep every chosen file under sources/, so the launcher itself reports unreadable ones."""
    sources: list[dict[str, str]] = []
    for name, upload in zip(paths, files, strict=True):
        if (upload.size or 0) > SOURCE_LIMIT:
            raise HTTPException(400, f"Files must be up to 64 MiB each: {name}")
        sources.append(
            {"path": name, "sha256": retain_source(upload, folder / "sources" / name, name)}
        )
    return sources


def review_staged(lib: Application, folder: Path, job: dict[str, Any]) -> tuple[bytes, bool]:
    """Ask the engine to review the staged job; (its answer, whether the review passed)."""
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
    if not review["ok"]:
        return result, False
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
    return result, True


@contextmanager
def enter_review(lib: Application) -> Iterator[str]:
    """Count a review in flight and give the workspace it reads. The review writes into that
    workspace until it ends, however it ends, so a switch is refused until then."""
    with lib.lock:
        if lib.quitting:
            raise HTTPException(503, LIBRARY_QUITTING)
        lib.reviews += 1
        workspace = lib.config.workspace
    try:
        yield workspace
    finally:
        with lib.lock:
            lib.reviews -= 1


def review_run(lib: Application, form: FormData) -> Response:
    """Stage the upload under intake/<id>, then ask the engine to review it offline."""
    paths, files, context, modules, max_turns = review_form(form)
    with enter_review(lib) as workspace:
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
            job["sources"] = stage_sources(folder, paths, files)
            result, valid = review_staged(lib, folder, job)
        finally:
            if not valid:
                shutil.rmtree(folder, ignore_errors=True)
    return Response(result, media_type="application/json")


RESUMABLE = ("stopped", "failed", "interrupted")
INPUTS_GONE = "The stopped run's inputs are no longer in the workspace"
COPY_FAILED = "Could not copy the stopped run's inputs"


def resume_request(raw: bytes) -> dict[str, Any]:
    """The resume body: id, cap_usd and max_turns (a JSON integer 1-64) and nothing else."""
    refusal = "Choose a stopped run, a maximum spend and 1–64 turns"
    try:
        request = json.loads(raw) if len(raw) <= REQUEST_LIMIT else None
    except ValueError:
        request = None
    if not isinstance(request, dict) or set(request) - {"id", "cap_usd", "max_turns"}:
        raise HTTPException(400, refusal)
    job_id, cap, turns = request.get("id"), request.get("cap_usd"), request.get("max_turns")
    if (
        not isinstance(job_id, str)
        or not JOB_ID.fullmatch(job_id)
        or not isinstance(cap, str)
        or not cap
        or type(turns) is not int
        or not 1 <= turns <= MAX_TURNS
    ):
        raise HTTPException(400, refusal)
    return request


def go_list(value: Any, convert: Callable[[Any], Any]) -> list[Any]:
    """A slice field as Go decodes it: null is empty, any other non-array raises ValueError."""
    if value is None:
        return []
    if not isinstance(value, list):
        raise events.GoDecodeError("not an array")
    return [convert(item) for item in value]


def go_slice(record: dict[str, list[Any]], name: str, convert: Callable[[Any], Any]) -> list[Any]:
    found: list[Any] = events.go_value(
        record, name, lambda value: go_list(value, convert), nil_resets=True
    )
    return found


def go_turns(value: Any) -> int:
    if value is not None and not events.is_int(value):
        raise events.GoDecodeError("max_turns is not an integer")
    return int(value or 0)


def recorded_source(item: Any) -> dict[str, str]:
    if item is not None and not isinstance(item, dict):
        raise events.GoDecodeError("not an object")
    record = item or {}
    return {key: events.go_value(record, key, events.go_text) for key in ("path", "sha256")}


def recorded_job(raw: bytes) -> dict[str, Any] | None:
    """A stopped run's job.json as Go decodes it into NewJob; None where Go's decode fails."""
    try:
        job = events.go_record(raw)
        for key in ("id", "workspace", "cap_usd", "resume_of"):
            events.go_value(job, key, events.go_text)
        events.go_value(job, "max_turns", go_turns)
        return {
            "config": events.go_value(job, "config", events.go_text),
            "modules": go_slice(job, "modules", events.go_text),
            "sources": go_slice(job, "sources", recorded_source),
        }
    except ValueError:
        return None


def stopped_run_state(raw: bytes) -> str | None:
    """status.json as Go decodes it into JobStatus: its state, None where the decode fails."""
    try:
        record = events.go_record(raw)
        for key in ("message", "id"):
            events.go_value(record, key, events.go_text)
        return str(events.go_value(record, "state", events.go_text))
    except ValueError:
        return None


# Directories are walked by descriptor, each opened relative to its parent without following a
# link, so a link swapped in after a check is refused where it is used. Stricter than Go's
# os.Root, which follows a link that stays inside the root: here every link is refused.
# Windows has no dir_fd for os.open: there only an lstat check made just before use stands in.
FD_WALK = hasattr(os, "O_NOFOLLOW") and os.open in os.supports_dir_fd
GONE = (
    errno.ENOENT,
    errno.ELOOP,
    errno.ENOTDIR,
    errno.EINVAL,
    errno.ENXIO,
    errno.ENAMETOOLONG,
    errno.EOPNOTSUPP,
)
DIR_FLAGS = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)


def walk_dirs(parent: int, parts: list[str], mode: int | None) -> int:
    """Open parts below the directory parent (created with mode when given); the caller closes."""
    handle = os.dup(parent)
    try:
        for part in parts:
            if mode is not None:
                try:
                    os.mkdir(part, mode, dir_fd=handle)
                except FileExistsError:
                    pass
            child = os.open(part, DIR_FLAGS | os.O_NOFOLLOW, dir_fd=handle)
            os.close(handle)
            handle = child
    except BaseException:
        os.close(handle)
        raise
    return handle


def mkdir_all_in(root: Path, name: str, mode: int = 0o700) -> None:
    """Create name and its missing parents inside root, never through a link or outside it.

    ValueError stands for fs.ErrInvalid; an existing non-directory or link raises OSError.
    """
    parts = [] if name == "." else name.split("/")
    if name != "." and (name.startswith("/") or any(part in ("", ".", "..") for part in parts)):
        raise ValueError(f"invalid path: {name!r}")
    if not FD_WALK:
        for position in range(len(parts)):
            directory = root.joinpath(*parts[: position + 1])
            try:
                directory.mkdir(mode=mode)
            except FileExistsError:
                if not stat.S_ISDIR(directory.lstat().st_mode):
                    raise NotADirectoryError(str(directory)) from None
        return
    handle = os.open(root, DIR_FLAGS)
    try:
        os.close(walk_dirs(handle, parts, mode))
    finally:
        os.close(handle)


def is_plain_file(base: Path, name: str) -> bool:
    """name under base is a regular file reached through no symbolic link (the lstat stand-in)."""
    current = base
    try:
        for part in name.split("/"):
            current = current / part
            if stat.S_ISLNK(current.lstat().st_mode):
                return False
        return stat.S_ISREG(current.lstat().st_mode)
    except OSError:
        return False


def source_names(job: dict[str, Any]) -> list[str]:
    names = ["context.json"]
    for source in job["sources"]:
        if not valid_source_path(source["path"]):
            raise HTTPException(409, INPUTS_GONE)
        names.append(f"sources/{source['path']}")
    return names


def open_source(old: int, folders: list[str], leaf: str) -> int:
    """A regular file of the stopped run, opened without following a link.

    An unreachable directory above it, or a missing, linked or non-regular leaf, is gone (409):
    Go's Lstat through the Root fails. A leaf that is there but cannot be opened (permission) is a
    copy failure (500): Go's Lstat succeeds and the copy fails.
    """
    try:
        parent = walk_dirs(old, folders, None)
    except OSError as error:
        raise HTTPException(409, INPUTS_GONE) from error
    try:
        source = os.open(leaf, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        if not stat.S_ISREG(os.fstat(source).st_mode):
            os.close(source)
            raise OSError(errno.EINVAL, "not a regular file")
    except OSError as error:
        if error.errno in GONE:
            raise HTTPException(409, INPUTS_GONE) from error
        raise HTTPException(500, COPY_FAILED) from error
    finally:
        os.close(parent)
    return source


def copy_names(old: int, new: int, names: list[str]) -> None:
    """Stream each file from the stopped run (a regular file, no link) into the new job."""
    for name in names:
        *folders, leaf = name.split("/")
        source = open_source(old, folders, leaf)
        with os.fdopen(source, "rb") as reader:
            try:
                parent = walk_dirs(new, folders, 0o700)
                try:
                    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
                    target = os.open(leaf, flags, 0o600, dir_fd=parent)
                finally:
                    os.close(parent)
                with os.fdopen(target, "wb") as writer:
                    shutil.copyfileobj(reader, writer)
            except OSError as error:
                raise HTTPException(500, COPY_FAILED) from error


def copy_by_path(old: Path, new: Path, names: list[str]) -> None:
    """The lstat stand-in for platforms without dir_fd: check, then copy by path."""
    for name in names:
        if not is_plain_file(old, name):
            raise HTTPException(409, INPUTS_GONE)
        try:
            target = new / name
            mkdir_all_in(new, str(Path(name).parent.as_posix()))
            with (old / name).open("rb") as reader, target.open("xb") as writer:
                shutil.copyfileobj(reader, writer)
        except OSError as error:
            raise HTTPException(500, COPY_FAILED) from error


def copy_resume_inputs(root: Path, old_id: str, job: dict[str, Any]) -> None:
    """Copy the stopped run's context and exactly the sources its job lists; only read the old."""
    old = root / "intake" / old_id
    if not old.is_dir():
        raise HTTPException(409, INPUTS_GONE)
    new = root / "intake" / job["id"]
    if not FD_WALK:
        try:
            new.mkdir(mode=0o700)
        except OSError as error:
            raise HTTPException(400, "The workspace is not writable") from error
        copy_by_path(old, new, source_names(job))
        return
    try:
        base = os.open(root, DIR_FLAGS)
    except OSError as error:
        raise HTTPException(400, "Choose an available workspace folder first") from error
    try:
        try:
            intake = walk_dirs(base, ["intake"], None)
            try:
                os.mkdir(job["id"], 0o700, dir_fd=intake)
                folder = os.open(job["id"], DIR_FLAGS | os.O_NOFOLLOW, dir_fd=intake)
            finally:
                os.close(intake)
        except OSError as error:
            raise HTTPException(400, "The workspace is not writable") from error
        try:
            holder = os.open(old, DIR_FLAGS)
        except OSError as error:
            os.close(folder)
            raise HTTPException(409, INPUTS_GONE) from error
        try:
            copy_names(holder, folder, source_names(job))
        finally:
            os.close(holder)
            os.close(folder)
    finally:
        os.close(base)


def resume_run(lib: Application, raw: bytes) -> Response:
    """Review a copy of a stopped run's inputs as a new job; never starts a worker."""
    request = resume_request(raw)
    with enter_review(lib) as workspace:
        return resume_in(lib, request, workspace)


def resume_in(lib: Application, request: dict[str, Any], workspace: str) -> Response:
    root = Path(workspace)
    old = root / "intake" / request["id"]
    try:
        state = stopped_run_state((old / "status.json").read_bytes())
    except OSError:
        state = None
    if state not in RESUMABLE:
        raise HTTPException(409, "Only a stopped, failed or interrupted run can be resumed")
    try:
        recorded = recorded_job((old / "job.json").read_bytes())
    except OSError:
        recorded = None
    if recorded is None:
        raise HTTPException(409, INPUTS_GONE)
    if not root.is_dir():
        raise HTTPException(400, "Choose an available workspace folder first")
    job: dict[str, Any] = {
        "id": f"web-{secrets.token_hex(16)}",
        "workspace": workspace,
        "config": recorded["config"],
        "cap_usd": request["cap_usd"],
        "modules": recorded["modules"],
        "max_turns": request["max_turns"],
        "sources": recorded["sources"],
        "resume_of": request["id"],
    }
    folder = root / "intake" / job["id"]
    valid = False
    try:
        copy_resume_inputs(root, request["id"], job)
        result, valid = review_staged(lib, folder, job)
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
        if lib.quitting:
            raise HTTPException(503, LIBRARY_QUITTING)
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
        try:
            process = launch_worker(lib, folder, job_id)
        except HTTPException:
            # No process exists, so nothing ran or was paid for: the reviewed run may start again.
            release_claim(folder, job_id)
            raise
        lib.active_jobs.add(job_id)
    threading.Thread(target=watch, args=(lib, job_id, folder, process), daemon=True).start()
    return json_response({"state": "running", "message": "Run started.", "id": job_id}, 202)


def release_claim(folder: Path, job_id: str) -> None:
    try:
        os.remove(folder / "start.claim")
    except FileNotFoundError:
        pass
    except OSError as error:
        log.warning("Release start claim for %s: %s", job_id, error)


def launch_worker(lib: Application, folder: Path, job_id: str) -> subprocess.Popen[bytes]:
    """Hold the worker lock, record the running state and spawn; the caller holds lib.lock."""
    try:
        lock = hold_worker_lock(folder / "worker.lock")
    except OSError as error:
        raise HTTPException(500, f"Could not prepare the run lock; {NOT_STARTED}") from error
    spawn_failed = False
    try:
        running = {
            "state": "running",
            "message": "CP-OS is validating the reviewed inputs and starting the selected "
            "workflow.",
            "id": job_id,
        }
        try:
            save_json(folder / "status.json", running)
        except OSError as error:
            spawn_failed = True  # Nothing was spawned; a stray fork's copy must not block a start.
            raise HTTPException(500, f"Could not retain start state; {NOT_STARTED}") from error
        try:
            return lib.engine.start(folder, lock)
        except Exception as error:  # Any spawn failure refuses; BaseException still propagates.
            spawn_failed = True
            log.warning("Run %s: the worker could not be started: %s", job_id, error, exc_info=True)
            message = f"CP-OS runtime could not start; {NOT_STARTED}"
            try:
                save_json(
                    folder / "status.json", {"state": "failed", "message": message, "id": job_id}
                )
            except OSError as save_error:
                log.warning(
                    "Run %s: the failed start could not be recorded: %s", job_id, save_error
                )
            raise HTTPException(503, message) from error
    finally:
        release_lock(lock)
        if spawn_failed:
            remove_failed_run_lock(folder / "worker.lock", job_id)


def remove_failed_run_lock(path: Path, job_id: str) -> None:
    """Unlink the lock of a start that failed before any worker, so a stray fork locks a dead inode.

    Used after a failed spawn or a failed status save. No worker holds this inode; the
    cross-instance guard is start.claim (not lib.lock), and the next start creates a fresh file.
    """
    try:
        os.remove(path)
    except FileNotFoundError:
        pass
    except OSError as error:
        log.warning("Remove the run lock of %s after a failed start: %s", job_id, error)


def read_job_state(folder: Path) -> str | None:
    """The state in status.json as Go decodes it; None where the decode fails.

    FileNotFoundError for a missing file; any other OSError for a link, a non-regular file or an
    unreadable one. Never follows a link or blocks on a FIFO.
    """
    with events.open_regular(folder / "status.json") as stream:
        return stopped_run_state(stream.read())


def job_state(folder: Path) -> str | None:
    """The state in the job's status.json as Go's JobStatus decode reads it; None if unreadable."""
    try:
        return read_job_state(folder)
    except OSError:
        return None


class WorkerMayStillRun(Exception):
    """settle_job could not prove the worker gone; the job is left as it is, to be checked again."""


def settle_job(folder: Path) -> None:
    """Mark a job interrupted when its worker has ended while its status still says running.

    The worker's lock is held while status.json is read and rewritten, and the lock file is
    checked to still be the path's before the write, so a verdict that has gone stale (a retry
    started a worker meanwhile) never settles a live job: WorkerMayStillRun, and the caller
    checks again later.
    """
    with dead_worker_proof(folder / "worker.lock") as still_valid:
        if still_valid is None:
            raise WorkerMayStillRun(folder.name)
        if job_state(folder) != "running":
            return
        if not still_valid():
            raise WorkerMayStillRun(folder.name)
        interrupted = {
            "state": "interrupted",
            "message": "The worker exited without a final result. Retained evidence remains "
            "available; no automatic paid retry was made.",
        }
        try:
            save_json(folder / "status.json", interrupted)
        except OSError as error:
            log.warning("Settle %s: %s", folder.name, error)


def tab_served(lib: Application, jobs: list[dict[str, Any]]) -> None:
    """Record a poll from a tab that can show the browser notice.

    A run served in a non-running state while its finish_job is still pending (it is in
    active_jobs) has been seen finished by that tab, so finish_job need not notify natively: the
    worker writes its final status before finish_job records the finish. Only pending runs are
    marked, so a mark cannot outlive its finish_job (a failed start that is retried keeps no stale
    mark). The check and the mark happen under lib.lock, which finish_job holds while it takes the
    mark and leaves active_jobs, so a mark is either honoured or not made. A non-running run
    served after its finish_job left active_jobs was seen finished too: the poll then counts as
    after the finish even if the clock has not ticked since lib.finished was set.
    """
    after_finish = False
    with lib.lock:
        for job in jobs:
            job_id = job.get("id")
            if not isinstance(job_id, str) or not job_id or job.get("state") == "running":
                continue
            if job_id in lib.active_jobs:
                lib.saw_finish.add(job_id)
            else:
                after_finish = True
        at = lib.now()
        if after_finish and at <= lib.finished:
            at = lib.finished + 1
        lib.watched = at


def list_runs(lib: Application, notify_values: list[str]) -> Response:
    """Answer the run list; a tab that can notify (anything but notify=0) counts as watching.

    notify=0 is a tab that builds no browser notice (the watcher sends it when
    Notification.permission is not granted); its poll must not suppress the native one.
    """
    with lib.lock:
        workspace = lib.config.workspace
    jobs = recent_jobs(workspace)
    notify_value = (
        notify_values[0] if notify_values else None
    )  # Go's Query().Get takes the first value.
    if notify_value != "0":
        tab_served(lib, jobs)
    return json_response(jobs)


def finish_job(lib: Application, folder: Path, job_id: str) -> None:
    """Settle a job whose worker has ended, end its activity, refresh and notice the finish.

    When a worker may still run the job stays in active_jobs and nothing is finished: see
    still_active.
    """
    unproven = False
    try:
        try:
            settle_job(folder)
        except WorkerMayStillRun:
            unproven = True
            return
        # Stored before the lock: a poll served the final state after the mark is taken must
        # still count as after the finish, which tab_served decides from this value.
        lib.finished = lib.now()
        with lib.lock:
            # The mark is taken and the job leaves active_jobs in one critical section, so a
            # tab's poll either marked the run before this point or sees it no longer pending.
            saw_finish = job_id in lib.saw_finish
            lib.saw_finish.discard(job_id)
            lib.active_jobs.discard(job_id)
        lib.refresh()  # False once quitting: no discovery; the notice is still decided.
        if not saw_finish and not notify.tab_watching(lib):
            notice_finish(lib, folder, job_id)
    finally:
        if not unproven and lib.on_finished is not None:
            lib.on_finished(job_id)


def notice_finish(lib: Application, folder: Path, job_id: str) -> None:
    """Send the native notice for a finished run; a failure is logged, never retried."""
    text = notify.finish_notice(folder)
    if text is None:
        return
    try:
        lib.notifier(*text)
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        log.warning("Run %s: native notice failed: %s", job_id, error)


def still_active(lib: Application, job_id: str) -> bool:
    """Whether the job is still active: finish_job leaves it so when a worker may still run."""
    with lib.lock:
        return job_id in lib.active_jobs


def watch(lib: Application, job_id: str, folder: Path, process: subprocess.Popen[bytes]) -> None:
    """When the worker exits without a final status, say so; never retry a paid run."""
    process.wait()
    finish_job(lib, folder, job_id)
    if still_active(lib, job_id):
        watch_worker(lib, job_id, folder)  # Something still holds the worker lock.


def adopt_jobs_locked(lib: Application, workspace: str) -> None:
    """Settle the jobs an earlier instance left running; a live worker's job is active again.

    A lock that cannot be checked leaves its job as it is. The caller holds lib.lock or owns lib.
    """
    intake = Path(workspace) / "intake"
    try:
        names = sorted(os.listdir(intake))
    except FileNotFoundError:
        return  # A fresh workspace has no intake folder.
    except OSError as error:
        log.warning("Adoption skipped: %s cannot be listed: %s", intake, error)
        return
    for name in names:
        folder = Path(workspace) / "intake" / name
        if not JOB_ID.fullmatch(name) or name in lib.active_jobs:
            continue
        try:
            state = read_job_state(folder)
        except FileNotFoundError:
            continue  # A reviewed job that never started has no status.
        except OSError as error:
            log.warning("Run %s: its status.json is skipped: %s", name, error)
            continue
        if state is None:
            log.warning("Run %s: its status.json is skipped: it cannot be decoded", name)
        if state != "running":
            continue
        try:
            alive = worker_alive(folder / "worker.lock")
        except OSError as error:
            log.warning(
                "Run %s: its worker lock cannot be checked; its state is left as it is: %s",
                name,
                error,
            )
            continue
        if not alive:
            try:
                settle_job(folder)
                continue
            except WorkerMayStillRun:
                pass  # A worker started meanwhile: watch it like a live one.
        lib.active_jobs.add(name)
        threading.Thread(target=watch_worker, args=(lib, name, folder), daemon=True).start()


def watch_worker(lib: Application, job_id: str, folder: Path) -> None:
    """Wait for a worker this instance did not start to release its lock, then finish its job."""
    reported = None
    while True:
        time.sleep(WORKER_POLL)
        try:
            gone = not worker_alive(folder / "worker.lock")
            reported = None
        except OSError as error:
            # An unreadable lock keeps the job active and is checked again; say so once per error.
            if str(error) != reported:
                log.warning("Run %s: its worker lock cannot be checked yet: %s", job_id, error)
                reported = str(error)
            continue
        if gone:
            finish_job(lib, folder, job_id)
            if not still_active(lib, job_id):
                return
