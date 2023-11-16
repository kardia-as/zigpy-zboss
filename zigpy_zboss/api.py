"""Module for ZBOSS api interface."""
from __future__ import annotations

import asyncio
import logging
import itertools
import contextlib
import zigpy.state
import async_timeout
import zigpy_zboss.types as t
import zigpy_zboss.config as conf

from zigpy_zboss import uart
from zigpy_zboss.frames import Frame
from zigpy_zboss import commands as c
from zigpy_zboss.nvram import NVRAMHelper
from collections import Counter, defaultdict
from zigpy_zboss.utils import IndicationListener
from zigpy_zboss.utils import BaseResponseListener
from zigpy_zboss.utils import OneShotResponseListener

LOGGER = logging.getLogger(__name__)

# All of these are in seconds
AFTER_BOOTLOADER_SKIP_BYTE_DELAY = 2.5
NETWORK_COMMISSIONING_TIMEOUT = 30
BOOTLOADER_PIN_TOGGLE_DELAY = 0.15
CONNECT_PING_TIMEOUT = 0.50
CONNECT_PROBE_TIMEOUT = 10

DEFAULT_TIMEOUT = 5


class ZBOSS:
    """Class linking zigpy with ZBOSS running on nRF SoC."""

    def __init__(self, config: conf.ConfigType):
        """Initialize ZBOSS class."""
        self._uart = None
        self._app = None
        self._config = config

        self._listeners = defaultdict(list)
        self._blocking_request_lock = asyncio.Lock()

        self.capabilities = None

        self.nvram = NVRAMHelper(self)
        self.network_info: zigpy.state.NetworkInformation = None
        self.node_info: zigpy.state.NodeInfo = None

        self._rx_fragments = []

        self._ncp_debug = None

    def set_application(self, app):
        """Set the application using the ZBOSS class."""
        assert self._app is None
        self._app = app

    @property
    def _port_path(self) -> str:
        return self._config[conf.CONF_DEVICE][conf.CONF_DEVICE_PATH]

    @property
    def _zboss_config(self) -> conf.ConfigType:
        return self._config[conf.CONF_ZBOSS_CONFIG]

    async def connect(self) -> None:
        """Connect to serial device.

        Connects to the device specified by the "device" section of the config
        dict.
        """
        # So we cannot connect twice
        assert self._uart is None

        try:
            self._uart = await uart.connect(
                self._config[conf.CONF_DEVICE], self)
        except (Exception, asyncio.CancelledError):
            LOGGER.debug(
                "Connection to %s failed, cleaning up", self._port_path)
            self.close()
            raise

        LOGGER.debug(
            "Connected to %s at %s baud", self._uart.name, self._uart.baudrate)

    def connection_made(self) -> None:
        """Notify that connection has been made.

        Called by the UART object when a connection has been made.
        """
        pass

    def connection_lost(self, exc) -> None:
        """Port has been closed.

        Called by the UART object to indicate that the port was closed.
        Propagates up to the `ControllerApplication` that owns this ZBOSS
        instance.
        """
        LOGGER.debug("We were disconnected from %s: %s", self._port_path, exc)

    def close(self) -> None:
        """Clean up resources, namely the listener queues.

        Calling this will reset ZBOSS to the same internal state as a fresh
        ZBOSS instance.
        """
        self._app = None
        self.version = None

        if self._uart is not None:
            self._uart.close()
            self._uart = None

    def frame_received(self, frame: Frame) -> bool:
        """Frame has been received.

        Called when a frame has been received.
        Returns whether or not the frame was handled by any listener.

        XXX: Can be called multiple times in a single event loop step!
        """
        if not frame.ll_header.flags & t.LLFlags.LastFrag:
            LOGGER.debug("Received fragment: %s", frame)
            self._rx_fragments.append(frame)
            return

        if self._rx_fragments:
            self._rx_fragments.append(frame)
            frame = Frame.handle_rx_fragmentation(self._rx_fragments)
            self._rx_fragments = []

        if frame.hl_packet.header not in c.COMMANDS_BY_ID:
            LOGGER.debug("Received an unknown frame: %s", frame)
            return

        command_cls = c.COMMANDS_BY_ID[frame.hl_packet.header]

        command = command_cls.from_frame(frame)

        LOGGER.debug("Received command: %s", command)
        matched = False
        one_shot_matched = False

        for listener in self._listeners[command.header]:
            if one_shot_matched and isinstance(
                    listener, OneShotResponseListener):
                continue

            if not listener.resolve(command):
                LOGGER.debug(f"{command} does not match {listener}")
                continue

            matched = True
            LOGGER.debug(f"{command} matches {listener}")

            if isinstance(listener, OneShotResponseListener):
                one_shot_matched = True

        if not matched:
            self._unhandled_command(command)

        return matched

    def _unhandled_command(self, command: t.CommandBase):
        """Command not handled by any listener."""
        LOGGER.debug(f"Command was not handled: {command}")

    async def request(
            self, request: t.CommandBase,
            timeout=DEFAULT_TIMEOUT, **response_params) -> t.CommandBase:
        """Send a REQ request and returns its RSP.

        Failing if any of the RSP's parameters don't match `response_params`.
        """
        if type(request) is not request.Req:
            raise ValueError(
                f"Cannot send a command that isn't a request: {request!r}")

        frame = request.to_frame()
        # If the frame is too long, it needs fragmentation.
        fragments = frame.handle_tx_fragmentation()

        response_future = self.wait_for_response(request.Rsp(partial=True))

        async with self._conditional_blocking_request_lock(request.blocking):
            return await self._send_frags(
                fragments, response_future, timeout=timeout)

    async def _send_frags(self, fragments, response_future, timeout):
        """Send frame fragments to the uart."""
        for frag in fragments:
            if frag.ll_header.flags.value & t.LLFlags.LastFrag.value:
                return await self._send_to_uart(frag, response_future, timeout)
            await self._send_to_uart(frag, None)

    async def _send_to_uart(
            self, frame, response_future, timeout=DEFAULT_TIMEOUT):
        """Send the frame and waits for the response."""
        if self._uart is None:
            return
        try:
            await self._uart.send(frame)
            if response_future:
                async with async_timeout.timeout(timeout):
                    return await response_future
        except asyncio.TimeoutError:
            LOGGER.debug(f"Timeout after {timeout}s: {frame}")
            raise

    @contextlib.asynccontextmanager
    async def _conditional_blocking_request_lock(self, blocking):
        """Use async lock if the request is a blocking request."""
        if blocking:
            async with self._blocking_request_lock:
                yield
        else:
            yield

    def wait_for_responses(
            self, responses, *, context=False) -> asyncio.Future:
        """Create a one-shot listener.

        Matches any *one* of the given responses.
        """
        listener = OneShotResponseListener(responses)

        LOGGER.debug("Creating one-shot listener %s", listener)

        for header in listener.matching_headers():
            self._listeners[header].append(listener)

        # Remove the listener when the future is done,
        # not only when it gets a result
        listener.future.add_done_callback(
            lambda _: self.remove_listener(listener))

        if context:
            return listener.future, listener
        else:
            return listener.future

    def wait_for_response(self, response: t.CommandBase) -> asyncio.Future:
        """Create a one-shot listener for a single response."""
        return self.wait_for_responses([response])

    def remove_listener(self, listener: BaseResponseListener) -> None:
        """
        Unbinds a listener from ZBOSS.

        Used by `wait_for_responses` to remove listeners for completed futures,
        regardless of their completion reason.
        """
        if not self._listeners:
            return

        LOGGER.debug("Removing listener %s", listener)

        for header in listener.matching_headers():
            try:
                self._listeners[header].remove(listener)
            except ValueError:
                pass

            if not self._listeners[header]:
                LOGGER.debug(
                    "Cleaning up empty listener list for header %s", header
                )
                del self._listeners[header]

        counts = Counter()

        for listener in itertools.chain.from_iterable(
                self._listeners.values()):
            counts[type(listener)] += 1

        LOGGER.debug(
            f"There are {counts[IndicationListener]} callbacks and"
            f" {counts[OneShotResponseListener]} one-shot listeners remaining"
        )

    def register_indication_listeners(
            self, responses, callback) -> IndicationListener:
        """Create an indication listener.

        Matches any of the provided responses.
        """
        listener = IndicationListener(responses, callback=callback)

        LOGGER.debug(f"Creating callback {listener}")

        for header in listener.matching_headers():
            self._listeners[header].append(listener)

        return listener

    def register_indication_listener(
        self, response: t.CommandBase, callback
    ) -> IndicationListener:
        """Create a callback listener for a single response."""
        return self.register_indication_listeners([response], callback)

    async def version(self):
        """Get NCP module version."""
        if self._app is not None:
            tsn = self._app.get_sequence()
        else:
            tsn = 0
        req = c.NcpConfig.GetModuleVersion.Req(TSN=tsn)
        res = await self.request(req)
        if res.StatusCode:
            return
        version = ['', '', '']
        for idx, ver in enumerate(
                [res.FWVersion, res.StackVersion, res.ProtocolVersion]):
            major = str((ver & 0xFF000000) >> 24)
            minor = str((ver & 0x00FF0000) >> 16)
            revision = str((ver & 0x0000FF00) >> 8)
            commit = str((ver & 0x000000FF))
            version[idx] = ".".join([major, minor, revision, commit])
        return tuple(version)

    async def reset(self, option=t.ResetOptions(0)):
        """Reset the NCP module (see ResetOptions)."""
        if self._app is not None:
            tsn = self._app.get_sequence()
        else:
            tsn = 0
        req = c.NcpConfig.NCPModuleReset.Req(TSN=tsn, Option=option)
        self._uart.reset_flag = True
        res = await self._send_to_uart(
            req.to_frame(),
            self.wait_for_response(
                c.NcpConfig.NCPModuleReset.Rsp(partial=True)
            ),
            timeout=10
        )
        if not res.TSN == 0xFF:
            raise ValueError("Should get TSN 0xFF")
