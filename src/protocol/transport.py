"""V2 multi-link communicator for Garmin GFDI over BLE.

Handles service registration on handle 0, COBS encoding,
and message routing.

Ported from Gadgetbridge CommunicatorV2.java.
"""

import asyncio
import struct
from enum import IntEnum

from src.logger import log
from src.protocol import encoding

BASE_UUID = "6A4E%04X-667B-11E3-949A-0800200C9A66"

CLIENT_ID = 2


class Service(IntEnum):
    GFDI = 0x0001


class _RequestType(IntEnum):
    REGISTER_ML_REQ = 0
    REGISTER_ML_RESP = 1
    CLOSE_HANDLE_REQ = 2
    CLOSE_HANDLE_RESP = 3
    UNK_HANDLE = 4
    CLOSE_ALL_REQ = 5
    CLOSE_ALL_RESP = 6


class Transport:
    def __init__(self, client):
        self.client = client
        self.gfdi_handle = None
        self._char_send = None
        self._char_recv = None
        self._message_callback = None
        self._cobs_buffer = bytearray()
        self._handle_event = asyncio.Event()
        self._max_write_size = 20  # conservative default, updated after connect
        self._send_lock = asyncio.Lock()

    async def init(self):
        services = self.client.services

        # Find a working send/receive characteristic pair
        for i in range(0x2810, 0x2815):
            recv_uuid = BASE_UUID % i
            send_uuid = BASE_UUID % (i + 0x10)

            recv_char = None
            send_char = None
            for service in services:
                for char in service.characteristics:
                    if char.uuid.upper().startswith(recv_uuid[:8].upper()):
                        recv_char = char
                    if char.uuid.upper().startswith(send_uuid[:8].upper()):
                        send_char = char

            if recv_char and send_char:
                self._char_recv = recv_char
                self._char_send = send_char
                log.info(
                    "Using characteristics recv=%s send=%s",
                    recv_char.uuid,
                    send_char.uuid,
                )
                break

        if not self._char_send or not self._char_recv:
            raise RuntimeError("No V2 multi-link characteristics found")

        try:
            await self.client._acquire_mtu()
        except Exception:
            pass

        mtu = getattr(self.client, "mtu_size", 23)
        self._max_write_size = max(mtu - 3, 20)
        log.info("MTU=%d, max write=%d", mtu, self._max_write_size)

        await self.client.start_notify(self._char_recv, self._on_notify)
        await self._close_all_services()
        # Close triggers CLOSE_ALL_RESP → GFDI registration → handle assigned
        await asyncio.wait_for(self._handle_event.wait(), timeout=10.0)
        log.info("GFDI registered on handle %d", self.gfdi_handle)

    def on_message(self, callback):
        self._message_callback = callback

    async def send(self, data: bytes):
        if self.gfdi_handle is None:
            log.error("Cannot send — GFDI handle not registered")
            return

        try:
            async with self._send_lock:
                await self._write(data)
        except Exception as error:
            log.debug("Send failed (disconnected?): %s", error)

    async def _write(self, data: bytes):
        encoded = encoding.encode(data)
        # Each chunk: 1 byte handle + up to (max_write_size - 1) bytes of data
        data_per_chunk = self._max_write_size - 1

        if len(encoded) <= data_per_chunk:
            packet = bytes([self.gfdi_handle]) + encoded
            await self.client.write_gatt_char(self._char_send, packet, response=False)
        else:
            position = 0
            while position < len(encoded):
                end = min(position + data_per_chunk, len(encoded))
                packet = bytes([self.gfdi_handle]) + encoded[position:end]
                await self.client.write_gatt_char(self._char_send, packet, response=False)
                position = end

    def stop(self):
        self._message_callback = None

    def _on_notify(self, _char, data):
        if len(data) < 1 or self._message_callback is None:
            return

        handle = data[0] & 0xFF

        if handle == 0:
            self._process_handle_management(bytes(data[1:]))
            return

        if self.gfdi_handle is not None and handle == self.gfdi_handle:
            self._cobs_buffer.extend(data[1:])
            self._try_decode_cobs()

    def _try_decode_cobs(self):
        # Look for frame delimiter (0x00) — must have leading 0x00 too
        while 0x00 in self._cobs_buffer[1:]:
            # Find the trailing 0x00 (skip leading 0x00)
            end = self._cobs_buffer.index(0x00, 1) + 1
            frame = bytes(self._cobs_buffer[:end])
            self._cobs_buffer = self._cobs_buffer[end:]

            decoded = encoding.decode(frame)
            if decoded and self._message_callback:
                self._message_callback(decoded)

    def _process_handle_management(self, data: bytes):
        if len(data) < 10:
            return

        msg_type = data[0]
        client_id = struct.unpack_from("<Q", data, 1)[0]

        if client_id != CLIENT_ID:
            return

        if msg_type == _RequestType.REGISTER_ML_RESP:
            if len(data) < 13:
                return
            service_code = struct.unpack_from("<H", data, 9)[0]
            status = data[11]
            handle = data[12]

            if status != 0:
                log.error("Service registration failed: service=0x%04x status=%d", service_code, status)
                return

            if service_code == Service.GFDI:
                self.gfdi_handle = handle
                self._handle_event.set()
                log.info("GFDI service registered on handle %d", handle)

        elif msg_type == _RequestType.CLOSE_ALL_RESP:
            log.info("All services closed, registering GFDI")
            self.gfdi_handle = None
            self._handle_event.clear()
            asyncio.ensure_future(self._register_gfdi())

        elif msg_type == _RequestType.CLOSE_HANDLE_RESP:
            log.info("Service handle closed")

    async def _close_all_services(self):
        buf = struct.pack("<bBqH", 0, _RequestType.CLOSE_ALL_REQ, CLIENT_ID, 0)
        await self.client.write_gatt_char(self._char_send, buf, response=False)

    async def _register_gfdi(self):
        buf = struct.pack(
            "<bBqHB",
            0,
            _RequestType.REGISTER_ML_REQ,
            CLIENT_ID,
            Service.GFDI,
            0,  # not reliable
        )
        await self.client.write_gatt_char(self._char_send, buf, response=False)
