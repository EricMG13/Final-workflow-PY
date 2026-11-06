"""S18 review fixes in the fetch leaf: an idna-unencodable host is a refusal, port 0 is refused,
and an unparsable Last-Modified header is "not located" (no fall back to the body line).

No test dials: the resolver below runs only the idna codec the system resolver runs first, and an
autouse guard fails any real socket or lookup.
"""

import socket
from collections.abc import Sequence

import pytest

from deploy_workflow.research import webfetch


@pytest.fixture(autouse=True)
def no_real_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(*args: object, **kwargs: object) -> None:
        raise AssertionError("a test reached the real network")

    monkeypatch.setattr(socket, "socket", refuse)
    monkeypatch.setattr(socket, "getaddrinfo", refuse)


def codec_resolver(host: str) -> Sequence[str]:
    """What ``socket.getaddrinfo`` does before any lookup: encode the host with idna."""
    host.encode("idna")
    raise AssertionError("the codec accepted the host; no lookup is made in a test")


def never_connect(target: webfetch.ConnectionTarget) -> webfetch.ConnectionLike:
    raise AssertionError("no connection is made for a host that does not resolve")


@pytest.mark.parametrize("host", ["a" * 64 + ".example.com", "a..example.com"])
def test_a_host_the_idna_codec_refuses_is_a_recorded_refusal(host: str) -> None:
    url = f"https://{host}/x"
    assert webfetch.check_url(url).host == host  # the static shape holds; only the lookup fails
    record, body, media = webfetch.fetch(
        url,
        manifest_hosts=frozenset({host}),
        resolver=codec_resolver,
        connect=never_connect,
        cap=100,
        clock=lambda: 0.0,
    )
    assert (body, media) == (None, None)
    assert record.reason == f"host {host} did not resolve: UnicodeEncodeError"
    assert (record.resolved_ip, record.status, record.item_id) == (None, None, None)


def test_port_zero_is_refused_not_mapped_to_443() -> None:
    with pytest.raises(webfetch.UrlRefused) as refused:
        webfetch.check_url("https://example.com:0/x")
    assert refused.value.reason == "url https://example.com:0/x: the port is not valid"


def test_an_absent_port_is_443_and_a_stated_one_is_kept() -> None:
    assert webfetch.check_url("https://example.com/x").port == 443
    assert webfetch.check_url("https://example.com:8443/x").port == 8443


def test_an_unparsable_last_modified_does_not_fall_back_to_the_body_line() -> None:
    headers = {"Last-Modified": "garbage"}
    assert webfetch.locate_published(headers, b"Published: 2027-01-01\n") == (None, None)


def test_without_the_header_the_body_line_is_located() -> None:
    found, source = webfetch.locate_published({}, b"Published: 2027-01-01\n")
    assert (found.isoformat() if found else None, source) == ("2027-01-01", "body:published-line")
