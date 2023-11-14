"""Module that connects and sends/receives bytes from the nRF52 SoC."""
import typing
import asyncio
import logging
import zigpy.serial
import async_timeout
import serial  # type: ignore
import zigpy_zboss.config as conf
from zigpy_zboss import types as t
from zigpy_zboss.frames import Frame
from zigpy_zboss.checksum import CRC8
from zigpy_zboss.logger import SERIAL_LOGGER
from zigpy_zboss.exceptions import InvalidFrame

LOGGER = logging.getLogger(__name__)
ACK_TIMEOUT = 1
SEND_RETRIES = 2
STARTUP_TIMEOUT = 5
RECONNECT_TIMEOUT = 10


class BufferTooShort(Exception):
    """Exception when the buffer is too short."""


class ZbossNcpProtocol(asyncio.Protocol):
    """Zboss Ncp Protocol class."""

    def __init__(self, config, api) -> None:
        """Initialize the ZbossNcpProtocol object."""
        self._api = api
        self._ack_seq = 0
        self._pack_seq = 0
        self._config = config
        self._transport = None
        self._reset_flag = False
        self._buffer = bytearray()
        self._reconnect_task = None
        self._tx_lock = asyncio.Lock()
        self._ack_received_event = None
        self._connected_event = asyncio.Event()

        self._port = config[conf.CONF_DEVICE_PATH]
        self._baudrate = config[conf.CONF_DEVICE_BAUDRATE]
        self._flow_control = config[conf.CONF_DEVICE_FLOW_CONTROL]

    @property
    def api(self):
        """Return the owner of that object."""
        return self._api

    @property
    def name(self) -> str:
        """Return serial name."""
        return self._transport.serial.name

    @property
    def baudrate(self) -> int:
        """Return the baudrate."""
        return self._transport.serial.baudrate

    @property
    def reset_flag(self) -> bool:
        """Return True if a reset is in process."""
        return self._reset_flag

    @reset_flag.setter
    def reset_flag(self, value) -> None:
        if isinstance(value, bool):
            self._reset_flag = value

    def connection_made(
            self, transport: asyncio.BaseTransport) -> None:
        """Notify serial port opened."""
        self._transport = transport
        message = f"Opened {transport.serial.name} serial port"
        if self._reset_flag:
            self._reset_flag = False
            return
        SERIAL_LOGGER.info(message)
        self._connected_event.set()

    def connection_lost(self, exc: typing.Optional[Exception]) -> None:
        """Lost connection."""
        if self._api is not None:
            self._api.connection_lost(exc)
        self.close()

        # Do not try to reconnect if no exception occured.
        if exc is None:
            return

        if not self._reset_flag:
            SERIAL_LOGGER.warning(
                f"Unexpected connection lost... {exc}")
        self._reconnect_task = asyncio.create_task(self._reconnect())

    async def _reconnect(self, timeout=RECONNECT_TIMEOUT):
        """Try to reconnect the disconnected serial port."""
        SERIAL_LOGGER.info("Trying to reconnect to the NCP module!")
        assert self._api is not None
        loop = asyncio.get_running_loop()
        async with async_timeout.timeout(timeout):
            while True:
                try:
                    _, proto = await zigpy.serial.create_serial_connection(
                        loop=loop,
                        protocol_factory=lambda: self,
                        url=self._port,
                        baudrate=self._baudrate,
                        xonxoff=(self._flow_control == "software"),
                        rtscts=(self._flow_control == "hardware"),
                    )
                    self._api._uart = proto
                    break
                except serial.serialutil.SerialException:
                    await asyncio.sleep(0.1)

    def close(self) -> None:
        """Close serial connection."""
        self._buffer.clear()
        self._ack_seq = 0
        self._pack_seq = 0
        if self._reconnect_task is not None:
            self._reconnect_task.cancel()
            self._reconnect_task = None
        # Reset transport
        if self._transport:
            message = "Closing serial port"
            LOGGER.debug(message)
            SERIAL_LOGGER.info(message)
            self._transport.close()
            self._transport = None

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

    def __repr__(self) -> str:
        """Return a string representing the class."""
        return (
            f"<"
            f"{type(self).__name__} connected to {self.name!r}"
            f" at {self.baudrate} baud"
            f" (api: {self._api})"
            f">"
        )


async def connect(config: conf.ConfigType, api) -> ZbossNcpProtocol:
    """Instantiate Uart object and connect to it."""
    loop = asyncio.get_running_loop()

    port = config[conf.CONF_DEVICE_PATH]
    baudrate = config[conf.CONF_DEVICE_BAUDRATE]
    flow_control = config[conf.CONF_DEVICE_FLOW_CONTROL]

    LOGGER.debug("Connecting to %s at %s baud", port, baudrate)

    _, protocol = await zigpy.serial.create_serial_connection(
        loop=loop,
        protocol_factory=lambda: ZbossNcpProtocol(config, api),
        url=port,
        baudrate=baudrate,
        xonxoff=(flow_control == "software"),
        rtscts=(flow_control == "hardware"),
    )

    try:
        async with async_timeout.timeout(STARTUP_TIMEOUT):
            await protocol._connected_event.wait()
    except asyncio.TimeoutError:
        protocol.close()
        raise RuntimeError("Could not communicate with NCP!")

    LOGGER.debug("Connected to %s at %s baud", port, baudrate)

    return protocol
