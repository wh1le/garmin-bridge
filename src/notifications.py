"""Notification protocol — send and manage notifications on the watch.

Generic notification sending. Feature modules (todos, desktop notifications)
call send() to push notifications. This module handles the protocol:
NOTIFICATION_UPDATE (5033), NOTIFICATION_CONTROL (5034), NOTIFICATION_DATA (5035).
"""

import asyncio
import struct
import time

from src.logger import log
from src.protocol import MessageType
from src.protocol.message import build
from src.protocol.checksum import crc16

# Update types
ADD    = 0
MODIFY = 1
REMOVE = 2

# Notification categories (from Gadgetbridge NotificationCategory enum)
CATEGORY_OTHER              = 0
CATEGORY_INCOMING_CALL      = 1
CATEGORY_MISSED_CALL        = 2
CATEGORY_VOICEMAIL          = 3
CATEGORY_SOCIAL             = 4
CATEGORY_SCHEDULE           = 5
CATEGORY_EMAIL              = 6
CATEGORY_NEWS               = 7
CATEGORY_HEALTH_AND_FITNESS = 8
CATEGORY_BUSINESS           = 9
CATEGORY_LOCATION           = 10
CATEGORY_ENTERTAINMENT      = 11
CATEGORY_SMS                = 12

# Action codes
ACTION_CUSTOM_1             = 1
ACTION_CUSTOM_2             = 2
ACTION_CUSTOM_3             = 3
ACTION_CUSTOM_4             = 4
ACTION_CUSTOM_5             = 5
ACTION_REPLY_INCOMING_CALL  = 94
ACTION_REPLY_MESSAGES       = 95
ACTION_ACCEPT_INCOMING_CALL = 96
ACTION_REJECT_INCOMING_CALL = 97
ACTION_DISMISS              = 98
ACTION_BLOCK_APPLICATION    = 99

# Icon positions
ICON_NONE   = 0x00
ICON_LEFT   = 0x01
ICON_RIGHT  = 0x02
ICON_BOTTOM = 0x04

# Notification flags
FLAG_FOREGROUND     = 0x01
FLAG_ACTION_DECLINE = 0x04

# Phone flags
PHONE_FLAG_NEW_ACTIONS = 0x02

# TLV attribute types
ATTR_APP_IDENTIFIER = 0
ATTR_TITLE          = 1
ATTR_SUBTITLE       = 2
ATTR_MESSAGE        = 3
ATTR_MESSAGE_SIZE   = 4
ATTR_DATE           = 5
ATTR_ACTIONS        = 127

_KNOWN_ATTRS = {
    ATTR_APP_IDENTIFIER, ATTR_TITLE, ATTR_SUBTITLE, ATTR_MESSAGE,
    ATTR_MESSAGE_SIZE, ATTR_DATE, ATTR_ACTIONS,
}


def register(protocol, actions=None, on_action=None):
    """Register the NOTIFICATION_CONTROL handler.

    actions: list of (code, icon_position, label) for notification actions.
    on_action: callback(protocol, notification_id, action_id) when user taps an action.
    """
    protocol._pending_notifications = {}
    protocol._notification_actions = actions or []
    protocol._notification_action_callback = on_action

    protocol.on(
        MessageType.NOTIFICATION_CONTROL,
        lambda msg_type, payload: _handle_control(protocol, msg_type, payload),
    )


def send(protocol, notification_id, title, body="", category=CATEGORY_OTHER):
    """Send a notification to the watch."""
    protocol._pending_notifications[notification_id] = {
        "title": title,
        "body": body,
    }

    log.debug("Sending notification id=%d title=%s", notification_id, title)
    message = _build_update(notification_id, category)
    asyncio.ensure_future(protocol._transport.send(message))


def _build_update(notification_id, category):
    """Build NOTIFICATION_UPDATE (5033) for ADD."""
    payload = struct.pack("<BBBBIB",
        ADD,
        FLAG_FOREGROUND | FLAG_ACTION_DECLINE,
        category,
        1,
        notification_id,
        PHONE_FLAG_NEW_ACTIONS,
    )
    return build(MessageType.NOTIFICATION_UPDATE, payload)


def _handle_control(protocol, _msg_type, payload):
    """Handle NOTIFICATION_CONTROL (5034)."""
    if len(payload) < 5:
        return

    command = payload[0]
    log.debug("NOTIFICATION_CONTROL command=%d payload=%s", command, payload.hex())

    if command == 0:
        _handle_get_attributes(protocol, payload)
    elif command == 1:
        _handle_get_app_attributes(protocol, payload)
    elif command == 128:
        _handle_action(protocol, payload)
    else:
        log.debug("Ignoring notification command %d", command)


def _handle_get_attributes(protocol, payload):
    """Respond to GET_NOTIFICATION_ATTRIBUTES with title/body."""
    notification_id = struct.unpack_from("<I", payload, 1)[0]
    log.info("Watch requesting notification %d details", notification_id)

    pending = getattr(protocol, "_pending_notifications", {})
    notification = pending.get(notification_id)

    if notification is None:
        log.warning("Unknown notification %d", notification_id)
        return

    requested_attrs = _parse_requested_attributes(payload[5:])
    actions = getattr(protocol, "_notification_actions", [])

    attributes = _build_attributes(notification, requested_attrs, actions)
    chunk = struct.pack("<BI", 0, notification_id) + attributes

    message = _build_data_message(chunk)
    asyncio.ensure_future(protocol._transport.send(message))


def _handle_get_app_attributes(protocol, payload):
    """Respond to GET_APP_ATTRIBUTES with app name."""
    app_id_end = payload.index(0x00, 1) if 0x00 in payload[1:] else len(payload)
    app_identifier = payload[1:app_id_end]
    log.info("Watch requesting app attributes for %s", app_identifier.decode("utf-8", errors="replace"))

    chunk = struct.pack("<B", 1)
    chunk += app_identifier + b"\x00"
    chunk += _tlv(0, b"garmin-bridge")

    message = _build_data_message(chunk)
    asyncio.ensure_future(protocol._transport.send(message))


def _handle_action(protocol, payload):
    """Handle PERFORM_NOTIFICATION_ACTION — dispatch to registered callback."""
    if len(payload) < 6:
        return

    notification_id = struct.unpack_from("<I", payload, 1)[0]
    action_id = payload[5]

    callback = getattr(protocol, "_notification_action_callback", None)
    if callback:
        callback(protocol, notification_id, action_id)
    else:
        log.info("Notification %d action: %d (no handler)", notification_id, action_id)


def _parse_requested_attributes(data):
    """Parse attribute requests from NOTIFICATION_CONTROL payload."""
    attrs = {}
    offset = 0
    while offset < len(data):
        attr_type = data[offset]
        offset += 1

        if attr_type in (ATTR_TITLE, ATTR_SUBTITLE, ATTR_MESSAGE):
            if offset + 1 < len(data) and data[offset] not in _KNOWN_ATTRS:
                attrs[attr_type] = struct.unpack_from("<H", data, offset)[0]
                offset += 2
            else:
                attrs[attr_type] = 0
        elif attr_type == ATTR_ACTIONS and offset < len(data):
            offset += 1
            attrs[attr_type] = 0
        else:
            attrs[attr_type] = 0

    return attrs


def _build_attributes(notification, requested_attrs, actions):
    """Build TLV-encoded notification attributes."""
    parts = []
    now = time.strftime("%Y%m%dT%H%M%S")

    for attr_type, max_length in requested_attrs.items():
        if attr_type == ATTR_APP_IDENTIFIER:
            parts.append(_tlv(ATTR_APP_IDENTIFIER, b"garmin-bridge"))

        elif attr_type == ATTR_TITLE:
            title = notification["title"].encode("utf-8")
            if max_length > 0:
                title = title[:max_length]
            parts.append(_tlv(ATTR_TITLE, title))

        elif attr_type == ATTR_SUBTITLE:
            parts.append(_tlv(ATTR_SUBTITLE, b""))

        elif attr_type == ATTR_MESSAGE:
            body = notification["body"].encode("utf-8")
            if max_length > 0:
                body = body[:max_length]
            parts.append(_tlv(ATTR_MESSAGE, body))

        elif attr_type == ATTR_MESSAGE_SIZE:
            body_length = len(notification["body"])
            parts.append(_tlv(ATTR_MESSAGE_SIZE, str(body_length).encode("ascii")))

        elif attr_type == ATTR_ACTIONS:
            parts.append(_tlv(ATTR_ACTIONS, _encode_actions(actions)))

        elif attr_type == ATTR_DATE:
            parts.append(_tlv(ATTR_DATE, now.encode("ascii")))

    return b"".join(parts)


def _encode_actions(actions):
    """Build the ACTIONS value: count(1) + encoded actions."""
    if not actions:
        return bytes([0])
    encoded = [_encode_action(code, icon, label) for code, icon, label in actions]
    return bytes([len(encoded)]) + b"".join(encoded)


def _encode_action(code, icon_position, label):
    """Encode a single action: code(1) + icon(1) + label_len(1) + label(N)."""
    label_bytes = label.encode("utf-8")
    return struct.pack("<BBB", code, icon_position, len(label_bytes)) + label_bytes


def _build_data_message(chunk_data):
    """Build NOTIFICATION_DATA (5035)."""
    checksum = crc16(chunk_data)
    payload = struct.pack("<HHH", len(chunk_data), checksum, 0)
    payload += chunk_data
    return build(MessageType.NOTIFICATION_DATA, payload)


def _tlv(attribute_type, value):
    """Encode a TLV attribute: type(1) + length(2 LE) + value(N)."""
    return struct.pack("<BH", attribute_type, len(value)) + value
