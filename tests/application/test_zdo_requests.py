import asyncio

import pytest
import zigpy.zdo.types as zdo_t
import zigpy.types as z_types

import zigpy_zboss.types as t
import zigpy_zboss.commands as c

from ..conftest import (
    BaseZStackDevice
)


@pytest.mark.asyncio
async def test_mgmt_nwk_update_req(
        make_application, mocker
):
    mocker.patch(
        "zigpy.application.CHANNEL_CHANGE_SETTINGS_RELOAD_DELAY_S", 0.1
    )

    app, zboss_server = make_application(server_cls=BaseZStackDevice)

    new_channel = 11
    old_channel = 1

    async def update_channel(req):
        # Wait a bit before updating
        await asyncio.sleep(0.1)
        zboss_server.new_channel = new_channel

        yield

    zboss_server.reply_once_to(
        request=c.APS.DataReq.Req(
            TSN=123, ParamLength=21, DataLength=3,
            ProfileID=260, ClusterId=zdo_t.ZDOCmd.Mgmt_NWK_Update_req,
            DstEndpoint=0, partial=True),
        responses=[c.APS.DataReq.Rsp(
            TSN=123,
            StatusCat=t.StatusCategory(1),
            StatusCode=0,
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
                StatusCode=0,
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
