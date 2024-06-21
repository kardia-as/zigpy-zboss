"""Test api requests."""
import asyncio
import logging

import async_timeout
import pytest

import zigpy_zboss.commands as c
import zigpy_zboss.types as t
from zigpy_zboss.frames import (ZBNCP_LL_BODY_SIZE_MAX, Frame, HLPacket,
                                LLHeader)


@pytest.mark.asyncio
async def test_cleanup_timeout_internal(connected_zboss):
    """Test internal cleanup timeout."""
    zboss, zboss_server = connected_zboss

    assert not any(zboss._listeners.values())

    with pytest.raises(asyncio.TimeoutError):
        await zboss.request(c.NcpConfig.GetModuleVersion.Req(TSN=1), 0.1)

    # We should be cleaned up
    assert not any(zboss._listeners.values())


@pytest.mark.asyncio
async def test_cleanup_timeout_external(connected_zboss):
    """Test external cleanup timeout."""
    zboss, zboss_server = connected_zboss

    assert not any(zboss._listeners.values())

    # This request will timeout because we didn't send anything back
    with pytest.raises(asyncio.TimeoutError):
        async with async_timeout.timeout(0.1):
            await zboss.request(c.NcpConfig.GetModuleVersion.Req(TSN=1), 10)

    # We should be cleaned up
    assert not any(zboss._listeners.values())


@pytest.mark.asyncio
async def test_zboss_request_kwargs(connected_zboss, event_loop):
    """Test zboss request."""
    zboss, zboss_server = connected_zboss

    # Invalid format
    with pytest.raises(KeyError):
        await zboss.request(c.NcpConfig.GetModuleVersion.Req(TSNT=1), 10)

    # Valid format, invalid name
    with pytest.raises(KeyError):
        await zboss.request(c.NcpConfig.GetModuleVersion.Req(TsN=1), 10)

    # Valid format, valid name
    ping_rsp = c.NcpConfig.GetModuleVersion.Rsp(
            TSN=10,
            StatusCat=t.StatusCategory(1),
            StatusCode=20,
            FWVersion=1,
            StackVersion=2,
            ProtocolVersion=3
        )

    async def send_ping_response():
        await zboss_server.send(ping_rsp)

    event_loop.call_soon(asyncio.create_task, send_ping_response())

    assert (
        await zboss.request(c.NcpConfig.GetModuleVersion.Req(TSN=1), 2)
    ) == ping_rsp

    # You cannot send anything but requests
    with pytest.raises(ValueError):
        await zboss.request(c.NcpConfig.GetZigbeeRole.Rsp(
            TSN=10,
            StatusCat=t.StatusCategory(1),
            StatusCode=20,
            DeviceRole=t.DeviceRole(1)
        ))

    # You cannot send indications
    with pytest.raises(ValueError):
        await zboss.request(
            c.NWK.NwkLeaveInd.Ind(partial=True)
        )


@pytest.mark.asyncio
async def test_zboss_req_rsp(connected_zboss, event_loop):
    """Test zboss request/response."""
    zboss, zboss_server = connected_zboss

    # Each SREQ must have a corresponding SRSP, so this will fail
    with pytest.raises(asyncio.TimeoutError):
        async with async_timeout.timeout(0.5):
            await zboss.request(c.NcpConfig.GetModuleVersion.Req(TSN=1), 10)

    # This will work
    ping_rsp = c.NcpConfig.GetModuleVersion.Rsp(
        TSN=10,
        StatusCat=t.StatusCategory(1),
        StatusCode=20,
        FWVersion=1,
        StackVersion=2,
        ProtocolVersion=3
    )

    async def send_ping_response():
        await zboss_server.send(ping_rsp)

    event_loop.call_soon(asyncio.create_task, send_ping_response())

    await zboss.request(c.NcpConfig.GetModuleVersion.Req(TSN=1), 10)


@pytest.mark.asyncio
async def test_zboss_unknown_frame(connected_zboss, caplog):
    """Test zboss unknown frame."""
    zboss, _ = connected_zboss
    hl_header = t.HLCommonHeader(
        version=0x0121, type=0xFFFF, id=0x123421
    )
    hl_packet = HLPacket(header=hl_header, data=t.Bytes())
    ll_header = LLHeader(flags=0xC0, size=0x0A)
    frame = Frame(ll_header=ll_header, hl_packet=hl_packet)

    caplog.set_level(logging.DEBUG)
    zboss.frame_received(frame)

    # Unknown frames are logged in their entirety but an error is not thrown
    assert repr(frame) in caplog.text


@pytest.mark.asyncio
async def test_send_failure_when_disconnected(connected_zboss):
    """Test send failure when disconnected."""
    zboss, _ = connected_zboss
    zboss._uart = None

    with pytest.raises(RuntimeError) as e:
        await zboss.request(c.NcpConfig.GetModuleVersion.Req(TSN=1), 10)

    assert "Coordinator is disconnected" in str(e.value)
    zboss.close()


@pytest.mark.asyncio
async def test_frame_merge(connected_zboss, mocker):
    """Test frame fragmentation."""
    zboss, zboss_server = connected_zboss

    large_data = b"a" * (ZBNCP_LL_BODY_SIZE_MAX * 2 + 50)
    command = c.NcpConfig.ReadNVRAM.Rsp(
                TSN=10,
                StatusCat=t.StatusCategory(1),
                StatusCode=20,
                NVRAMVersion=t.uint16_t(0x0000),
                DatasetId=t.DatasetId(0x0000),
                Dataset=t.NVRAMDataset(large_data),
                DatasetVersion=t.uint16_t(0x0000)
            )
    frame = command.to_frame()

    callback = mocker.Mock()

    zboss.register_indication_listener(
        c.NcpConfig.ReadNVRAM.Rsp(
            TSN=10,
            StatusCat=t.StatusCategory(1),
            StatusCode=20,
            NVRAMVersion=t.uint16_t(0x0000),
            DatasetId=t.DatasetId(0x0000),
            Dataset=t.NVRAMDataset(large_data),
            DatasetVersion=t.uint16_t(0x0000)
        ), callback
    )

    # Perform fragmentation
    fragments = frame.handle_tx_fragmentation()
    assert len(fragments) > 1

    # Receiving first and middle fragments
    for fragment in fragments[:-1]:
        assert not zboss.frame_received(fragment)

    # receiving the last fragment
    assert zboss.frame_received(fragments[-1])

    # Check the state of _rx_fragments after merging
    assert zboss._rx_fragments == []
