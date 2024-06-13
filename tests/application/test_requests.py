import asyncio
import pytest
from unittest.mock import AsyncMock as CoroutineMock
import zigpy.types as zigpy_t
import zigpy.endpoint
import zigpy.profiles
from zigpy.exceptions import DeliveryError

import zigpy_zboss.types as t
import zigpy_zboss.config as conf
import zigpy_zboss.commands as c

from ..conftest import (
    BaseZStackDevice
)


@pytest.mark.asyncio
async def test_zigpy_request(make_application):
    app, zboss_server = make_application(BaseZStackDevice)
    await app.startup(auto_form=False)

    device = app.add_initialized_device(ieee=t.EUI64(range(8)), nwk=0xAABB)

    ep = device.add_endpoint(1)
    ep.status = zigpy.endpoint.Status.ZDO_INIT
    ep.profile_id = 260
    ep.add_input_cluster(6)

    # Construct the payload with the correct FrameControl byte
    # FrameControl bits: 0001 0000 -> 0x10 for Server_to_Client
    frame_control_byte = 0x18
    tsn = 0x01
    command_id = 0x01

    payload = [frame_control_byte, tsn, command_id]
    payload_length = len(payload)
    # Respond to a light turn on request
    zboss_server.reply_once_to(
        request=c.APS.DataReq.Req(
            TSN=1, ParamLength=21, DataLength=3,
            DstAddr=t.EUI64.convert("00:00:00:00:00:00:aa:bb"),
            ProfileID=260, ClusterId=6, DstEndpoint=1, SrcEndpoint=1, Radius=0,
            DstAddrMode=zigpy_t.AddrMode.NWK,
            TxOptions=c.aps.TransmitOptions.NONE,
            UseAlias=t.Bool.false, AliasSrcAddr=0x0000, AliasSeqNbr=0,
            Payload=[1, 1, 1]),
        responses=[c.APS.DataReq.Rsp(
            TSN=1,
            StatusCat=t.StatusCategory(4),
            StatusCode=1,
            DstAddr=t.EUI64.convert("00:00:00:00:00:00:aa:bb"),
            DstEndpoint=1,
            SrcEndpoint=1,
            TxTime=1,
            DstAddrMode=zigpy_t.AddrMode.NWK
        ),
            c.APS.DataIndication.Ind(
                ParamLength=21,
                PayloadLength=payload_length,
                FrameFC=t.APSFrameFC(0x01),
                SrcAddr=t.NWK(0xAABB),
                DstAddr=t.NWK(0x1234),
                GrpAddr=t.NWK(0x5678),
                DstEndpoint=1,
                SrcEndpoint=1,
                ClusterId=6,
                ProfileId=260,
                PacketCounter=10,
                SrcMACAddr=t.NWK(0xAABB),
                DstMACAddr=t.NWK(0x1234),
                LQI=255,
                RSSI=-70,
                KeySrcAndAttr=t.ApsAttributes(0x01),
                Payload=t.Payload(payload)
            )],
    )

    # Turn on the light
    await device.endpoints[1].on_off.on()

    await app.shutdown()


# @pytest.mark.parametrize("device", FORMED_DEVICES)
# async def test_zigpy_request_failure(device, make_application, mocker):
#     app, zboss_server = make_application(device)
#     await app.startup(auto_form=False)
#
#     TSN = 1
#
#     device = app.add_initialized_device(ieee=t.EUI64(range(8)), nwk=0xAABB)
#
#     ep = device.add_endpoint(1)
#     ep.profile_id = 260
#     ep.add_input_cluster(6)
#
#     # Fail to respond to a light turn on request
#     zboss_server.reply_to(
#         request=c.AF.DataRequestExt.Req(
#             DstAddrModeAddress=t.AddrModeAddress(
#                 mode=t.AddrMode.NWK, address=device.nwk
#             ),
#             DstEndpoint=1,
#             SrcEndpoint=1,
#             ClusterId=6,
#             TSN=TSN,
#             Data=bytes([0x01, TSN, 0x01]),
#             partial=True,
#         ),
#         responses=[
#             c.AF.DataRequestExt.Rsp(Status=t.Status.SUCCESS),
#             c.AF.DataConfirm.Callback(
#                 Status=t.Status.FAILURE,
#                 Endpoint=1,
#                 TSN=TSN,
#             ),
#         ],
#     )
#
#     mocker.spy(app, "send_packet")
#
#     # Fail to turn on the light
#     with pytest.raises(InvalidCommandResponse):
#         await device.endpoints[1].on_off.on()
#
#     assert app.send_packet.call_count == 1
#     await app.shutdown()
#
#

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "addr",
    [
        zigpy.types.AddrModeAddress(addr_mode=zigpy.types.AddrMode.IEEE, address=t.EUI64(range(8))),
        zigpy.types.AddrModeAddress(addr_mode=zigpy.types.AddrMode.NWK, address=t.NWK(0xAABB)),
    ],
)
async def test_request_addr_mode(addr, make_application, mocker):
    app, zboss_server = make_application(server_cls=BaseZStackDevice)

    await app.startup(auto_form=False)

    device = app.add_initialized_device(ieee=t.EUI64(range(8)), nwk=0xAABB)

    mocker.patch.object(app, "send_packet", new=CoroutineMock())

    await app.request(
        device,
        use_ieee=(addr.addr_mode == zigpy.types.AddrMode.IEEE),
        profile=1,
        cluster=2,
        src_ep=3,
        dst_ep=4,
        sequence=5,
        data=b"6",
    )

    assert app.send_packet.call_count == 1
    assert app.send_packet.mock_calls[0].args[0].dst == addr

    await app.shutdown()

@pytest.mark.asyncio
async def test_mrequest(make_application, mocker):
    app, zboss_server = make_application(server_cls=BaseZStackDevice)

    mocker.patch.object(app, "send_packet", new=CoroutineMock())
    group = app.groups.add_group(0x1234, "test group")

    await group.endpoint.on_off.on()

    assert app.send_packet.call_count == 1
    assert (
        app.send_packet.mock_calls[0].args[0].dst
        == zigpy.types.AddrModeAddress(
        addr_mode=zigpy.types.AddrMode.Group, address=0x1234
        )
    )
    assert app.send_packet.mock_calls[0].args[0].data.serialize() == b"\x01\x01\x01"

    await app.shutdown()

@pytest.mark.asyncio
async def test_mrequest_doesnt_block(make_application, event_loop):
    app, zboss_server = make_application(server_cls=BaseZStackDevice)

    zboss_server.reply_once_to(
        request=c.APS.DataReq.Req(
            TSN=1, ParamLength=21, DataLength=3,
            DstAddr=t.EUI64.convert("00:00:00:00:00:00:12:34"),
            ProfileID=260, ClusterId=6, DstEndpoint=0, SrcEndpoint=1, Radius=0,
            DstAddrMode=zigpy_t.AddrMode.Group,
            TxOptions=c.aps.TransmitOptions.NONE,
            UseAlias=t.Bool.false, AliasSrcAddr=0x0000, AliasSeqNbr=0,
            Payload=[1, 1, 1]),
        responses=[
            c.APS.DataReq.Rsp(
                TSN=1,
                StatusCat=t.StatusCategory(1),
                StatusCode=0,
                DstAddr=t.EUI64.convert("00:00:00:00:00:00:aa:bb"),
                DstEndpoint=1,
                SrcEndpoint=1,
                TxTime=1,
                DstAddrMode=zigpy_t.AddrMode.Group,
            ),
        ],
    )

    data_confirm_rsp = c.APS.DataIndication.Ind(
        ParamLength=21, PayloadLength=None, FrameFC=None,
        SrcAddr=None, DstAddr=None, GrpAddr=None, DstEndpoint=1,
        SrcEndpoint=1, ClusterId=6, ProfileId=260,
        PacketCounter=None, SrcMACAddr=None, DstMACAddr=None,
        LQI=None, RSSI=None, KeySrcAndAttr=None, Payload=None, partial=True
    )

    request_sent = event_loop.create_future()
    async def on_request_sent():
        await zboss_server.send(data_confirm_rsp)

    request_sent.add_done_callback(
        lambda _: event_loop.create_task(on_request_sent())
    )

    await app.startup(auto_form=False)

    group = app.groups.add_group(0x1234, "test group")
    await group.endpoint.on_off.on()
    request_sent.set_result(True)

    await app.shutdown()

@pytest.mark.asyncio
async def test_broadcast(make_application, mocker):
    app, zboss_server = make_application(server_cls=BaseZStackDevice)
    await app.startup()
    zboss_server.reply_once_to(
        request=c.APS.DataReq.Req(TSN=1, ParamLength=21, DataLength=3,
                                  DstAddr=t.EUI64.convert(
                                      "00:00:00:00:00:00:ff:fd"),
                                  ProfileID=260, ClusterId=3, DstEndpoint=255,
                                  SrcEndpoint=1, Radius=3,
                                  DstAddrMode=zigpy_t.AddrMode.Group,
                                  TxOptions=c.aps.TransmitOptions.NONE,
                                  UseAlias=t.Bool.false,
                                  AliasSrcAddr=0x0000, AliasSeqNbr=0,
                                  Payload=[63, 63, 63]),
        responses=[
            c.APS.DataReq.Rsp(
                TSN=1,
                StatusCat=t.StatusCategory(1),
                StatusCode=0,
                DstAddr=t.EUI64.convert("00:00:00:00:00:00:ff:fd"),
                DstEndpoint=255,
                SrcEndpoint=1,
                TxTime=1,
                DstAddrMode=zigpy_t.AddrMode.Group,
            ),
        ],
    )

    await app.broadcast(
        profile=260,  # ZHA
        cluster=0x0003,  # Identify
        src_ep=1,
        dst_ep=0xFF,  # Any endpoint
        grpid=0,
        radius=3,
        sequence=1,
        data=b"???",
        broadcast_address=zigpy_t.BroadcastAddress.RX_ON_WHEN_IDLE,
    )

    await app.shutdown()

@pytest.mark.asyncio
async def test_request_concurrency(make_application, mocker):
    app, zboss_server = make_application(
        server_cls=BaseZStackDevice,
        client_config={conf.CONF_MAX_CONCURRENT_REQUESTS: 2},
    )

    await app.startup()

    device = app.add_initialized_device(ieee=t.EUI64(range(8)), nwk=0xAABB)

    ep = device.add_endpoint(1)
    ep.status = zigpy.endpoint.Status.ZDO_INIT
    ep.profile_id = 260
    ep.add_input_cluster(6)

    # Keep track of how many requests we receive at once
    in_flight_requests = 0
    did_lock = False

    def make_response(req):
        async def callback(req):
            nonlocal in_flight_requests
            nonlocal did_lock

            if app._concurrent_requests_semaphore.locked():
                did_lock = True

            in_flight_requests += 1
            assert in_flight_requests <= 2

            await asyncio.sleep(0.1)
            await zboss_server.send(c.APS.DataReq.Rsp(
                TSN=req.TSN,
                StatusCat=t.StatusCategory(1),
                StatusCode=0,
                DstAddr=req.DstAddr,
                DstEndpoint=req.DstEndpoint,
                SrcEndpoint=req.SrcEndpoint,
                TxTime=1,
                DstAddrMode=req.DstAddrMode,
            ))
            await asyncio.sleep(0)

            in_flight_requests -= 1
            assert in_flight_requests >= 0

        asyncio.create_task(callback(req))

    zboss_server.reply_to(
        request=c.APS.DataReq.Req(
            partial=True), responses=[make_response]

    )

    # We create a whole bunch at once
    await asyncio.gather(
        *[
            app.request(
                device,
                profile=260,
                cluster=1,
                src_ep=1,
                dst_ep=1,
                sequence=seq,
                data=b"\x00",
            )
            for seq in range(10)
        ]
    )

    assert in_flight_requests == 0
    assert did_lock

    await app.shutdown()

@pytest.mark.asyncio
async def test_request_cancellation_shielding(
    make_application, mocker, event_loop
):
    app, zboss_server = make_application(server_cls=BaseZStackDevice)

    await app.startup(auto_form=False)

    device = app.add_initialized_device(ieee=t.EUI64(range(8)), nwk=0xAABB)

    ep = device.add_endpoint(1)
    ep.status = zigpy.endpoint.Status.ZDO_INIT
    ep.profile_id = 260
    ep.add_input_cluster(6)

    frame_control_byte = 0x18
    tsn = 0x01
    command_id = 0x01

    payload = [frame_control_byte, tsn, command_id]
    payload_length = len(payload)

    # The data confirm timeout must be shorter than the ARSP timeout
    mocker.spy(app._api, "_unhandled_command")

    delayed_reply_sent = event_loop.create_future()

    def delayed_reply(req):
        async def inner():
            await asyncio.sleep(0.5)
            await zboss_server.send(
                c.APS.DataIndication.Ind(
                    ParamLength=21,
                    PayloadLength=payload_length,
                    FrameFC=t.APSFrameFC(0x01),
                    SrcAddr=t.NWK(0xAABB),
                    DstAddr=t.NWK(0x1234),
                    GrpAddr=t.NWK(0x5678),
                    DstEndpoint=1,
                    SrcEndpoint=1,
                    ClusterId=6,
                    ProfileId=260,
                    PacketCounter=10,
                    SrcMACAddr=t.NWK(0xAABB),
                    DstMACAddr=t.NWK(0x1234),
                    LQI=255,
                    RSSI=-70,
                    KeySrcAndAttr=t.ApsAttributes(0x01),
                    Payload=t.Payload(payload)
                )
            )
            delayed_reply_sent.set_result(True)

        asyncio.create_task(inner())

    data_req = zboss_server.reply_once_to(
        c.APS.DataReq.Req(
            TSN=1, ParamLength=21, DataLength=3,
            DstAddr=t.EUI64.convert("00:00:00:00:00:00:aa:bb"),
            ProfileID=260, ClusterId=6, DstEndpoint=1, SrcEndpoint=1, Radius=0,
            DstAddrMode=zigpy_t.AddrMode.NWK,
            TxOptions=c.aps.TransmitOptions.NONE,
            UseAlias=t.Bool.false, AliasSrcAddr=0x0000, AliasSeqNbr=0,
            Payload=[1, 1, 1]),
        responses=[
            c.APS.DataReq.Rsp(
                TSN=1,
                StatusCat=t.StatusCategory(4),
                StatusCode=1,
                DstAddr=t.EUI64.convert("00:00:00:00:00:00:aa:bb"),
                DstEndpoint=1,
                SrcEndpoint=1,
                TxTime=1,
                DstAddrMode=zigpy_t.AddrMode.NWK
            ),
            delayed_reply,
        ],
    )

    with pytest.raises(asyncio.TimeoutError):
        # Turn on the light
        await device.request(
            260,
            6,
            1,
            1,
            1,
            b'\x01\x01\x01',
            expect_reply=True,
            timeout=0.1,
        )

    await data_req
    await delayed_reply_sent

    assert app._api._unhandled_command.call_count == 0

    await app.shutdown()


@pytest.mark.asyncio
async def test_send_security_and_packet_source_route(make_application, mocker):
    app, zboss_server = make_application(server_cls=BaseZStackDevice)
    await app.startup(auto_form=False)

    packet = zigpy_t.ZigbeePacket(
        src=zigpy_t.AddrModeAddress(
            addr_mode=zigpy_t.AddrMode.NWK, address=app.state.node_info.nwk
        ),
        src_ep=0x9A,
        dst=zigpy.types.AddrModeAddress(
            addr_mode=zigpy_t.AddrMode.NWK, address=0xEEFF
        ),
        dst_ep=0xBC,
        tsn=0xDE,
        profile_id=0x1234,
        cluster_id=0x0006,
        data=zigpy_t.SerializableBytes(b"test data"),
        extended_timeout=False,
        tx_options=(
            zigpy_t.TransmitOptions.ACK |
            zigpy_t.TransmitOptions.APS_Encryption
        ),
        source_route=[0xAABB, 0xCCDD],
    )

    data_req = zboss_server.reply_once_to(
        request=c.APS.DataReq.Req(
            TSN=222, ParamLength=21, DataLength=9,
            DstAddr=t.EUI64.convert("00:00:00:00:00:00:ee:ff"),
            ProfileID=4660, ClusterId=6, DstEndpoint=188, SrcEndpoint=154,
            Radius=0, DstAddrMode=zigpy_t.AddrMode.NWK,
            TxOptions=(
                    c.aps.TransmitOptions.SECURITY_ENABLED |
                    c.aps.TransmitOptions.ACK_ENABLED
            ),
            UseAlias=t.Bool.false, AliasSrcAddr=0x0000, AliasSeqNbr=0,
            Payload=[116, 101, 115, 116, 32, 100, 97, 116, 97]),
        responses=[
            c.APS.DataReq.Rsp(
                TSN=1,
                StatusCat=t.StatusCategory(4),
                StatusCode=1,
                DstAddr=t.EUI64.convert("00:00:00:00:00:00:aa:bb"),
                DstEndpoint=1,
                SrcEndpoint=1,
                TxTime=1,
                DstAddrMode=zigpy_t.AddrMode.NWK
            ),
        ],
    )

    await app.send_packet(packet)
    req = await data_req
    assert (
            c.aps.TransmitOptions.SECURITY_ENABLED
            in c.aps.TransmitOptions(req.TxOptions)
    )

    await app.shutdown()




@pytest.mark.asyncio
async def test_send_packet_failure_disconnected(make_application, mocker):
    app, zboss_server = make_application(server_cls=BaseZStackDevice)
    await app.startup(auto_form=False)

    app._api = None

    packet = zigpy_t.ZigbeePacket(
        src=zigpy_t.AddrModeAddress(addr_mode=zigpy_t.AddrMode.NWK, address=0x0000),
        src_ep=0x9A,
        dst=zigpy_t.AddrModeAddress(addr_mode=zigpy_t.AddrMode.NWK, address=0xEEFF),
        dst_ep=0xBC,
        tsn=0xDE,
        profile_id=0x1234,
        cluster_id=0x0006,
        data=zigpy_t.SerializableBytes(b"test data"),
    )

    with pytest.raises(zigpy.exceptions.DeliveryError) as excinfo:
        await app.send_packet(packet)

    assert "Coordinator is disconnected" in str(excinfo.value)

    await app.shutdown()