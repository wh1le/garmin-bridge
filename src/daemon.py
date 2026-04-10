"""Daemon setup — register all handlers on the protocol.

Wires up weather, calendar, notifications, and todos.
"""

import asyncio

from src.protocol import Protocol, MessageType
from src.protocol import handshake
from src import weather, calendar, todos


async def setup(client):
    """Create protocol, start handshake, register all handlers."""
    protocol = Protocol(client)

    protocol.on(
        MessageType.WEATHER_REQUEST,
        lambda msg_type, payload: weather.handle_request(protocol, msg_type, payload),
    )

    def handle_protobuf(msg_type, payload):
        if not calendar.handle_request(protocol, msg_type, payload):
            asyncio.ensure_future(
                protocol._transport.send(handshake.handle_protobuf_request(payload))
            )

    protocol.on(MessageType.PROTOBUF_REQUEST, handle_protobuf)

    await protocol.start()

    todos.register(protocol)

    return protocol
