"""Module setting up a debugging serial connection with the NCP."""
import asyncio
import logging
import logging.handlers

import serialx

from zigpy_zboss import types as t

DEBUG_LOG_FILE_NAME = "ncp_debug.log"

DEBUG_LOGGER = logging.getLogger(__name__)

LOG_FORMAT = ("%(asctime)s [%(levelname)s]: %(message)s")
LOG_LEVEL = logging.DEBUG
default_log_file_path = "/tmp/" + DEBUG_LOG_FILE_NAME
RECONNECT_TIMEOUT = 10


DEBUG_LOGGER.setLevel(LOG_LEVEL)
debug_logger_file_handler = logging.handlers.RotatingFileHandler(
    default_log_file_path,
    maxBytes=1024 * 1024,
    backupCount=5
)
debug_logger_file_handler.setLevel(LOG_LEVEL)
debug_logger_file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
DEBUG_LOGGER.propagate = False
DEBUG_LOGGER.addHandler(debug_logger_file_handler)


class NcpDebugLogger(asyncio.Protocol):
    """Class responsible for a serial debug connection."""

    def __init__(self, api, dev_path):
        """Class initializer."""
        self._api = api
        self._transport = None
        self._dev_path = dev_path
        self._buffer = bytearray()
        self._connected_event = asyncio.Event()

    def connection_made(
            self, transport: serialx.SerialTransport) -> None:
        """Notify when serial port opened."""
        self._transport = transport
        serial = getattr(transport, "serial", None)
        serial_name = (
            getattr(serial, "name", None)
            or getattr(serial, "port", None)
            or getattr(serial, "portstr", None)
            or self._dev_path
        )
        message = f"Opened {serial_name} serial port"
        DEBUG_LOGGER.debug(message)
        self._connected_event.set()

    def connection_lost(self, exc) -> None:
        """Lost connection."""
        self.close()
        asyncio.create_task(self._reconnect())

    async def _reconnect(self, timeout=RECONNECT_TIMEOUT):
        """Try to reconnect the disconnected serial port."""
        loop = asyncio.get_running_loop()
        async with asyncio.timeout(timeout):
            while True:
                try:
                    _, proto = await serialx.create_serial_connection(
                        loop=loop,
                        protocol_factory=lambda: self,
                        url=self._dev_path,
                        baudrate=115_200,
                        parity=serialx.PARITY_NONE,
                        stopbits=serialx.STOPBITS_ONE,
                        xonxoff=False,
                        rtscts=False,
                    )
                    self._api._ncp_debug = proto
                    break
                except serialx.SerialException:
                    await asyncio.sleep(0.1)

    def close(self) -> None:
        """Close connection."""
        self._buffer.clear()
        if self._transport:
            DEBUG_LOGGER.debug("Closing serial port")
            self._transport.close()
            self._transport = None

    def data_received(self, data: bytes) -> None:
        """Notify when there is data received from serial connection."""
        self._buffer += data
        buff = self._buffer.split(b'\xde\xad')
        if len(buff) > 1:
            for line in buff[:-1]:
                try:
                    DEBUG_LOGGER.debug(t.Bytes.__repr__(b'\xde\xad' + line))
                except Exception:
                    DEBUG_LOGGER.error("--- | Could not decode line | ---")
            self._buffer = buff[-1]


async def connect_ncp_debug(api, dev_path) -> NcpDebugLogger:
    """Connect to serial device."""
    loop = asyncio.get_running_loop()

    DEBUG_LOGGER.info(f"Connecting to {dev_path} for NCP debugging")

    _, protocol = await serialx.create_serial_connection(
        loop=loop,
        protocol_factory=lambda: NcpDebugLogger(api, dev_path),
        url=dev_path,
        baudrate=115200,
        parity=serialx.PARITY_NONE,
        stopbits=serialx.STOPBITS_ONE,
        xonxoff=False,
        rtscts=False,
    )

    await protocol._connected_event.wait()

    return protocol
