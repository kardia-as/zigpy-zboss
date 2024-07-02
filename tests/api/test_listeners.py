"""Test listeners."""
import asyncio
from unittest.mock import call

import pytest

import zigpy_zboss.commands as c
import zigpy_zboss.types as t
from zigpy_zboss.api import IndicationListener, OneShotResponseListener


@pytest.mark.asyncio
async def test_resolve(event_loop, mocker):
    """Test listener resolution."""
    callback = mocker.Mock()
    callback_listener = IndicationListener(
        [c.NcpConfig.GetZigbeeRole.Rsp(
            TSN=10,
            StatusCat=t.StatusCategory(1),
            StatusCode=t.StatusCodeGeneric.OK,
            DeviceRole=t.DeviceRole(1)
        )], callback
    )

    future = event_loop.create_future()
    one_shot_listener = OneShotResponseListener([c.NcpConfig.GetZigbeeRole.Rsp(
            TSN=10,
            StatusCat=t.StatusCategory(1),
            StatusCode=t.StatusCodeGeneric.OK,
            DeviceRole=t.DeviceRole(1)
        )], future)

    match = c.NcpConfig.GetZigbeeRole.Rsp(
            TSN=10,
            StatusCat=t.StatusCategory(1),
            StatusCode=t.StatusCodeGeneric.OK,
            DeviceRole=t.DeviceRole(1)
        )
    no_match = c.NcpConfig.GetModuleVersion.Rsp(
                TSN=10,
                StatusCat=t.StatusCategory(1),
                StatusCode=t.StatusCodeGeneric.OK,
                FWVersion=1,
                StackVersion=2,
                ProtocolVersion=3,
            )

    assert callback_listener.resolve(match)
    assert not callback_listener.resolve(no_match)
    assert callback_listener.resolve(match)
    assert not callback_listener.resolve(no_match)

    assert one_shot_listener.resolve(match)
    assert not one_shot_listener.resolve(no_match)

    callback.assert_has_calls([call(match), call(match)])
    assert callback.call_count == 2

    assert (await future) == match

    # Cancelling a callback will have no effect
    assert not callback_listener.cancel()

    # Cancelling a one-shot listener does not throw any errors
    assert one_shot_listener.cancel()
    assert one_shot_listener.cancel()
    assert one_shot_listener.cancel()


@pytest.mark.asyncio
async def test_cancel(event_loop):
    """Test cancelling one-shot listener."""
    # Cancelling a one-shot listener prevents it from being fired
    future = event_loop.create_future()
    one_shot_listener = OneShotResponseListener([c.NcpConfig.GetZigbeeRole.Rsp(
            TSN=10,
            StatusCat=t.StatusCategory(1),
            StatusCode=t.StatusCodeGeneric.OK,
            partial=True
        )], future)
    one_shot_listener.cancel()

    match = c.NcpConfig.GetZigbeeRole.Rsp(
            TSN=10,
            StatusCat=t.StatusCategory(1),
            StatusCode=t.StatusCodeGeneric.OK,
            DeviceRole=t.DeviceRole(1)
        )
    assert not one_shot_listener.resolve(match)

    with pytest.raises(asyncio.CancelledError):
        await future


@pytest.mark.asyncio
async def test_multi_cancel(event_loop, mocker):
    """Test cancelling indication listener."""
    callback = mocker.Mock()
    callback_listener = IndicationListener(
        [c.NcpConfig.GetZigbeeRole.Rsp(
            TSN=10,
            StatusCat=t.StatusCategory(1),
            StatusCode=t.StatusCodeGeneric.OK,
            partial=True
        )], callback
    )

    future = event_loop.create_future()
    one_shot_listener = OneShotResponseListener([c.NcpConfig.GetZigbeeRole.Rsp(
            TSN=10,
            StatusCat=t.StatusCategory(1),
            StatusCode=t.StatusCodeGeneric.OK,
            partial=True
        )], future)

    match = c.NcpConfig.GetZigbeeRole.Rsp(
            TSN=10,
            StatusCat=t.StatusCategory(1),
            StatusCode=t.StatusCodeGeneric.OK,
            DeviceRole=t.DeviceRole(1)
        )
    no_match = c.NcpConfig.GetModuleVersion.Rsp(
                TSN=10,
                StatusCat=t.StatusCategory(1),
                StatusCode=t.StatusCodeGeneric.OK,
                FWVersion=1,
                StackVersion=2,
                ProtocolVersion=3,
            )

    assert callback_listener.resolve(match)
    assert not callback_listener.resolve(no_match)

    assert one_shot_listener.resolve(match)
    assert not one_shot_listener.resolve(no_match)

    callback.assert_called_once_with(match)
    assert (await future) == match


@pytest.mark.asyncio
async def test_api_cancel_listeners(connected_zboss, mocker):
    """Test cancel listeners from api."""
    zboss, zboss_server = connected_zboss

    callback = mocker.Mock()

    zboss.register_indication_listener(
        c.NcpConfig.GetZigbeeRole.Rsp(
            TSN=10,
            StatusCat=t.StatusCategory(1),
            StatusCode=t.StatusCodeGeneric.OK,
            DeviceRole=t.DeviceRole(1)
        ), callback
    )
    future = zboss.wait_for_responses(
        [
            c.NcpConfig.GetZigbeeRole.Rsp(
                TSN=10,
                StatusCat=t.StatusCategory(1),
                StatusCode=t.StatusCodeGeneric.OK,
                DeviceRole=t.DeviceRole(1)
            ),
            c.NcpConfig.GetModuleVersion.Rsp(
                TSN=10,
                StatusCat=t.StatusCategory(1),
                StatusCode=t.StatusCodeGeneric.OK,
                FWVersion=1,
                StackVersion=2,
                ProtocolVersion=3,
            ),
        ]
    )

    assert not future.done()
    zboss.close()

    with pytest.raises(asyncio.CancelledError):
        await future

    # add_done_callback won't be executed immediately
    await asyncio.sleep(0.1)

    # only one shot listerner is cleared
    # we do not remove indication listeners
    # because
    assert len(zboss._listeners) == 0
