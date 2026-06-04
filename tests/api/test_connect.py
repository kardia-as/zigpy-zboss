"""Test cases for zigpy-zboss API connect/close methods."""
import pytest

import zigpy_zboss.commands as c
import zigpy_zboss.types as t
from zigpy_zboss.api import ZBOSS

from ..conftest import BaseServerZBOSS, config_for_port_path


@pytest.mark.asyncio
async def test_connect(make_zboss_server):
    """Test that ZBOSS.connect() connects and probes the NCP."""
    zboss_server = make_zboss_server(server_cls=BaseServerZBOSS)

    # connect() probes the NCP with GetZigbeeRole until it answers.
    zboss_server.reply_to(
        request=c.NcpConfig.GetZigbeeRole.Req(partial=True),
        responses=lambda req: c.NcpConfig.GetZigbeeRole.Rsp(
            TSN=req.TSN,
            StatusCat=t.StatusCategory(1),
            StatusCode=t.StatusCodeGeneric.OK,
            DeviceRole=t.DeviceRole(1),
        ),
    )

    zboss = ZBOSS(config_for_port_path(zboss_server.port_path))

    await zboss.connect()

    assert zboss._uart is not None

    zboss.close()


@pytest.mark.asyncio
async def test_api_close(connected_zboss, mocker):
    """Test that ZBOSS.close() properly cleans up the object."""
    zboss, zboss_server = connected_zboss
    uart = zboss._uart
    mocker.spy(uart, "close")

    # add some dummy listeners, should be cleared on close
    zboss._listeners = {
        'listener1': [mocker.Mock()], 'listener2': [mocker.Mock()]
    }

    zboss.close()

    # Make sure our UART was actually closed
    assert zboss._uart is None
    assert zboss._app is None
    assert uart.close.call_count == 1

    # ZBOSS.close should not throw any errors if called multiple times
    zboss.close()
    zboss.close()

    def dict_minus(d, minus):
        return {k: v for k, v in d.items() if k not in minus}

    ignored_keys = [
        "_blocking_request_lock",
        "_reset_uart_reconnect",
        "_disconnected_event",
        "nvram",
        "version"
    ]

    # Closing ZBOSS should reset it completely to that of a fresh object
    # We have to ignore our mocked method and the lock
    zboss2 = ZBOSS(zboss._config)
    assert (
            zboss2._blocking_request_lock.locked()
            == zboss._blocking_request_lock.locked()
    )
    assert dict_minus(zboss.__dict__, ignored_keys) == dict_minus(
        zboss2.__dict__, ignored_keys
    )

    zboss2.close()
    zboss2.close()

    assert dict_minus(zboss.__dict__, ignored_keys) == dict_minus(
        zboss2.__dict__, ignored_keys
    )
