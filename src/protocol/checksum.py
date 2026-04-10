"""CRC-16 checksum for Garmin GFDI messages.

Ported from Gadgetbridge ChecksumCalculator.java.
Uses a nibble-based lookup table approach.
"""

_TABLE = [
    0x0000, 0xCC01, 0xD801, 0x1400, 0xF001, 0x3C00, 0x2800, 0xE401,
    0xA001, 0x6C00, 0x7800, 0xB401, 0x5000, 0x9C01, 0x8801, 0x4400,
]


def crc16(data: bytes | bytearray, init: int = 0) -> int:
    crc = init
    for b in data:
        crc = (((crc >> 4) & 0x0FFF) ^ _TABLE[crc & 0x0F]) ^ _TABLE[b & 0x0F]
        crc = (((crc >> 4) & 0x0FFF) ^ _TABLE[crc & 0x0F]) ^ _TABLE[(b >> 4) & 0x0F]
    return crc & 0xFFFF
