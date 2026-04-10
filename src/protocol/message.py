"""GFDI message framing — build and parse Garmin protocol messages.

Binary layout:
  [size:2][type:2][payload:N][crc:2]
All fields little-endian. Size includes itself.
"""

import struct
from enum import IntEnum

from src.protocol.checksum import crc16


class MessageType(IntEnum):
    RESPONSE = 5000
    FIT_DEFINITION = 5011
    FIT_DATA = 5012
    WEATHER_REQUEST = 5014
    DEVICE_INFORMATION = 5024
    DEVICE_SETTINGS = 5026
    SYSTEM_EVENT = 5030
    CONFIGURATION = 5050
    CURRENT_TIME_REQUEST = 5052
    AUTH_NEGOTIATION = 5101


class Status(IntEnum):
    ACK = 0
    NAK = 1
    UNSUPPORTED = 2
    DECODE_ERROR = 3
    CRC_ERROR = 4
    LENGTH_ERROR = 5


def build(msg_type: int, payload: bytes = b"") -> bytes:
    size = 2 + 2 + len(payload) + 2  # size + type + payload + crc
    header = struct.pack("<HH", size, msg_type)
    body = header + payload
    checksum = crc16(body)
    return body + struct.pack("<H", checksum)


def build_response(original_type: int, status: int, payload: bytes = b"") -> bytes:
    resp_payload = struct.pack("<HB", original_type, status) + payload
    return build(MessageType.RESPONSE, resp_payload)


def parse(data: bytes) -> tuple[int, bytes] | None:
    if len(data) < 6:
        return None

    size, msg_type = struct.unpack_from("<HH", data, 0)
    if size != len(data):
        return None

    expected_crc = crc16(data[: size - 2])
    actual_crc = struct.unpack_from("<H", data, size - 2)[0]
    if expected_crc != actual_crc:
        return None

    payload = data[4 : size - 2]

    # Garmin encodes some types with high bit set
    if msg_type & 0x8000:
        msg_type = (msg_type & 0xFF) + 5000

    return msg_type, payload
