from src.protocol.message import build, parse, build_response, MessageType, Status


# --- build + parse roundtrip ---

def test_roundtrip_empty_payload():
    msg_type, payload = parse(build(MessageType.WEATHER_REQUEST))
    assert msg_type == MessageType.WEATHER_REQUEST
    assert payload == b""


def test_roundtrip_with_payload():
    original = b"\x01\x02\x03\x04\x05"
    msg_type, payload = parse(build(MessageType.CONFIGURATION, original))
    assert msg_type == MessageType.CONFIGURATION
    assert payload == original


def test_roundtrip_preserves_all_message_types():
    for msg_type in MessageType:
        result = parse(build(msg_type, b"\xff"))
        assert result is not None
        assert result[0] == msg_type


# --- build ---

def test_build_minimum_size():
    """Smallest message: size(2) + type(2) + crc(2) = 6 bytes."""
    assert len(build(MessageType.RESPONSE)) == 6


def test_build_size_grows_with_payload():
    small = build(MessageType.RESPONSE, b"\x01")
    large = build(MessageType.RESPONSE, b"\x01\x02\x03")
    assert len(large) - len(small) == 2


# --- parse ---

def test_parse_rejects_too_short():
    assert parse(b"\x00\x01\x02") is None


def test_parse_rejects_wrong_size():
    msg = build(MessageType.RESPONSE)
    corrupted = msg + b"\x00"
    assert parse(corrupted) is None


def test_parse_rejects_bad_checksum():
    msg = bytearray(build(MessageType.RESPONSE))
    msg[-1] ^= 0xFF  # flip last byte
    assert parse(bytes(msg)) is None


# --- build_response ---

def test_build_response_roundtrip():
    msg_type, payload = parse(build_response(MessageType.WEATHER_REQUEST, Status.ACK))
    assert msg_type == MessageType.RESPONSE
    assert payload[0:2] != b""  # contains original type
    assert payload[2] == Status.ACK
