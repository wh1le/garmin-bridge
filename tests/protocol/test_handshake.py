import struct

from src.protocol.handshake import (
    handle_device_information,
    handle_configuration,
    handle_auth_negotiation,
    handle_current_time_request,
    handle_notification_subscription,
    handle_protobuf_request,
    build_device_settings,
    build_system_event_sync_ready,
)
from src.protocol.message import parse, MessageType, Status


def _parse_response(data):
    """Parse a response message, return (original_type, status, extra_payload)."""
    msg_type, payload = parse(data)
    assert msg_type == MessageType.RESPONSE
    original_type = struct.unpack_from("<H", payload, 0)[0]
    status = payload[2]
    return original_type, status, payload[3:]


# --- handle_device_information ---

def test_device_information_returns_valid_message():
    payload = struct.pack("<HHIHH", 150, 3851, 0x12345678, 1230, 512)
    payload += bytes([11]) + b"fenix 6 Pro"
    payload += bytes([5]) + b"fenix"
    payload += bytes([5]) + b"6 Pro"
    payload += bytes([0, 0])

    result = handle_device_information(payload)
    original_type, status, _ = _parse_response(result)

    assert original_type == MessageType.DEVICE_INFORMATION
    assert status == Status.ACK


def test_device_information_handles_short_payload():
    result = handle_device_information(b"")
    assert parse(result) is not None


# --- handle_configuration ---

def test_configuration_mirrors_capabilities():
    capabilities = bytes([0xFB, 0xFF, 0x3F, 0xA6])
    payload = bytes([len(capabilities)]) + capabilities

    messages = handle_configuration(payload)

    assert len(messages) == 1
    msg_type, msg_payload = parse(messages[0])
    assert msg_type == MessageType.CONFIGURATION
    assert msg_payload[0] == len(capabilities)
    assert msg_payload[1:] == capabilities


def test_configuration_empty_payload_returns_empty():
    assert handle_configuration(b"") == []


# --- handle_auth_negotiation ---

def test_auth_negotiation_returns_ack():
    payload = struct.pack("<BI", 1, 0x00000001)
    result = handle_auth_negotiation(payload)
    original_type, status, _ = _parse_response(result)

    assert original_type == MessageType.AUTH_NEGOTIATION
    assert status == Status.ACK


# --- handle_current_time_request ---

def test_current_time_returns_ack_with_timestamp():
    payload = struct.pack("<I", 42)
    result = handle_current_time_request(payload)
    original_type, status, extra = _parse_response(result)

    assert original_type == MessageType.CURRENT_TIME_REQUEST
    assert status == Status.ACK

    reference_id = struct.unpack_from("<I", extra, 0)[0]
    garmin_ts = struct.unpack_from("<I", extra, 4)[0]

    assert reference_id == 42
    assert garmin_ts > 0


# --- handle_notification_subscription ---

def test_notification_subscription_returns_ack():
    payload = bytes([1, 0])  # enable=1, unknown=0
    result = handle_notification_subscription(payload)
    original_type, status, _ = _parse_response(result)

    assert original_type == MessageType.NOTIFICATION_SUBSCRIPTION
    assert status == Status.ACK


# --- handle_protobuf_request ---

def test_protobuf_request_returns_unsupported():
    payload = bytes([5]) + bytes(18)  # request_id=5
    result = handle_protobuf_request(payload)
    original_type, status, _ = _parse_response(result)

    assert original_type == MessageType.PROTOBUF_REQUEST
    assert status == Status.UNSUPPORTED


# --- build_device_settings ---

def test_device_settings_is_valid_message():
    result = build_device_settings()
    msg_type, payload = parse(result)

    assert msg_type == MessageType.DEVICE_SETTINGS
    assert payload[0] == 3  # 3 settings


# --- build_system_event_sync_ready ---

def test_system_event_sync_ready_is_valid_message():
    result = build_system_event_sync_ready()
    msg_type, payload = parse(result)

    assert msg_type == MessageType.SYSTEM_EVENT
    assert payload[0] == 8  # SYNC_READY ordinal
