"""Test application startup."""
from unittest.mock import AsyncMock as CoroutineMock

import pytest
from zigpy.exceptions import NetworkNotFormed

import zigpy_zboss.commands as c
import zigpy_zboss.types as t
from zigpy_zboss.api import ZBOSS

from ..conftest import BaseZbossDevice, BaseZbossGenericDevice


@pytest.mark.asyncio
async def test_info(make_application, caplog):
    """Test network information."""
    app, zboss_server = make_application(
        server_cls=BaseZbossGenericDevice, active_sequence=True
    )

    pan_id = 0x5679
    ext_pan_id = t.EUI64.convert("00:11:22:33:44:55:66:77")
    channel = 11
    channel_mask = 0x07fff800
    parent_address = t.NWK(0x5679)
    coordinator_version = 1
    # Simulate responses for each request in load_network_info
    zboss_server.reply_once_to(
        request=c.NcpConfig.GetZigbeeRole.Req(TSN=1),
        responses=[c.NcpConfig.GetZigbeeRole.Rsp(
            TSN=1,
            StatusCat=t.StatusCategory(4),
            StatusCode=t.StatusCodeGeneric.OK,
            DeviceRole=t.DeviceRole(1))]
    )

    zboss_server.reply_once_to(
        request=c.NcpConfig.GetZigbeeRole.Req(TSN=1),
        responses=[c.NcpConfig.GetZigbeeRole.Rsp(
            TSN=1,
            StatusCat=t.StatusCategory(4),
            StatusCode=t.StatusCodeGeneric.OK,
            DeviceRole=t.DeviceRole(1))]
    )

    zboss_server.reply_once_to(
        request=c.NcpConfig.GetJoinStatus.Req(TSN=2),
        responses=[c.NcpConfig.GetJoinStatus.Rsp(
            TSN=2,
            StatusCat=t.StatusCategory(4),
            StatusCode=t.StatusCodeGeneric.OK,
            Joined=1)]
    )

    zboss_server.reply_once_to(
        request=c.NcpConfig.GetShortAddr.Req(TSN=3),
        responses=[c.NcpConfig.GetShortAddr.Rsp(
            TSN=3,
            StatusCat=t.StatusCategory(4),
            StatusCode=t.StatusCodeGeneric.OK,
            NWKAddr=t.NWK(0xAABB))]
    )

    zboss_server.reply_once_to(
        request=c.NcpConfig.GetLocalIEEE.Req(TSN=4, MacInterfaceNum=0),
        responses=[c.NcpConfig.GetLocalIEEE.Rsp(
            TSN=4,
            StatusCat=t.StatusCategory(4),
            StatusCode=t.StatusCodeGeneric.OK,
            MacInterfaceNum=0,
            IEEE=t.EUI64(range(8)))]
    )

    zboss_server.reply_once_to(
        request=c.NcpConfig.GetZigbeeRole.Req(TSN=5),
        responses=[c.NcpConfig.GetZigbeeRole.Rsp(
            TSN=5,
            StatusCat=t.StatusCategory(4),
            StatusCode=t.StatusCodeGeneric.OK,
            DeviceRole=t.DeviceRole(2))]
    )

    zboss_server.reply_once_to(
        request=c.NcpConfig.GetExtendedPANID.Req(TSN=6),
        responses=[c.NcpConfig.GetExtendedPANID.Rsp(
            TSN=6,
            StatusCat=t.StatusCategory(4),
            StatusCode=t.StatusCodeGeneric.OK,
            ExtendedPANID=ext_pan_id)]
    )

    zboss_server.reply_once_to(
        request=c.NcpConfig.GetShortPANID.Req(TSN=7),
        responses=[c.NcpConfig.GetShortPANID.Rsp(
            TSN=7,
            StatusCat=t.StatusCategory(4),
            StatusCode=t.StatusCodeGeneric.OK,
            PANID=t.PanId(pan_id))]
    )

    zboss_server.reply_once_to(
        request=c.NcpConfig.GetCurrentChannel.Req(TSN=8),
        responses=[c.NcpConfig.GetCurrentChannel.Rsp(
            TSN=8,
            StatusCat=t.StatusCategory(4),
            StatusCode=t.StatusCodeGeneric.OK,
            Channel=channel, Page=0)]
    )

    zboss_server.reply_once_to(
        request=c.NcpConfig.GetChannelMask.Req(TSN=9),
        responses=[c.NcpConfig.GetChannelMask.Rsp(
            TSN=9,
            StatusCat=t.StatusCategory(4),
            StatusCode=t.StatusCodeGeneric.OK,
            ChannelList=[t.ChannelEntry(page=1, channel_mask=channel_mask)])]
    )

    zboss_server.reply_once_to(
        request=c.NcpConfig.GetTrustCenterAddr.Req(
            TSN=12
        ),
        responses=[c.NcpConfig.GetTrustCenterAddr.Rsp(
            TSN=12,
            StatusCat=t.StatusCategory(1),
            StatusCode=t.StatusCodeGeneric.OK,
            TCIEEE=t.EUI64.convert("00:11:22:33:44:55:66:77")
            # Example Trust Center IEEE address
        )]
    )

    zboss_server.reply_once_to(
        request=c.NcpConfig.GetRxOnWhenIdle.Req(TSN=13),
        responses=[c.NcpConfig.GetRxOnWhenIdle.Rsp(
            TSN=13,
            StatusCat=t.StatusCategory(4),
            StatusCode=t.StatusCodeGeneric.OK,
            RxOnWhenIdle=1)]
    )

    zboss_server.reply_once_to(
        request=c.NcpConfig.GetEDTimeout.Req(TSN=14),
        responses=[c.NcpConfig.GetEDTimeout.Rsp(
            TSN=14,
            StatusCat=t.StatusCategory(4),
            StatusCode=t.StatusCodeGeneric.OK,
            Timeout=t.TimeoutIndex(0x00))]
    )

    zboss_server.reply_once_to(
        request=c.NcpConfig.GetMaxChildren.Req(TSN=15),
        responses=[c.NcpConfig.GetMaxChildren.Rsp(
            TSN=15,
            StatusCat=t.StatusCategory(4),
            StatusCode=t.StatusCodeGeneric.OK,
            ChildrenNbr=10)]
    )

    zboss_server.reply_once_to(
        request=c.NcpConfig.GetAuthenticationStatus.Req(TSN=16),
        responses=[c.NcpConfig.GetAuthenticationStatus.Rsp(
            TSN=16,
            StatusCat=t.StatusCategory(4),
            StatusCode=t.StatusCodeGeneric.OK,
            Authenticated=True)]
    )

    zboss_server.reply_once_to(
        request=c.NcpConfig.GetParentAddr.Req(TSN=17),
        responses=[c.NcpConfig.GetParentAddr.Rsp(
            TSN=17,
            StatusCat=t.StatusCategory(4),
            StatusCode=t.StatusCodeGeneric.OK,
            NWKParentAddr=parent_address)]
    )

    zboss_server.reply_once_to(
        request=c.NcpConfig.GetCoordinatorVersion.Req(TSN=18),
        responses=[c.NcpConfig.GetCoordinatorVersion.Rsp(
            TSN=18,
            StatusCat=t.StatusCategory(4),
            StatusCode=t.StatusCodeGeneric.OK,
            CoordinatorVersion=coordinator_version)]
    )

    zboss_server.reply_once_to(
        request=c.ZDO.PermitJoin.Req(
            TSN=20,
            DestNWK=t.NWK(0x0000),
            PermitDuration=t.uint8_t(0),
            TCSignificance=t.uint8_t(0x01),
        ),
        responses=[c.ZDO.PermitJoin.Rsp(
            TSN=20,
            StatusCat=t.StatusCategory(4),
            StatusCode=t.StatusCodeGeneric.OK,
        )]
    )

    zboss_server.reply_once_to(
        request=c.NcpConfig.NCPModuleReset.Req(
            TSN=21, Option=t.ResetOptions(0)
        ),
        responses=[c.NcpConfig.NCPModuleReset.Rsp(
            TSN=21,
            StatusCat=t.StatusCategory(4),
            StatusCode=t.StatusCodeGeneric.OK
        )]
    )

    await app.startup(auto_form=False)

    assert app.state.network_info.pan_id == 0x5679
    assert app.state.network_info.extended_pan_id == t.EUI64(
        ext_pan_id.serialize()[::-1])
    assert app.state.network_info.channel == channel
    assert app.state.network_info.channel_mask == channel_mask
    assert app.state.network_info.network_key.seq == 1
    assert app.state.network_info.stack_specific[
               "parent_nwk"
           ] == parent_address
    assert app.state.network_info.stack_specific[
               "authenticated"
           ] == 1
    assert app.state.network_info.stack_specific[
               "coordinator_version"
           ] == coordinator_version

    # Anything to make sure it's set
    assert app._device.node_desc.maximum_outgoing_transfer_size == 82

    await app.shutdown()


@pytest.mark.asyncio
async def test_endpoints(make_application):
    """Test endpoints."""
    app, zboss_server = make_application(server_cls=BaseZbossDevice)

    endpoints = []
    zboss_server.register_indication_listener(
        c.ZDO.PermitJoin.Req(partial=True), endpoints.append
    )

    await app.startup(auto_form=False)

    # We currently just register one endpoint
    assert len(endpoints) == 1
    assert 1 in app._device.endpoints

    await app.shutdown()


@pytest.mark.asyncio
async def test_not_configured(make_application):
    """Test device not configured."""
    app, zboss_server = make_application(
        server_cls=BaseZbossGenericDevice, active_sequence=True
    )

    # Simulate responses for each request in load_network_info
    zboss_server.reply_once_to(
        request=c.NcpConfig.GetZigbeeRole.Req(TSN=1),
        responses=[c.NcpConfig.GetZigbeeRole.Rsp(
            TSN=1,
            StatusCat=t.StatusCategory(4),
            StatusCode=t.StatusCodeGeneric.OK,
            DeviceRole=t.DeviceRole(1))]
    )

    zboss_server.reply_once_to(
        request=c.NcpConfig.GetZigbeeRole.Req(TSN=1),
        responses=[c.NcpConfig.GetZigbeeRole.Rsp(
            TSN=1,
            StatusCat=t.StatusCategory(4),
            StatusCode=t.StatusCodeGeneric.OK,
            DeviceRole=t.DeviceRole(1))]
    )

    zboss_server.reply_once_to(
        request=c.NcpConfig.GetJoinStatus.Req(TSN=2),
        responses=[c.NcpConfig.GetJoinStatus.Rsp(
            TSN=2,
            StatusCat=t.StatusCategory(4),
            StatusCode=t.StatusCodeGeneric.OK,
            Joined=0)]
    )

    zboss_server.reply_once_to(
        request=c.NcpConfig.NCPModuleReset.Req(
            TSN=3, Option=t.ResetOptions(0)
        ),
        responses=[c.NcpConfig.NCPModuleReset.Rsp(
            TSN=3,
            StatusCat=t.StatusCategory(4),
            StatusCode=t.StatusCodeGeneric.OK
        )]
    )

    # We cannot start the application if Z-Stack
    # is not configured and without auto_form
    with pytest.raises(NetworkNotFormed):
        await app.startup(auto_form=False)


@pytest.mark.asyncio
async def test_reset(make_application, mocker):
    """Test application reset."""
    app, zboss_server = make_application(server_cls=BaseZbossDevice)

    # `_reset` should be called at least once
    # to put the radio into a consistent state
    mocker.spy(ZBOSS, "reset")
    assert ZBOSS.reset.call_count == 0

    await app.startup()
    await app.shutdown()

    assert ZBOSS.reset.call_count >= 1


@pytest.mark.asyncio
async def test_auto_form_unnecessary(make_application, mocker):
    """Test unnecessary auto form."""
    app, zboss_server = make_application(server_cls=BaseZbossDevice)
    mocker.patch.object(app, "form_network", new=CoroutineMock())

    await app.startup(auto_form=True)

    assert app.form_network.call_count == 0

    await app.shutdown()


@pytest.mark.asyncio
async def test_auto_form_necessary(make_application, mocker):
    """Test necessary auto form."""
    app, zboss_server = make_application(server_cls=BaseZbossDevice)

    assert app.state.network_info.channel == 0
    assert app.state.network_info.channel_mask == t.Channels.NO_CHANNELS

    await app.startup(auto_form=True)

    assert app.state.network_info.channel != 0
    assert app.state.network_info.channel_mask != t.Channels.NO_CHANNELS

    await app.shutdown()


@pytest.mark.asyncio
async def test_concurrency_auto_config(make_application):
    """Test auto config concurrency."""
    app, zboss_server = make_application(server_cls=BaseZbossDevice)
    await app.connect()
    await app.start_network()

    assert app._concurrent_requests_semaphore.max_value == 8
