"""Module defining all ZDO commands."""
from __future__ import annotations
from zigpy.zdo import types as zdo_t

import zigpy.types
import zigpy.zdo.types

import zigpy_zboss.types as t


class ZdoCommandCode(t.enum16):
    """Enum class for ZDO command_ids."""

    ZDO_NWK_ADDR_REQ = 0x0201
    ZDO_IEEE_ADDR_REQ = 0x0202
    ZDO_POWER_DESC_REQ = 0x0203
    ZDO_NODE_DESC_REQ = 0x0204
    ZDO_SIMPLE_DESC_REQ = 0x0205
    ZDO_ACTIVE_EP_REQ = 0x0206
    ZDO_MATCH_DESC_REQ = 0x0207
    ZDO_BIND_REQ = 0x0208
    ZDO_UNBIND_REQ = 0x0209
    ZDO_MGMT_LEAVE_REQ = 0x020a
    ZDO_PERMIT_JOINING_REQ = 0x020b
    ZDO_DEV_ANNCE_IND = 0x020c
    ZDO_REJOIN = 0x020d
    ZDO_SYSTEM_SRV_DISCOVERY_REQ = 0x020e
    ZDO_MGMT_BIND_REQ = 0x020f
    ZDO_MGMT_LQI_REQ = 0x0210
    ZDO_MGMT_NWK_UPDATE_REQ = 0x0211
    ZDO_GET_STATS = 0x0213
    ZDO_DEV_AUTHORIZED_IND = 0x0214
    ZDO_DEV_UPDATE_IND = 0x0215
    ZDO_SET_NODE_DESC_MANUF_CODE = 0x0216


class EnergyValues(t.LVList, item_type=t.uint8_t, length_type=t.uint8_t):
    """List of enery values."""


class NWKArray(t.CompleteList, item_type=t.NWK):
    """List of nwk addresses."""


class AddrRequestType(t.enum8):
    """Enum class for address request type."""

    SINGLE = 0x00
    EXTENDED = 0x01


class ZDO(t.CommandsBase):
    """Commands accessing ZDO.

    This category of the API provides an access to the Zigbee Device Object
    resided at the NCP.
    """

    NwkAddrReq = t.CommandDef(
        t.ControlType.REQ,
        ZdoCommandCode.ZDO_NWK_ADDR_REQ,
        blocking=True,
        req_schema=(
            t.Param("TSN", t.uint8_t, "Transmission Sequence Number"),
            t.Param(
                "DstNWK",
                t.NWK,
                "NWK address of the remote device to send request to",
            ),
            t.Param(
                "IEEE",
                t.EUI64,
                "IEEE address to be matched by the remote device",
            ),
            t.Param(
                "RequestType",
                AddrRequestType,
                "0x00 -- single device request, 0x01 -- Extended",
            ),
            t.Param(
                "StartIndex",
                t.int8s,
                "Starting index of the returned associated device list."
                "Valid only if the Request type is Extended response"
            ),
        ),
        rsp_schema=t.STATUS_SCHEMA + (
            t.Param(
                "RemoteDevIEEE",
                t.EUI64,
                "IEEE address of the matched remote device"
            ),
            t.Param(
                "RemoteDevNWK",
                t.NWK,
                "NWK address of the matched remote device"
            ),
            t.Param(
                "NumAssocDev",
                t.uint8_t,
                "Number of associated devices in the following address list."
                " Present only if Request type parameter of the request is "
                "Extended response"
            ),
            t.Param(
                "StartIndex",
                t.uint8_t,
                "Starting index of the returned associated device the list. "
                "Present only if the Request type is Extended response and "
                "Num Assoc Dev is not 0"
            ),
            t.Param(
                "AssocDevNWKList",
                NWKArray,
                "Variable-size array of NWK addresses of devices associated "
                "with the remote device. Present only if the Request type is "
                "Extended response and Num Assoc Dev is not 0"
            ),
        ),
    )
    IeeeAddrReq = t.CommandDef(
        t.ControlType.REQ,
        ZdoCommandCode.ZDO_IEEE_ADDR_REQ,
        blocking=True,
        req_schema=(
            t.Param("TSN", t.uint8_t, "Transmission Sequence Number"),
            t.Param(
                "DstNWK",
                t.NWK,
                "NWK address of the remote device to send request to",
            ),
            t.Param(
                "NWKtoMatch",
                t.NWK,
                "NWK address to be matched by the remote device",
            ),
            t.Param(
                "RequestType",
                t.uint8_t,
                "0x00 -- single device request, 0x01 -- Extended",
            ),
            t.Param(
                "StartIndex",
                t.int8s,
                "Starting index of the returned associated device list."
                "Valid only if the Request type is Extended response"
            ),
        ),
        rsp_schema=t.STATUS_SCHEMA + (
            t.Param(
                "RemoteDevIEEE",
                t.EUI64,
                "IEEE address of the matched remote device"
            ),
            t.Param(
                "RemoteDevNWK",
                t.NWK,
                "NWK address of the matched remote device"
            ),
            t.Param(
                "NumAssocDev",
                t.uint8_t,
                "Number of associated devices in the following address list."
                " Present only if Request type parameter of the request is "
                "Extended response",
                optional=True,
            ),
            t.Param(
                "StartIndex",
                t.uint8_t,
                "Starting index of the returned associated device the list. "
                "Present only if the Request type is Extended response and "
                "Num Assoc Dev is not 0",
                optional=True,
            ),
            t.Param(
                "AssocDevNWKList",
                NWKArray,
                "Variable-size array of NWK addresses of devices associated "
                "with the remote device. Present only if the Request type is "
                "Extended response and Num Assoc Dev is not 0",
                optional=True,
            ),
        ),
    )
    PowerDesc = t.CommandDef(
        t.ControlType.REQ,
        ZdoCommandCode.ZDO_POWER_DESC_REQ,
        blocking=True,
        req_schema=(
            t.Param("TSN", t.uint8_t, "Transmission Sequence Number"),
            t.Param(
                "NWK",
                t.NWK,
                "NWK address to be matched by the remote device",
            ),
        ),
        rsp_schema=t.STATUS_SCHEMA + (
            t.Param(
                "PowerDesc",
                zigpy.zdo.types.PowerDescriptor,
                "Power Descriptor Bit Fields"
            ),
            t.Param("SrcNWK", t.NWK, "NWK address of source device"),
        ),
    )
    MgtLeave = t.CommandDef(
        t.ControlType.REQ,
        ZdoCommandCode.ZDO_MGMT_LEAVE_REQ,
        blocking=True,
        req_schema=(
            t.Param("TSN", t.uint8_t, "Transmission Sequence Number"),
            t.Param(
                "DestNWK",
                t.NWK,
                "NWK address of the remote device to send the request to",
            ),
            t.Param(
                "IEEE",
                t.EUI64,
                "IEEE address of the device to be removed from the network.",
            ),
            t.Param("Flags", t.uint8_t, "Leave flags bitfield",),
        ),
        rsp_schema=t.STATUS_SCHEMA,
    )
    PermitJoin = t.CommandDef(
        t.ControlType.REQ,
        ZdoCommandCode.ZDO_PERMIT_JOINING_REQ,
        blocking=True,
        req_schema=(
            t.Param("TSN", t.uint8_t, "Transmission Sequence Number"),
            t.Param(
                "DestNWK",
                t.NWK,
                "NWK address of the remote device to send the request to",
            ),
            t.Param(
                "PermitDuration",
                t.uint8_t,
                "The length of time in seconds during which the ZigBee "
                "coordinator or router will allow associations. The value"
                " 0x00 and 0xff indicate that permission is disabled or "
                "enabled, respectively, without a specified time limit",
            ),
            t.Param(
                "TCSignificance",
                t.uint8_t,
                "Trust center significance",
            ),
        ),
        rsp_schema=t.STATUS_SCHEMA,
    )
    DevAnnceInd = t.CommandDef(
        t.ControlType.IND,
        ZdoCommandCode.ZDO_DEV_ANNCE_IND,
        rsp_schema=(
            t.Param("NWK", t.NWK, "Short address of the joined device"),
            t.Param("IEEE", t.EUI64, "IEEE address of the joined device."),
            t.Param(
                "MacCap", t.uint8_t, "MAC Capabilities of the joined device"),
        ),
    )
    SetNodeDescManCode = t.CommandDef(
        t.ControlType.REQ,
        ZdoCommandCode.ZDO_SET_NODE_DESC_MANUF_CODE,
        blocking=True,
        req_schema=(
            t.Param("TSN", t.uint8_t, "Transmission Sequence Number"),
            t.Param("ManCode", t.uint16_t, "Manufacturer code to set"),
        ),
        rsp_schema=t.STATUS_SCHEMA,
    )
    NodeDescReq = t.CommandDef(
        t.ControlType.REQ,
        ZdoCommandCode.ZDO_NODE_DESC_REQ,
        blocking=True,
        req_schema=(
            t.Param("TSN", t.uint8_t, "Transmission Sequence Number"),
            t.Param("NwkAddr", t.NWK, "Network address of interest"),
        ),
        rsp_schema=t.STATUS_SCHEMA + (
            t.Param("NodeDesc", zdo_t.NodeDescriptor, "Node descriptor"),
            t.Param("NwkAddr", t.NWK, "Network address of source device"),
        ),
    )
    ActiveEpReq = t.CommandDef(
        t.ControlType.REQ,
        ZdoCommandCode.ZDO_ACTIVE_EP_REQ,
        blocking=True,
        req_schema=(
            t.Param("TSN", t.uint8_t, "Transmission Sequence Number"),
            t.Param("NwkAddr", t.NWK, "Network address of interest"),
        ),
        rsp_schema=t.STATUS_SCHEMA + (
            t.Param(
                "ActiveEpList",
                zigpy.types.LVBytes,
                "Active enpoints list"
            ),
            t.Param("NwkAddr", t.NWK, "Network address of source device"),
        ),
    )
    MatchDescReq = t.CommandDef(
        t.ControlType.REQ,
        ZdoCommandCode.ZDO_MATCH_DESC_REQ,
        blocking=False,
        req_schema=(
            t.Param("TSN", t.uint8_t, "Transmission Sequence Number"),
            t.Param("NwkAddr", t.NWK, "Network address of interest"),
            t.Param("ProfileId", t.uint16_t, "ID of the profile of interest"),
            t.Param(
                "InClusterCnt",
                t.uint8_t,
                "Count of Input cluster IDs in the following list"
            ),
            t.Param(
                "OutClusterCnt",
                t.uint8_t,
                "Count of Output cluster IDs in the following list"
            ),
            t.Param(
                "InClusterList",
                t.List[t.uint16_t],
                "Network address of interest"
            ),
            t.Param(
                "OutClusterList",
                t.List[t.uint16_t],
                "Network address of interest"
            ),
        ),
        rsp_schema=t.STATUS_SCHEMA + (
            t.Param(
                "ActiveEpList",
                zigpy.types.LVBytes,
                "Active enpoints list"
            ),
            t.Param("NwkAddr", t.NWK, "Network address of source device"),
        ),
    )
    SimpleDescriptorReq = t.CommandDef(
        t.ControlType.REQ,
        ZdoCommandCode.ZDO_SIMPLE_DESC_REQ,
        blocking=True,
        req_schema=(
            t.Param("TSN", t.uint8_t, "Transmission Sequence Number"),
            t.Param("NwkAddr", t.NWK, "Network address of interest"),
            t.Param("Endpoint", t.uint8_t, "Endpoint of interest"),
        ),
        rsp_schema=t.STATUS_SCHEMA + (
            t.Param("SimpleDesc", t.SimpleDescriptor, "Simple descriptor"),
            t.Param("NwkAddr", t.NWK, "Network address of source device"),
        ),
    )
    BindReq = t.CommandDef(
        t.ControlType.REQ,
        ZdoCommandCode.ZDO_BIND_REQ,
        blocking=True,
        req_schema=(
            t.Param("TSN", t.uint8_t, "Transmission Sequence Number"),
            t.Param(
                "TargetNwkAddr",
                t.NWK,
                "NWK address of the remote device to send the request to"),
            t.Param("SrcIEEE", t.EUI64, "IEEE address of the source device."),
            t.Param("SrcEndpoint", t.uint8_t, "Source endpoint"),
            t.Param("ClusterId", t.uint16_t, "Cluster ID to bind"),
            t.Param("DstAddrMode", t.BindAddrMode, "Destination addr mode"),
            t.Param(
                "DstAddr",
                t.EUI64,
                "Destination addr depending on dst addr mode. Always 8 bytes."
                " 2-bytes short address must be put into first 2 bytes"
            ),
            t.Param(
                "DstEndpoint",
                t.uint8_t,
                "Destination endpoint number. Shall be set to 0, "
                "if Destination Address Mode isn't 0x03."),
        ),
        rsp_schema=t.STATUS_SCHEMA
    )
    UnbindReq = t.CommandDef(
        t.ControlType.REQ,
        ZdoCommandCode.ZDO_UNBIND_REQ,
        blocking=True,
        req_schema=(
            t.Param("TSN", t.uint8_t, "Transmission Sequence Number"),
            t.Param(
                "TargetNwkAddr",
                t.NWK,
                "NWK address of the remote device to send the request to"),
            t.Param("SrcIEEE", t.EUI64, "IEEE address of the source device."),
            t.Param("SrcEndpoint", t.uint8_t, "Source endpoint"),
            t.Param("ClusterId", t.uint16_t, "Cluster ID to unbind"),
            t.Param("DstAddrMode", t.BindAddrMode, "Destination addr mode"),
            t.Param(
                "DstAddr",
                t.EUI64,
                "Destination addr depending on dst addr mode. Always 8 bytes."
                " 2-bytes short address must be put into first 2 bytes"
            ),
            t.Param(
                "DstEndpoint",
                t.uint8_t,
                "Destination endpoint number. Shall be set to 0, "
                "if Destination Address Mode isn't 0x03."),
        ),
        rsp_schema=t.STATUS_SCHEMA
    )
    MgmtLqi = t.CommandDef(
        t.ControlType.REQ,
        ZdoCommandCode.ZDO_MGMT_LQI_REQ,
        blocking=True,
        req_schema=(
            t.Param("TSN", t.uint8_t, "Transmission Sequence Number"),
            t.Param(
                "DestNWK",
                t.NWK,
                "The address of the device to send a request to"
            ),
            t.Param("Index", t.uint8_t, "Start entry index"),
        ),
        rsp_schema=t.STATUS_SCHEMA + (
            t.Param("Neighbors", zdo_t.Neighbors, "Neighbors"),
        ),
    )
    MgmtNwkUpdate = t.CommandDef(
        t.ControlType.REQ,
        ZdoCommandCode.ZDO_MGMT_NWK_UPDATE_REQ,
        blocking=True,
        req_schema=(
            t.Param("TSN", t.uint8_t, "Transmission Sequence Number"),
            t.Param("ScanChannelMask", t.Channels, "Scan channel mask"),
            t.Param("ScanDuration", t.uint8_t, "Scan duration"),
            t.Param(
                "ScanCount",
                t.uint8_t,
                "the number of energy scans to be conducted and reported"
            ),
            t.Param(
                "MgrAddr", t.NWK, "the NWK address of the network manager"),
            t.Param(
                "DstNWK",
                t.NWK,
                "the address of the device to send a request to"
            ),
        ),
        rsp_schema=t.STATUS_SCHEMA + (
            t.Param("ScannedChannels", t.Channels, ""),
            t.Param("TotalTransmissions", t.uint16_t, ""),
            t.Param("TransmissionFailures", t.uint16_t, ""),
            t.Param("EnergyValues", EnergyValues, ""),
        ),
    )
    DevUpdateInd = t.CommandDef(
        t.ControlType.IND,
        ZdoCommandCode.ZDO_DEV_UPDATE_IND,
        rsp_schema=(
            t.Param("IEEE", t.EUI64, "the IEEE address of the joined device"),
            t.Param("Nwk", t.NWK, "the NWK address of the joined device"),
            t.Param(
                "Status", t.DeviceUpdateStatus, "Device Update Status Code"),
        ),
    )
