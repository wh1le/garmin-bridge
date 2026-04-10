"""Garmin GFDI protocol stack.

Single public API — consumers import from here, not from submodules.

    from src.protocol import Protocol, MessageType, Status, serializer
"""

import asyncio
import struct

from src.logger import log
from src.protocol import handshake, serializer
from src.protocol.message import MessageType, Status, build, build_response, parse
from src.protocol.transport import Transport

__all__ = [
    "Protocol",
    "MessageType",
    "Status",
    "serializer",
]


class Protocol:
    """High-level protocol interface over a BLE connection.

    Wraps Transport (V2 link management) and message framing.
    Consumers register handlers by message type, then call start().
    """

    def __init__(self, client):
        self._transport = Transport(client)
        self._handlers = {}

    async def start(self):
        self._register_handshake()
        self._transport.on_message(self._dispatch)
        await self._transport.init()

    def on(self, msg_type, handler):
        self._handlers[msg_type] = handler

    async def send(self, msg_type, payload=b""):
        await self._transport.send(build(msg_type, payload))

    async def respond(self, original_type, status=Status.ACK, payload=b""):
        await self._transport.send(build_response(original_type, status, payload))

    def _register_handshake(self):
        """Register built-in handlers for the connection handshake."""
        self._on_handshake(MessageType.DEVICE_INFORMATION, handshake.handle_device_information)
        self._on_handshake(MessageType.AUTH_NEGOTIATION, handshake.handle_auth_negotiation)
        self._on_handshake(MessageType.CURRENT_TIME_REQUEST, handshake.handle_current_time_request)
        self._on_handshake(MessageType.NOTIFICATION_SUBSCRIPTION, handshake.handle_notification_subscription)

        self._handlers[MessageType.CONFIGURATION] = self._handle_configuration
        self._handlers[MessageType.RESPONSE] = self._handle_response

    def _on_handshake(self, msg_type, handler_fn):
        """Register a handler that returns bytes to send."""
        def handle(_msg_type, payload):
            asyncio.ensure_future(self._transport.send(handler_fn(payload)))
        self._handlers[msg_type] = handle

    def _handle_configuration(self, _msg_type, payload):
        """Handle CONFIGURATION exchange + send device settings + sync ready."""
        messages = handshake.handle_configuration(payload)
        messages.append(handshake.build_device_settings())
        messages.append(handshake.build_system_event_sync_ready())
        for message in messages:
            asyncio.ensure_future(self._transport.send(message))

    def _handle_response(self, _msg_type, payload):
        """Log watch responses for debugging."""
        if len(payload) >= 3:
            original_type = struct.unpack_from("<H", payload, 0)[0]
            status = payload[2]
            original_name = _message_name(original_type)
            status_name = Status(status).name if status < len(Status) else str(status)
            log.debug("RESPONSE to %s: %s", original_name, status_name)

    def _dispatch(self, raw):
        result = parse(raw)
        if result is None:
            log.debug("Failed to parse message: %s", raw.hex())
            return

        msg_type, payload = result
        name = _message_name(msg_type)
        handler = self._handlers.get(msg_type)

        if handler:
            log.debug("Received %s (%d bytes)", name, len(payload))
            handler(msg_type, payload)
        else:
            log.debug("Unhandled %s (%d bytes): %s", name, len(payload), payload.hex())


def _message_name(msg_type):
    """Human-readable name for a message type."""
    try:
        return MessageType(msg_type).name
    except ValueError:
        return f"UNKNOWN({msg_type})"
