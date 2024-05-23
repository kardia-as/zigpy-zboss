import asyncio
import logging

import pytest
import async_timeout

import zigpy_zboss.types as t
import zigpy_zboss.config as conf
import zigpy_zboss.commands as c
from zigpy_zboss.frames import (
    Frame, InvalidFrame, CRC8,
    HLPacket, ZBNCP_LL_BODY_SIZE_MAX, LLHeader
)


@pytest.mark.asyncio
async def test_cleanup_timeout_internal(connected_zboss):
    zboss, zboss_server = connected_zboss

    assert not any(zboss._listeners.values())

    with pytest.raises(asyncio.TimeoutError):
        await zboss.request(c.NcpConfig.GetModuleVersion.Req(TSN=1), 0.1)

    # We should be cleaned up
    assert not any(zboss._listeners.values())

    zboss.close()


@pytest.mark.asyncio
async def test_cleanup_timeout_external(connected_zboss):
    zboss, zboss_server = connected_zboss

    assert not any(zboss._listeners.values())

    # This request will timeout because we didn't send anything back
    with pytest.raises(asyncio.TimeoutError):
        async with async_timeout.timeout(0.1):
            await zboss.request(c.NcpConfig.GetModuleVersion.Req(TSN=1), 10)

    # We should be cleaned up
    assert not any(zboss._listeners.values())

    zboss.close()
    await asyncio.sleep(0.1)


@pytest.mark.asyncio
async def test_zboss_request_kwargs(connected_zboss, event_loop):
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
    zboss.close()


@pytest.mark.asyncio
async def test_zboss_sreq_srsp(connected_zboss, event_loop):
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

    zboss.close()

# @pytest.mark.asyncio
# async def test_zboss_unknown_frame(connected_zboss, caplog):
#     zboss, _ = connected_zboss
#     hl_header = t.HLCommonHeader(
#         version=0x0121, type=0xFFFF, id=0x123421
#     )
#     hl_packet = HLPacket(header=hl_header, data=t.Bytes())
#     frame = Frame(ll_header=LLHeader(), hl_packet=hl_packet)
#
#     caplog.set_level(logging.ERROR)
#     zboss.frame_received(frame)
#
#     # Unknown frames are logged in their entirety but an error is not thrown
#     assert repr(frame) in caplog.text
#
#     zboss.close()


# async def test_handling_known_bad_command_parsing(connected_zboss, caplog):
#     zboss, _ = connected_zboss
#
#     bad_frame = GeneralFrame(
#         header=t.CommandHeader(
#             id=0x9F, subsystem=t.Subsystem.ZDO, type=t.CommandType.AREQ
#         ),
#         data=b"\x13\xDB\x84\x01\x21",
#     )
#
#     caplog.set_level(logging.WARNING)
#     zboss.frame_received(bad_frame)
#
#     # The frame is expected to fail to parse so will be
#     # logged as only a warning
#     assert len(caplog.records) == 1
#     assert caplog.records[0].levelname == "WARNING"
#     assert repr(bad_frame) in caplog.messages[0]
#
#
# async def test_handling_unknown_bad_command_parsing(connected_zboss):
#     zboss, _ = connected_zboss
#
#     bad_frame = GeneralFrame(
#         header=t.CommandHeader(
#             id=0xCB, subsystem=t.Subsystem.ZDO, type=t.CommandType.AREQ
#         ),
#         data=b"\x13\xDB\x84\x01\x21",
#     )
#
#     with pytest.raises(ValueError):
#         zboss.frame_received(bad_frame)
#
#

@pytest.mark.asyncio
async def test_send_failure_when_disconnected(connected_zboss):
    zboss, _ = connected_zboss
    zboss._uart = None

    with pytest.raises(RuntimeError) as e:
        await zboss.request(c.NcpConfig.GetModuleVersion.Req(TSN=1), 10)

    assert "Coordinator is disconnected" in str(e.value)
    zboss.close()
