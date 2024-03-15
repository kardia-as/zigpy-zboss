"""Zigbee device object."""
import logging
import zigpy.util
import zigpy.device
import zigpy.endpoint
import zigpy.types as t
import zigpy_zboss.types as t_zboss
from typing import Any
from zigpy_zboss import commands as c
from zigpy.zdo import types as zdo_t
from zigpy.zdo import ZDO as ZigpyZDO


LOGGER = logging.getLogger(__name__)


class ZbossZDO(ZigpyZDO):
    """The ZDO endpoint of a ZBOSS device."""

    def handle_mgmt_permit_joining_req(
        self,
        permit_duration: int,
        tc_significance: int,
    ):
        """Handle ZDO permit joining request."""
        hdr = zdo_t.ZDOHeader(zdo_t.ZDOCmd.Mgmt_Permit_Joining_req, 0)
        dst_addressing = t.Addressing.IEEE

        self.listener_event("permit_duration", permit_duration)
        self.listener_event(
            "zdo_mgmt_permit_joining_req",
            self._device,
            dst_addressing,
            hdr,
            (permit_duration, tc_significance),
        )

    async def Bind_req(self, eui64, ep, cluster, dst_address):
        """Binding request."""
        if dst_address.addrmode == t.AddrMode.IEEE:
            addr_mode = t_zboss.BindAddrMode.IEEE
            dst_eui64 = dst_address.ieee
        # ZBOSS does not support the NWK mode for binding
        elif dst_address.addrmode == t.AddrMode.NWK:
            self.log(
                logging.WARNING,
                "Nwk address mode is not supported for the Bind request."
            )
        elif dst_address.addrmode == t.AddrMode.Group:
            addr_mode = t_zboss.BindAddrMode.Group
            dst_eui64 = [
                dst_address.nwk % 0x100,
                dst_address.nwk >> 8,
                0,
                0,
                0,
                0,
                0,
                0,
            ]

        res = await self._device._application._api.request(
            c.ZDO.BindReq.Req(
                TSN=self._device._application.get_sequence(),
                TargetNwkAddr=self._device.nwk,
                SrcIEEE=eui64,
                SrcEndpoint=ep,
                ClusterId=cluster,
                DstAddrMode=addr_mode,
                DstAddr=dst_eui64,
                DstEndpoint=dst_address.endpoint,
            )
        )
        if res.StatusCode != 0:
            return (res.StatusCode % 0xFF, dst_address, cluster)

        return (zdo_t.Status.SUCCESS, dst_address, cluster)

    async def Unbind_req(self, eui64, ep, cluster, dst_address):
        """Unbinding request."""
        if dst_address.addrmode == t.AddrMode.IEEE:
            addr_mode = t_zboss.BindAddrMode.IEEE
            dst_eui64 = t.Addressing.IEEE
        # ZBOSS does not support the NWK mode for binding
        elif dst_address.addrmode == t.AddrMode.NWK:
            self.log(
                logging.WARNING,
                "Nwk address mode is not supported for the Unbind request."
            )
        elif dst_address.addrmode == t.AddrMode.Group:
            addr_mode = t_zboss.BindAddrMode.Group
            dst_eui64 = [
                dst_address.nwk % 0x100,
                dst_address.nwk >> 8,
                0,
                0,
                0,
                0,
                0,
                0,
            ]

        res = await self._device._application._api.request(
            c.ZDO.UnbindReq.Req(
                TSN=self._device._application.get_sequence(),
                TargetNwkAddr=self._device.nwk,
                SrcIEEE=eui64,
                SrcEndpoint=ep,
                ClusterId=cluster,
                DstAddrMode=addr_mode,
                DstAddr=dst_eui64,
                DstEndpoint=dst_address.endpoint,
            )
        )
        if res.StatusCode != 0:
            return (res.StatusCode % 0xFF, dst_address, cluster)

        return (zdo_t.Status.SUCCESS, dst_address, cluster)

    def request(self, command, *args, use_ieee=False):
        """Request overwrite for Bind/Unbind requests."""
        if command == zdo_t.ZDOCmd.Bind_req:
            return self.Bind_req(*args)
        if command == zdo_t.ZDOCmd.Unbind_req:
            return self.Unbind_req(*args)
        return super().request(command, *args, use_ieee=use_ieee)

    async def Node_Desc_req(self, nwk):
        """Node descriptor request."""
        res = await self._device._application._api.request(
            c.ZDO.NodeDescReq.Req(
                TSN=self._device._application.get_sequence(),
                NwkAddr=nwk
            )
        )
        if res.StatusCode != 0:
            return (res.StatusCode, None, None)

        return (zdo_t.Status.SUCCESS, None, res.NodeDesc)

    async def Simple_Desc_req(self, nwk, ep):
        """Request simple descriptor."""
        res = await self._device._application._api.request(
            c.ZDO.SimpleDescriptorReq.Req(
                TSN=self._device._application.get_sequence(),
                NwkAddr=nwk,
                Endpoint=ep
            )
        )
        if res.StatusCode != 0:
            return (res.StatusCode, None, None)

        desc = zdo_t.SimpleDescriptor(
            endpoint=res.SimpleDesc.endpoint,
            profile=res.SimpleDesc.profile,
            device_type=res.SimpleDesc.device_type,
            device_version=res.SimpleDesc.device_version,
            input_clusters=res.SimpleDesc.input_clusters,
            output_clusters=res.SimpleDesc.output_clusters,
        )

        return (zdo_t.Status.SUCCESS, None, desc)

    async def Active_EP_req(self, nwk):
        """Request active end points."""
        res = await self._device._application._api.request(
            c.ZDO.ActiveEpReq.Req(
                TSN=self._device._application.get_sequence(),
                NwkAddr=nwk
            )
        )
        if res.StatusCode != 0:
            return (res.StatusCode, None, None)

        return (zdo_t.Status.SUCCESS, None, res.ActiveEpList)

    async def Mgmt_Lqi_req(self, idx):
        """Request Link Quality Index."""
        res = await self._device._application._api.request(
            c.ZDO.MgmtLqi.Req(
                TSN=self._device._application.get_sequence(),
                DestNWK=self._device.nwk,
                Index=idx,
            )
        )
        if res.StatusCode != 0:
            return (res.StatusCode, None)

        return (res.StatusCode, res.Neighbors)

    async def Mgmt_Leave_req(self, ieee, flags):
        """Request device leaving the network."""
        res = await self._device._application._api.request(
            c.ZDO.MgtLeave.Req(
                TSN=self._device._application.get_sequence(),
                DestNWK=t.NWK(self._device._application.devices[ieee].nwk),
                IEEE=t.EUI64(ieee),
                Flags=t.uint8_t(flags),
            )
        )
        return res.StatusCode

    async def Mgmt_Permit_Joining_req(self, duration, tc_significance):
        """Request join permition."""
        res = await self._device._application._api.request(
            c.ZDO.PermitJoin.Req(
                TSN=self._device._application.get_sequence(),
                DestNWK=t.NWK(t.BroadcastAddress.RX_ON_WHEN_IDLE),
                PermitDuration=t.uint8_t(duration),
                TCSignificance=t.uint8_t(tc_significance),
            )
        )
        return res.StatusCode

    async def Mgmt_NWK_Update_req(self, nwkUpdate):
        """Request join permition."""
        res = await self._device._application._api.request(
            c.ZDO.MgmtNwkUpdate.Req(
                TSN=self._device._application.get_sequence(),
                ScanChannelMask=nwkUpdate.ScanChannels,
                ScanDuration=nwkUpdate.ScanDuration,
                ScanCount=nwkUpdate.ScanCount or 0,
                MgrAddr=self._device.nwk,
                DstNWK=t.NWK(0x0000),
            )
        )
        if res.StatusCode != 0:
            return (None, None, None, None, None)
        return (None, res.ScannedChannels, None, None, res.EnergyValues)

    async def zboss_specific_cmd(self, packet: t.ZigbeePacket) -> None:
        """Reroute ZDO packet sent over APSDE to custom ZBOSS ZDO commands."""
        try:
            zdo_hdr, zdo_args = self.deserialize(
                cluster_id=packet.cluster_id, data=packet.data.serialize()
            )
        except ValueError:
            LOGGER.debug("Could not parse ZDO message from packet")
            return

        if zdo_hdr.command_id == zdo_t.ZDOCmd.IEEE_addr_req:
            await self._IEEE_addr_req(packet, zdo_hdr, zdo_args)

    async def _IEEE_addr_req(
            self,
            packet: t.ZigbeePacket,
            zdo_hdr: zdo_t.ZDOHeader,
            zdo_args: tuple[Any]) -> None:
        """Send ZDO IEEE addr request and handle the response."""
        tsn = zdo_hdr.tsn
        nwki, req_type, index = zdo_args
        res = await self._api.request(
            c.ZDO.IeeeAddrReq.Req(
                TSN=tsn,
                DstNWK=packet.dst.address,
                NWKtoMatch=nwki,
                RequestType=req_type,
                StartIndex=index,
                )
        )

        if res.StatusCode:
            # ZDO command failed, use dummy values.
            ieee = t.EUI64([0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff])
            nwki = t.NWK(0xffff)
        else:
            ieee = res.RemoteDevIEEE
            nwki = res.RemoteDevNWK

        status = zdo_t.Status(res.StatusCode)
        data = tsn.serialize() \
            + status.serialize() \
            + ieee.serialize() \
            + nwki.serialize()

        packet = t.ZigbeePacket(
            src=t.AddrModeAddress(
                addr_mode=t.AddrMode.NWK,
                address=res.RemoteDevNWK,
            ),
            src_ep=0,
            dst=t.AddrModeAddress(
                addr_mode=t.AddrMode.NWK,
                address=self.state.node_info.nwk,
            ),
            dst_ep=0,
            tsn=tsn,
            profile_id=0,
            cluster_id=zdo_t.ZDOCmd.IEEE_addr_rsp,
            data=t.SerializableBytes(data),
            tx_options=t.TransmitOptions.NONE,
            lqi=None,
            rssi=None
        )
        self._device._application.packet_received(packet)


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
