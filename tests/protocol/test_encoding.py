import pytest

from src.protocol.encoding import encode, decode


@pytest.mark.parametrize("original", [
    b"\x01\x02\x03",
    b"\x00",
    b"\x00\x00\x00",
    b"\x01\x00\x03\x04",
    b"\xff" * 300,
    b"hello world",
    bytes(range(256)),
])
def test_roundtrip(original):
    assert decode(encode(original)) == original


def test_encoded_starts_and_ends_with_zero():
    encoded = encode(b"anything")
    assert encoded[0] == 0x00
    assert encoded[-1] == 0x00


def test_no_zeros_inside_encoded_payload():
    encoded = encode(bytes(range(256)))
    inner = encoded[1:-1]
    assert 0x00 not in inner


def test_decode_rejects_short_input():
    assert decode(b"\x00\x01\x00") == b""


def test_decode_rejects_missing_leading_zero():
    assert decode(b"\x01\x02\x01\x00") == b""


def test_decode_rejects_missing_trailing_zero():
    assert decode(b"\x00\x02\x01\x03") == b""
