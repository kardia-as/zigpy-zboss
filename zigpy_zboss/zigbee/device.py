"""Zigbee device object."""
import logging
from typing import Any

import zigpy.device
import zigpy.exceptions
import zigpy.types as t
from zigpy.zdo import ZDO as ZigpyZDO
from zigpy.zdo import types as zdo_t

import zigpy_zboss.types as t_zboss
from zigpy_zboss import commands as c

LOGGER = logging.getLogger(__name__)

# NCP spec 3.4.2.1: every unicast ZDO request is processed within 5s, or 12s
# for a sleepy ZED, excluding host-NCP transport overhead. Scans instead
# depend on the scan duration and channel list.
ZDO_TIMEOUT = 15
ZDO_SCAN_TIMEOUT = 70


class ZbossZDO(ZigpyZDO):
    """The ZDO endpoint of a ZBOSS device.

    The ZBOSS NCP has no APSDE path for ZDO: every ZDO request has to be sent
    as its own NCP command. Rather than overriding the individual `*_req`
    methods, which quirks discard when they replace a device object, the
    translation happens in `zboss_specific_cmd` on the outgoing packet. That
    hook lives on the coordinator, which is never quirked, so every device
    takes the same path and gets standard zigpy return values.
    """

    async def Mgmt_NWK_Update_req(self, nwkUpdate):
        """Issue a ZDO Mgmt_NWK_Update (energy scan / channel change)."""
        res = await self._device._application._api.request(
            c.ZDO.MgmtNwkUpdate.Req(
                TSN=self._device._application.get_sequence(),
                ScanChannelMask=nwkUpdate.ScanChannels,
                ScanDuration=nwkUpdate.ScanDuration,
                ScanCount=nwkUpdate.ScanCount or 0,
                MgrAddr=self._device.nwk,
                DstNWK=t.NWK(0x0000),
            ),
            timeout=ZDO_SCAN_TIMEOUT,
        )
        if res.StatusCode != 0:
            raise zigpy.exceptions.DeliveryError(
                f"Mgmt_NWK_Update_req failed: {res.StatusCode}",
                status=res.StatusCode,
            )
        return (None, res.ScannedChannels, None, None, res.EnergyValues)

    async def zboss_specific_cmd(self, packet: t.ZigbeePacket) -> None:
        """Reroute ZDO packets sent over APSDE to ZBOSS ZDO commands."""
        try:
            zdo_hdr, zdo_args = self.deserialize(
                cluster_id=packet.cluster_id, data=packet.data.serialize()
            )
        except ValueError:
            LOGGER.debug("Could not parse ZDO message from packet")
            return

        handler = self._ZDO_PACKET_HANDLERS.get(zdo_hdr.command_id)

        if handler is not None:
            await handler(self, packet, zdo_hdr, zdo_args)
            return

        is_response = bool(zdo_hdr.command_id & 0x8000)
        is_unicast = packet.dst.addr_mode in (t.AddrMode.NWK, t.AddrMode.IEEE)

        # Only unicast requests have a caller waiting on a reply. Dropping one
        # silently would stall that caller until it times out.
        if is_response or not is_unicast:
            LOGGER.debug("Dropping unsupported ZDO packet: %r", packet)
            return

        raise zigpy.exceptions.DeliveryError(
            f"ZBOSS NCP cannot send ZDO command {zdo_hdr.command_id!r}"
        )

    @property
    def _api(self):
        """Return the NCP API of the application this ZDO belongs to."""
        return self._device._application._api

    def _next_tsn(self) -> int:
        """Return the next NCP transmission sequence number."""
        return self._device._application.get_sequence()

    def _target_nwk(self, packet: t.ZigbeePacket) -> t.NWK:
        """Return the NWK address a ZDO packet is addressed to."""
        if packet.dst.addr_mode != t.AddrMode.IEEE:
            return t.NWK(packet.dst.address)

        try:
            device = self._device._application.get_device(
                ieee=packet.dst.address
            )
        except KeyError as exc:
            raise zigpy.exceptions.DeliveryError(
                f"Cannot send ZDO request to unknown device {packet.dst!r}"
            ) from exc

        return t.NWK(device.nwk)

    def _send_zdo_rsp(
            self,
            packet: t.ZigbeePacket,
            zdo_hdr: zdo_t.ZDOHeader,
            *values: Any,
            src: t.AddrModeAddress | None = None) -> None:
        """Feed a synthesized ZDO response back into zigpy.

        `src` defaults to the request's destination, which is what zigpy
        matches the pending request against. Broadcast requests have to
        override it with the address that actually answered.
        """
        rsp_cmd = zdo_t.ZDOCmd(zdo_hdr.command_id | 0x8000)
        _, schema = zdo_t.CLUSTERS[rsp_cmd]

        args = list(values)
        while args and args[-1] is None:
            args.pop()

        data = t.uint8_t(zdo_hdr.tsn).serialize() + t.serialize(args, schema)

        self._device._application.packet_received(
            t.ZigbeePacket(
                src=packet.dst if src is None else src,
                src_ep=0,
                dst=t.AddrModeAddress(
                    addr_mode=t.AddrMode.NWK,
                    address=t.NWK(0x0000),
                ),
                dst_ep=0,
                tsn=zdo_hdr.tsn,
                profile_id=0,
                cluster_id=rsp_cmd,
                data=t.SerializableBytes(data),
                tx_options=t.TransmitOptions.NONE,
                lqi=None,
                rssi=None,
            )
        )

    @staticmethod
    def _bind_dst_address(dst_address: zdo_t.MultiAddress):
        """Convert a ZDO bind destination into ZBOSS addressing."""
        if dst_address.addrmode == t.AddrMode.IEEE:
            return (
                t_zboss.BindAddrMode.IEEE,
                dst_address.ieee,
                dst_address.endpoint,
            )

        # ZBOSS does not support the NWK mode for binding
        if dst_address.addrmode != t.AddrMode.Group:
            raise zigpy.exceptions.DeliveryError(
                f"Unsupported bind address mode: {dst_address.addrmode!r}"
            )

        # A group destination carries no endpoint, but ZBOSS always wants one
        return (
            t_zboss.BindAddrMode.Group,
            t.EUI64(
                [
                    dst_address.nwk % 0x100,
                    dst_address.nwk >> 8,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                ]
            ),
            t.uint8_t(0),
        )

    async def _bind_req(
            self,
            packet: t.ZigbeePacket,
            zdo_hdr: zdo_t.ZDOHeader,
            zdo_args: tuple[Any]) -> None:
        """Send ZDO bind request and handle the response."""
        src_ieee, src_ep, cluster_id, dst_address = zdo_args
        addr_mode, dst_addr, dst_ep = self._bind_dst_address(dst_address)

        res = await self._api.request(
            c.ZDO.BindReq.Req(
                TSN=self._next_tsn(),
                TargetNwkAddr=self._target_nwk(packet),
                SrcIEEE=src_ieee,
                SrcEndpoint=src_ep,
                ClusterId=cluster_id,
                DstAddrMode=addr_mode,
                DstAddr=dst_addr,
                DstEndpoint=dst_ep,
            ),
            timeout=ZDO_TIMEOUT,
        )
        self._send_zdo_rsp(packet, zdo_hdr, res.StatusCode)

    async def _unbind_req(
            self,
            packet: t.ZigbeePacket,
            zdo_hdr: zdo_t.ZDOHeader,
            zdo_args: tuple[Any]) -> None:
        """Send ZDO unbind request and handle the response."""
        src_ieee, src_ep, cluster_id, dst_address = zdo_args
        addr_mode, dst_addr, dst_ep = self._bind_dst_address(dst_address)

        res = await self._api.request(
            c.ZDO.UnbindReq.Req(
                TSN=self._next_tsn(),
                TargetNwkAddr=self._target_nwk(packet),
                SrcIEEE=src_ieee,
                SrcEndpoint=src_ep,
                ClusterId=cluster_id,
                DstAddrMode=addr_mode,
                DstAddr=dst_addr,
                DstEndpoint=dst_ep,
            ),
            timeout=ZDO_TIMEOUT,
        )
        self._send_zdo_rsp(packet, zdo_hdr, res.StatusCode)

    async def _node_desc_req(
            self,
            packet: t.ZigbeePacket,
            zdo_hdr: zdo_t.ZDOHeader,
            zdo_args: tuple[Any]) -> None:
        """Send ZDO node descriptor request and handle the response."""
        (nwk,) = zdo_args
        res = await self._api.request(
            c.ZDO.NodeDescReq.Req(TSN=self._next_tsn(), NwkAddr=nwk),
            timeout=ZDO_TIMEOUT,
        )
        node_desc = None if res.StatusCode else res.NodeDesc

        self._send_zdo_rsp(packet, zdo_hdr, res.StatusCode, nwk, node_desc)

    async def _active_ep_req(
            self,
            packet: t.ZigbeePacket,
            zdo_hdr: zdo_t.ZDOHeader,
            zdo_args: tuple[Any]) -> None:
        """Send ZDO active endpoints request and handle the response."""
        (nwk,) = zdo_args
        res = await self._api.request(
            c.ZDO.ActiveEpReq.Req(TSN=self._next_tsn(), NwkAddr=nwk),
            timeout=ZDO_TIMEOUT,
        )
        # Active_EP_rsp has no optional endpoint list, so it cannot be omitted
        endpoints = [] if res.StatusCode else res.ActiveEpList

        self._send_zdo_rsp(packet, zdo_hdr, res.StatusCode, nwk, endpoints)

    async def _simple_desc_req(
            self,
            packet: t.ZigbeePacket,
            zdo_hdr: zdo_t.ZDOHeader,
            zdo_args: tuple[Any]) -> None:
        """Send ZDO simple descriptor request and handle the response."""
        nwk, endpoint = zdo_args
        res = await self._api.request(
            c.ZDO.SimpleDescriptorReq.Req(
                TSN=self._next_tsn(), NwkAddr=nwk, Endpoint=endpoint
            ),
            timeout=ZDO_TIMEOUT,
        )

        if res.StatusCode:
            desc = None
        else:
            desc = zdo_t.SizePrefixedSimpleDescriptor(
                endpoint=res.SimpleDesc.endpoint,
                profile=res.SimpleDesc.profile,
                device_type=res.SimpleDesc.device_type,
                device_version=res.SimpleDesc.device_version,
                input_clusters=res.SimpleDesc.input_clusters,
                output_clusters=res.SimpleDesc.output_clusters,
            )

        self._send_zdo_rsp(packet, zdo_hdr, res.StatusCode, nwk, desc)

    async def _mgmt_lqi_req(
            self,
            packet: t.ZigbeePacket,
            zdo_hdr: zdo_t.ZDOHeader,
            zdo_args: tuple[Any]) -> None:
        """Send ZDO LQI request and handle the response."""
        (start_index,) = zdo_args
        res = await self._api.request(
            c.ZDO.MgmtLqi.Req(
                TSN=self._next_tsn(),
                DestNWK=self._target_nwk(packet),
                Index=start_index,
            ),
            timeout=ZDO_TIMEOUT,
        )
        neighbors = None if res.StatusCode else res.Neighbors

        self._send_zdo_rsp(packet, zdo_hdr, res.StatusCode, neighbors)

    async def _mgmt_leave_req(
            self,
            packet: t.ZigbeePacket,
            zdo_hdr: zdo_t.ZDOHeader,
            zdo_args: tuple[Any]) -> None:
        """Send ZDO leave request and handle the response."""
        ieee, options = zdo_args
        res = await self._api.request(
            c.ZDO.MgtLeave.Req(
                TSN=self._next_tsn(),
                DestNWK=self._target_nwk(packet),
                IEEE=t.EUI64(ieee),
                Flags=t.uint8_t(options),
            ),
            timeout=ZDO_TIMEOUT,
        )
        self._send_zdo_rsp(packet, zdo_hdr, res.StatusCode)

    async def _mgmt_permit_joining_req(
            self,
            packet: t.ZigbeePacket,
            zdo_hdr: zdo_t.ZDOHeader,
            zdo_args: tuple[Any]) -> None:
        """Send ZDO permit joining request and handle the response."""
        is_unicast = packet.dst.addr_mode in (t.AddrMode.NWK, t.AddrMode.IEEE)

        if is_unicast:
            dest_nwk = t.NWK(t.BroadcastAddress.RX_ON_WHEN_IDLE)
        else:
            dest_nwk = t.NWK(packet.dst.address)

        duration, tc_significance = zdo_args
        res = await self._api.request(
            c.ZDO.PermitJoin.Req(
                TSN=self._next_tsn(),
                DestNWK=dest_nwk,
                PermitDuration=t.uint8_t(duration),
                TCSignificance=t.uint8_t(tc_significance),
            ),
            timeout=ZDO_TIMEOUT,
        )

        if is_unicast:
            self._send_zdo_rsp(packet, zdo_hdr, res.StatusCode)

    async def _IEEE_addr_req(
            self,
            packet: t.ZigbeePacket,
            zdo_hdr: zdo_t.ZDOHeader,
            zdo_args: tuple[Any]) -> None:
        """Send ZDO IEEE addr request and handle the response."""
        nwki, req_type, index = zdo_args
        res = await self._api.request(
            c.ZDO.IeeeAddrReq.Req(
                TSN=zdo_hdr.tsn,
                DstNWK=packet.dst.address,
                NWKtoMatch=nwki,
                RequestType=req_type,
                StartIndex=index,
                ),
            timeout=ZDO_TIMEOUT,
        )

        if res.StatusCode:
            # ZDO command failed, use dummy values.
            ieee = t.EUI64([0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff])
            nwki = t.NWK(0xffff)
            src_ad = t.NWK(0x0000)
        else:
            ieee = res.RemoteDevIEEE
            nwki = res.RemoteDevNWK
            src_ad = res.RemoteDevNWK

        # This request is broadcast, so the reply comes from the device that
        # matched it rather than from the packet's destination.
        self._send_zdo_rsp(
            packet,
            zdo_hdr,
            res.StatusCode,
            ieee,
            nwki,
            src=t.AddrModeAddress(
                addr_mode=t.AddrMode.NWK,
                address=src_ad,
            ),
        )

    _ZDO_PACKET_HANDLERS = {
        zdo_t.ZDOCmd.IEEE_addr_req: _IEEE_addr_req,
        zdo_t.ZDOCmd.Node_Desc_req: _node_desc_req,
        zdo_t.ZDOCmd.Simple_Desc_req: _simple_desc_req,
        zdo_t.ZDOCmd.Active_EP_req: _active_ep_req,
        zdo_t.ZDOCmd.Bind_req: _bind_req,
        zdo_t.ZDOCmd.Unbind_req: _unbind_req,
        zdo_t.ZDOCmd.Mgmt_Lqi_req: _mgmt_lqi_req,
        zdo_t.ZDOCmd.Mgmt_Leave_req: _mgmt_leave_req,
        zdo_t.ZDOCmd.Mgmt_Permit_Joining_req: _mgmt_permit_joining_req,
    }


class ZbossDevice(zigpy.device.Device):
    """Class representing an nRF device."""

    def __init__(self, *args, **kwargs):
        """Initialize instance."""
        super().__init__(*args, **kwargs)
        assert hasattr(self, "zdo")
        self.zdo = ZbossZDO(self)
        self.endpoints[0] = self.zdo


class ZbossCoordinator(ZbossDevice):
    """Zigpy Device representing the controller."""

    def __init__(self, *args, **kwargs):
        """Initialize instance."""
        super().__init__(*args, **kwargs)

    @property
    def manufacturer(self):
        """Return manufacturer."""
        return "Nordic Semiconductor"

    @property
    def model(self):
        """Return model."""
        return "nRF52840"
