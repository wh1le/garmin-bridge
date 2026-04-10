"""Minimal protobuf codec and GFDI protobuf message wrapper.

Hand-encodes/decodes protobuf — no protobuf dependency.
Also handles the GFDI wrapper around protobuf (request_id, offsets, lengths).
"""

import struct


# --- Protobuf encoding ---

def varint(value):
    """Encode an unsigned integer as a protobuf varint."""
    result = bytearray()
    while value > 0x7F:
        result.append((value & 0x7F) | 0x80)
        value >>= 7
    result.append(value & 0x7F)
    return bytes(result)


def field_varint(field_number, value):
    """Encode a varint field: tag + varint value."""
    tag = (field_number << 3) | 0  # wire type 0 = varint
    return varint(tag) + varint(value)


def field_bool(field_number, value):
    """Encode a bool field."""
    return field_varint(field_number, 1 if value else 0)


def field_bytes(field_number, data):
    """Encode a length-delimited field: tag + length + data."""
    tag = (field_number << 3) | 2  # wire type 2 = length-delimited
    return varint(tag) + varint(len(data)) + data


def field_string(field_number, value):
    """Encode a string field."""
    return field_bytes(field_number, value.encode("utf-8"))


def field_message(field_number, encoded_message):
    """Wrap an already-encoded message as a nested field."""
    return field_bytes(field_number, encoded_message)


# --- Protobuf decoding ---

def decode_varint(data, offset):
    """Decode a varint at offset. Returns (value, new_offset)."""
    value = 0
    shift = 0
    while offset < len(data):
        byte = data[offset]
        value |= (byte & 0x7F) << shift
        offset += 1
        if byte & 0x80 == 0:
            return value, offset
        shift += 7
    return value, offset


def decode_field(data, offset):
    """Decode one protobuf field. Returns (field_number, wire_type, value, new_offset)."""
    tag, offset = decode_varint(data, offset)
    field_number = tag >> 3
    wire_type = tag & 0x07

    if wire_type == 0:  # varint
        value, offset = decode_varint(data, offset)
    elif wire_type == 2:  # length-delimited
        length, offset = decode_varint(data, offset)
        value = data[offset:offset + length]
        offset += length
    elif wire_type == 5:  # 32-bit fixed
        value = struct.unpack_from("<I", data, offset)[0]
        offset += 4
    elif wire_type == 1:  # 64-bit fixed
        value = struct.unpack_from("<Q", data, offset)[0]
        offset += 8
    else:
        raise ValueError(f"Unknown wire type {wire_type}")

    return field_number, wire_type, value, offset


def decode_all(data):
    """Decode all fields in a protobuf message. Returns list of (field_number, value)."""
    fields = []
    offset = 0
    while offset < len(data):
        field_number, _wire_type, value, offset = decode_field(data, offset)
        fields.append((field_number, value))
    return fields


def get_field(data, target_field_number):
    """Find a specific field in protobuf data. Returns value or None."""
    for field_number, value in decode_all(data):
        if field_number == target_field_number:
            return value
    return None


# --- GFDI protobuf wrapper ---
# Layout: request_id(2) + data_offset(4) + total_length(4) + data_length(4) + protobuf(N)

def parse_request(payload):
    """Parse GFDI PROTOBUF_REQUEST wrapper. Returns (request_id, protobuf_data) or None."""
    if len(payload) < 14:
        return None

    request_id   = struct.unpack_from("<H", payload, 0)[0]
    data_offset  = struct.unpack_from("<I", payload, 2)[0]
    total_length = struct.unpack_from("<I", payload, 6)[0]
    data_length  = struct.unpack_from("<I", payload, 10)[0]

    if data_offset != 0 or total_length != data_length:
        return None  # chunked messages not supported

    protobuf_data = payload[14:14 + data_length]
    return request_id, protobuf_data


def build_response(request_id, protobuf_data):
    """Build GFDI PROTOBUF_RESPONSE wrapper payload."""
    return struct.pack("<HIII",
        request_id,
        0,                      # data_offset
        len(protobuf_data),     # total_length
        len(protobuf_data),     # data_length
    ) + protobuf_data
