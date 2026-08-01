"""Test that ZDO requests behave the same with and without a quirk.

`zigpy.quirks.get_device()` returns a plain `zigpy.device.Device` subclass,
so a quirked device cannot carry any `ZbossZDO` method overrides. Every ZDO
request is therefore translated on the outgoing packet instead, and both
kinds of device must end up sending the same NCP command and returning the
same value.
"""
import pytest
import zigpy.endpoint
import zigpy.exceptions
import zigpy.quirks
import zigpy.types as zigpy_t
import zigpy.zdo
import zigpy.zdo.types as zdo_t

import zigpy_zboss.commands as c
import zigpy_zboss.types as t
from zigpy_zboss.zigbee.device import ZbossZDO

from ..conftest import BaseZbossDevice

DEVICE_IEEE = t.EUI64.convert("18:7a:3e:ff:fe:7d:13:85")
DEVICE_NWK = 0xF79F

# Both device kinds are exercised by every test: without a quirk the device
# is a ZbossDevice, with one it is a plain zigpy device.
quirked = pytest.mark.parametrize("quirked", [False, True])


def _ok_rsp(cmd, **kwargs):
    """Build a successful response for a ZBOSS ZDO command."""
    return cmd.Rsp(
        TSN=123,
        StatusCat=t.StatusCategory(1),
        StatusCode=t.StatusCodeGeneric.OK,
        **kwargs,
    )


async def _start(make_application, quirked):
    """Start an application with one device, quirked or not."""
    app, zboss_server = make_application(BaseZbossDevice)
    await app.startup(auto_form=False)

    device = app.add_initialized_device(ieee=DEVICE_IEEE, nwk=DEVICE_NWK)

    if quirked:
        device = zigpy.quirks.CustomDevice(
            app, device.ieee, device.nwk, device
        )
        app.devices[device.ieee] = device
        device.add_endpoint(1).status = zigpy.endpoint.Status.ZDO_INIT

    device.endpoints[1].add_input_cluster(6)

    assert isinstance(device.zdo, ZbossZDO) is not quirked

    return app, zboss_server, device


@quirked
@pytest.mark.asyncio
async def test_bind(make_application, quirked):
    """Binding sends a BindReq and returns the standard ZDO response."""
    app, zboss_server, device = await _start(make_application, quirked)

    bind_req = zboss_server.reply_once_to(
        request=c.ZDO.BindReq.Req(TSN=123, partial=True),
        responses=[_ok_rsp(c.ZDO.BindReq)],
    )

    result = await device.endpoints[1].on_off.bind()

    received = await bind_req

    assert received.TargetNwkAddr == DEVICE_NWK
    assert received.SrcIEEE == DEVICE_IEEE
    assert received.SrcEndpoint == 1
    assert received.ClusterId == 6
    assert received.DstAddrMode == t.BindAddrMode.IEEE
    assert result == [zdo_t.Status.SUCCESS]

    await app.shutdown()


@quirked
@pytest.mark.asyncio
async def test_unbind(make_application, quirked):
    """Unbinding sends an UnbindReq and returns the standard response."""
    app, zboss_server, device = await _start(make_application, quirked)

    unbind_req = zboss_server.reply_once_to(
        request=c.ZDO.UnbindReq.Req(TSN=123, partial=True),
        responses=[_ok_rsp(c.ZDO.UnbindReq)],
    )

    result = await device.endpoints[1].on_off.unbind()

    received = await unbind_req

    assert received.ClusterId == 6
    assert result == [zdo_t.Status.SUCCESS]

    await app.shutdown()


@quirked
@pytest.mark.asyncio
async def test_bind_failure_status(make_application, quirked):
    """A non-zero NCP status is reported back to the caller."""
    app, zboss_server, device = await _start(make_application, quirked)

    zboss_server.reply_once_to(
        request=c.ZDO.BindReq.Req(TSN=123, partial=True),
        responses=[
            c.ZDO.BindReq.Rsp(
                TSN=123,
                StatusCat=t.StatusCategory(1),
                StatusCode=t.StatusCodeGeneric.ERROR,
            )
        ],
    )

    (status,) = await device.endpoints[1].on_off.bind()

    assert status != zdo_t.Status.SUCCESS

    await app.shutdown()


@quirked
@pytest.mark.asyncio
async def test_bind_to_group(make_application, quirked):
    """A group destination is packed into the first two DstAddr bytes."""
    app, zboss_server, device = await _start(make_application, quirked)

    bind_req = zboss_server.reply_once_to(
        request=c.ZDO.BindReq.Req(TSN=123, partial=True),
        responses=[_ok_rsp(c.ZDO.BindReq)],
    )

    result = await device.zdo.request(
        zdo_t.ZDOCmd.Bind_req,
        DEVICE_IEEE,
        1,
        6,
        zdo_t.MultiAddress(addrmode=zigpy_t.AddrMode.Group, nwk=0x1234),
    )

    received = await bind_req

    assert received.DstAddrMode == t.BindAddrMode.Group
    assert received.DstAddr == t.EUI64([0x34, 0x12, 0, 0, 0, 0, 0, 0])
    assert received.DstEndpoint == 0
    assert result == [zdo_t.Status.SUCCESS]

    await app.shutdown()


@quirked
@pytest.mark.asyncio
async def test_leave(make_application, quirked):
    """A device can be removed from the network."""
    app, zboss_server, device = await _start(make_application, quirked)

    leave_req = zboss_server.reply_once_to(
        request=c.ZDO.MgtLeave.Req(TSN=123, partial=True),
        responses=[_ok_rsp(c.ZDO.MgtLeave)],
    )

    result = await device.zdo.leave()

    received = await leave_req

    assert received.IEEE == DEVICE_IEEE
    assert received.DestNWK == DEVICE_NWK
    assert result == [zdo_t.Status.SUCCESS]

    await app.shutdown()


@quirked
@pytest.mark.asyncio
async def test_node_desc(make_application, quirked):
    """A device can be interviewed."""
    app, zboss_server, device = await _start(make_application, quirked)

    node_desc = zdo_t.NodeDescriptor(
        logical_type=zdo_t.LogicalType.Router,
        complex_descriptor_available=0,
        user_descriptor_available=0,
        reserved=0,
        aps_flags=0,
        frequency_band=zdo_t.NodeDescriptor.FrequencyBand.Freq2400MHz,
        mac_capability_flags=142,
        manufacturer_code=4190,
        maximum_buffer_size=82,
        maximum_incoming_transfer_size=82,
        server_mask=11264,
        maximum_outgoing_transfer_size=82,
        descriptor_capability_field=0,
    )

    zboss_server.reply_once_to(
        request=c.ZDO.NodeDescReq.Req(TSN=123, partial=True),
        responses=[
            _ok_rsp(
                c.ZDO.NodeDescReq, NodeDesc=node_desc, NwkAddr=DEVICE_NWK
            )
        ],
    )

    assert await device.get_node_descriptor() == node_desc

    await app.shutdown()


@quirked
@pytest.mark.asyncio
async def test_simple_desc(make_application, quirked):
    """An endpoint can be interviewed."""
    app, zboss_server, device = await _start(make_application, quirked)

    simple_desc = t.SimpleDescriptor(
        endpoint=1,
        profile=260,
        device_type=769,
        device_version=1,
        input_clusters_count=3,
        output_clusters_count=1,
        input_clusters=[0, 3, 6],
        output_clusters=[25],
    )

    zboss_server.reply_once_to(
        request=c.ZDO.SimpleDescriptorReq.Req(TSN=123, partial=True),
        responses=[
            _ok_rsp(
                c.ZDO.SimpleDescriptorReq,
                SimpleDesc=simple_desc,
                NwkAddr=DEVICE_NWK,
            )
        ],
    )

    status, _, desc = await device.zdo.Simple_Desc_req(DEVICE_NWK, 1)

    assert status == zdo_t.Status.SUCCESS
    assert desc.endpoint == 1
    assert desc.profile == 260
    assert list(desc.input_clusters) == [0, 3, 6]

    await app.shutdown()


@quirked
@pytest.mark.asyncio
async def test_lqi(make_application, quirked):
    """A device's neighbour table can be read."""
    app, zboss_server, device = await _start(make_application, quirked)

    neighbors = zdo_t.Neighbors(
        Entries=0, StartIndex=0, NeighborTableList=[]
    )

    zboss_server.reply_once_to(
        request=c.ZDO.MgmtLqi.Req(TSN=123, partial=True),
        responses=[_ok_rsp(c.ZDO.MgmtLqi, Neighbors=neighbors)],
    )

    status, received = await device.zdo.Mgmt_Lqi_req(0)

    assert status == zdo_t.Status.SUCCESS
    assert received == neighbors

    await app.shutdown()


@quirked
@pytest.mark.asyncio
async def test_unsupported_unicast_zdo_fails_fast(make_application, quirked):
    """An untranslatable ZDO request errors instead of silently hanging."""
    app, _, device = await _start(make_application, quirked)

    with pytest.raises(zigpy.exceptions.DeliveryError):
        await device.zdo.request(zdo_t.ZDOCmd.Mgmt_Bind_req, 0)

    await app.shutdown()


@quirked
@pytest.mark.asyncio
async def test_unsupported_zdo_broadcast_is_dropped(make_application, quirked):
    """Broadcasts have no caller waiting on a reply, so they are dropped."""
    app, _, _ = await _start(make_application, quirked)

    await zigpy.zdo.broadcast(
        app,
        zdo_t.ZDOCmd.Mgmt_Rtg_req,
        0x0000,
        0x00,
        0,
        broadcast_address=zigpy_t.BroadcastAddress.ALL_ROUTERS_AND_COORDINATOR,
    )

    await app.shutdown()
