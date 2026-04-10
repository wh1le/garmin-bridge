"""Connection handshake — initial message exchange after GFDI registration.

The watch sends DEVICE_INFORMATION, CONFIGURATION, AUTH_NEGOTIATION,
and optionally CURRENT_TIME_REQUEST. We respond to each to establish
a working session where the watch knows we support weather, time, etc.

Each handler takes a payload and returns bytes to send back.
"""

import struct
import time

from src.logger import log
from src.protocol.message import MessageType, Status, build, build_response
from src.protocol import serializer


def handle_device_information(payload):
    """Respond to DEVICE_INFORMATION (5024). Returns bytes to send."""
    protocol_version = 150
    if len(payload) >= 2:
        protocol_version = struct.unpack_from("<H", payload, 0)[0]

    log.info("Watch sent DEVICE_INFORMATION (protocol=%d)", protocol_version)

    protocol_flags = 1 if protocol_version // 100 == 1 else 0

    response = struct.pack("<HH", protocol_version, 0xFFFF)
    response += struct.pack("<I", 0xFFFFFFFF)
    response += struct.pack("<HH", 7791, 0xFFFF)
    response += _pack_string("garmin-bridge")
    response += _pack_string("Linux")
    response += _pack_string("garmin-bridge")
    response += struct.pack("<B", protocol_flags)

    return build_response(MessageType.DEVICE_INFORMATION, Status.ACK, response)


def handle_configuration(payload):
    """Respond to CONFIGURATION (5050). Returns list of bytes to send."""
    if len(payload) < 1:
        return []

    num_bytes = payload[0]
    watch_capabilities = payload[1:1 + num_bytes]
    log.info("Watch sent CONFIGURATION (%d capability bytes)", num_bytes)

    config_payload = bytes([num_bytes]) + watch_capabilities
    return [build(MessageType.CONFIGURATION, config_payload)]


def handle_auth_negotiation(payload):
    """Respond to AUTH_NEGOTIATION (5101). Returns bytes to send."""
    unknown = payload[0] if len(payload) >= 1 else 0
    flags = struct.unpack_from("<I", payload, 1)[0] if len(payload) >= 5 else 0
    log.info("Watch sent AUTH_NEGOTIATION (unknown=%d flags=0x%08x)", unknown, flags)

    response = struct.pack("<BI", 0, 0)
    return build_response(MessageType.AUTH_NEGOTIATION, Status.ACK, response)


def handle_current_time_request(payload):
    """Respond to CURRENT_TIME_REQUEST (5052). Returns bytes to send."""
    reference_id = struct.unpack_from("<I", payload, 0)[0] if len(payload) >= 4 else 0
    log.info("Watch sent CURRENT_TIME_REQUEST (ref=%d)", reference_id)

    now = int(time.time())
    garmin_ts = serializer.garmin_timestamp(now)
    local_offset = -(time.timezone if time.daylight == 0 else time.altzone)

    response = struct.pack("<IIIII", reference_id, garmin_ts, local_offset, 0, 0)
    return build_response(MessageType.CURRENT_TIME_REQUEST, Status.ACK, response)


def handle_notification_subscription(payload):
    """Respond to NOTIFICATION_SUBSCRIPTION (5036). Returns bytes to send."""
    enable = payload[0] if len(payload) >= 1 else 0
    unknown = payload[1] if len(payload) >= 2 else 0
    log.info("Watch sent NOTIFICATION_SUBSCRIPTION (enable=%d)", enable)

    response = struct.pack("<BBB", 0, enable, unknown)
    return build_response(MessageType.NOTIFICATION_SUBSCRIPTION, Status.ACK, response)


def handle_protobuf_request(payload):
    """Respond to PROTOBUF_REQUEST (5043) with UNSUPPORTED.

    Calendar and other protobuf services are not implemented yet.
    """
    request_id = payload[0] if len(payload) >= 1 else 0
    log.info("Watch sent PROTOBUF_REQUEST (id=%d, %d bytes)", request_id, len(payload))
    return build_response(MessageType.PROTOBUF_REQUEST, Status.UNSUPPORTED)


def build_device_settings():
    """Build DEVICE_SETTINGS (5026) enabling weather."""
    log.info("Sending DEVICE_SETTINGS (weather enabled)")

    payload = bytes([
        3,        # setting count
        6, 1, 1,  # auto_upload = true
        7, 1, 1,  # weather_conditions = true
        8, 1, 1,  # weather_alerts = true
    ])
    return build(MessageType.DEVICE_SETTINGS, payload)


def build_system_event_sync_ready():
    """Build SYSTEM_EVENT (5030) with SYNC_READY."""
    log.info("Sending SYSTEM_EVENT (SYNC_READY)")
    return build(MessageType.SYSTEM_EVENT, bytes([8]))


def _pack_string(value):
    """Length-prefixed UTF-8 string (Garmin wire format)."""
    encoded = value.encode("utf-8")
    return bytes([len(encoded)]) + encoded
