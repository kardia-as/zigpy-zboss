"""Test response."""
import asyncio

import async_timeout
import pytest

import zigpy_zboss.commands as c
import zigpy_zboss.types as t
from zigpy_zboss.utils import deduplicate_commands


@pytest.mark.asyncio
async def test_responses(connected_zboss):
    """Test responses."""
    zboss, zboss_server = connected_zboss

    assert not any(zboss._listeners.values())

    future = zboss.wait_for_response(
        c.NcpConfig.GetZigbeeRole.Rsp(
            TSN=10,
            StatusCat=t.StatusCategory(1),
            StatusCode=20,
            partial=True
        ))

    assert any(zboss._listeners.values())

    response = c.NcpConfig.GetZigbeeRole.Rsp(
        TSN=10,
        StatusCat=t.StatusCategory(1),
        StatusCode=20,
        DeviceRole=t.DeviceRole(1)
    )
    await zboss_server.send(response)

    assert (await future) == response

    # Our listener will have been cleaned up after a step
    await asyncio.sleep(0)
    assert not any(zboss._listeners.values())


@pytest.mark.asyncio
async def test_responses_multiple(connected_zboss):
    """Test multiple responses."""
    zboss, _ = connected_zboss

    assert not any(zboss._listeners.values())

    future1 = zboss.wait_for_response(c.NcpConfig.GetZigbeeRole.Rsp(
        TSN=10,
        StatusCat=t.StatusCategory(1),
        StatusCode=20,
        partial=True
    ))
    future2 = zboss.wait_for_response(c.NcpConfig.GetZigbeeRole.Rsp(
        TSN=10,
        StatusCat=t.StatusCategory(1),
        StatusCode=20,
        partial=True
    ))
    future3 = zboss.wait_for_response(c.NcpConfig.GetZigbeeRole.Rsp(
        TSN=10,
        StatusCat=t.StatusCategory(1),
        StatusCode=20,
        partial=True
    ))

    response = c.NcpConfig.GetZigbeeRole.Rsp(
        TSN=10,
        StatusCat=t.StatusCategory(1),
        StatusCode=20,
        DeviceRole=t.DeviceRole(1)
    )
    zboss.frame_received(response.to_frame())

    await future1
    await asyncio.sleep(0)
    await asyncio.sleep(0)
    await asyncio.sleep(0)

    assert not future2.done()
    assert not future3.done()

    assert any(zboss._listeners.values())


@pytest.mark.asyncio
async def test_response_timeouts(connected_zboss):
    """Test future response timeouts."""
    zboss, _ = connected_zboss

    response = c.NcpConfig.GetZigbeeRole.Rsp(
        TSN=10,
        StatusCat=t.StatusCategory(1),
        StatusCode=20,
        DeviceRole=t.DeviceRole(1)
    )

    async def send_soon(delay):
        await asyncio.sleep(delay)
        zboss.frame_received(response.to_frame())

    asyncio.create_task(send_soon(0.1))

    async with async_timeout.timeout(0.5):
        assert (await zboss.wait_for_response(c.NcpConfig.GetZigbeeRole.Rsp(
            TSN=10,
            StatusCat=t.StatusCategory(1),
            StatusCode=20,
            partial=True
        ))) == response

    # The response was successfully received so we
    # should have no outstanding listeners
    await asyncio.sleep(0)
    assert not any(zboss._listeners.values())

    asyncio.create_task(send_soon(0.6))

    with pytest.raises(asyncio.TimeoutError):
        async with async_timeout.timeout(0.5):
            assert (
                       await zboss.wait_for_response(
                           c.NcpConfig.GetZigbeeRole.Rsp(
                               TSN=10,
                               StatusCat=t.StatusCategory(1),
                               StatusCode=20,
                               partial=True
                           ))
                   ) == response

    # Our future still completed, albeit unsuccessfully.
    # We should have no leaked listeners here.
    assert not any(zboss._listeners.values())


@pytest.mark.asyncio
async def test_response_matching_partial(connected_zboss):
    """Test partial response matching."""
    zboss, _ = connected_zboss

    future = zboss.wait_for_response(
        c.NcpConfig.GetZigbeeRole.Rsp(
            TSN=10,
            StatusCat=t.StatusCategory(2),
            StatusCode=20,
            partial=True
        )
    )

    response1 = c.NcpConfig.GetZigbeeRole.Rsp(
        TSN=10,
        StatusCat=t.StatusCategory(1),
        StatusCode=20,
        DeviceRole=t.DeviceRole(1)
    )
    response2 = c.NcpConfig.GetZigbeeRole.Rsp(
        TSN=10,
        StatusCat=t.StatusCategory(2),
        StatusCode=20,
        DeviceRole=t.DeviceRole(1)
    )
    response3 = c.NcpConfig.GetZigbeeRole.Rsp(
        TSN=11,
        StatusCat=t.StatusCategory(2),
        StatusCode=20,
        DeviceRole=t.DeviceRole(1)
    )

    zboss.frame_received(response1.to_frame())
    zboss.frame_received(response2.to_frame())
    zboss.frame_received(response3.to_frame())

    assert future.done()
    assert (await future) == response2


@pytest.mark.asyncio
async def test_response_matching_exact(connected_zboss):
    """Test exact response matching."""
    zboss, _ = connected_zboss

    response1 = c.NcpConfig.GetZigbeeRole.Rsp(
        TSN=10,
        StatusCat=t.StatusCategory(1),
        StatusCode=20,
        DeviceRole=t.DeviceRole(1)
    )
    response2 = c.NcpConfig.GetZigbeeRole.Rsp(
        TSN=10,
        StatusCat=t.StatusCategory(1),
        StatusCode=20,
        DeviceRole=t.DeviceRole(2)
    )
    response3 = c.NcpConfig.GetZigbeeRole.Rsp(
        TSN=11,
        StatusCat=t.StatusCategory(1),
        StatusCode=20,
        DeviceRole=t.DeviceRole(1)
    )

    future = zboss.wait_for_response(response2)

    zboss.frame_received(response1.to_frame())
    zboss.frame_received(response2.to_frame())
    zboss.frame_received(response3.to_frame())

    # Future should be immediately resolved
    assert future.done()
    assert (await future) == response2


@pytest.mark.asyncio
async def test_response_not_matching_out_of_order(connected_zboss):
    """Test not matching response."""
    zboss, _ = connected_zboss

    response = c.NcpConfig.GetZigbeeRole.Rsp(
        TSN=10,
        StatusCat=t.StatusCategory(1),
        StatusCode=20,
        DeviceRole=t.DeviceRole(1)
    )
    zboss.frame_received(response.to_frame())

    future = zboss.wait_for_response(response)

    # This future will never resolve because we were not
    # expecting a response and discarded it
    assert not future.done()


@pytest.mark.asyncio
async def test_wait_responses_empty(connected_zboss):
    """Test wait empty response."""
    zboss, _ = connected_zboss

    # You shouldn't be able to wait for an empty list of responses
    with pytest.raises(ValueError):
        await zboss.wait_for_responses([])


@pytest.mark.asyncio
async def test_response_callback_simple(connected_zboss, event_loop, mocker):
    """Test simple response callback."""
    zboss, _ = connected_zboss

    sync_callback = mocker.Mock()

    good_response = c.NcpConfig.GetZigbeeRole.Rsp(
        TSN=10,
        StatusCat=t.StatusCategory(1),
        StatusCode=20,
        DeviceRole=t.DeviceRole(1)
    )
    bad_response = c.NcpConfig.GetZigbeeRole.Rsp(
        TSN=10,
        StatusCat=t.StatusCategory(1),
        StatusCode=0,
        DeviceRole=t.DeviceRole(1)
    )

    zboss.register_indication_listener(good_response, sync_callback)

    zboss.frame_received(bad_response.to_frame())
    assert sync_callback.call_count == 0

    zboss.frame_received(good_response.to_frame())
    sync_callback.assert_called_once_with(good_response)


@pytest.mark.asyncio
async def test_response_callbacks(connected_zboss, event_loop, mocker):
    """Test response callbacks."""
    zboss, _ = connected_zboss

    sync_callback = mocker.Mock()
    bad_sync_callback = mocker.Mock(
        side_effect=RuntimeError
    )  # Exceptions should not interfere with other callbacks

    async_callback_responses = []

    # XXX: I can't get AsyncMock().call_count to work, even though
    # the callback is definitely being called
    async def async_callback(response):
        await asyncio.sleep(0)
        async_callback_responses.append(response)

    good_response1 = c.NcpConfig.GetZigbeeRole.Rsp(
        TSN=10,
        StatusCat=t.StatusCategory(1),
        StatusCode=20,
        DeviceRole=t.DeviceRole(1)
    )
    good_response2 = c.NcpConfig.GetZigbeeRole.Rsp(
        TSN=10,
        StatusCat=t.StatusCategory(1),
        StatusCode=20,
        DeviceRole=t.DeviceRole(2)
    )
    good_response3 = c.NcpConfig.GetModuleVersion.Rsp(
        TSN=10,
        StatusCat=t.StatusCategory(1),
        StatusCode=20,
        FWVersion=1,
        StackVersion=2,
        ProtocolVersion=3
    )
    bad_response1 = c.ZDO.MgtLeave.Rsp(TSN=10,
                                       StatusCat=t.StatusCategory(1),
                                       StatusCode=20)
    bad_response2 = c.NcpConfig.GetModuleVersion.Req(TSN=1)

    responses = [
        # Duplicating matching responses shouldn't do anything
        c.NcpConfig.GetZigbeeRole.Rsp(
            TSN=10,
            StatusCat=t.StatusCategory(1),
            StatusCode=20,
            partial=True
        ),
        c.NcpConfig.GetZigbeeRole.Rsp(
            TSN=10,
            StatusCat=t.StatusCategory(1),
            StatusCode=20,
            partial=True
        ),
        # Matching against different response types should also work
        c.NcpConfig.GetModuleVersion.Rsp(
            TSN=10,
            StatusCat=t.StatusCategory(1),
            StatusCode=20,
            FWVersion=1,
            StackVersion=2,
            ProtocolVersion=3
        ),
        c.NcpConfig.GetZigbeeRole.Rsp(
            TSN=10,
            StatusCat=t.StatusCategory(1),
            StatusCode=20,
            DeviceRole=t.DeviceRole(1)
        ),
        c.NcpConfig.GetZigbeeRole.Rsp(
            TSN=10,
            StatusCat=t.StatusCategory(1),
            StatusCode=20,
            DeviceRole=t.DeviceRole(1)
        ),
        c.NcpConfig.GetModuleVersion.Rsp(
            TSN=10,
            StatusCat=t.StatusCategory(1),
            StatusCode=20,
            FWVersion=1,
            StackVersion=2,
            ProtocolVersion=4
        ),
    ]

    assert set(deduplicate_commands(responses)) == {
        c.NcpConfig.GetZigbeeRole.Rsp(
            TSN=10,
            StatusCat=t.StatusCategory(1),
            StatusCode=20,
            partial=True
        ),
        c.NcpConfig.GetModuleVersion.Rsp(
            TSN=10,
            StatusCat=t.StatusCategory(1),
            StatusCode=20,
            FWVersion=1,
            StackVersion=2,
            ProtocolVersion=3
        ),
        c.NcpConfig.GetModuleVersion.Rsp(
            TSN=10,
            StatusCat=t.StatusCategory(1),
            StatusCode=20,
            FWVersion=1,
            StackVersion=2,
            ProtocolVersion=4
        ),
    }

    # We shouldn't see any effects from receiving a frame early
    zboss.frame_received(good_response1.to_frame())

    for callback in [bad_sync_callback, async_callback, sync_callback]:
        zboss.register_indication_listeners(responses, callback)

    zboss.frame_received(good_response1.to_frame())
    zboss.frame_received(bad_response1.to_frame())
    zboss.frame_received(good_response2.to_frame())
    zboss.frame_received(bad_response2.to_frame())
    zboss.frame_received(good_response3.to_frame())

    await asyncio.sleep(0)

    assert sync_callback.call_count == 3
    assert bad_sync_callback.call_count == 3

    await asyncio.sleep(0.1)
    # assert async_callback.call_count == 3  # XXX: this always returns zero
    assert len(async_callback_responses) == 3


@pytest.mark.asyncio
async def test_wait_for_responses(connected_zboss, event_loop):
    """Test wait for responses."""
    zboss, _ = connected_zboss

    response1 = c.NcpConfig.GetZigbeeRole.Rsp(
        TSN=10,
        StatusCat=t.StatusCategory(1),
        StatusCode=20,
        DeviceRole=t.DeviceRole(1)
    )
    response2 = c.NcpConfig.GetZigbeeRole.Rsp(
        TSN=10,
        StatusCat=t.StatusCategory(1),
        StatusCode=20,
        DeviceRole=t.DeviceRole(2)
    )
    response3 = c.NcpConfig.GetModuleVersion.Rsp(
        TSN=10,
        StatusCat=t.StatusCategory(1),
        StatusCode=20,
        FWVersion=1,
        StackVersion=2,
        ProtocolVersion=3
    )
    response4 = c.ZDO.MgtLeave.Rsp(TSN=10,
                                   StatusCat=t.StatusCategory(1),
                                   StatusCode=20)
    response5 = c.NcpConfig.GetModuleVersion.Req(TSN=1)

    # We shouldn't see any effects from receiving a frame early
    zboss.frame_received(response1.to_frame())

    # Will match the first response1 and detach
    future1 = zboss.wait_for_responses(
        [c.NcpConfig.GetZigbeeRole.Rsp(
            TSN=10,
            StatusCat=t.StatusCategory(1),
            StatusCode=20,
            partial=True
        ), c.NcpConfig.GetZigbeeRole.Rsp(
            TSN=10,
            StatusCat=t.StatusCategory(1),
            StatusCode=20,
            partial=True
        )]
    )

    # Will match the first response3 and detach
    future2 = zboss.wait_for_responses(
        [
            c.NcpConfig.GetModuleVersion.Rsp(
                TSN=10,
                StatusCat=t.StatusCategory(1),
                StatusCode=20,
                FWVersion=1,
                StackVersion=2,
                ProtocolVersion=3
            ),
            c.NcpConfig.GetZigbeeRole.Rsp(
                TSN=10,
                StatusCat=t.StatusCategory(1),
                StatusCode=20,
                DeviceRole=t.DeviceRole(10)
            ),
        ]
    )

    # Will not match anything
    future3 = zboss.wait_for_responses([c.NcpConfig.GetModuleVersion.Rsp(
        TSN=10,
        StatusCat=t.StatusCategory(1),
        StatusCode=20,
        FWVersion=1,
        StackVersion=2,
        ProtocolVersion=4
    )])

    # Will match response1 the second time around
    future4 = zboss.wait_for_responses(
        [
            # Matching against different response types should also work
            c.NcpConfig.GetModuleVersion.Rsp(
                TSN=10,
                StatusCat=t.StatusCategory(1),
                StatusCode=20,
                FWVersion=1,
                StackVersion=2,
                ProtocolVersion=3
            ),
            c.NcpConfig.GetZigbeeRole.Rsp(
                TSN=10,
                StatusCat=t.StatusCategory(1),
                StatusCode=20,
                DeviceRole=t.DeviceRole(1)
            ),
            c.NcpConfig.GetZigbeeRole.Rsp(
                TSN=10,
                StatusCat=t.StatusCategory(1),
                StatusCode=20,
                DeviceRole=t.DeviceRole(1)
            ),
            c.NcpConfig.GetModuleVersion.Rsp(
                TSN=10,
                StatusCat=t.StatusCategory(1),
                StatusCode=20,
                FWVersion=1,
                StackVersion=2,
                ProtocolVersion=4
            ),
        ]
    )

    zboss.frame_received(response1.to_frame())
    zboss.frame_received(response2.to_frame())
    zboss.frame_received(response3.to_frame())
    zboss.frame_received(response4.to_frame())
    zboss.frame_received(response5.to_frame())

    assert future1.done()
    assert future2.done()
    assert not future3.done()
    assert not future4.done()

    await asyncio.sleep(0)

    zboss.frame_received(response1.to_frame())
    zboss.frame_received(response2.to_frame())
    zboss.frame_received(response3.to_frame())
    zboss.frame_received(response4.to_frame())
    zboss.frame_received(response5.to_frame())

    assert future1.done()
    assert future2.done()
    assert not future3.done()
    assert future4.done()

    assert (await future1) == response1
    assert (await future2) == response3
    assert (await future4) == response1

    await asyncio.sleep(0)

    zboss.frame_received(c.NcpConfig.GetModuleVersion.Rsp(
        TSN=10,
        StatusCat=t.StatusCategory(1),
        StatusCode=20,
        FWVersion=1,
        StackVersion=2,
        ProtocolVersion=4
    ).to_frame())
    assert future3.done()
    assert (await future3) == c.NcpConfig.GetModuleVersion.Rsp(
        TSN=10,
        StatusCat=t.StatusCategory(1),
        StatusCode=20,
        FWVersion=1,
        StackVersion=2,
        ProtocolVersion=4
    )
