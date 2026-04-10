"""COBS (Consistent Overhead Byte Stuffing) codec.

Garmin variant: leading 0x00 + COBS-encoded payload + trailing 0x00.
"""


def encode(data: bytes) -> bytes:
    out = bytearray([0x00])  # Garmin leading zero
    i = 0
    n = len(data)

    while i < n:
        start = i
        while i < n and data[i] != 0x00:
            i += 1

        payload_size = i - start
        last_was_zero = i < n and data[i] == 0x00

        while payload_size >= 0xFE:
            out.append(0xFF)
            out.extend(data[start : start + 0xFE])
            payload_size -= 0xFE
            start += 0xFE

        out.append(payload_size + 1)
        out.extend(data[start : start + payload_size])

        if last_was_zero:
            i += 1

    if len(data) > 0 and data[-1] == 0x00:
        out.append(0x01)

    out.append(0x00)  # trailing delimiter
    return bytes(out)


def decode(data: bytes) -> bytes:
    if len(data) < 4:
        return b""
    if data[0] != 0x00:
        return b""
    if data[-1] != 0x00:
        return b""

    buf = data[1:-1]  # strip leading and trailing 0x00
    out = bytearray()
    i = 0

    while i < len(buf):
        code = buf[i] & 0xFF
        i += 1

        if code == 0:
            break

        payload_size = code - 1
        for _ in range(payload_size):
            if i >= len(buf):
                break
            out.append(buf[i])
            i += 1

        if code != 0xFF and i < len(buf):
            out.append(0x00)

    return bytes(out)
