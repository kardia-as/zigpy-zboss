"""Test zigpy callbacks."""
import asyncio

import pytest
import zigpy.types as zigpy_t
import zigpy.zdo.types as zdo_t

import zigpy_zboss.commands as c
import zigpy_zboss.types as t

from ..conftest import BaseZbossDevice, serialize_zdo_command


@pytest.mark.asyncio
async def test_on_zdo_device_announce_nwk_change(make_application, mocker):
    """Test device announce network address change."""
    app, zboss_server = make_application(server_cls=BaseZbossDevice)
    await app.startup(auto_form=False)

    mocker.spy(app, "handle_join")
    mocker.patch.object(app, "handle_message")

    device = app.add_initialized_device(ieee=t.EUI64(range(8)), nwk=0xFA9E)
    new_nwk = device.nwk + 1

    payload = bytearray(serialize_zdo_command(
        command_id=zdo_t.ZDOCmd.Device_annce,
        NWKAddr=new_nwk,
        IEEEAddr=device.ieee,
        Capability=t.MACCapability.DeviceType,
        Status=t.DeviceUpdateStatus.tc_rejoin,
    ))
    payload_length = len(payload)

    # Assume its NWK changed and we're just finding out
    await zboss_server.send(
        c.APS.DataIndication.Ind(
            ParamLength=21, PayloadLength=payload_length,
            FrameFC=t.APSFrameFC(0x01),
            SrcAddr=t.NWK(0x0001), DstAddr=t.NWK(0x0000),
            GrpAddr=t.NWK(0x0000), DstEndpoint=1,
            SrcEndpoint=1, ClusterId=zdo_t.ZDOCmd.Device_annce, ProfileId=260,
            PacketCounter=10, SrcMACAddr=t.NWK(0x0000),
            DstMACAddr=t.NWK(0x0000),
            LQI=255, RSSI=-70, KeySrcAndAttr=t.ApsAttributes(0x01),
            Payload=t.Payload(payload)
        )
    )

    await zboss_server.send(
        c.ZDO.DevAnnceInd.Ind(
            NWK=new_nwk,
            IEEE=device.ieee,
            MacCap=1,
        )
    )

    await asyncio.sleep(0.1)

    app.handle_join.assert_called_once_with(
        nwk=new_nwk, ieee=device.ieee, parent_nwk=None
    )

    # The device's NWK has been updated
    assert device.nwk == new_nwk

    await app.shutdown()


@pytest.mark.asyncio
async def test_on_zdo_device_leave_callback(make_application, mocker):
    """Test ZDO device leave indication."""
    app, zboss_server = make_application(server_cls=BaseZbossDevice)
    await app.startup(auto_form=False)

    mocker.patch.object(app, "handle_leave")

    nwk = 0xAABB
    ieee = t.EUI64(range(8))

    await zboss_server.send(
        c.NWK.NwkLeaveInd.Ind(
            IEEE=ieee, Rejoin=0
        )
    )
    app.handle_leave.assert_called_once_with(nwk=nwk, ieee=ieee)

    await app.shutdown()


@pytest.mark.asyncio
async def test_on_af_message_callback(make_application, mocker):
    """Test AF message indication."""
    app, zboss_server = make_application(server_cls=BaseZbossDevice)
    await app.startup(auto_form=False)

    mocker.patch.object(app, "packet_received")
    device = app.add_initialized_device(ieee=t.EUI64(range(8)), nwk=0xAABB)

    af_message = c.APS.DataIndication.Ind(
        ParamLength=21, PayloadLength=len(b"test"),
        FrameFC=t.APSFrameFC(0x01),
        SrcAddr=device.nwk, DstAddr=t.NWK(0x0000),
        GrpAddr=t.NWK(0x0000), DstEndpoint=1,
        SrcEndpoint=4, ClusterId=2, ProfileId=260,
        PacketCounter=10, SrcMACAddr=t.NWK(0x0000),
        DstMACAddr=t.NWK(0x0000),
        LQI=19, RSSI=0, KeySrcAndAttr=t.ApsAttributes(0x01),
        Payload=t.Payload(b"test")
    )

    # Normal message
    await zboss_server.send(af_message)
    await asyncio.sleep(0.1)

    assert app.packet_received.call_count == 1
    _call = app.packet_received.call_args[0][0]
    assert _call.src == zigpy_t.AddrModeAddress(
        addr_mode=zigpy_t.AddrMode.NWK,
        address=device.nwk,
    )
    assert _call.src_ep == 4
    assert _call.dst == zigpy_t.AddrModeAddress(
        zigpy_t.AddrMode.NWK, app.state.node_info.nwk
    )
    assert _call.dst_ep == 1
    assert _call.cluster_id == 2
    assert _call.data.serialize() == b"test"
    assert _call.lqi == 19
    assert _call.rssi == 0
    assert _call.profile_id == 260

    app.packet_received.reset_mock()

    zll_message = c.APS.DataIndication.Ind(
        ParamLength=21, PayloadLength=len(b"test"),
        FrameFC=t.APSFrameFC(0x01),
        SrcAddr=device.nwk, DstAddr=t.NWK(0x0000),
        GrpAddr=t.NWK(0x0000), DstEndpoint=2,
        SrcEndpoint=4, ClusterId=2, ProfileId=260,
        PacketCounter=10, SrcMACAddr=t.NWK(0x0000),
        DstMACAddr=t.NWK(0x0000),
        LQI=19, RSSI=0, KeySrcAndAttr=t.ApsAttributes(0x01),
        Payload=t.Payload(b"test")
    )

    # ZLL message
    await zboss_server.send(zll_message)
    await asyncio.sleep(0.1)

    assert app.packet_received.call_count == 1
    _call = app.packet_received.call_args[0][0]
    assert _call.src == zigpy_t.AddrModeAddress(
        addr_mode=zigpy_t.AddrMode.NWK, address=device.nwk
    )
    assert _call.src_ep == 4
    assert _call.dst == zigpy_t.AddrModeAddress(
        zigpy_t.AddrMode.NWK, app.state.node_info.nwk
    )
    assert _call.dst_ep == 2
    assert _call.cluster_id == 2
    assert _call.data.serialize() == b"test"
    assert _call.lqi == 19
    assert _call.rssi == 0
    assert _call.profile_id == 260

    app.packet_received.reset_mock()

    unknown_message = c.APS.DataIndication.Ind(
        ParamLength=21, PayloadLength=len(b"test"),
        FrameFC=t.APSFrameFC(0x01),
        SrcAddr=device.nwk, DstAddr=t.NWK(0x0000),
        GrpAddr=t.NWK(0x0000), DstEndpoint=3,
        SrcEndpoint=4, ClusterId=2, ProfileId=260,
        PacketCounter=10, SrcMACAddr=t.NWK(0x0000),
        DstMACAddr=t.NWK(0x0000),
        LQI=19, RSSI=0, KeySrcAndAttr=t.ApsAttributes(0x01),
        Payload=t.Payload(b"test")
    )

    # Message on an unknown endpoint (is this possible?)
    await zboss_server.send(unknown_message)
    await asyncio.sleep(0.1)

    assert app.packet_received.call_count == 1
    _call = app.packet_received.call_args[0][0]
    assert _call.src == zigpy_t.AddrModeAddress(
        addr_mode=zigpy_t.AddrMode.NWK, address=device.nwk
    )
    assert _call.src_ep == 4
    assert _call.dst == zigpy_t.AddrModeAddress(
        zigpy_t.AddrMode.NWK, app.state.node_info.nwk
    )
    assert _call.dst_ep == 3
    assert _call.cluster_id == 2
    assert _call.data.serialize() == b"test"
    assert _call.lqi == 19
    assert _call.rssi == 0
    assert _call.profile_id == 260

    app.packet_received.reset_mock()


@pytest.mark.asyncio
async def test_receive_zdo_broadcast(make_application, mocker):
    """Test receive ZDO broadcast."""
    app, zboss_server = make_application(server_cls=BaseZbossDevice)
    await app.startup(auto_form=False)

    mocker.patch.object(app, "packet_received")

    zdo_callback = c.APS.DataIndication.Ind(
        ParamLength=21, PayloadLength=len(b"bogus"),
        FrameFC=t.APSFrameFC.Broadcast,
        SrcAddr=t.NWK(0x35D9), DstAddr=t.NWK(0x0000),
        GrpAddr=t.NWK(0x0000), DstEndpoint=0,
        SrcEndpoint=0, ClusterId=19, ProfileId=260,
        PacketCounter=10, SrcMACAddr=t.NWK(0x0000),
        DstMACAddr=t.NWK(0xFFFF),
        LQI=19, RSSI=0, KeySrcAndAttr=t.ApsAttributes(0x01),
        Payload=t.Payload(b"bogus")
    )
    await zboss_server.send(zdo_callback)
    await asyncio.sleep(0.1)

    assert app.packet_received.call_count == 1
    packet = app.packet_received.mock_calls[0].args[0]
    assert packet.src == zigpy_t.AddrModeAddress(
        addr_mode=zigpy_t.AddrMode.NWK, address=0x35D9
    )
    assert packet.src_ep == 0x00
    assert packet.dst == zigpy_t.AddrModeAddress(
        addr_mode=zigpy_t.AddrMode.Broadcast,
        address=zigpy_t.BroadcastAddress.ALL_ROUTERS_AND_COORDINATOR,
    )
    assert packet.dst_ep == 0x00
    assert packet.cluster_id == zdo_callback.ClusterId
    assert packet.data.serialize() == zdo_callback.Payload.serialize()

    await app.shutdown()


@pytest.mark.asyncio
async def test_receive_af_broadcast(make_application, mocker):
    """Test receive AF broadcast."""
    app, zboss_server = make_application(server_cls=BaseZbossDevice)
    await app.startup(auto_form=False)

    mocker.patch.object(app, "packet_received")

    payload = b"\x11\xA6\x00\x74\xB5\x7C\x00\x02\x5F"

    af_callback = c.APS.DataIndication.Ind(
        ParamLength=21, PayloadLength=len(payload),
        FrameFC=t.APSFrameFC.Broadcast,
        SrcAddr=t.NWK(0x1234), DstAddr=t.NWK(0x0000),
        GrpAddr=t.NWK(0x0000), DstEndpoint=2,
        SrcEndpoint=254, ClusterId=4096, ProfileId=260,
        PacketCounter=10, SrcMACAddr=t.NWK(0x0000),
        DstMACAddr=t.NWK(0xFFFF),
        LQI=19, RSSI=0, KeySrcAndAttr=t.ApsAttributes(0x01),
        Payload=t.Payload(payload)
    )
    await zboss_server.send(af_callback)
    await asyncio.sleep(0.1)

    assert app.packet_received.call_count == 1
    packet = app.packet_received.mock_calls[0].args[0]
    assert packet.src == zigpy_t.AddrModeAddress(
        addr_mode=zigpy_t.AddrMode.NWK,
        address=0x1234,
    )
    assert packet.src_ep == af_callback.SrcEndpoint
    assert packet.dst == zigpy_t.AddrModeAddress(
        addr_mode=zigpy_t.AddrMode.Broadcast,
        address=zigpy_t.BroadcastAddress.ALL_ROUTERS_AND_COORDINATOR,
    )
    assert packet.dst_ep == af_callback.DstEndpoint
    assert packet.cluster_id == af_callback.ClusterId
    assert packet.lqi == af_callback.LQI
    assert packet.data.serialize() == af_callback.Payload.serialize()

    await app.shutdown()


@pytest.mark.asyncio
async def test_receive_af_group(make_application, mocker):
    """Test receive AF group."""
    app, zboss_server = make_application(server_cls=BaseZbossDevice)
    await app.startup(auto_form=False)

    mocker.patch.object(app, "packet_received")

    payload = b"\x11\xA6\x00\x74\xB5\x7C\x00\x02\x5F"

    af_callback = c.APS.DataIndication.Ind(
        ParamLength=21, PayloadLength=len(payload),
        FrameFC=t.APSFrameFC.Group,
        SrcAddr=t.NWK(0x1234), DstAddr=t.NWK(0x0000),
        GrpAddr=t.NWK(0x1234), DstEndpoint=0,
        SrcEndpoint=254, ClusterId=4096, ProfileId=260,
        PacketCounter=10, SrcMACAddr=t.NWK(0x0000),
        DstMACAddr=t.NWK(0xFFFF),
        LQI=19, RSSI=0, KeySrcAndAttr=t.ApsAttributes(0x01),
        Payload=t.Payload(payload)
    )
    await zboss_server.send(af_callback)
    await asyncio.sleep(0.1)

    assert app.packet_received.call_count == 1
    packet = app.packet_received.mock_calls[0].args[0]
    assert packet.src == zigpy_t.AddrModeAddress(
        addr_mode=zigpy_t.AddrMode.NWK,
        address=0x1234,
    )
    assert packet.src_ep == af_callback.SrcEndpoint
    assert packet.dst == zigpy_t.AddrModeAddress(
        addr_mode=zigpy_t.AddrMode.Group, address=0x1234
    )
    assert packet.cluster_id == af_callback.ClusterId
    assert packet.lqi == af_callback.LQI
    assert packet.data.serialize() == af_callback.Payload.serialize()

    await app.shutdown()
