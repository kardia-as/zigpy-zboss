"""Test ZbossZDO Bind/Unbind requests."""
import pytest
import zigpy.types as zigpy_t
import zigpy.zdo.types as zdo_t

import zigpy_zboss.commands as c
import zigpy_zboss.types as t

from ..conftest import BaseZbossDevice

SRC_IEEE = t.EUI64.convert("00:11:22:33:44:55:66:77")
DST_IEEE = t.EUI64.convert("aa:bb:cc:dd:ee:ff:00:11")


def _ok_rsp(cmd):
    """Build a successful response for a Bind/Unbind request."""
    return cmd.Rsp(
        TSN=123,
        StatusCat=t.StatusCategory(1),
        StatusCode=t.StatusCodeGeneric.OK,
    )


async def _start(make_application):
    """Start an application with one initialized device."""
    app, zboss_server = make_application(BaseZbossDevice)
    await app.startup(auto_form=False)
    device = app.add_initialized_device(ieee=t.EUI64(range(8)), nwk=0xAABB)
    return app, zboss_server, device


@pytest.mark.asyncio
async def test_bind_req_ieee(make_application):
    """Bind_req sends the destination IEEE address in IEEE addr mode."""
    app, zboss_server, device = await _start(make_application)

    dst_address = zdo_t.MultiAddress(
        addrmode=zigpy_t.AddrMode.IEEE,
        ieee=DST_IEEE,
        endpoint=1,
    )

    bind_req = zboss_server.reply_once_to(
        request=c.ZDO.BindReq.Req(TSN=123, partial=True),
        responses=[_ok_rsp(c.ZDO.BindReq)],
    )

    status, returned_addr, returned_cluster = await device.zdo.request(
        zdo_t.ZDOCmd.Bind_req, SRC_IEEE, 1, 6, dst_address
    )

    received = await bind_req

    assert received.DstAddrMode == t.BindAddrMode.IEEE
    assert received.DstAddr == DST_IEEE
    assert received.SrcIEEE == SRC_IEEE
    assert received.SrcEndpoint == 1
    assert received.ClusterId == 6
    assert received.DstEndpoint == 1
    assert received.TargetNwkAddr == device.nwk

    assert status == zdo_t.Status.SUCCESS
    assert returned_addr is dst_address
    assert returned_cluster == 6

    await app.shutdown()


@pytest.mark.asyncio
async def test_unbind_req_ieee(make_application):
    """Unbind_req sends the destination IEEE address, not the addr mode.

    Regression test: ``dst_eui64`` was previously set to
    ``t.Addressing.IEEE`` (the AddrMode enum value) instead of
    ``dst_address.ieee`` (the actual destination EUI64).
    """
    app, zboss_server, device = await _start(make_application)

    dst_address = zdo_t.MultiAddress(
        addrmode=zigpy_t.AddrMode.IEEE,
        ieee=DST_IEEE,
        endpoint=1,
    )

    unbind_req = zboss_server.reply_once_to(
        request=c.ZDO.UnbindReq.Req(TSN=123, partial=True),
        responses=[_ok_rsp(c.ZDO.UnbindReq)],
    )

    status, returned_addr, returned_cluster = await device.zdo.request(
        zdo_t.ZDOCmd.Unbind_req, SRC_IEEE, 1, 6, dst_address
    )

    received = await unbind_req

    assert received.DstAddrMode == t.BindAddrMode.IEEE
    # The real destination EUI64 must be sent, not the AddrMode enum value.
    assert received.DstAddr == DST_IEEE
    assert received.SrcIEEE == SRC_IEEE
    assert received.SrcEndpoint == 1
    assert received.ClusterId == 6
    assert received.DstEndpoint == 1
    assert received.TargetNwkAddr == device.nwk

    assert status == zdo_t.Status.SUCCESS
    assert returned_addr is dst_address
    assert returned_cluster == 6

    await app.shutdown()


@pytest.mark.asyncio
async def test_bind_req_group(make_application):
    """Bind_req packs the group address into the first two DstAddr bytes."""
    app, zboss_server, device = await _start(make_application)

    dst_address = zdo_t.MultiAddress(
        addrmode=zigpy_t.AddrMode.Group,
        nwk=0x1234,
        endpoint=0,
    )

    bind_req = zboss_server.reply_once_to(
        request=c.ZDO.BindReq.Req(TSN=123, partial=True),
        responses=[_ok_rsp(c.ZDO.BindReq)],
    )

    status, _, _ = await device.zdo.request(
        zdo_t.ZDOCmd.Bind_req, SRC_IEEE, 1, 6, dst_address
    )

    received = await bind_req

    assert received.DstAddrMode == t.BindAddrMode.Group
    # 0x1234 little-endian in the first two bytes, rest zero-padded.
    assert received.DstAddr == t.EUI64([0x34, 0x12, 0, 0, 0, 0, 0, 0])
    assert status == zdo_t.Status.SUCCESS

    await app.shutdown()


@pytest.mark.asyncio
async def test_unbind_req_group(make_application):
    """Unbind_req packs the group address into the first two DstAddr bytes."""
    app, zboss_server, device = await _start(make_application)

    dst_address = zdo_t.MultiAddress(
        addrmode=zigpy_t.AddrMode.Group,
        nwk=0x1234,
        endpoint=0,
    )

    unbind_req = zboss_server.reply_once_to(
        request=c.ZDO.UnbindReq.Req(TSN=123, partial=True),
        responses=[_ok_rsp(c.ZDO.UnbindReq)],
    )

    status, _, _ = await device.zdo.request(
        zdo_t.ZDOCmd.Unbind_req, SRC_IEEE, 1, 6, dst_address
    )

    received = await unbind_req

    assert received.DstAddrMode == t.BindAddrMode.Group
    assert received.DstAddr == t.EUI64([0x34, 0x12, 0, 0, 0, 0, 0, 0])
    assert status == zdo_t.Status.SUCCESS

    await app.shutdown()


@pytest.mark.asyncio
async def test_unbind_req_failure_status(make_application):
    """A non-zero StatusCode is returned verbatim to the caller."""
    app, zboss_server, device = await _start(make_application)

    dst_address = zdo_t.MultiAddress(
        addrmode=zigpy_t.AddrMode.IEEE,
        ieee=DST_IEEE,
        endpoint=1,
    )

    error_code = t.StatusCodeGeneric.ERROR
    zboss_server.reply_once_to(
        request=c.ZDO.UnbindReq.Req(TSN=123, partial=True),
        responses=[c.ZDO.UnbindReq.Rsp(
            TSN=123,
            StatusCat=t.StatusCategory(1),
            StatusCode=error_code,
        )],
    )

    status, returned_addr, returned_cluster = await device.zdo.request(
        zdo_t.ZDOCmd.Unbind_req, SRC_IEEE, 1, 6, dst_address
    )

    assert status == error_code
    assert returned_addr is dst_address
    assert returned_cluster == 6

    await app.shutdown()
