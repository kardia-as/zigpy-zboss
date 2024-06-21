"""Test application connect."""
import asyncio
from unittest.mock import AsyncMock, patch

import pytest

import zigpy_zboss.commands as c
import zigpy_zboss.config as conf
import zigpy_zboss.types as t
from zigpy_zboss.uart import connect as uart_connect
from zigpy_zboss.zigbee.application import ControllerApplication

from ..conftest import BaseServerZBOSS, BaseZbossDevice


@pytest.mark.asyncio
async def test_no_double_connect(make_zboss_server, mocker):
    """Test no multiple connection."""
    zboss_server = make_zboss_server(server_cls=BaseServerZBOSS)

    app = mocker.Mock()
    await uart_connect(
        conf.SCHEMA_DEVICE(
            {conf.CONF_DEVICE_PATH: zboss_server.serial_port}
        ), app
    )

    with pytest.raises(RuntimeError):
        await uart_connect(
            conf.SCHEMA_DEVICE(
                {conf.CONF_DEVICE_PATH: zboss_server.serial_port}), app
        )


@pytest.mark.asyncio
async def test_leak_detection(make_zboss_server, mocker):
    """Test leak detection."""
    zboss_server = make_zboss_server(server_cls=BaseServerZBOSS)

    def count_connected():
        return sum(t._is_connected for t in zboss_server._transports)

    # Opening and closing one connection will keep the count at zero
    assert count_connected() == 0
    app = mocker.Mock()
    protocol1 = await uart_connect(
        conf.SCHEMA_DEVICE({conf.CONF_DEVICE_PATH: zboss_server.serial_port}),
        app
    )
    assert count_connected() == 1
    protocol1.close()
    assert count_connected() == 0

    # Once more for good measure
    protocol2 = await uart_connect(
        conf.SCHEMA_DEVICE({conf.CONF_DEVICE_PATH: zboss_server.serial_port}),
        app
    )
    assert count_connected() == 1
    protocol2.close()
    assert count_connected() == 0


@pytest.mark.asyncio
async def test_probe_unsuccessful_slow(make_zboss_server, mocker):
    """Test unsuccessful probe."""
    zboss_server = make_zboss_server(
        server_cls=BaseServerZBOSS, shorten_delays=False
    )

    # Don't respond to anything
    zboss_server._listeners.clear()

    mocker.patch("zigpy_zboss.zigbee.application.PROBE_TIMEOUT", new=0.1)

    assert not (
        await ControllerApplication.probe(
            conf.SCHEMA_DEVICE(
                {conf.CONF_DEVICE_PATH: zboss_server.serial_port}
            )
        )
    )

    assert not any([t._is_connected for t in zboss_server._transports])


@pytest.mark.asyncio
async def test_probe_successful(make_zboss_server, event_loop):
    """Test successful probe."""
    zboss_server = make_zboss_server(
        server_cls=BaseServerZBOSS, shorten_delays=False
    )

    # This will work
    ping_rsp = c.NcpConfig.GetZigbeeRole.Rsp(
        TSN=10,
        StatusCat=t.StatusCategory(1),
        StatusCode=20,
        DeviceRole=t.DeviceRole(1),
    )

    async def send_ping_response():
        await zboss_server.send(ping_rsp)

    event_loop.call_soon(asyncio.create_task, send_ping_response())

    assert await ControllerApplication.probe(
        conf.SCHEMA_DEVICE({conf.CONF_DEVICE_PATH: zboss_server.serial_port})
    )
    assert not any([t._is_connected for t in zboss_server._transports])


@pytest.mark.asyncio
async def test_probe_multiple(make_application):
    """Test multiple probe."""
    # Make sure that our listeners don't get cleaned up after each probe
    app, zboss_server = make_application(server_cls=BaseZbossDevice)

    app.close = lambda: None

    config = conf.SCHEMA_DEVICE(
        {conf.CONF_DEVICE_PATH: zboss_server.serial_port}
    )

    assert await app.probe(config)
    assert await app.probe(config)
    assert await app.probe(config)
    assert await app.probe(config)

    assert not any([t._is_connected for t in zboss_server._transports])


@pytest.mark.asyncio
async def test_shutdown_from_app(mocker, make_application, event_loop):
    """Test shutdown from application."""
    app, zboss_server = make_application(server_cls=BaseZbossDevice)

    await app.startup(auto_form=False)

    # It gets deleted but we save a reference to it
    transport = app._api._uart._transport
    mocker.spy(transport, "close")

    # Close the connection application-side
    await app.shutdown()

    # And the serial connection should have been closed
    assert transport.close.call_count >= 1


@pytest.mark.asyncio
async def test_clean_shutdown(make_application):
    """Test clean shutdown."""
    app, zboss_server = make_application(server_cls=BaseZbossDevice)
    await app.startup(auto_form=False)

    # This should not throw
    await app.shutdown()

    assert app._api is None


@pytest.mark.asyncio
async def test_multiple_shutdown(make_application):
    """Test multiple shutdown."""
    app, zboss_server = make_application(server_cls=BaseZbossDevice)
    await app.startup(auto_form=False)

    await app.shutdown()
    await app.shutdown()
    await app.shutdown()


@pytest.mark.asyncio
@patch(
    "zigpy_zboss.zigbee.application.ControllerApplication._watchdog_period",
    new=0.1
)
async def test_watchdog(make_application):
    """Test the watchdog."""
    app, zboss_server = make_application(server_cls=BaseZbossDevice)
    app._watchdog_feed = AsyncMock(wraps=app._watchdog_feed)

    await app.startup(auto_form=False)
    await asyncio.sleep(0.6)
    assert len(app._watchdog_feed.mock_calls) >= 5

    await app.shutdown()
