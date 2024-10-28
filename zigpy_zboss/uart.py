"""Module that connects and sends/receives bytes from the nRF52 SoC."""
import asyncio
import logging
import typing

import async_timeout
import zigpy.serial

import zigpy_zboss.config as conf
from zigpy_zboss import types as t
from zigpy_zboss.checksum import CRC8
from zigpy_zboss.exceptions import InvalidFrame
from zigpy_zboss.frames import Frame
from zigpy_zboss.logger import SERIAL_LOGGER

LOGGER = logging.getLogger(__name__)
ACK_TIMEOUT = 1
STARTUP_TIMEOUT = 5


class BufferTooShort(Exception):
    """Exception when the buffer is too short."""


class ZbossNcpProtocol(asyncio.Protocol):
    """Zboss Ncp Protocol class."""

    def __init__(self, api) -> None:
        """Initialize the ZbossNcpProtocol object."""
        super().__init__()
        self._api = api
        self._ack_seq = 0
        self._pack_seq = 0
        self._tx_lock = asyncio.Lock()
        self._ack_received_event = None

    def connection_lost(self, exc: typing.Optional[Exception]) -> None:
        """Lost connection."""
        super().connection_lost(exc)
        if self._api is not None:
            self._api.connection_lost(exc)

    def close(self) -> None:
        """Close serial connection."""
        super().close()
        self._api = None
        self._ack_seq = 0
        self._pack_seq = 0

    def write(self, data: bytes) -> None:
        """Write raw bytes to the transport.

        This method should be used instead
        of directly writing to the transport with `transport.write`.
        """
        if self._transport is not None:
            SERIAL_LOGGER.debug("TX: %s", t.Bytes.__repr__(data))
            self._transport.write(data)

    async def send(self, frame: Frame) -> None:
        """Send data, and wait for acknowledgement."""
        async with self._tx_lock:
            if isinstance(frame, Frame) and self._transport:
                self._ack_received_event = asyncio.Event()
                try:
                    async with async_timeout.timeout(ACK_TIMEOUT):
                        frame = self._set_frame_flag(frame)
                        frame = self._ll_checksum(frame)
                        self.write(frame.serialize())
                        await self._ack_received_event.wait()
                except asyncio.TimeoutError:
                    SERIAL_LOGGER.debug(
                        f'No ACK after {ACK_TIMEOUT}s for '
                        f'{t.Bytes.__repr__(frame.serialize())}'
                    )

    def _set_frame_flag(self, frame):
        """Return frame with required flags set."""
        flag = t.LLFlags(self._pack_seq << 2)
        flag |= frame.ll_header.flags
        frame.ll_header = frame.ll_header.with_flags(flag)
        return frame

    def _ll_checksum(self, frame):
        """Return frame with new crc8 checksum calculation."""
        crc = CRC8(frame.ll_header.serialize()[2:6]).digest()
        frame.ll_header = frame.ll_header.with_crc8(crc)
        return frame

    def data_received(self, data: bytes) -> None:
        """Notify when there is data received from serial connection."""
        self._buffer += data
        for frame in self._extract_frames():
            SERIAL_LOGGER.debug(f"RX: {t.Bytes.__repr__(frame.serialize())}")
            ll_header = frame.ll_header
            # Check if the frame is an ACK
            if ll_header.flags & t.LLFlags.isACK:
                ack_seq = (ll_header.flags & t.LLFlags.ACKSeq) >> 4
                if ack_seq == self._pack_seq:
                    # Calculate next sequence number
                    self._pack_seq = self._pack_seq % 3 + 1
                    self._ack_received_event.set()
                continue

            # Acknowledge the received frame
            self._ack_seq = (frame.ll_header.flags & t.LLFlags.PacketSeq) >> 2
            self.write(self._ack_frame().serialize())

            if frame.hl_packet is not None:
                try:
                    self._api.frame_received(frame)
                except Exception as e:
                    LOGGER.error(
                        "Received an exception while passing frame to API: %s",
                        frame,
                        exc_info=e,
                    )

    def _extract_frames(self) -> typing.Iterator[Frame]:
        """Extract frames from the buffer until it is exhausted."""
        while True:
            try:
                yield self._extract_frame()
            except BufferTooShort:
                # If the buffer is too short, there is nothing more we can do
                break
            except InvalidFrame:
                # If the buffer contains invalid data,
                # drop it until we find the signature
                signature_idx = self._buffer.find(
                    Frame.signature.serialize(), 1)

                if signature_idx < 0:
                    # If we don't have a signature in the buffer,
                    # drop everything
                    self._buffer.clear()
                else:
                    del self._buffer[:signature_idx]

    def _extract_frame(self) -> Frame:
        """Extract a single frame from the buffer."""
        # The shortest possible frame is 7 bytes long
        if len(self._buffer) < 7:
            raise BufferTooShort()

        # The buffer must start with a SoF
        if self._buffer[0:2] != Frame.signature.serialize():
            raise InvalidFrame()

        length, _ = t.uint16_t.deserialize(self._buffer[2:4])

        # Don't bother deserializing anything if the packet is too short
        if len(self._buffer) < length + 2:
            raise BufferTooShort()

        # Check that the packet type is ZBOSS NCP API HL.
        if self._buffer[4] != t.TYPE_ZBOSS_NCP_API_HL:
            raise InvalidFrame()

        # At this point we should have a complete frame
        # If not, deserialization will fail and the error will propapate up
        frame, rest = Frame.deserialize(self._buffer)

        # If we get this far then we have a valid frame. Update the buffer.
        del self._buffer[: len(self._buffer) - len(rest)]

        return frame

    def _ack_frame(self):
        """Return acknowledgement frame."""
        ack_frame = Frame.ack(self._ack_seq)
        return ack_frame


async def connect(config: conf.ConfigType, api) -> ZbossNcpProtocol:
    port = config[zigpy.config.CONF_DEVICE_PATH]

    _, protocol = await zigpy.serial.create_serial_connection(
        loop=asyncio.get_running_loop(),
        protocol_factory=lambda: ZbossNcpProtocol(api),
        url=port,
        baudrate=config[zigpy.config.CONF_DEVICE_BAUDRATE],
        flow_control=config[zigpy.config.CONF_DEVICE_FLOW_CONTROL],
    )

    await protocol.wait_until_connected()

    return protocol
