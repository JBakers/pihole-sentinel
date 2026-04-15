"""Unit tests for mock Pi-hole DNS responder.

These tests validate the UDP DNS response builder used in Docker integration
so monitor.py dig checks can be exercised in tests.
"""

import importlib.util
from pathlib import Path


_MOCK_PATH = Path(__file__).resolve().parent.parent / "docker" / "mock-pihole" / "mock_pihole.py"
_spec = importlib.util.spec_from_file_location("mock_pihole", _MOCK_PATH)
mock_pihole = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mock_pihole)


def _dns_query_a_example_com() -> bytes:
    # ID=0x1234, standard query, QDCOUNT=1
    header = b"\x12\x34\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00"
    qname = b"\x07example\x03com\x00"
    qtype_qclass = b"\x00\x01\x00\x01"  # A IN
    return header + qname + qtype_qclass


def test_build_dns_response_noerror_contains_answer():
    query = _dns_query_a_example_com()
    mock_pihole.state["dns_working"] = True

    response = mock_pihole.build_dns_response(query)

    assert response[:2] == b"\x12\x34"  # transaction id preserved
    assert response[2:4] == b"\x81\x80"  # standard response + NOERROR
    assert response[6:8] == b"\x00\x01"  # ancount=1
    assert response.endswith(b"\x01\x02\x03\x04")  # A record 1.2.3.4


def test_build_dns_response_servfail_without_answer():
    query = _dns_query_a_example_com()
    mock_pihole.state["dns_working"] = False

    response = mock_pihole.build_dns_response(query)

    assert response[:2] == b"\x12\x34"  # transaction id preserved
    assert response[2:4] == b"\x81\x82"  # SERVFAIL
    assert response[6:8] == b"\x00\x00"  # ancount=0


def test_build_dns_response_invalid_query_returns_empty():
    assert mock_pihole.build_dns_response(b"\x00\x01") == b""
