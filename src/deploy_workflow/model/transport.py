"""Bounded https transport: connect, idle and overall limits; https only; no redirect followed.

Error messages name the exception type and never carry a header, body or URL query, so a key
cannot reach them. A timeout error keeps the bytes read so far in ``partial`` so the caller
can settle a cut stream from a usage event that already arrived.
"""

from __future__ import annotations

import http.client
import io
import socket
import threading
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol, cast
from urllib.parse import urlsplit

CONNECT_S = 30.0
IDLE_S = 120.0  # spec §8
OVERALL_S = 1800.0  # PF-R13: Deploy VII sol-high took 692 s for 55K output tokens (limits.json)
READ_CHUNK_BYTES = 64 * 1024


class TransportError(Exception):
    """The request could not complete. The message never holds a key."""

    def __init__(self, message: str, partial: bytes = b"") -> None:
        super().__init__(message)
        self.partial = partial


class InsecureUrl(TransportError):
    """Refused before any connection: not https."""


class NotConnected(TransportError):
    """The connection (TCP, TLS) failed before any request byte was written: nothing was sent."""


class ConnectTimeout(NotConnected):
    """No connection within ``connect_s``; nothing was sent."""


class IdleTimeout(TransportError):
    """No byte for ``idle_s`` on a streamed reply."""


class OverallTimeout(TransportError):
    """The wall-clock deadline ``overall_s`` passed."""


@dataclass(frozen=True)
class Request:
    url: str
    headers: Mapping[str, str] = field(repr=False)
    body: bytes = field(repr=False)
    connect_s: float = CONNECT_S
    idle_s: float = IDLE_S
    overall_s: float = OVERALL_S
    stream: bool = False


@dataclass(frozen=True)
class Response:
    status: int
    body: bytes = field(repr=False)
    headers: Mapping[str, str] = field(default_factory=dict, repr=False)  # lower-case names


Transport = Callable[[Request], Response]


class _Reply(Protocol):
    status: int

    def read1(self, size: int = -1, /) -> bytes: ...
    def getheaders(self) -> list[tuple[str, str]]: ...


class _Connection(Protocol):
    sock: Any

    def connect(self) -> None: ...
    def request(self, method: str, url: str, body: bytes, headers: Mapping[str, str]) -> None: ...
    def getresponse(self) -> _Reply: ...
    def close(self) -> None: ...


class _Timer(Protocol):
    def start(self) -> None: ...
    def cancel(self) -> None: ...
    def join(self) -> None: ...


ConnectionFactory = Callable[[str, int, float], _Connection]
TimerFactory = Callable[[float, Callable[[], None]], _Timer]


def _default_connection(host: str, port: int, timeout: float) -> _Connection:
    return cast(_Connection, http.client.HTTPSConnection(host, port, timeout=timeout))


def _default_timer(interval: float, function: Callable[[], None]) -> _Timer:
    timer = threading.Timer(interval, function)
    timer.daemon = True
    return timer


class _Deadline:
    """Shared state of one call: the wall-clock deadline and the watchdog's verdict."""

    def __init__(self, request: Request, clock: Callable[[], float]) -> None:
        self.request = request
        self.clock = clock
        self.at = clock() + request.overall_s
        self.expired = threading.Event()

    def remaining(self) -> float:
        return self.at - self.clock()

    def per_read(self) -> float:
        """The socket timeout for the next read: idle (streaming) capped by what is left."""
        left = max(self.remaining(), 0.001)
        return min(self.request.idle_s, left) if self.request.stream else left

    def overall_timeout(self, partial: bytes = b"") -> OverallTimeout:
        return OverallTimeout(
            f"wall-clock deadline of {self.request.overall_s} s exceeded", partial
        )


class _BoundedRaw(io.RawIOBase):
    """Raw reader over the socket's own file: before every socket read it refuses past the
    deadline and sets the timeout to what is left, so a header or chunk-size trickle ends
    at the overall limit."""

    def __init__(self, inner: Any, sock: Any, deadline: _Deadline) -> None:
        super().__init__()
        self._inner, self._sock, self._deadline = inner, sock, deadline

    def readable(self) -> bool:
        return True

    def readinto(self, b: Any) -> int | None:
        if self._deadline.expired.is_set() or self._deadline.remaining() <= 0:
            raise self._deadline.overall_timeout()
        self._sock.settimeout(self._deadline.per_read())
        return cast(int | None, self._inner.readinto(b))

    def close(self) -> None:
        self._inner.close()
        super().close()


class _BoundedSocket:
    """The connection's socket with `makefile` bounded by the deadline; the rest delegates."""

    def __init__(self, sock: Any, deadline: _Deadline) -> None:
        self._sock, self._deadline = sock, deadline

    def makefile(self, mode: str = "rb") -> io.BufferedReader:
        # buffering=0 is the SocketIO itself: keeping only `.raw` of a buffered file would let
        # the dropped wrapper close the shared SocketIO when it is garbage-collected.
        raw = self._sock.makefile(mode, buffering=0)
        return io.BufferedReader(_BoundedRaw(raw, self._sock, self._deadline))

    def __getattr__(self, name: str) -> Any:
        return getattr(self._sock, name)


# The failures after the send that are not a timeout: (exception type, message label). Anything
# else after the send (e.g. ValueError from a closed file) is an "unexpected error". Each may have
# reached the provider, so it becomes a named TransportError the caller classifies
# SentChargeUnknown; it is not swallowed: the type is kept in the message.
_AFTER_SEND_LABELS: tuple[tuple[type[BaseException], str], ...] = (
    (OSError, "network error"),
    (http.client.HTTPException, "http error"),
)
_AFTER_SEND_ERRORS = (
    OSError,
    http.client.HTTPException,
    ValueError,
    RuntimeError,
    TypeError,
    AttributeError,
    LookupError,
    EOFError,
)


def _after_send_failure(
    error: BaseException, deadline: _Deadline, partial: bytes
) -> TransportError:
    """A failure after the request may have been written: the deadline's verdict wins."""
    if deadline.expired.is_set():
        return deadline.overall_timeout(partial)
    label = next((t for kind, t in _AFTER_SEND_LABELS if isinstance(error, kind)), None)
    return TransportError(f"{label or 'unexpected error'}: {type(error).__name__}", partial)


def _connect(conn: _Connection, request: Request) -> None:
    """Open the connection; a failure here wrote no request byte, so it is ``NotConnected``."""
    try:
        conn.connect()
    except TimeoutError:
        raise ConnectTimeout(f"no connection within {request.connect_s} s") from None
    except OSError as error:
        raise NotConnected(f"connection failed: {type(error).__name__}") from None


def _merged_headers(reply: _Reply) -> dict[str, str]:
    """Lower-case header names; a repeated header's values joined with ", "."""
    headers: dict[str, str] = {}
    for name, value in reply.getheaders():
        key = name.lower()
        headers[key] = f"{headers[key]}, {value}" if key in headers else value
    return headers


def _watchdog(deadline: _Deadline, raw_sock: Any, timer_factory: TimerFactory) -> _Timer:
    """Start the timer that shuts the socket at the deadline (its shutdown is an OverallTimeout)."""

    def expire() -> None:
        deadline.expired.set()
        try:
            raw_sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass  # already closed or never connected: the flag above still ends the call

    timer = timer_factory(max(deadline.remaining(), 0.0), expire)
    timer.start()
    return timer


def _exchange(conn: _Connection, path: str, deadline: _Deadline, chunks: list[bytes]) -> _Reply:
    """Send the request and read the whole reply into ``chunks``, bounded by ``deadline``."""
    request = deadline.request
    try:
        conn.request("POST", path, request.body, request.headers)
        reply = conn.getresponse()
        while chunk := reply.read1(READ_CHUNK_BYTES):
            chunks.append(chunk)
            if deadline.expired.is_set() or deadline.remaining() < 0:
                raise deadline.overall_timeout(b"".join(chunks))
    except TransportError as error:
        error.partial = error.partial or b"".join(chunks)
        raise
    except TimeoutError:
        if deadline.expired.is_set() or deadline.remaining() <= 0:
            raise deadline.overall_timeout(b"".join(chunks)) from None
        if request.stream:
            raise IdleTimeout(f"no byte within {request.idle_s} s", b"".join(chunks)) from None
        raise OverallTimeout(
            f"no byte within {deadline.request.overall_s} s", b"".join(chunks)
        ) from None
    except _AFTER_SEND_ERRORS as error:
        raise _after_send_failure(error, deadline, b"".join(chunks)) from None
    return reply


def https_transport(
    request: Request,
    *,
    clock: Callable[[], float] = time.monotonic,
    connection_factory: ConnectionFactory = _default_connection,
    timer_factory: TimerFactory = _default_timer,
) -> Response:
    """One bounded call. The overall limit is hard: a watchdog shuts the socket at the
    deadline (a timer shutdown is an OverallTimeout), every socket read is given only the
    time left, and the deadline is checked after every read. A failure to connect is
    ``NotConnected`` (nothing was sent); every failure after that may have reached the provider."""
    parts = urlsplit(request.url)
    if parts.scheme != "https" or not parts.hostname:
        raise InsecureUrl("only https endpoints are permitted")
    path = parts.path or "/"
    if parts.query:
        path = f"{path}?{parts.query}"
    deadline = _Deadline(request, clock)
    conn = connection_factory(parts.hostname, parts.port or 443, request.connect_s)
    chunks: list[bytes] = []
    watchdog: _Timer | None = None
    try:
        _connect(conn, request)
        raw_sock = conn.sock
        raw_sock.settimeout(deadline.per_read())
        conn.sock = _BoundedSocket(raw_sock, deadline)
        watchdog = _watchdog(deadline, raw_sock, timer_factory)
        reply = _exchange(conn, path, deadline, chunks)
        if deadline.expired.is_set() or deadline.remaining() < 0:
            raise deadline.overall_timeout(b"".join(chunks))
        return Response(reply.status, b"".join(chunks), _merged_headers(reply))
    finally:
        if watchdog is not None:
            watchdog.cancel()
            watchdog.join()  # no watchdog thread outlives the call
        conn.close()
