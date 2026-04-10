import struct

from src.notifications import (
    _encode_actions,
    _encode_action,
    _build_update,
    _parse_requested_attributes,
    _tlv,
    ATTR_TITLE, ATTR_MESSAGE, ATTR_ACTIONS, ATTR_DATE, ATTR_APP_IDENTIFIER,
    ACTION_CUSTOM_1, ACTION_DISMISS,
    ICON_LEFT, ICON_RIGHT,
    ADD, CATEGORY_BUSINESS,
)
from src.protocol.message import parse, MessageType


# --- _build_update ---

def test_build_update_is_valid_message():
    result = _build_update(12345, CATEGORY_BUSINESS)
    msg_type, payload = parse(result)

    assert msg_type == MessageType.NOTIFICATION_UPDATE
    assert payload[0] == ADD


def test_build_update_contains_notification_id():
    result = _build_update(12345, CATEGORY_BUSINESS)
    _, payload = parse(result)

    notification_id = struct.unpack_from("<I", payload, 4)[0]
    assert notification_id == 12345


# --- _encode_actions ---

def test_encode_actions_empty():
    result = _encode_actions([])
    assert result == bytes([0])


def test_encode_actions_with_items():
    actions = [
        (ACTION_CUSTOM_1, ICON_RIGHT, "Done"),
        (ACTION_DISMISS, ICON_LEFT, "Dismiss"),
    ]
    result = _encode_actions(actions)

    assert result[0] == 2  # count
    assert b"Done" in result
    assert b"Dismiss" in result


# --- _encode_action ---

def test_encode_action_format():
    result = _encode_action(ACTION_CUSTOM_1, ICON_RIGHT, "Done")

    assert result[0] == ACTION_CUSTOM_1
    assert result[1] == ICON_RIGHT
    assert result[2] == 4  # label length
    assert result[3:] == b"Done"


# --- _parse_requested_attributes ---

def test_parse_full_request():
    # TITLE(1) + max_length(150) + MESSAGE(3) + max_length(700)
    data = bytes([1]) + struct.pack("<H", 150) + bytes([3]) + struct.pack("<H", 700)
    attrs = _parse_requested_attributes(data)

    assert attrs[ATTR_TITLE] == 150
    assert attrs[ATTR_MESSAGE] == 700


def test_parse_short_request_without_lengths():
    # ACTIONS(127) + param(20) + DATE(5) + TITLE(1) + MESSAGE_SIZE(4)
    data = bytes([127, 20, 5, 1, 4])
    attrs = _parse_requested_attributes(data)

    assert ATTR_ACTIONS in attrs
    assert ATTR_DATE in attrs
    assert ATTR_TITLE in attrs


def test_parse_empty():
    assert _parse_requested_attributes(b"") == {}


# --- _tlv ---

def test_tlv_format():
    result = _tlv(ATTR_TITLE, b"hello")

    assert result[0] == ATTR_TITLE
    assert struct.unpack_from("<H", result, 1)[0] == 5  # length
    assert result[3:] == b"hello"


def test_tlv_empty_value():
    result = _tlv(ATTR_APP_IDENTIFIER, b"")

    assert result[0] == ATTR_APP_IDENTIFIER
    assert struct.unpack_from("<H", result, 1)[0] == 0
