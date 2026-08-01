"""Test application ZDO request."""
import asyncio
from unittest.mock import AsyncMock, Mock

import pytest
import zigpy.types as z_types
import zigpy.zdo.types as zdo_t
from zigpy.const import APS_REPLY_TIMEOUT_EXTENDED

import zigpy_zboss.commands as c
import zigpy_zboss.types as t

from ..conftest import BaseZbossDevice

REMOTE_IEEE = t.EUI64.convert("00:11:22:33:44:55:66:77")
REMOTE_NWK = 0x1234


@pytest.mark.asyncio
async def test_mgmt_nwk_update_req(make_application, mocker):
    """Test ZDO_MGMT_NWK_UPDATE_REQ request."""
    mocker.patch(
        "zigpy.application.CHANNEL_CHANGE_SETTINGS_RELOAD_DELAY_S", 0.1
    )

    app, zboss_server = make_application(server_cls=BaseZbossDevice)

    new_channel = 11
    old_channel = 1

    async def update_channel(req):
        # Wait a bit before updating
        await asyncio.sleep(0.1)
        zboss_server.new_channel = new_channel

        yield

    zboss_server.reply_once_to(
        request=c.APS.DataReq.Req(
            TSN=123,
            ParamLength=21,
            DataLength=3,
            ProfileID=260,
            ClusterId=zdo_t.ZDOCmd.Mgmt_NWK_Update_req,
            DstEndpoint=0,
            partial=True
        ),
        responses=[c.APS.DataReq.Rsp(
            TSN=123,
            StatusCat=t.StatusCategory(1),
            StatusCode=t.StatusCodeGeneric.OK,
            DstAddr=t.EUI64.convert("00:00:00:00:00:00:aa:bb"),
            DstEndpoint=1,
            SrcEndpoint=1,
            TxTime=1,
            DstAddrMode=z_types.AddrMode.Group,
        )],
    )
    nwk_update_req = zboss_server.reply_once_to(
        request=c.ZDO.MgmtNwkUpdate.Req(
            TSN=123,
            DstNWK=t.NWK(0x0000),
            ScanChannelMask=t.Channels.from_channel_list([new_channel]),
            ScanDuration=zdo_t.NwkUpdate.CHANNEL_CHANGE_REQ,
            ScanCount=0,
            MgrAddr=0x0000,
        ),
        responses=[
            c.ZDO.MgmtNwkUpdate.Rsp(
                TSN=123,
                StatusCat=t.StatusCategory(1),
                StatusCode=t.StatusCodeGeneric.OK,
                ScannedChannels=t.Channels.from_channel_list([new_channel]),
                TotalTransmissions=1,
                TransmissionFailures=0,
                EnergyValues=c.zdo.EnergyValues(t.LVList([1])),
            ),
            update_channel,
        ],
    )

    await app.startup(auto_form=False)

    assert app.state.network_info.channel == old_channel

    await app.move_network_to_channel(new_channel=new_channel)

    await nwk_update_req

    assert app.state.network_info.channel == new_channel

    await app.shutdown()


@pytest.mark.asyncio
async def test_ieee_addr_req_discovery(make_application):
    """A broadcast IEEE_addr_req is answered on behalf of the remote device."""
    app, zboss_server = make_application(server_cls=BaseZbossDevice)
    await app.startup(auto_form=False)

    zboss_server.reply_once_to(
        request=c.ZDO.IeeeAddrReq.Req(NWKtoMatch=REMOTE_NWK, partial=True),
        responses=[
            c.ZDO.IeeeAddrReq.Rsp(
                TSN=123,
                StatusCat=t.StatusCategory(1),
                StatusCode=t.StatusCodeGeneric.OK,
                RemoteDevIEEE=REMOTE_IEEE,
                RemoteDevNWK=t.NWK(REMOTE_NWK),
            )
        ],
    )

    app.packet_received = Mock(wraps=app.packet_received)

    await app._discover_unknown_device(t.NWK(REMOTE_NWK))

    (rsp,) = app.packet_received.call_args.args

    assert rsp.cluster_id == zdo_t.ZDOCmd.IEEE_addr_rsp
    assert rsp.src.address == REMOTE_NWK
    assert rsp.src_ep == 0
    assert rsp.dst_ep == 0

    _, args = app._device.zdo.deserialize(
        zdo_t.ZDOCmd.IEEE_addr_rsp, rsp.data.serialize()
    )
    status, ieee, nwk = args[:3]

    assert status == zdo_t.Status.SUCCESS
    assert ieee == REMOTE_IEEE
    assert nwk == REMOTE_NWK

    await app.shutdown()


@pytest.mark.asyncio
async def test_ieee_addr_req_failure(make_application):
    """A failed IEEE_addr_req is answered with dummy values."""
    app, zboss_server = make_application(server_cls=BaseZbossDevice)
    await app.startup(auto_form=False)

    zboss_server.reply_once_to(
        request=c.ZDO.IeeeAddrReq.Req(NWKtoMatch=REMOTE_NWK, partial=True),
        responses=[
            c.ZDO.IeeeAddrReq.Rsp(
                TSN=123,
                StatusCat=t.StatusCategory(1),
                StatusCode=t.StatusCodeGeneric.ERROR,
                RemoteDevIEEE=REMOTE_IEEE,
                RemoteDevNWK=t.NWK(REMOTE_NWK),
            )
        ],
    )

    app.packet_received = Mock(wraps=app.packet_received)

    await app._discover_unknown_device(t.NWK(REMOTE_NWK))

    (rsp,) = app.packet_received.call_args.args

    assert rsp.src.address == 0x0000

    _, args = app._device.zdo.deserialize(
        zdo_t.ZDOCmd.IEEE_addr_rsp, rsp.data.serialize()
    )
    status, ieee, nwk = args[:3]

    assert status != zdo_t.Status.SUCCESS
    assert ieee == t.EUI64([0xFF] * 8)
    assert nwk == 0xFFFF

    await app.shutdown()


@pytest.mark.asyncio
async def test_zdo_ncp_timeout_does_not_preempt_zigpy(make_application):
    """The NCP timeout must outlast the longest deadline zigpy will use.

    A ZDO command is only answered once the on-air transaction resolves, so
    capping it at the NCP default made zigpy's extended window unreachable
    and turned every request into three.
    """
    app, zboss_server = make_application(server_cls=BaseZbossDevice)
    await app.startup(auto_form=False)
    app.add_initialized_device(ieee=REMOTE_IEEE, nwk=REMOTE_NWK)

    app._api.request = AsyncMock(
        return_value=c.ZDO.MgtLeave.Rsp(
            TSN=1,
            StatusCat=t.StatusCategory(1),
            StatusCode=t.StatusCodeGeneric.OK,
        )
    )

    await app.send_packet(
        z_types.ZigbeePacket(
            src=z_types.AddrModeAddress(
                addr_mode=z_types.AddrMode.NWK, address=0x0000
            ),
            src_ep=0,
            dst=z_types.AddrModeAddress(
                addr_mode=z_types.AddrMode.NWK, address=REMOTE_NWK
            ),
            dst_ep=0,
            tsn=1,
            profile_id=0,
            cluster_id=zdo_t.ZDOCmd.Mgmt_Leave_req,
            data=z_types.SerializableBytes(
                b"\x01" + REMOTE_IEEE.serialize() + b"\x00"
            ),
        )
    )

    timeout = app._api.request.mock_calls[0].kwargs["timeout"]
    assert timeout >= APS_REPLY_TIMEOUT_EXTENDED

    await app.shutdown()
