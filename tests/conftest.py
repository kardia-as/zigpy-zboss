"""Shared fixtures and utilities for testing zigpy-zboss."""
import asyncio
import sys
import inspect
import pytest
import typing
import gc
import logging


from unittest.mock import Mock, PropertyMock, patch

import zigpy_zboss.config as conf
from zigpy_zboss.uart import ZbossNcpProtocol
import zigpy_zboss.types as t
from zigpy_zboss.api import ZBOSS

LOGGER = logging.getLogger(__name__)

FAKE_SERIAL_PORT = "/dev/ttyFAKE0"


# Globally handle async tests and error on unawaited coroutines
def pytest_collection_modifyitems(session, config, items):
    for item in items:
        item.add_marker(
            pytest.mark.filterwarnings(
                "error::pytest.PytestUnraisableExceptionWarning"
            )
        )
        item.add_marker(pytest.mark.filterwarnings("error::RuntimeWarning"))


@pytest.hookimpl(trylast=True)
def pytest_fixture_post_finalizer(fixturedef, request) -> None:
    """Called after fixture teardown"""
    if fixturedef.argname != "event_loop":
        return

    policy = asyncio.get_event_loop_policy()
    try:
        loop = policy.get_event_loop()
    except RuntimeError:
        loop = None
    if loop is not None:
        # Cleanup code based on the implementation of asyncio.run()
        try:
            if not loop.is_closed():
                asyncio.runners._cancel_all_tasks(loop)
                loop.run_until_complete(loop.shutdown_asyncgens())
                if sys.version_info >= (3, 9):
                    loop.run_until_complete(loop.shutdown_default_executor())
        finally:
            loop.close()
    new_loop = policy.new_event_loop()  # Replace existing event loop
    # Ensure subsequent calls to get_event_loop() succeed
    policy.set_event_loop(new_loop)


@pytest.fixture
def event_loop(
    request: pytest.FixtureRequest,
) -> typing.Iterator[asyncio.AbstractEventLoop]:
    """Create an instance of the default event loop for each test case."""
    yield asyncio.get_event_loop_policy().new_event_loop()
    # Call the garbage collector to trigger ResourceWarning's as soon
    # as possible (these are triggered in various __del__ methods).
    # Without this, resources opened in one test can fail other tests
    # when the warning is generated.
    gc.collect()
    # Event loop cleanup handled by pytest_fixture_post_finalizer


class ForwardingSerialTransport:
    """
    Serial transport that hooks directly into a protocol
    """

    def __init__(self, protocol):
        self.protocol = protocol
        self._is_connected = False
        self.other = None

        self.serial = Mock()
        self.serial.name = FAKE_SERIAL_PORT
        self.serial.baudrate = 45678
        type(self.serial).dtr = self._mock_dtr_prop = PropertyMock(
            return_value=None
        )
        type(self.serial).rts = self._mock_rts_prop = PropertyMock(
            return_value=None
        )

    def _connect(self):
        assert not self._is_connected
        self._is_connected = True
        self.other.protocol.connection_made(self)

    def write(self, data):
        assert self._is_connected
        self.protocol.data_received(data)

    def close(
            self, *, error=ValueError("Connection was closed")  # noqa: B008
    ):
        LOGGER.debug("Closing %s", self)

        if not self._is_connected:
            return

        self._is_connected = False

        # Our own protocol gets gracefully closed
        self.other.close(error=None)

        # The protocol we're forwarding to gets the error
        self.protocol.connection_lost(error)

    def __repr__(self):
        return f"<{type(self).__name__} to {self.protocol}>"


def config_for_port_path(path):
    return conf.CONFIG_SCHEMA(
        {
            conf.CONF_DEVICE: {conf.CONF_DEVICE_PATH: path},
            conf.CONF_DEVICE_BAUDRATE: 115200,
            conf.CONF_DEVICE_FLOW_CONTROL: None
        }
    )


@pytest.fixture
def make_zboss_server(mocker):
    transports = []

    def inner(server_cls, config=None, shorten_delays=True):
        if config is None:
            config = config_for_port_path(FAKE_SERIAL_PORT)

        if shorten_delays:
            mocker.patch(
                "zigpy_zboss.api.AFTER_BOOTLOADER_SKIP_BYTE_DELAY", 0.001
            )
            mocker.patch("zigpy_zboss.api.BOOTLOADER_PIN_TOGGLE_DELAY", 0.001)

        server = server_cls(config)
        server._transports = transports

        server.port_path = FAKE_SERIAL_PORT
        server._uart = None

        def passthrough_serial_conn(
                loop, protocol_factory, url, *args, **kwargs
        ):
            LOGGER.info("Intercepting serial connection to %s", url)

            assert url == FAKE_SERIAL_PORT

            # No double connections!
            if any([t._is_connected for t in transports]):
                raise RuntimeError(
                    "Cannot open two connections to the same serial port"
                )
            if server._uart is None:
                server._uart = ZbossNcpProtocol(
                    config[conf.CONF_DEVICE], server
                )
                mocker.spy(server._uart, "data_received")

            client_protocol = protocol_factory()

            # Client writes go to the server
            client_transport = ForwardingSerialTransport(server._uart)
            transports.append(client_transport)

            # Server writes go to the client
            server_transport = ForwardingSerialTransport(client_protocol)

            # Notify them of one another
            server_transport.other = client_transport
            client_transport.other = server_transport

            # And finally connect both simultaneously
            server_transport._connect()
            client_transport._connect()

            fut = loop.create_future()
            fut.set_result((client_transport, client_protocol))

            return fut

        mocker.patch(
            "serial_asyncio.create_serial_connection",
            new=passthrough_serial_conn
        )

        # So we don't have to import it every time
        server.serial_port = FAKE_SERIAL_PORT

        return server

    yield inner


@pytest.fixture
def make_connected_zboss(make_zboss_server, mocker):
    async def inner(server_cls):
        config = conf.CONFIG_SCHEMA(
            {
                conf.CONF_DEVICE: {conf.CONF_DEVICE_PATH: FAKE_SERIAL_PORT},
            }
        )

        zboss = ZBOSS(config)
        zboss_server = make_zboss_server(server_cls=server_cls)

        await zboss.connect()

        zboss.nvram.align_structs = server_cls.align_structs
        zboss.version = server_cls.version

        return zboss, zboss_server

    return inner


@pytest.fixture
def connected_zboss(event_loop, make_connected_zboss):
    zboss, zboss_server = event_loop.run_until_complete(
        make_connected_zboss(BaseServerZBOSS)
    )
    yield zboss, zboss_server
    zboss.close()


class BaseServerZBOSS(ZBOSS):
    align_structs = False
    version = None

    async def _flatten_responses(self, request, responses):
        if responses is None:
            return
        elif isinstance(responses, t.CommandBase):
            yield responses
        elif inspect.iscoroutinefunction(responses):
            async for rsp in responses(request):
                yield rsp
        elif inspect.isasyncgen(responses):
            async for rsp in responses:
                yield rsp
        elif callable(responses):
            async for rsp in self._flatten_responses(
                    request, responses(request)
            ):
                yield rsp
        else:
            for response in responses:
                async for rsp in self._flatten_responses(request, response):
                    yield rsp

    async def _send_responses(self, request, responses):
        async for response in self._flatten_responses(request, responses):
            await asyncio.sleep(0.001)
            LOGGER.debug(
                "Replying to %s with %s", request, response
            )
            await self.send(response)

    def reply_once_to(self, request, responses, *, override=False):
        if override:
            self._listeners[request.header].clear()

        request_future = self.wait_for_response(request)

        async def replier():
            request = await request_future
            await self._send_responses(request, responses)

            return request

        return asyncio.create_task(replier())

    def reply_to(self, request, responses, *, override=False):
        if override:
            self._listeners[request.header].clear()

        async def callback(request):
            callback.call_count += 1
            await self._send_responses(request, responses)

        callback.call_count = 0

        self.register_indication_listener(
            request, lambda r: asyncio.create_task(callback(r))
        )

        return callback

    async def send(self, response):
        if response is not None and self._uart is not None:
            await self._uart.send(response.to_frame(align=self.align_structs))

    def close(self):
        # We don't clear listeners on shutdown
        with patch.object(self, "_listeners", {}):
            return super().close()
