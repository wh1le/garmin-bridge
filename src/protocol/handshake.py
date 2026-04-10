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
    log.info("Watch sent CONFIGURATION (%d capability bytes)", num_bytes)

    # Gadgetbridge enables almost all 120 capability bits.
    # Set all bits, then clear the ones Gadgetbridge excludes (104-111, 114-119).
    our_capabilities = bytearray(b"\xFF" * num_bytes)
    excluded_bits = list(range(104, 112)) + list(range(114, 120))
    for bit in excluded_bits:
        byte_index = bit // 8
        bit_index  = bit % 8
        if byte_index < num_bytes:
            our_capabilities[byte_index] &= ~(1 << bit_index)

    config_payload = bytes([len(our_capabilities)]) + bytes(our_capabilities)

    return [
        build_response(MessageType.CONFIGURATION, Status.ACK),
        build(MessageType.CONFIGURATION, config_payload),
    ]


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

    response = struct.pack("<IIIII",
        reference_id,
        garmin_ts,
        local_offset,
        0,  # next DST end
        0,  # next DST start
    )
    return build_response(MessageType.CURRENT_TIME_REQUEST, Status.ACK, response)


def build_device_settings():
    """Build DEVICE_SETTINGS (5026) enabling weather. Returns bytes to send."""
    log.info("Sending DEVICE_SETTINGS (weather enabled)")

    # Settings enum ordinals from SetDeviceSettingsMessage.java:
    # 6 = AUTO_UPLOAD_ENABLED, 7 = WEATHER_CONDITIONS_ENABLED, 8 = WEATHER_ALERTS_ENABLED
    payload = bytes([3])  # number of settings

    # AUTO_UPLOAD_ENABLED = true
    payload += bytes([6, 1, 1])
    # WEATHER_CONDITIONS_ENABLED = true
    payload += bytes([7, 1, 1])
    # WEATHER_ALERTS_ENABLED = true
    payload += bytes([8, 1, 1])

    return build(MessageType.DEVICE_SETTINGS, payload)


def build_system_event_sync_ready():
    """Build SYSTEM_EVENT (5030) with SYNC_READY. Returns bytes to send."""
    log.info("Sending SYSTEM_EVENT (SYNC_READY)")
    # SYNC_READY = ordinal 8
    payload = bytes([8])
    return build(MessageType.SYSTEM_EVENT, payload)


# --- Private ---

def _pack_string(value):
    """Length-prefixed UTF-8 string (Garmin wire format)."""
    encoded = value.encode("utf-8")
    return bytes([len(encoded)]) + encoded
