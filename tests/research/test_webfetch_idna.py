"""A host the IDNA codec refuses is a typed refusal, never an escaped UnicodeError (S16 A03/C04).

Before the fix `check_url` accepted `www..example.com` (an empty label) and a 64-character label;
`socket.getaddrinfo` then raised UnicodeEncodeError (a ValueError, not an OSError), which escaped
`fetch()` and stopped the whole intake. Fakes only: an autouse guard fails any real socket or
name lookup.
"""

import socket

import pytest

from deploy_workflow.research import webfetch
from deploy_workflow.research.intake import IntakeError, parse_rows

EMPTY_LABEL = "https://www..example.com/a"
LONG_LABEL = "https://" + "a" * 64 + ".example.com/a"  # 64 > the 63-character label limit
REASON = "the host is not a valid domain name (an empty label or one over 63 characters)"


@pytest.fixture(autouse=True)
def no_real_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(*args: object, **kwargs: object) -> None:
        raise AssertionError("a test reached the real network")

    monkeypatch.setattr(socket, "socket", refuse)
    monkeypatch.setattr(socket, "getaddrinfo", refuse)


def _fetch(url: str, resolver: webfetch.Resolver, connect: webfetch.Connector, host: str):
    return webfetch.fetch(
        url,
        manifest_hosts=frozenset({host}),
        resolver=resolver,
        connect=connect,
        cap=100,
        clock=lambda: 0.0,
    )


def _never(*args: object) -> list[str]:
    raise AssertionError("resolved or connected a host check_url should refuse")


@pytest.mark.parametrize("url", [EMPTY_LABEL, LONG_LABEL])
def test_check_url_refuses_a_host_idna_cannot_encode(url: str) -> None:
    with pytest.raises(webfetch.UrlRefused) as raised:
        webfetch.check_url(url)
    assert str(raised.value) == f"url {url}: {REASON}"


def test_a_63_character_label_and_a_trailing_dot_are_still_accepted() -> None:
    url = "https://" + "a" * 63 + ".example.com./a"
    assert webfetch.check_url(url).host == "a" * 63 + ".example.com."


@pytest.mark.parametrize("url", [EMPTY_LABEL, LONG_LABEL])
def test_fetch_records_the_refusal_without_resolving(url: str) -> None:
    host = url.split("/")[2]
    record, body, media = _fetch(url, _never, _never, host)
    assert record.reason == f"url {url}: {REASON}"
    assert (record.resolved_ip, record.status, body, media) == (None, None, None, None)


def test_a_unicode_error_from_the_resolver_is_a_recorded_refusal() -> None:
    url = "https://good.example/a"
    record, body, _media = _fetch(url, _raise_unicode, _never, "good.example")
    assert record.reason == "host good.example did not resolve: UnicodeEncodeError"
    assert body is None


def _raise_unicode(host: str) -> list[str]:
    """What socket.getaddrinfo and ssl's server_hostname do with a label IDNA refuses."""
    ("." + host).encode("idna")  # a leading empty label: UnicodeEncodeError
    raise AssertionError("idna accepted an empty label")


def test_a_manifest_row_with_such_a_host_is_an_intake_error() -> None:
    row = {"tag": "research", "url": EMPTY_LABEL, "family": "f", "locator": "L1"}
    with pytest.raises(IntakeError) as raised:
        parse_rows([row])
    assert str(raised.value) == f"url {EMPTY_LABEL}: {REASON}"


def test_a_redirect_to_such_a_host_is_refused() -> None:
    with pytest.raises(webfetch.UrlRefused) as raised:
        webfetch._redirect_target("https://good.example/a", "https://www..example.com/b")
    assert str(raised.value) == f"redirect to https://www..example.com/b refused: {REASON}"


class _Redirect:
    """A connection whose one answer is a 302 to `location`."""

    def __init__(self, location: str) -> None:
        self.location = location
        self.status = 302

    def request(self, method: str, url: str, *, headers: object) -> None:
        pass

    def getresponse(self) -> "_Redirect":
        return self

    def getheader(self, name: str, default: str | None = None) -> str | None:
        return self.location if name.lower() == "location" else default

    def read(self, amt: int) -> bytes:
        return b""

    def close(self) -> None:
        pass


@pytest.mark.parametrize(
    "location", ["https://www..example.com/b", "//" + "b" * 64 + ".example.com/"]
)
def test_a_redirect_to_a_host_idna_refuses_is_a_recorded_refusal(location: str) -> None:
    # even when the manifest names the bad host, the fetch records a refusal (no escaped error)
    host = location.split("/")[2]
    record, body, media = _fetch(
        "https://good.example/a",
        lambda host: ["93.184.216.34"],
        lambda target: _Redirect(location),
        host,
    )
    assert record.reason is not None
    assert record.reason.endswith(f"refused: {REASON}")
    assert (record.hops, body, media) == (0, None, None)
