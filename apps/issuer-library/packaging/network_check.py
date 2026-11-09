"""Build the folder that tells the owner whether the work PC can run Credit OS from a share.

Copy the folder to the network drive and double-click Check.cmd on the work PC. check.py
imports the compiled pydantic_core from the share, serves one loopback route with
FastAPI and uvicorn, and writes the outcome to %TEMP%\\credit-os-network-check.txt.
"""

import importlib.util
import shutil
import sys
import tomllib
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
LOCK = HERE.parents[2] / "uv.lock"
# The server closure of `import fastapi` plus uvicorn; opentelemetry-api is imported by fastapi.
PACKAGES = [
    "pydantic",
    "pydantic-core",
    "annotated-types",
    "typing-extensions",
    "typing-inspection",
    "fastapi",
    "starlette",
    "annotated-doc",
    "uvicorn",
    "h11",
    "click",
    "anyio",
    "idna",
    "opentelemetry-api",
]
PYTHON = r"C:\Program Files\Statestreet\Python313\pythonw.exe"

CHECK_CMD = (
    "@echo off\r\n"
    f'set "PYTHONW={PYTHON}"\r\n'
    'if not exist "%PYTHONW%" (\r\n'
    "  echo The company Python was not found at %PYTHONW%\r\n"
    "  pause\r\n"
    "  exit /b 1\r\n"
    ")\r\n"
    'if exist "%TEMP%\\credit-os-network-check.txt" del "%TEMP%\\credit-os-network-check.txt"\r\n'
    '"%PYTHONW%" -I -B -X utf8 "%~dp0check.py"\r\n'
    'notepad "%TEMP%\\credit-os-network-check.txt"\r\n'
)

# Runs under pythonw (no console, stdout/stderr are None) with -I, so the script folder is
# not on sys.path; lib is added by hand and the launch path is kept as given (UNC or drive).
# The broad except exists only to record the failure text in the result file; it never
# reports PASS.
CHECK_PY = r"""import os
import sys
import tempfile
import threading
import time
import traceback

lines = []
try:
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib"))
    started = time.perf_counter()
    import pydantic_core

    lines.append("pydantic_core: " + pydantic_core.__file__)
    import socket
    import urllib.request

    import fastapi
    import uvicorn

    lines.append("import_ms: %d" % ((time.perf_counter() - started) * 1000))
    app = fastapi.FastAPI()

    @app.get("/health")
    def health():
        return {"ok": True}

    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen(16)
    port = listener.getsockname()[1]
    server = uvicorn.Server(
        uvicorn.Config(app, log_config=None, access_log=False, lifespan="off")
    )
    thread = threading.Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
    started = time.perf_counter()
    thread.start()
    try:
        deadline = time.monotonic() + 30
        while not server.started and thread.is_alive() and time.monotonic() < deadline:
            time.sleep(0.01)
        if not server.started:
            raise RuntimeError("uvicorn did not start within 30 s")
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open("http://127.0.0.1:%d/health" % port, timeout=15) as reply:
            if reply.status != 200:
                raise RuntimeError("GET /health returned %s" % reply.status)
        lines.append("first_response_ms: %d" % ((time.perf_counter() - started) * 1000))
    finally:
        server.should_exit = True
        thread.join(10)
    lines.append("python: " + sys.version)
    lines.append("executable: " + sys.executable)
    lines.append("PASS")
except BaseException:
    lines.append("FAIL")
    lines.append(traceback.format_exc())
folder = os.environ.get("TEMP") or tempfile.gettempdir()
with open(os.path.join(folder, "credit-os-network-check.txt"), "w", encoding="utf-8") as out:
    out.write("\n".join(lines) + "\n")
sys.exit(0 if lines[-1] == "PASS" else 1)
"""


def download(url: str, sha: str, name: str) -> Path:
    """Fetch one SHA-256-verified wheel through the existing runtime bundler."""
    spec = importlib.util.spec_from_file_location("issuer_runtime", HERE / "runtime.py")
    assert spec is not None and spec.loader is not None
    runtime = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runtime)
    return Path(runtime.download(url, sha, name))


def pinned_wheels() -> list[tuple[str, str, str]]:
    """Return (url, sha256, filename) for each package: the lock's cp313 win_amd64 or any wheel."""
    lock = tomllib.loads(LOCK.read_text(encoding="utf-8"))
    by_name = {entry["name"]: entry for entry in lock["package"]}
    chosen = []
    for package in PACKAGES:
        matches = []
        for wheel in by_name[package].get("wheels", []):
            filename = wheel["url"].rsplit("/", 1)[1]
            if filename.endswith("-none-any.whl") or (
                "-cp313-" in filename
                and filename.endswith("-win_amd64.whl")
                and "-cp313t-" not in filename
            ):
                matches.append((wheel["url"], wheel["hash"].removeprefix("sha256:"), filename))
        if len(matches) != 1:
            raise ValueError(f"No unique pinned Windows wheel: {package}")
        chosen.append(matches[0])
    return chosen


def write_scripts(target: Path) -> None:
    target.mkdir(parents=True, exist_ok=True)
    (target / "check.py").write_text(CHECK_PY, encoding="utf-8")
    (target / "Check.cmd").write_bytes(CHECK_CMD.encode())


def build(target: Path) -> None:
    lib = target / "lib"
    if lib.exists():
        shutil.rmtree(lib)
    lib.mkdir(parents=True)
    for url, sha, filename in pinned_wheels():
        with zipfile.ZipFile(download(url, sha, filename)) as archive:
            archive.extractall(lib)
    write_scripts(target)
    binaries = [p for p in target.rglob("*") if p.suffix.lower() in {".exe", ".dll"}]
    if binaries:
        raise ValueError(f"The check folder must hold no executable: {binaries[0]}")


if __name__ == "__main__":
    build(Path(sys.argv[1]))
