"""The local HTTP application: catalogue, store, pinned files, assets and the run API."""

from __future__ import annotations

import contextlib
import hashlib
import json
import logging
import mimetypes
import os
import re
import stat
import threading
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, quote

from fastapi import FastAPI, Request, Response
from fastapi.responses import PlainTextResponse
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import Headers, MutableHeaders
from starlette.exceptions import HTTPException
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from .discovery import discover
from .jobs import (
    JSON,
    REQUEST_LIMIT,
    UPLOAD_LIMIT,
    UPLOAD_MESSAGE,
    Engine,
    adopt_jobs_locked,
    engine_root,
    job_status,
    json_response,
    local_engine,
    recent_jobs,
    resume_run,
    review_run,
    run_events,
    start_run,
)
from .launch import LAUNCHER_ONLY, Session, cookie_name
from .model import Catalogue, digest, local_path, read_file
from .quit import LIBRARY_QUITTING, claim_quit, hold_refreshing
from .settings import Config, Locations, load_config, save_json

APPLICATION = "finalworkflow-issuer-library/1"
APP_POLICY = (
    "default-src 'none'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data:; font-src 'self'; connect-src 'self'; frame-src 'self'; "
    "base-uri 'none'; form-action 'none'; frame-ancestors 'none'"
)
FORM_POLICY = (
    "sandbox allow-scripts allow-downloads; default-src 'none'; script-src 'unsafe-inline'; "
    "style-src 'unsafe-inline'; font-src data:; img-src data:; connect-src 'none'; "
    "base-uri 'none'; form-action 'none'; frame-ancestors http://{host}"
)
# Reports retain their local scripts but receive an opaque sandboxed origin:
# a report cannot read the library API, modify settings or access the network.
REPORT_POLICY = (
    "sandbox allow-scripts allow-downloads; default-src 'none'; script-src 'unsafe-inline'; "
    "style-src 'unsafe-inline'; img-src data:; font-src data:; connect-src 'none'; "
    "base-uri 'none'; form-action 'none'; frame-ancestors {ancestors}"
)
ASSET_FOLDERS = ("fonts", "brand", "icons")
ASSET_TYPES = (".html", ".css", ".js")
TEXT_TYPES = ("text/", "application/json", "application/javascript", "image/svg+xml")
RANGE = re.compile(r"bytes=([0-9]*)-([0-9]*)")
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
# The front end beside the engine: apps/issuer-library/web in the repository, web/ in a package.
WEB = engine_root().parent / "web"

log = logging.getLogger("issuer_library")


class StoreCache:
    """The last workspace store output. run_lock is held while the store runs, so concurrent
    requests share one run; it is never taken while holding Application.refreshing or
    Application.lock, and neither is taken while holding it, so they cannot deadlock. state_lock
    guards the entry and the generation and is held only for a field read or write, so clear()
    never waits for a run: it bumps the generation, and a run that began before the bump does
    not store its body."""

    def __init__(self) -> None:
        self.run_lock = threading.Lock()
        self.state_lock = threading.Lock()
        self.generation = 0
        self.key = ""
        self.body: bytes | None = None

    def clear(self) -> None:
        with self.state_lock:
            self.generation += 1
            self.key, self.body = "", None

    def current(self) -> int:
        """The generation now; a run records it before it reads anything."""
        with self.state_lock:
            return self.generation

    def lookup(self, key: str) -> bytes | None:
        """The cached body for key, or None when there is none."""
        with self.state_lock:
            return self.body if key == self.key else None

    def store(self, key: str, body: bytes, generation: int) -> None:
        """Keep body under key unless clear() ran since generation was read."""
        with self.state_lock:
            if self.generation == generation:
                self.key, self.body = key, body


def describe(label: str, name: Path) -> str:
    try:
        info = name.lstat()
    except FileNotFoundError:
        return f"{label}\tmissing"
    return f"{label}\t{info.st_size}\t{info.st_mtime_ns}"


def tree_files(workspace: Path, tree: str) -> list[str]:
    """One line per regular file under workspace/tree; links and junctions are never followed, a
    missing tree is empty, a file that vanishes mid-walk is recorded missing and a regular file in
    place of the tree is described itself (as Go's WalkDir does). Any other error raises."""
    top = workspace / tree
    try:
        mode = top.lstat().st_mode
    except FileNotFoundError:
        return []
    if stat.S_ISREG(mode):
        return [describe(tree, top)]
    if not stat.S_ISDIR(mode) or top.is_junction():
        return []
    lines: list[str] = []
    pending = [top]
    while pending:
        with os.scandir(pending.pop()) as entries:
            for entry in entries:
                relative = Path(entry.path).relative_to(workspace).as_posix()
                try:
                    info = entry.stat(follow_symlinks=False)
                except FileNotFoundError:
                    lines.append(f"{relative}\tmissing")
                    continue
                if entry.is_symlink() or entry.is_junction():
                    continue
                if stat.S_ISDIR(info.st_mode):
                    pending.append(Path(entry.path))
                elif stat.S_ISREG(info.st_mode):
                    lines.append(f"{relative}\t{info.st_size}\t{info.st_mtime_ns}")
    return lines


def workspace_fingerprint(workspace: str, catalogue: Catalogue, engine_dir: Path) -> str:
    """The inputs of one store run: the catalogue without its build time, and size and mtime
    (never contents) of every regular file under workspace/runs and workspace/deliverables, the
    only workspace trees store.py reads, plus store.py, catalog.json and the visualisation
    catalogue. A missing file is recorded as missing, not as an error.
    ponytail: one entry keyed on size and mtime; an edit that keeps both is missed until Refresh.
    Hash the files if that happens.
    """
    raw = catalogue.model_copy(update={"built_at": ""}).model_dump_json()
    lines = [
        line for tree in ("runs", "deliverables") for line in tree_files(Path(workspace), tree)
    ]
    # store.py's REPO: the engine folder itself when packaged (it has src), else the checkout root.
    repo = engine_dir if (engine_dir / "src").is_dir() else engine_dir / ".." / ".." / ".."
    lines += [
        describe("engine/store.py", engine_dir / "store.py"),
        describe("engine/catalog.json", engine_dir / "catalog.json"),
        describe(
            "docs/visualisations/catalogue.csv", repo / "docs" / "visualisations" / "catalogue.csv"
        ),
    ]
    return hashlib.sha256((raw + "\n" + "\n".join(sorted(lines))).encode()).hexdigest()


class UploadTooLarge(Exception):
    pass


def bounded_receive(receive: Receive, limit: int) -> Receive:
    received = 0

    async def inner() -> Message:
        nonlocal received
        message = await receive()
        received += len(message.get("body", b""))
        if received > limit:
            raise UploadTooLarge
        return message

    return inner


def last_body_close(html: bytes) -> int:
    """Offset of the final "</body>" in html, len(html) when there is none.

    bytes.lower() folds ASCII only and keeps the length, so the offset indexes the original
    bytes; Unicode lower-casing would change lengths (U+0130, Kelvin sign, invalid UTF-8)."""
    found = html.lower().rfind(b"</body>")
    return len(html) if found < 0 else found


def attachment(filename: str) -> str:
    if filename.isascii():
        return 'attachment; filename="' + filename.replace('"', '\\"') + '"'
    return f"attachment; filename*=UTF-8''{quote(filename)}"


def content_type(name: str) -> str:
    guessed = mimetypes.guess_type(name)[0] or "application/octet-stream"
    if guessed.startswith(TEXT_TYPES):
        guessed += "; charset=utf-8"
    return guessed


def serve_bytes(request: Request, raw: bytes, headers: dict[str, str]) -> Response:
    """The verified bytes, with one byte range when the browser asks for one."""
    headers = {**headers, "Accept-Ranges": "bytes"}
    wanted = request.headers.get("range")
    if wanted is None:
        return Response(raw, headers=headers)
    size = len(raw)
    match = RANGE.fullmatch(wanted.strip())
    if match is None or not (match[1] or match[2]):
        start, end = size, size
    elif match[1]:
        start = int(match[1])
        end = min(int(match[2]), size - 1) if match[2] else size - 1
    else:
        start, end = max(size - int(match[2]), 0), size - 1
    if start >= size or end < start:
        return PlainTextResponse(
            "invalid range\n", 416, headers={**headers, "Content-Range": f"bytes */{size}"}
        )
    headers["Content-Range"] = f"bytes {start}-{end}/{size}"
    return Response(raw[start : end + 1], 206, headers=headers)


class Boundary:
    """Loopback requests from this app only, with this launch's session, and the headers every
    response carries."""

    def __init__(self, app: ASGIApp, lib: Application) -> None:
        self.app = app
        self.lib = lib

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_marked(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                headers["Cache-Control"] = "no-store"
                headers["X-Content-Type-Options"] = "nosniff"
                headers["Referrer-Policy"] = "no-referrer"
                headers["Cross-Origin-Resource-Policy"] = "same-origin"
            await send(message)

        refusal = self.refusal(scope)
        if refusal is not None:
            await refusal(scope, receive, send_marked)
            return
        # net/http answers an authorised HEAD from the GET route with no body; so does this.
        head = scope["method"] == "HEAD"
        if head:
            scope = {**scope, "method": "GET"}
        sender = self.without_body(send_marked) if head else send_marked
        await self.app(scope, receive, sender)

    @staticmethod
    def without_body(send: Send) -> Send:
        async def bodiless(message: Message) -> None:
            if message["type"] == "http.response.body":
                message = {**message, "body": b""}
            await send(message)

        return bodiless

    def refusal(self, scope: Scope) -> Response | None:
        """The answer that stops the request here, or None when it may reach the routes."""
        headers = Headers(scope=scope)
        if self.foreign(headers):
            return PlainTextResponse("Local app requests only\n", 403)
        if scope["path"] == "/launch":
            return self.launch(scope)
        if scope["path"] != "/health" and not self.authorised(headers):
            return PlainTextResponse(LAUNCHER_ONLY + "\n", 403)
        if scope["method"] == "POST" and (
            headers.get("x-issuer-library") != "1"
            or (
                not scope["path"].startswith("/api/runs/")
                and headers.get("content-type") != "application/json"
            )
        ):
            return PlainTextResponse("Invalid application request\n", 403)
        return None

    def foreign(self, headers: Headers) -> bool:
        """A request that is not this app's own: another host, Origin or site."""
        origin = headers.get("origin", "")
        host = self.lib.host
        sites = headers.getlist("sec-fetch-site")
        return (
            headers.get("host") != host
            or bool(origin and origin != f"http://{host}")
            or any(site not in ("same-origin", "none") for site in sites)
        )

    def launch(self, scope: Scope) -> Response:
        """Exchange the one-time ticket for the session cookie; only a GET spends it."""
        if scope["method"] != "GET":
            return PlainTextResponse("Method not allowed\n", 405)
        query = parse_qsl(scope["query_string"].decode("latin-1"), keep_blank_values=True)
        ticket = next((value for key, value in query if key == "ticket"), "")
        cookie = self.lib.session.exchange(ticket)
        if cookie is None:
            return PlainTextResponse(LAUNCHER_ONLY + "\n", 403)
        # Plain loopback HTTP has no TLS, so no Secure; no expiry, so it lasts the browser session.
        name = cookie_name(self.lib.host)
        return Response(
            b"",
            303,
            headers={
                "Location": "/",
                "Set-Cookie": f"{name}={cookie}; Path=/; HttpOnly; SameSite=Strict",
            },
        )

    def authorised(self, headers: Headers) -> bool:
        """Whether any cookie of this launch's name holds its session secret; every one is
        checked, so a planted cookie of the same name cannot shadow the valid one."""
        name = cookie_name(self.lib.host)
        for line in headers.getlist("cookie"):
            for pair in line.split(";"):
                key, _, value = pair.strip().partition("=")
                if len(value) > 1 and value[0] == value[-1] == '"':
                    value = value[1:-1]
                if key == name and self.lib.session.valid(value):
                    return True
        return False


class Application:
    """The library's state: one workspace, its discovered catalogue and at most one active run."""

    def __init__(
        self, loc: Locations, override: str = "", host: str = "", engine: Engine | None = None
    ) -> None:
        self.config, self.locked = load_config(loc)
        if override:
            if self.locked:
                raise ValueError("workspace override is disabled by IT configuration")
            self.config = Config(workspace=os.path.abspath(override))
        self.loc = loc
        self.host = host
        self.engine = engine or local_engine()
        self.web = WEB
        self.seed = Catalogue.model_validate_json((self.web / "legacy-catalog.json").read_bytes())
        self.instance = digest(str(loc.state).encode())
        self.lock = threading.Lock()
        self.active_jobs: set[str] = set()
        self.stop: Callable[[], None] = lambda: None
        self.catalogue = Catalogue()
        self.store_cache = StoreCache()
        self.refresh_locked()
        # The ticket's lifetime counts from when the library is ready, after its first discovery.
        self.session = Session()
        self.reviews = 0
        self.quitting = False
        # Held for a discovery or workspace change; taken before lock, never while holding it.
        self.refreshing = threading.Lock()
        adopt_jobs_locked(self, self.config.workspace)
        self.asgi = build(self)

    def refresh_locked(self) -> None:
        self.catalogue = discover(self.config.workspace, self.seed)
        self.catalogue.policy_locked = self.locked
        # The persisted index is a disposable snapshot, never an authority on restart.
        try:
            save_json(self.loc.state / "index.json", self.catalogue)
        except OSError as error:
            log.warning("Index cache: %s", error)
            self.catalogue.issues.append(
                "Search index could not be saved; live browsing is still available."
            )

    def refresh(self) -> None:
        with self.refresh_slot(), self.lock:
            self.refresh_locked()

    def catalogue_locked(self) -> Response:
        return Response(self.catalogue.model_dump_json(), media_type=JSON)

    @contextlib.contextmanager
    def refresh_slot(self) -> Iterator[None]:
        """Hold refreshing for a discovery; refused with 503 once the library is quitting."""
        if not hold_refreshing(self):
            raise HTTPException(503, LIBRARY_QUITTING)
        try:
            yield
        finally:
            self.refreshing.release()

    def apply_settings(self, raw: bytes) -> Response:
        with self.refresh_slot(), self.lock:
            if self.active_jobs:
                raise HTTPException(409, "Wait for the active run before changing its workspace")
            if self.locked:
                raise HTTPException(403, "Workspace is managed by IT")
            try:
                config = (
                    Config.model_validate_json(raw, extra="forbid")
                    if len(raw) <= REQUEST_LIMIT
                    else None
                )
            except ValueError:
                config = None
            if config is None:
                raise HTTPException(400, "Invalid settings")
            if not os.path.isabs(config.workspace):
                raise HTTPException(400, "Enter an absolute workspace folder")
            config.workspace = os.path.normpath(config.workspace)
            if not os.path.isdir(config.workspace):
                raise HTTPException(400, "The workspace folder is unavailable")
            try:
                save_json(self.loc.state / "settings.json", config)
            except OSError as error:
                raise HTTPException(500, "Could not save settings") from error
            self.config = config
            self.refresh_locked()
            adopt_jobs_locked(self, config.workspace)
            return self.catalogue_locked()

    def quit(self) -> Response:
        runs, reviews = claim_quit(self)
        if runs or reviews:
            raise HTTPException(
                409,
                "A run or review is active. Keep the application open until it finishes or stops.",
            )
        threading.Thread(target=self.stop, daemon=True).start()
        return json_response({"stopped": True})

    def workspace_store(self) -> Response:
        with self.lock:
            snapshot = self.catalogue.model_copy()
            catalogue = self.catalogue.model_dump(mode="json")
            workspace = self.config.workspace
        body = self.store_body(workspace, snapshot, catalogue)
        return Response(body, media_type="application/json")  # written with run_lock released

    def store_body(self, workspace: str, snapshot: Catalogue, catalogue: dict[str, Any]) -> bytes:
        """The store output, rerun only when its fingerprint changed. A failed fingerprint or
        store is not cached."""
        cache = self.store_cache
        with cache.run_lock:
            generation = cache.current()
            key: str | None = None
            try:
                key = workspace_fingerprint(workspace, snapshot, self.engine.root)
            except (OSError, ValueError) as error:
                # Documented fail-open: without a key the store still runs, just uncached.
                log.warning("Workspace fingerprint: %s; running the store uncached", error)
            else:
                cached = cache.lookup(key)
                if cached is not None:
                    return cached
            try:
                store = self.engine.library(workspace, catalogue)
            except Exception as error:  # Producer-written files; the app still opens.
                log.warning("Workspace store: %r", error)
                raise HTTPException(
                    503,
                    "the workspace could not be read; check the runtime installation and "
                    "workspace folder",
                ) from error
            body = json.dumps(store, ensure_ascii=False).encode()
            if key is not None:
                cache.store(key, body, generation)
            return body

    def report_presentation(self, original: bytes) -> bytes:
        style = (self.web / "report-adapter.css").read_bytes()
        brand = (self.web / "brand.css").read_bytes()
        script = (self.web / "report-adapter.js").read_bytes()
        position = last_body_close(original)
        return b"".join(
            [
                original[:position],
                b"<style data-library-presentation>",
                style,
                brand,
                b"</style><script data-library-presentation>",
                script,
                b"</script>",
                original[position:],
            ]
        )

    def serve_file(self, request: Request, name: str) -> Response:
        with self.lock:
            admitted = name in self.catalogue._allowed
            sha256 = self.catalogue._allowed.get(name, "")
            workspace = self.config.workspace
        if not admitted or not local_path(name):
            raise HTTPException(404, "Not Found")
        if not os.path.isdir(workspace):
            raise HTTPException(410, "Workspace unavailable")
        try:
            raw = read_file(Path(workspace), name)
        except (OSError, ValueError) as error:
            raise HTTPException(410, "File unavailable; refresh the library") from error
        pinned = request.query_params.get("sha256", "")
        actual = digest(raw) if sha256 or pinned else ""
        if sha256 and actual != sha256:
            raise HTTPException(409, "File changed since verification; refresh the library")
        if pinned and actual != pinned:
            raise HTTPException(
                409, "This link refers to a different evidence version; refresh the library"
            )
        extension = os.path.splitext(name)[1].lower()
        headers = {"Content-Type": "text/plain; charset=utf-8"}
        if extension in (".html", ".htm"):
            headers["Content-Type"] = "text/html; charset=utf-8"
        if extension == ".pdf":
            headers["Content-Type"] = "application/pdf"
        if extension == ".xlsx":
            headers["Content-Type"] = XLSX
            headers["Content-Disposition"] = attachment(os.path.basename(name))
        download = request.query_params.get("download") == "1"
        if download:
            filename = os.path.basename(name)
            if sha256 and filename in ("report.html", "model.html"):
                filename = os.path.basename(os.path.dirname(name)) + ".html"
            headers["Content-Disposition"] = attachment(filename)
        ancestors = "'none'"
        if (
            extension in (".html", ".htm")
            and sha256
            and request.query_params.get("embedded") == "1"
        ):
            ancestors = f"http://{self.host}"
            # A published model is served as verified, embedded or not; only a report is adapted.
            if not download and os.path.basename(name) == "report.html":
                raw = self.report_presentation(raw)
        headers["Content-Security-Policy"] = REPORT_POLICY.format(ancestors=ancestors)
        return serve_bytes(request, raw, headers)

    def serve_asset(self, request: Request, name: str) -> Response:
        name = name or "index.html"
        parts = name.split("/")
        packaged = (len(parts) == 1 and name.endswith(ASSET_TYPES)) or (
            len(parts) == 2 and parts[0] in ASSET_FOLDERS
        )
        if not local_path(name) or not packaged or name == "legacy-catalog.json":
            raise HTTPException(404, "Not Found")
        try:
            raw = read_file(self.web, name)
        except (OSError, ValueError) as error:
            raise HTTPException(404, "Not Found") from error
        policy = APP_POLICY
        if name == "context-form.html":
            policy = FORM_POLICY.format(host=self.host)
        headers = {"Content-Security-Policy": policy, "Content-Type": content_type(name)}
        return serve_bytes(request, raw, headers)


def events_route(app: FastAPI, lib: Application) -> None:
    @app.get("/api/runs/events")
    def runs_events(request: Request) -> Response:
        with lib.lock:
            workspace = lib.config.workspace
        return run_events(workspace, request.query_params.get("id", ""))


def resume_route(app: FastAPI, lib: Application) -> None:
    @app.post("/api/runs/resume")
    async def runs_resume(request: Request) -> Response:
        body = b""
        async for chunk in request.stream():  # Stop reading once the body is past the limit.
            body += chunk
            if len(body) > REQUEST_LIMIT:
                break
        return await run_in_threadpool(resume_run, lib, body)


def build(lib: Application) -> FastAPI:
    """Routes over the application; every handler keeps the Go server's status codes and texts."""
    app = FastAPI(openapi_url=None, docs_url=None, redoc_url=None)
    app.add_middleware(Boundary, lib=lib)

    @app.exception_handler(HTTPException)
    async def plain(request: Request, error: HTTPException) -> Response:
        return PlainTextResponse(f"{error.detail}\n", error.status_code, headers=error.headers)

    @app.get("/health")
    def health() -> Response:
        return json_response({"application": APPLICATION, "instance": lib.instance})

    @app.get("/api/catalogue")
    def catalogue() -> Response:
        with lib.lock:
            return lib.catalogue_locked()

    @app.get("/api/workspace")
    def workspace() -> Response:
        return lib.workspace_store()

    @app.post("/api/refresh")
    def refresh() -> Response:
        try:
            with lib.refresh_slot(), lib.lock:
                lib.refresh_locked()
                return lib.catalogue_locked()
        finally:
            lib.store_cache.clear()  # after the locks are released

    @app.post("/api/settings")
    async def settings(request: Request) -> Response:
        try:
            return await run_in_threadpool(lib.apply_settings, await request.body())
        finally:
            # After the locks are released; the key also names the workspace.
            lib.store_cache.clear()

    @app.post("/api/quit")
    def quit_library() -> Response:
        return lib.quit()

    @app.get("/api/runs/list")
    def runs_list() -> Response:
        with lib.lock:
            workspace = lib.config.workspace
        return json_response(recent_jobs(workspace))

    @app.get("/api/runs/status")
    def runs_status(request: Request) -> Response:
        with lib.lock:
            workspace = lib.config.workspace
        return job_status(workspace, request.query_params.get("id", ""))

    events_route(app, lib)

    @app.post("/api/runs/review")
    async def runs_review(request: Request) -> Response:
        bounded = Request(request.scope, bounded_receive(request.receive, UPLOAD_LIMIT))
        try:
            form = await bounded.form()
        except (HTTPException, UploadTooLarge) as error:
            raise HTTPException(400, UPLOAD_MESSAGE) from error
        try:
            return await run_in_threadpool(review_run, lib, form)
        finally:
            await form.close()

    @app.post("/api/runs/start")
    async def runs_start(request: Request) -> Response:
        return await run_in_threadpool(start_run, lib, await request.body())

    resume_route(app, lib)

    @app.api_route("/files/{name:path}", methods=["GET", "HEAD"])
    def files(request: Request, name: str) -> Response:
        return lib.serve_file(request, name)

    @app.api_route("/{name:path}", methods=["GET", "HEAD"])
    def assets(request: Request, name: str) -> Response:
        return lib.serve_asset(request, name)

    return app
