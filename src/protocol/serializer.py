"""Garmin binary serializer — converts Python values to wire format.

Packs definition records (schema) and data records (rows) for the
Garmin FIT binary table format. Also provides value converters for
Garmin-specific types (timestamps, coordinates, temperatures).
"""

import struct

# Garmin epoch: Dec 31, 1989 00:00:00 UTC
GARMIN_EPOCH = 631065600


def definition(local_type, native_msg, fields):
    """Build a definition record. fields = [(number, size, base_type), ...]"""
    buf = bytes([0x40 | (local_type & 0x0F), 0, 0])
    buf += struct.pack("<H", native_msg)
    buf += bytes([len(fields)])
    for number, size, base_type in fields:
        buf += bytes([number, size, base_type])
    return buf


def data(local_type, fmt, *values):
    """Build a data record: header byte + struct-packed values."""
    return bytes([local_type & 0x0F]) + struct.pack(fmt, *values)


def garmin_timestamp(unix_ts):
    """Convert Unix timestamp to Garmin epoch."""
    return unix_ts - GARMIN_EPOCH


def garmin_coordinate(degrees):
    """Convert degrees to Garmin semicircles."""
    return int(degrees * (2**31 / 180))


def clamp_temperature(value):
    """Clamp temperature to signed byte range (-128 to 127)."""
    return max(-128, min(127, round(value)))


def pack_string(value, size):
    """Pad/truncate a UTF-8 string to fixed byte width."""
    encoded = value.encode("utf-8")[: size - 1]
    return encoded + b"\x00" * (size - len(encoded))
