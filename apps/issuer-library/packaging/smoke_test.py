"""Exercise the launcher over loopback, without a browser or providers.

With no argument it starts the repository's own server (the uv environment, PYTHONPATH=src).
With a package folder it starts that package's pinned runtime, as the Windows launcher does.
"""

import http.client
import json
import os
import runpy
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
workspace = ROOT
# Every provider key the Redactor knows, from its one list.
redact = runpy.run_path(str(workspace / "src/deploy_workflow/model/redact.py"))
environment = {k: v for k, v in os.environ.items() if k not in redact["KEY_ENV_NAMES"]}
if len(sys.argv) > 1:
    package = Path(sys.argv[1]).resolve()
    launcher = [
        str(package / "engine/runtime/python.exe"),
        "-I",
        "-B",
        "-X",
        "utf8",
        "-m",
        "issuer_library",
    ]
    context = (package / "engine/smoke-context.json").read_bytes()
else:
    launcher = [sys.executable, "-B", "-X", "utf8", "-m", "issuer_library"]
    environment["PYTHONPATH"] = str(ROOT / "src")
    context = (ROOT / "cases/context/research-minimal.json").read_bytes()
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
with tempfile.TemporaryDirectory(prefix="issuer-library-smoke-") as temporary:
    state = Path(temporary) / "state"
    other = Path(temporary) / "workspace-émetteur"
    other.mkdir()
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    address = f"http://127.0.0.1:{port}"
    arguments = [*launcher, "--state-dir", str(state), "--port", str(port), "--no-browser"]

    def request(
        endpoint: str, payload: object = None, content_type: str = "application/json"
    ) -> Any:
        headers = {}
        raw = None
        if payload is not None:
            raw = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
            headers = {"Content-Type": content_type, "X-Issuer-Library": "1", "Origin": address}
        with opener.open(
            urllib.request.Request(address + endpoint, raw, headers), timeout=10
        ) as response:
            body = response.read()
            return json.loads(body) if "json" in response.headers["Content-Type"] else body

    def launch_status(path: str) -> tuple[int, str, str]:
        """GET path without a cookie or a redirect: status, Location and Set-Cookie."""
        connection = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
        try:
            connection.request("GET", path)
            response = connection.getresponse()
            response.read()
            return (
                response.status,
                response.getheader("Location", ""),
                response.getheader("Set-Cookie", ""),
            )
        finally:
            connection.close()

    def ready(process: subprocess.Popen[bytes]) -> None:
        """Wait for the launcher, then exchange the one-time link it prints with --no-browser for
        its session cookie, as the browser does. The cookie stays on the opener, in memory."""
        opener.addheaders = [("User-agent", "issuer-library-smoke")]
        for _ in range(100):
            if process.poll() is not None:
                raise AssertionError("Launcher exited before serving")
            try:
                if launch_status("/health")[0] == 200:
                    break
            except OSError:
                pass
            time.sleep(0.1)
        else:
            raise AssertionError("Launcher did not become ready")
        assert process.stdout is not None
        stdout = process.stdout
        lines: list[bytes] = []
        reader = threading.Thread(target=lambda: lines.append(stdout.readline()), daemon=True)
        reader.start()
        reader.join(10)
        if not lines:
            raise AssertionError("Launcher printed no launch link")
        line = lines[0].decode().strip()
        if not line.startswith(f"Issuer Library: {address}/launch?ticket="):
            raise AssertionError("Launcher printed no launch link")
        path = line.removeprefix(f"Issuer Library: {address}")
        assert launch_status("/api/catalogue")[0] == 403, "Catalogue answered without the cookie"
        status, location, cookie = launch_status(path)
        assert status == 303 and location == "/", "Launch link was not exchanged"
        assert cookie.endswith("; Path=/; HttpOnly; SameSite=Strict"), "Session cookie attributes"
        assert launch_status(path)[0] == 403, "Launch link worked twice"
        opener.addheaders.append(("Cookie", cookie.split(";", 1)[0]))

    process = subprocess.Popen(
        arguments + ["--workspace", str(workspace)], env=environment, stdout=subprocess.PIPE
    )
    launched = [process]
    try:
        ready(process)
        catalogue = request("/api/catalogue")
        # The HTML Model deliveries hold no report, which the library does not present yet.
        assert sorted(issue.split(":")[0] for issue in catalogue["issues"]) == [
            f"deliverables/tdg-model-{n}" for n in (1, 2, 3)
        ]
        runs = {row["id"] for row in catalogue["real"] if not row["id"].startswith("delivery:")}
        assert runs == {path.name for path in (workspace / "runs").iterdir() if path.is_dir()}
        reports = {
            a["href"] for row in catalogue["real"] for a in row["artifacts"] if a["available"]
        }
        assert len(reports) == len(list(workspace.glob("deliverables/*/report.html"))) + len(
            list(workspace.glob("runs/*/deliveries/*/report.html"))
        )
        for report in reports:
            assert b"<html" in request(report).lower()
        store = request("/api/workspace")
        assert "tdg-002" in store["runs"] and len(store["reports"]) == len(reports)
        # A repeat launch cannot learn the running instance's secret. It asks the idle instance to
        # quit through the state folder, then starts with a fresh one-time link: the old session
        # no longer opens the library and the new one does.
        earlier = opener.addheaders[-1]
        first = process
        process = subprocess.Popen(
            arguments + ["--workspace", str(workspace)], env=environment, stdout=subprocess.PIPE
        )
        launched.append(process)
        assert first.wait(timeout=15) == 0, "Idle library did not quit for the relaunch"
        ready(process)
        assert opener.addheaders[-1] != earlier, "Repeat launch kept the previous session secret"
        assert not list(state.glob("quit.*")), "Repeat launch left a quit file"
        current = opener.addheaders.pop()
        opener.addheaders.append(earlier)
        try:
            request("/api/catalogue")
        except urllib.error.HTTPError as error:
            assert error.code == 403, error.code
        else:
            raise AssertionError("The previous session still opened the library")
        opener.addheaders[-1] = current
        assert request("/api/catalogue")["workspace"] == str(workspace)
        request("/api/settings", {"workspace": str(other)})
        boundary = "IssuerLibraryOfflineSmoke"
        parts = []
        for name, raw in [
            ("context", context),
            ("config", b"sol-medium"),
            ("cap_usd", b"10.00"),
            ("source_paths", b'["annual.txt"]'),
        ]:
            parts.append(
                f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n'.encode()
                + raw
                + b"\r\n"
            )
        parts.append(
            (
                f'--{boundary}\r\nContent-Disposition: form-data; name="sources"; '
                'filename="source.txt"\r\nContent-Type: text/plain\r\n\r\n'
                f"Synthetic offline source. No issuer analysis.\r\n--{boundary}--\r\n"
            ).encode()
        )
        review = request(
            "/api/runs/review", b"".join(parts), "multipart/form-data; boundary=" + boundary
        )
        assert review["ok"] and not review["provider_ready"], review
        draft = other / "intake" / review["id"]
        assert (draft / "review.json").exists()
        assert list((other / "runs").iterdir()) == [], "Offline review created a run"
        try:
            request(
                "/api/runs/start",
                {"id": review["id"], "review_id": review["review_id"], "confirm": True},
            )
        except urllib.error.HTTPError as error:
            assert error.code == 409
        else:
            raise AssertionError("Unconfigured provider passed the Start gate")
        assert not (draft / "start.claim").exists()
        added = other / "runs/automatically-discovered"
        added.mkdir(parents=True)
        (added / "CP-0.md").write_text("Synthetic discovery smoke fixture.\n")
        for _ in range(38):
            catalogue = request("/api/catalogue")
            if any(row["id"] == "automatically-discovered" for row in catalogue["real"]):
                break
            time.sleep(1)
        else:
            raise AssertionError("Periodic discovery did not find new run")
        assert catalogue["real"][0]["completion"] is None
        request("/api/quit", {})
        assert process.wait(timeout=5) == 0
        process = subprocess.Popen(arguments, env=environment, stdout=subprocess.PIPE)
        launched.append(process)
        ready(process)
        assert request("/api/catalogue")["workspace"] == str(other)
        request("/api/quit", {})
        assert process.wait(timeout=5) == 0
        print(
            "PASS: launch, retained reports, workspace store, repeat launch, Unicode workspace, "
            "offline CP-OS context/source/budget review and unavailable-provider Start gate, "
            "automatic discovery, settings persistence, shutdown and restart; "
            "no browser acceptance implied."
        )
    finally:
        for each in launched:
            if each.poll() is None:
                each.terminate()
                each.wait(timeout=5)
            if each.stdout is not None:
                each.stdout.close()
