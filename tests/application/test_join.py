import asyncio

import pytest
import zigpy.device
import zigpy.types
import zigpy.util

import zigpy_zboss.commands as c
import zigpy_zboss.types as t

from ..conftest import BaseZStackDevice


@pytest.mark.asyncio
async def test_permit_join(mocker, make_application):
    app, zboss_server = make_application(server_cls=BaseZStackDevice)

    permit_join_coordinator = zboss_server.reply_once_to(
        request=c.ZDO.PermitJoin.Req(
            TSN=123,
            DestNWK=t.NWK(0x0000),
            PermitDuration=t.uint8_t(10),
            TCSignificance=t.uint8_t(0x01),
        ),
        responses=[
            c.ZDO.PermitJoin.Rsp(
                TSN=123,
                StatusCat=t.StatusCategory(1),
                StatusCode=20,
            ),
        ],
    )

    await app.startup(auto_form=False)
    await app.permit(time_s=10)

    await asyncio.sleep(0.1)

    assert permit_join_coordinator.done()

    await app.shutdown()


@pytest.mark.asyncio
async def test_join_coordinator(make_application):
    app, zboss_server = make_application(server_cls=BaseZStackDevice)

    # Handle us opening joins on the coordinator
    permit_join_coordinator = zboss_server.reply_once_to(
        request=c.ZDO.PermitJoin.Req(
            TSN=123,
            DestNWK=t.NWK(0x0000),
            PermitDuration=t.uint8_t(60),
            TCSignificance=t.uint8_t(0x01),
            partial=True
        ),
        responses=[
            c.ZDO.PermitJoin.Rsp(
                TSN=123,
                StatusCat=t.StatusCategory(1),
                StatusCode=20,
            ),
        ],
    )

    await app.startup(auto_form=False)
    await app.permit(node=app.state.node_info.ieee)

    await permit_join_coordinator

    await app.shutdown()


@pytest.mark.asyncio
async def test_join_device(make_application):
    ieee = t.EUI64.convert("EC:1B:BD:FF:FE:54:4F:40")
    nwk = 0x1234

    app, zboss_server = make_application(server_cls=BaseZStackDevice)
    app.add_initialized_device(ieee=ieee, nwk=nwk)

    permit_join = zboss_server.reply_once_to(
        request=c.ZDO.PermitJoin.Req(
            TSN=123,
            DestNWK=t.NWK(zigpy.types.t.BroadcastAddress.RX_ON_WHEN_IDLE),
            PermitDuration=t.uint8_t(60),
            TCSignificance=t.uint8_t(0),
        ),
        responses=[
            c.ZDO.PermitJoin.Rsp(
                TSN=123,
                StatusCat=t.StatusCategory(1),
                StatusCode=20,
            )
        ],
    )

    await app.startup(auto_form=False)
    await app.permit(node=ieee)

    await permit_join

    await app.shutdown()


@pytest.mark.asyncio
async def test_on_zdo_device_join(make_application, mocker):
    app, zboss_server = make_application(server_cls=BaseZStackDevice)
    await app.startup(auto_form=False)

    mocker.patch.object(app, "handle_join", wraps=app.handle_join)

    nwk = 0x1234
    ieee = t.EUI64.convert("11:22:33:44:55:66:77:88")

    await zboss_server.send(c.ZDO.DevAnnceInd.Ind(
        NWK=nwk,
        IEEE=ieee,
        MacCap=t.uint8_t(0x01)
    )
    )

    await asyncio.sleep(0.1)

    app.handle_join.assert_called_once_with(
        nwk=nwk, ieee=ieee, parent_nwk=None
    )

    await app.shutdown()
