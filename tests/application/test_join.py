"""Test application device joining."""
import asyncio

import pytest
import zigpy.device
import zigpy.types
import zigpy.util

import zigpy_zboss.commands as c
import zigpy_zboss.types as t

from ..conftest import BaseZbossDevice


@pytest.mark.asyncio
async def test_permit_join(mocker, make_application):
    """Test permit join."""
    app, zboss_server = make_application(server_cls=BaseZbossDevice)

    permit_join_routers = zboss_server.reply_once_to(
        request=c.ZDO.PermitJoin.Req(
            TSN=123,
            DestNWK=t.NWK(
                zigpy.types.t.BroadcastAddress.ALL_ROUTERS_AND_COORDINATOR
            ),
            PermitDuration=t.uint8_t(10),
            TCSignificance=t.uint8_t(0),
        ),
        responses=[
            c.ZDO.PermitJoin.Rsp(
                TSN=123,
                StatusCat=t.StatusCategory(1),
                StatusCode=t.StatusCodeGeneric.OK,
            ),
        ],
    )

    permit_join_coordinator = zboss_server.reply_once_to(
        request=c.NWK.PermitJoin.Req(
            TSN=123,
            PermitDuration=t.uint8_t(10),
        ),
        responses=[
            c.NWK.PermitJoin.Rsp(
                TSN=123,
                StatusCat=t.StatusCategory(1),
                StatusCode=t.StatusCodeGeneric.OK,
            ),
        ],
    )

    await app.startup(auto_form=False)
    await app.permit(time_s=10)

    await asyncio.sleep(0.1)

    assert permit_join_routers.done()
    assert permit_join_coordinator.done()

    await app.shutdown()


@pytest.mark.asyncio
async def test_join_coordinator(make_application):
    """Test coordinator join."""
    app, zboss_server = make_application(server_cls=BaseZbossDevice)

    # Handle us opening joins on the coordinator
    permit_join_coordinator = zboss_server.reply_once_to(
        request=c.NWK.PermitJoin.Req(
            TSN=123,
            PermitDuration=t.uint8_t(60),
            partial=True
        ),
        responses=[
            c.NWK.PermitJoin.Rsp(
                TSN=123,
                StatusCat=t.StatusCategory(1),
                StatusCode=t.StatusCodeGeneric.OK,
            ),
        ],
    )

    await app.startup(auto_form=False)
    await app.permit(node=app.state.node_info.ieee)

    await permit_join_coordinator

    await app.shutdown()


@pytest.mark.asyncio
async def test_join_device(make_application):
    """Test device join."""
    ieee = t.EUI64.convert("EC:1B:BD:FF:FE:54:4F:40")
    # Not 0x1234: that is the coordinator's own NWK in the test server, and
    # `get_device()` resolves it to the coordinator instead of this device.
    nwk = 0xABCD

    app, zboss_server = make_application(server_cls=BaseZbossDevice)
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
                StatusCode=t.StatusCodeGeneric.OK,
            )
        ],
    )

    await app.startup(auto_form=False)
    await app.permit(node=ieee)

    await permit_join

    await app.shutdown()


@pytest.mark.asyncio
async def test_on_zdo_device_join(make_application, mocker):
    """Test ZDO device join indication listener."""
    app, zboss_server = make_application(server_cls=BaseZbossDevice)
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


@pytest.mark.asyncio
async def test_on_dev_update_unsecured_join_defers(make_application, mocker):
    """An unsecured join must not start the interview.

    The device has only associated at that point: it has no network key and
    cannot answer, so the interview has to wait until it is really on the
    network.
    """
    app, zboss_server = make_application(server_cls=BaseZbossDevice)
    await app.startup(auto_form=False)

    mocker.patch.object(app, "handle_join", wraps=app.handle_join)

    ieee = t.EUI64.convert("11:22:33:44:55:66:77:88")

    await zboss_server.send(
        c.ZDO.DevUpdateInd.Ind(
            IEEE=ieee,
            Nwk=0xABCD,
            Status=t.DeviceUpdateStatus.unsecured_join,
        )
    )

    await asyncio.sleep(0.1)

    app.handle_join.assert_not_called()
    assert ieee not in app.devices

    await app.shutdown()


@pytest.mark.asyncio
async def test_on_dev_authorized_joins(make_application, mocker):
    """Authorization has to be able to bring a device in on its own.

    `Device_annce` is a broadcast and can be lost, so it cannot be the only
    signal that starts the interview.
    """
    app, zboss_server = make_application(server_cls=BaseZbossDevice)
    await app.startup(auto_form=False)

    mocker.patch.object(app, "handle_join", wraps=app.handle_join)

    nwk = 0xABCD
    ieee = t.EUI64.convert("11:22:33:44:55:66:77:88")

    await zboss_server.send(
        c.ZDO.DevAuthorizedInd.Ind(
            IEEE=ieee,
            Nwk=nwk,
            AuthorizationType=t.uint8_t(1),
            AuthorizationStatus=t.uint8_t(0),
        )
    )

    await asyncio.sleep(0.1)

    app.handle_join.assert_called_once_with(nwk, ieee, 0x0000)

    await app.shutdown()


@pytest.mark.asyncio
async def test_announcement_then_authorization_interviews_once(
        make_application, mocker):
    """Both join signals normally fire; only one may start the interview.

    `schedule_initialize` cancels and restarts any interview already
    running, so the authorization must not step in once the announcement
    has been handled.
    """
    app, zboss_server = make_application(server_cls=BaseZbossDevice)
    await app.startup(auto_form=False)

    schedule_initialize = mocker.patch.object(
        zigpy.device.Device, "schedule_initialize", autospec=True
    )

    nwk = 0xABCD
    ieee = t.EUI64.convert("11:22:33:44:55:66:77:88")

    await zboss_server.send(
        c.ZDO.DevAnnceInd.Ind(NWK=nwk, IEEE=ieee, MacCap=t.uint8_t(0x8E))
    )
    await zboss_server.send(
        c.ZDO.DevAuthorizedInd.Ind(
            IEEE=ieee,
            Nwk=nwk,
            AuthorizationType=t.uint8_t(1),
            AuthorizationStatus=t.uint8_t(0),
        )
    )

    await asyncio.sleep(0.1)

    assert schedule_initialize.call_count == 1

    await app.shutdown()


@pytest.mark.asyncio
async def test_on_dev_authorized_updates_stale_address(
        make_application, mocker):
    """A lost announcement must not leave the device at its old address."""
    app, zboss_server = make_application(server_cls=BaseZbossDevice)
    await app.startup(auto_form=False)

    ieee = t.EUI64.convert("11:22:33:44:55:66:77:88")
    app.add_initialized_device(ieee=ieee, nwk=0x1111)

    mocker.patch.object(zigpy.device.Device, "schedule_initialize")

    await zboss_server.send(
        c.ZDO.DevAuthorizedInd.Ind(
            IEEE=ieee,
            Nwk=0xABCD,
            AuthorizationType=t.uint8_t(1),
            AuthorizationStatus=t.uint8_t(0),
        )
    )

    await asyncio.sleep(0.1)

    assert app.devices[ieee].nwk == 0xABCD

    await app.shutdown()


@pytest.mark.asyncio
async def test_duplicate_announcement_does_not_restart_interview(
        make_application, mocker):
    """Routers rebroadcast `Device_annce`, so it arrives more than once.

    Every repeat would otherwise cancel the running interview and start it
    again from scratch.
    """
    app, zboss_server = make_application(server_cls=BaseZbossDevice)
    await app.startup(auto_form=False)

    # Leaving this mocked keeps the device un-initialized, standing in for
    # an interview that is still running.
    schedule_initialize = mocker.patch.object(
        zigpy.device.Device, "schedule_initialize"
    )

    nwk = 0xABCD
    ieee = t.EUI64.convert("11:22:33:44:55:66:77:88")
    announcement = c.ZDO.DevAnnceInd.Ind(
        NWK=nwk, IEEE=ieee, MacCap=t.uint8_t(0x8E)
    )

    await zboss_server.send(announcement)
    await zboss_server.send(announcement)
    await zboss_server.send(announcement)

    await asyncio.sleep(0.1)

    assert schedule_initialize.call_count == 1

    await app.shutdown()


@pytest.mark.asyncio
async def test_announcement_at_new_address_restarts_interview(
        make_application, mocker):
    """A device that moved has to be re-interviewed at its new address."""
    app, zboss_server = make_application(server_cls=BaseZbossDevice)
    await app.startup(auto_form=False)

    schedule_initialize = mocker.patch.object(
        zigpy.device.Device, "schedule_initialize"
    )

    ieee = t.EUI64.convert("11:22:33:44:55:66:77:88")

    await zboss_server.send(
        c.ZDO.DevAnnceInd.Ind(NWK=0xABCD, IEEE=ieee, MacCap=t.uint8_t(0x8E))
    )
    await zboss_server.send(
        c.ZDO.DevAnnceInd.Ind(NWK=0xBEEF, IEEE=ieee, MacCap=t.uint8_t(0x8E))
    )

    await asyncio.sleep(0.1)

    assert schedule_initialize.call_count == 2
    assert app.devices[ieee].nwk == 0xBEEF

    await app.shutdown()


@pytest.mark.asyncio
async def test_announcement_for_initialized_device_is_handled(
        make_application, mocker):
    """An initialized device rejoining still has to reach zigpy."""
    app, zboss_server = make_application(server_cls=BaseZbossDevice)
    await app.startup(auto_form=False)

    nwk = 0xABCD
    ieee = t.EUI64.convert("11:22:33:44:55:66:77:88")
    app.add_initialized_device(ieee=ieee, nwk=nwk)

    mocker.patch.object(app, "handle_join", wraps=app.handle_join)

    await zboss_server.send(
        c.ZDO.DevAnnceInd.Ind(NWK=nwk, IEEE=ieee, MacCap=t.uint8_t(0x8E))
    )

    await asyncio.sleep(0.1)

    app.handle_join.assert_called_once_with(
        nwk=nwk, ieee=ieee, parent_nwk=None
    )

    await app.shutdown()
