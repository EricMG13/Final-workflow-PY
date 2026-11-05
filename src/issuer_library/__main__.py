"""Start the library on a stable loopback port, or open the instance that is already running."""

from __future__ import annotations

import argparse
import json
import logging
import os
import socket
import sys
import threading
import time
import urllib.request
import zlib
from dataclasses import replace
from pathlib import Path

import uvicorn

from .desktop import open_browser, platform_locations, show_error
from .model import digest
from .server import APPLICATION, Application

log = logging.getLogger("issuer_library")


def running_instance(address: str, instance: str) -> bool:
    """Whether this user's library already answers at the address."""
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    # A simultaneous launch may have bound the port but not started serving yet.
    for _ in range(5):
        try:
            with opener.open(f"{address}/health", timeout=2) as response:
                health = json.loads(response.read(4096))
        except (OSError, ValueError):
            health = None
        if (
            isinstance(health, dict)
            and health.get("application") == APPLICATION
            and health.get("instance") == instance
        ):
            return True
        time.sleep(0.2)
    return False


def rotate_log(path: Path) -> None:
    try:
        if path.stat().st_size > 1 << 20:
            os.replace(path, path.with_name("library.log.previous"))
    except OSError:
        pass


def run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="issuer-library", description=__doc__)
    parser.add_argument("--workspace", default="", help="Workspace folder (disabled by IT policy)")
    parser.add_argument(
        "--state-dir", default="", help="Override per-user state directory for testing"
    )
    parser.add_argument("--no-browser", action="store_true", help="Start without opening a browser")
    parser.add_argument(
        "--port", type=int, default=0, help="Loopback port; zero selects a stable per-user port"
    )
    arguments = parser.parse_args(argv)
    loc = platform_locations()
    if arguments.state_dir:
        loc = replace(loc, state=Path(os.path.abspath(arguments.state_dir)))
    os.makedirs(loc.state, mode=0o700, exist_ok=True)
    rotate_log(loc.state / "library.log")
    logging.basicConfig(
        filename=loc.state / "library.log",
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    port = arguments.port or 49000 + zlib.crc32(str(loc.state).encode()) % 10000
    if not 1024 <= port <= 65535:
        raise ValueError("port must be between 1024 and 65535")
    host = f"127.0.0.1:{port}"
    address = f"http://{host}"
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    if os.name != "nt":
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        listener.bind(("127.0.0.1", port))
    except OSError as error:
        listener.close()
        if running_instance(address, digest(str(loc.state).encode())):
            if arguments.workspace:
                raise ValueError(
                    "library is already running; change its workspace in Settings or quit it first"
                ) from error
            if not arguments.no_browser:
                open_browser(address)
            return 0
        raise ValueError(f"local port is occupied by another application: {error}") from error
    listener.listen(128)
    app = Application(loc, arguments.workspace, host)
    server = uvicorn.Server(
        uvicorn.Config(
            app.asgi,
            host="127.0.0.1",
            port=port,
            log_config=None,
            access_log=False,
            lifespan="off",
            timeout_keep_alive=30,
            timeout_graceful_shutdown=3,
            h11_max_incomplete_event_size=16384,
        )
    )

    def stop() -> None:
        server.should_exit = True

    app.stop = stop

    def rediscover() -> None:
        while not server.should_exit:
            time.sleep(30)
            with app.lock:
                app.refresh_locked()

    threading.Thread(target=rediscover, daemon=True).start()
    if not arguments.no_browser:

        def browse() -> None:
            try:
                open_browser(address)
            except OSError as error:
                log.warning("Open browser: %s", error)
                show_error(f"Open {address} in your browser.\n{error}")

        threading.Thread(target=browse, daemon=True).start()
    print("Issuer Library:", address)
    log.info("Listening at %s", address)
    server.run(sockets=[listener])
    return 0


def main() -> int:
    try:
        return run()
    except (OSError, ValueError) as error:
        log.error("%s", error)
        show_error(str(error))
        return 1


if __name__ == "__main__":
    sys.exit(main())
