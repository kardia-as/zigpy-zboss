"""Module defining all APS commands."""
import zigpy.types
import zigpy_zboss.types as t


class APSCommandCode(t.enum16):
    """Enum class for APS command_ids."""

    APSDE_DATA_REQ = 0x0301
    APSME_BIND = 0x0302
    APSME_UNBIND = 0x0303
    APSME_ADD_GROUP = 0x0304
    APSME_RM_GROUP = 0x0305
    APSDE_DATA_IND = 0x0306
    APSME_RM_ALL_GROUPS = 0x0307
    APS_CHECK_BINDING = 0x0308
    APS_GET_GROUP_TABLE = 0x0309
    APSME_UNBIND_ALL = 0x030a


class KeySrcAndAttr(t.bitmap8):
    """Enum class for key source."""

    KeySrc = 1 << 0
    KeyUsed = 3 << 1


class TransmitOptions(t.bitmap8):
    """Enum class for transmit options."""

    NONE = 0x00

    # Security enabled transmission
    SECURITY_ENABLED = 0x01
    # Obsolete
    OBSOLETE = 0x02
    # Acknowledged transmission
    ACK_ENABLED = 0x04
    # Fragmentation permitted
    FRAGMENTATION_PERMITED = 0x08
    # Include extended nonce in APS security frame.
    EXTENDED_NONCE_ENABLED = 0x10
    # Force mesh route discovery for this request.
    FORCE_ROUTE_DISCOVERY = 0x20
    # Send route record for this request.
    SEND_ROUTE_RECORD = 0x40


class APS(t.CommandsBase):
    """APS layer commands.

    This category of the API provides an access to the
    Application Support Sub-layer at the NCP
    """

    DataReq = t.CommandDef(
        t.ControlType.REQ,
        APSCommandCode.APSDE_DATA_REQ,
        req_schema=(
            t.Param("TSN", t.uint8_t, "Transmission Sequence Number",),
            t.Param(
                "ParamLength",
                t.uint8_t,
                "Length of parameters section (fixed as 21 bytes)"
            ),
            t.Param("DataLength", t.uint16_t, "Data section length"),
            t.Param(
                "DstAddr",
                t.EUI64,
                "Destination addr depending on dst addr mode. Always 8 bytes."
                " 2-bytes short address must be put into first 2 bytes"
            ),
            t.Param("ProfileID", t.uint16_t, "Profile ID"),
            t.Param("ClusterId", t.uint16_t, "Cluster ID"),
            t.Param("DstEndpoint", t.uint8_t, "Destination endpoint"),
            t.Param("SrcEndpoint", t.uint8_t, "Source endpoint"),
            t.Param("Radius", t.uint8_t, "Radius in hops"),
            t.Param(
                "DstAddrMode", zigpy.types.AddrMode, "Destination addr mode"),
            t.Param("TxOptions", TransmitOptions, "Tx Options bitmap"),
            t.Param(
                "UseAlias",
                t.uint8_t,
                "0 or 1. If 1, use alias src address, else local short address"
            ),
            t.Param(
                "AliasSrcAddr",
                t.uint16_t,
                "Alias source address. Ignored if use alias 0"
            ),
            t.Param(
                "AliasSeqNbr",
                t.uint8_t,
                "Alias sequence number. Ignored if use alias 0"
            ),
            t.Param("Payload", t.Payload, "data bytes array"),
        ),
        rsp_schema=t.STATUS_SCHEMA + (
            t.Param(
                "DstAddr",
                t.EUI64,
                "Destination addr depending on dst addr mode. Always 8 bytes."
                " 2-bytes short address must be put into first 2 bytes"
            ),
            t.Param("DstEndpoint", t.uint8_t, "Destination endpoint"),
            t.Param("SrcEndpoint", t.uint8_t, "Source endpoint"),
            t.Param("TxTime", t.uint32_t, "Transmit timestamp, ms"),
            t.Param(
                "DstAddrMode", zigpy.types.AddrMode, "Destination addr mode"),
        ),
    )
    Bind = t.CommandDef(
        t.ControlType.REQ,
        APSCommandCode.APSME_BIND,
        req_schema=(
            t.Param("TSN", t.uint8_t, "Transmission Sequence Number",),
            t.Param("SrcIEEE", t.EUI64, "IEEE address of the source device."),
            t.Param("SrcEndpoint", t.uint8_t, "Source endpoint number"),
            t.Param("ClusterId", t.uint16_t, "Cluster ID to bind"),
            t.Param("DstAddrMode", t.BindAddrMode, "Destination Addr Mode"),
            t.Param(
                "DstAddr",
                t.EUI64,
                "IEEE or NWK address of the destination device depending "
                "on address mode specified"
            ),
            t.Param("DstEndpoint", t.uint8_t, "Destination endpoint number"),
        ),
        rsp_schema=t.STATUS_SCHEMA + (
            t.Param("Idx", t.uint8_t, "Index of bind table entry"),
        ),
    )
    UnBind = t.CommandDef(
        t.ControlType.REQ,
        APSCommandCode.APSME_UNBIND,
        req_schema=(
            t.Param("TSN", t.uint8_t, "Transmission Sequence Number",),
            t.Param("SrcIEEE", t.EUI64, "IEEE address of the source device."),
            t.Param("SrcEndpoint", t.uint8_t, "Source endpoint number"),
            t.Param("ClusterId", t.uint16_t, "Cluster ID to bind"),
            t.Param("DstAddrMode", t.BindAddrMode, "Destination Addr Mode"),
            t.Param(
                "DstAddr",
                t.EUI64,
                "IEEE or NWK address of the destination device depending "
                "on address mode specified"
            ),
            t.Param("DstEndpoint", t.uint8_t, "Destination endpoint number"),
        ),
        rsp_schema=t.STATUS_SCHEMA
    )
    AddGroup = t.CommandDef(
        t.ControlType.REQ,
        APSCommandCode.APSME_ADD_GROUP,
        req_schema=(
            t.Param("TSN", t.uint8_t, "Transmission Sequence Number",),
            t.Param("GroupNWKAddr", t.NWK, "NWK address of the group"),
            t.Param("Endpoint", t.uint8_t, "Endpoint number"),
        ),
        rsp_schema=t.STATUS_SCHEMA,
    )
    RemoveGroup = t.CommandDef(
        t.ControlType.REQ,
        APSCommandCode.APSME_RM_GROUP,
        req_schema=(
            t.Param("TSN", t.uint8_t, "Transmission Sequence Number",),
            t.Param("GroupNWKAddr", t.NWK, "NWK address of the group"),
            t.Param("Endpoint", t.uint8_t, "Endpoint number"),
        ),
        rsp_schema=t.STATUS_SCHEMA,
    )
    DataIndication = t.CommandDef(
        t.ControlType.IND,
        APSCommandCode.APSDE_DATA_IND,
        rsp_schema=(
            t.Param(
                "ParamLength",
                t.uint8_t,
                "Length of parameters section (fixed as 21 bytes)"
            ),
            t.Param("PayloadLength", t.uint16_t, "Length of data"),
            t.Param("FrameFC", t.APSFrameFC, "Received APS frame FC field"),
            t.Param("SrcAddr", t.NWK, "Received frame source NWK address"),
            t.Param(
                "DstAddr", t.NWK, "Received frame destination NWK address"),
            t.Param(
                "GrpAddr",
                t.NWK,
                "Received frame APS group address "
                "(if frame is marked as Group addressed in FC)"
            ),
            t.Param("DstEndpoint", t.uint8_t, "Destination endpoint"),
            t.Param("SrcEndpoint", t.uint8_t, "Source endpoint"),
            t.Param("ClusterId", t.uint16_t, "Cluster ID"),
            t.Param("ProfileId", t.uint16_t, "Profile ID"),
            t.Param("PacketCounter", t.uint8_t, "APS packet counter"),
            t.Param(
                "SrcMACAddr",
                t.NWK,
                "Received frame last hop source MAC address"
            ),
            t.Param(
                "DstMACAddr",
                t.NWK,
                "Received frame last hop destination MAC address"
            ),
            t.Param("LQI", t.uint8_t, "Received frame LQI"),
            t.Param("RSSI", t.int8s, "Received frame RSSI"),
            t.Param(
                "KeySrcAndAttr",
                t.ApsAttributes,
                "Aps Key source and APS key used bitmap"
            ),
            t.Param("Payload", t.Payload, "data bytes array"),
        ),
    )
    RmAllGroups = t.CommandDef(
        t.ControlType.REQ,
        APSCommandCode.APSME_RM_ALL_GROUPS,
        req_schema=(
            t.Param("TSN", t.uint8_t, "Transmission Sequence Number"),
            t.Param("Endpoint", t.uint8_t, "Endpoint Number"),
        ),
        rsp_schema=t.STATUS_SCHEMA,
    )
    CheckBinding = t.CommandDef(
        t.ControlType.REQ,
        APSCommandCode.APS_CHECK_BINDING,
        blocking=True,
        req_schema=(
            t.Param("TSN", t.uint8_t, "Transmission Sequence Number"),
            t.Param("Endpoint", t.uint8_t, "Endpoint Number"),
            t.Param("ClusterId", t.uint16_t, "Cluster ID"),
        ),
        rsp_schema=t.STATUS_SCHEMA + (
            t.Param(
                "Exists",
                t.uint8_t,
                "flag indicating whether a binding exists"
            ),
        ),
    )
    GetGroupTable = t.CommandDef(
        t.ControlType.REQ,
        APSCommandCode.APS_GET_GROUP_TABLE,
        blocking=True,
        req_schema=(
            t.Param("TSN", t.uint8_t, "Transmission Sequence Number"),
        ),
        rsp_schema=t.STATUS_SCHEMA + (
            t.Param("GrpList", t.GrpList, "group list"),
        ),
    )
    UnbindAll = t.CommandDef(
        t.ControlType.REQ,
        APSCommandCode.APSME_UNBIND_ALL,
        blocking=True,
        req_schema=(
            t.Param("TSN", t.uint8_t, "Transmission Sequence Number"),
        ),
        rsp_schema=t.STATUS_SCHEMA
    )
