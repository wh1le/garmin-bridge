"""Garmin GFDI protocol stack.

Single public API — consumers import from here, not from submodules.

    from src.protocol import Protocol, MessageType, Status, fit
"""

from src.logger import log
from src.protocol import serializer
from src.protocol import handshake
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
    Consumers register handlers by message type, then call run().
    """

    def __init__(self, client):
        self._transport = Transport(client)
        self._handlers: dict[int, object] = {}

    async def start(self):
        self._register_handshake()
        self._transport.on_message(self._dispatch)
        await self._transport.init()

    def on(self, msg_type: int, handler):
        self._handlers[msg_type] = handler

    async def send(self, msg_type: int, payload: bytes = b""):
        await self._transport.send(build(msg_type, payload))

    async def send_raw(self, data: bytes):
        await self._transport.send(data)

    async def respond(self, original_type: int, status: int = Status.ACK, payload: bytes = b""):
        await self._transport.send(build_response(original_type, status, payload))

    def _register_handshake(self):
        """Register built-in handlers for the connection handshake."""
        import asyncio

        def make_handler(handler_fn):
            def handle(_msg_type, payload):
                asyncio.ensure_future(
                    self._transport.send(handler_fn(payload))
                )
            return handle

        def config_handler(_msg_type, payload):
            messages = handshake.handle_configuration(payload)
            # After config exchange, send device settings + sync ready
            messages.append(handshake.build_device_settings())
            messages.append(handshake.build_system_event_sync_ready())
            for message in messages:
                asyncio.ensure_future(self._transport.send(message))

        self._handlers[MessageType.DEVICE_INFORMATION] = make_handler(
            handshake.handle_device_information)
        self._handlers[MessageType.AUTH_NEGOTIATION] = make_handler(
            handshake.handle_auth_negotiation)
        self._handlers[MessageType.CURRENT_TIME_REQUEST] = make_handler(
            handshake.handle_current_time_request)
        self._handlers[MessageType.CONFIGURATION] = config_handler
        self._handlers[MessageType.RESPONSE] = lambda _mt, _p: None

    def _dispatch(self, raw: bytes):
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
