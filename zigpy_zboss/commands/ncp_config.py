"""Module defining all NcpConfig commands."""
import zigpy_zboss.types as t


class NcpConfigCommandCode(t.enum16):
    """Enum class for NCP config command_ids."""

    GET_MODULE_VERSION = 0x0001
    NCP_RESET = 0x0002
    GET_ZIGBEE_ROLE = 0x0004
    SET_ZIGBEE_ROLE = 0x0005
    GET_ZIGBEE_CHANNEL_MASK = 0x0006
    SET_ZIGBEE_CHANNEL_MASK = 0x0007
    GET_ZIGBEE_CHANNEL = 0x0008
    GET_PAN_ID = 0x0009
    SET_PAN_ID = 0x000a
    GET_LOCAL_IEEE_ADDR = 0x000b
    SET_LOCAL_IEEE_ADDR = 0x000c
    GET_TX_POWER = 0x0010
    SET_TX_POWER = 0x0011
    GET_RX_ON_WHEN_IDLE = 0x0012
    SET_RX_ON_WHEN_IDLE = 0x0013
    GET_JOINED = 0x0014
    GET_AUTHENTICATED = 0x0015
    GET_ED_TIMEOUT = 0x0016
    SET_ED_TIMEOUT = 0x0017
    SET_NWK_KEY = 0x001b
    GET_NWK_KEYS = 0x001e
    GET_APS_KEY_BY_IEEE = 0x001f
    GET_PARENT_ADDRESS = 0x0022
    GET_EXTENDED_PAN_ID = 0x0023
    GET_COORDINATOR_VERSION = 0x0024
    GET_SHORT_ADDRESS = 0x0025
    GET_TRUST_CENTER_ADDRESS = 0x0026
    NCP_RESET_IND = 0x002b
    NVRAM_WRITE = 0x002e
    NVRAM_READ = 0x002f
    NVRAM_ERASE = 0x0030
    NVRAM_CLEAR = 0x0031
    SET_TC_POLICY = 0x0032
    SET_EXTENDED_PAN_ID = 0x0033
    SET_MAX_CHILDREN = 0x0034
    GET_MAX_CHILDREN = 0x0035


class NcpConfig(t.CommandsBase):
    """Ncp Config commands.

    This category of the API provides general configuration
    facilities of the NCP.
    """

    GetModuleVersion = t.CommandDef(
        t.ControlType.REQ,
        NcpConfigCommandCode.GET_MODULE_VERSION,
        req_schema=(
            t.Param("TSN", t.uint8_t, "Transmission Sequence Number"),
        ),
        rsp_schema=t.STATUS_SCHEMA + (
            t.Param("FWVersion", t.uint32_t, "NCP module firmware version"),
            t.Param("StackVersion", t.uint32_t, "NCP module stack version"),
            t.Param(
                "ProtocolVersion", t.uint32_t, "NCP module protocol version"),
        ),
    )
    NCPModuleReset = t.CommandDef(
        t.ControlType.REQ,
        NcpConfigCommandCode.NCP_RESET,
        req_schema=(
            t.Param("TSN", t.uint8_t, "Transmission Sequence Number"),
            t.Param("Option", t.ResetOptions, "Reset options"),
        ),
        rsp_schema=t.STATUS_SCHEMA,
    )
    GetZigbeeRole = t.CommandDef(
        t.ControlType.REQ,
        NcpConfigCommandCode.GET_ZIGBEE_ROLE,
        req_schema=(
            t.Param("TSN", t.uint8_t, "Transmission Sequence Number"),
        ),
        rsp_schema=t.STATUS_SCHEMA + (
            t.Param("DeviceRole", t.DeviceRole, "Zigbee device role"),
        ),
    )
    SetZigbeeRole = t.CommandDef(
        t.ControlType.REQ,
        NcpConfigCommandCode.SET_ZIGBEE_ROLE,
        req_schema=(
            t.Param("TSN", t.uint8_t, "Transmission Sequence Number"),
            t.Param("DeviceRole", t.DeviceRole, "Zigbee device role"),
        ),
        rsp_schema=t.STATUS_SCHEMA,
    )
    GetChannelMask = t.CommandDef(
        t.ControlType.REQ,
        NcpConfigCommandCode.GET_ZIGBEE_CHANNEL_MASK,
        req_schema=(
            t.Param("TSN", t.uint8_t, "Transmission Sequence Number"),
        ),
        rsp_schema=t.STATUS_SCHEMA + (
            t.Param(
                "ChannelList",
                t.ChannelEntryList,
                "Array of ChannelListEntry structures"
            ),
        ),
    )
    SetChannelMask = t.CommandDef(
        t.ControlType.REQ,
        NcpConfigCommandCode.SET_ZIGBEE_CHANNEL_MASK,
        req_schema=(
            t.Param("TSN", t.uint8_t, "Transmission Sequence Number"),
            t.Param("Page", t.uint8_t, "Channel page number"),
            t.Param("Mask", t.Channels, "Channel mask"),
        ),
        rsp_schema=t.STATUS_SCHEMA,
    )
    GetCurrentChannel = t.CommandDef(
        t.ControlType.REQ,
        NcpConfigCommandCode.GET_ZIGBEE_CHANNEL,
        req_schema=(
            t.Param("TSN", t.uint8_t, "Transmission Sequence Number"),
        ),
        rsp_schema=t.STATUS_SCHEMA + (
            t.Param("Page", t.uint8_t, "Channel page number"),
            t.Param("Channel", t.uint8_t, "Channel number"),
        ),
    )
    GetShortPANID = t.CommandDef(
        t.ControlType.REQ,
        NcpConfigCommandCode.GET_PAN_ID,
        req_schema=(
            t.Param("TSN", t.uint8_t, "Transmission Sequence Number"),
        ),
        rsp_schema=t.STATUS_SCHEMA + (
            t.Param("PANID", t.PanId, "Short PAN ID"),
        ),
    )
    SetShortPANID = t.CommandDef(
        t.ControlType.REQ,
        NcpConfigCommandCode.SET_PAN_ID,
        blocking=True,
        req_schema=(
            t.Param("TSN", t.uint8_t, "Transmission Sequence Number"),
            t.Param("PANID", t.PanId, "Short PAN ID"),
        ),
        rsp_schema=t.STATUS_SCHEMA,
    )
    GetLocalIEEE = t.CommandDef(
        t.ControlType.REQ,
        NcpConfigCommandCode.GET_LOCAL_IEEE_ADDR,
        req_schema=(
            t.Param("TSN", t.uint8_t, "Transmission Sequence Number"),
            t.Param("MacInterfaceNum", t.uint8_t, "Mac interface number"),
        ),
        rsp_schema=t.STATUS_SCHEMA + (
            t.Param("MacInterfaceNum", t.uint8_t, "Mac interface number"),
            t.Param("IEEE", t.EUI64, "IEEE address"),
        ),
    )
    SetLocalIEEE = t.CommandDef(
        t.ControlType.REQ,
        NcpConfigCommandCode.SET_LOCAL_IEEE_ADDR,
        req_schema=(
            t.Param("TSN", t.uint8_t, "Transmission Sequence Number"),
            t.Param("MacInterfaceNum", t.uint8_t, "Mac interface number"),
            t.Param("IEEE", t.EUI64, "IEEE address"),
        ),
        rsp_schema=t.STATUS_SCHEMA,
    )
    GetTransmitPower = t.CommandDef(
        t.ControlType.REQ,
        NcpConfigCommandCode.GET_TX_POWER,
        req_schema=(
            t.Param("TSN", t.uint8_t, "Transmission Sequence Number"),
        ),
        rsp_schema=t.STATUS_SCHEMA + (
            t.Param(
                "CurrentTxPower", t.int8s, "Current transmit power in dBm"),
        ),
    )
    SetTransmitPower = t.CommandDef(
        t.ControlType.REQ,
        NcpConfigCommandCode.SET_TX_POWER,
        req_schema=(
            t.Param("TSN", t.uint8_t, "Transmission Sequence Number"),
            t.Param(
                "RequiredTxPower",
                t.int8s,
                "Required transmitter power. In the range of -20..+20 dBm"
            ),
        ),
        rsp_schema=t.STATUS_SCHEMA + (
            t.Param(
                "ResultantTxPower",
                t.int8s,
                "If the required TX power is valid, "
                "returns the same value or the lowest possible"),
        ),
    )
    GetRxOnWhenIdle = t.CommandDef(
        t.ControlType.REQ,
        NcpConfigCommandCode.GET_RX_ON_WHEN_IDLE,
        req_schema=(
            t.Param("TSN", t.uint8_t, "Transmission Sequence Number"),
        ),
        rsp_schema=t.STATUS_SCHEMA + (
            t.Param(
                "RxOnWhenIdle",
                t.uint8_t,
                "Rx On When Idle PIB attribute value: 0 - False, 1 - True"
            ),
        ),
    )
    SetRxOnWhenIdle = t.CommandDef(
        t.ControlType.REQ,
        NcpConfigCommandCode.SET_RX_ON_WHEN_IDLE,
        req_schema=(
            t.Param("TSN", t.uint8_t, "Transmission Sequence Number"),
            t.Param(
                "RxOnWhenIdle",
                t.uint8_t,
                "Rx On When Idle PIB attribute value: 0 - False, 1 - True"
            ),
        ),
        rsp_schema=t.STATUS_SCHEMA,
    )
    GetJoinStatus = t.CommandDef(
        t.ControlType.REQ,
        NcpConfigCommandCode.GET_JOINED,
        req_schema=(
            t.Param("TSN", t.uint8_t, "Transmission Sequence Number"),
        ),
        rsp_schema=t.STATUS_SCHEMA + (
            t.Param(
                "Joined",
                t.uint8_t,
                "Bit 0: Device is joined 0 - False, 1 - True"
                "Bit 1: Parent is lost 0 - False, 1 - True"
            ),
        ),
    )
    GetAuthenticationStatus = t.CommandDef(
        t.ControlType.REQ,
        NcpConfigCommandCode.GET_AUTHENTICATED,
        req_schema=(
            t.Param("TSN", t.uint8_t, "Transmission Sequence Number"),
        ),
        rsp_schema=t.STATUS_SCHEMA + (
            t.Param(
                "Authenticated",
                t.uint8_t,
                "0 Device is not authenticated"
                "1 device is authenticated"
            ),
        ),
    )
    GetEDTimeout = t.CommandDef(
        t.ControlType.REQ,
        NcpConfigCommandCode.GET_ED_TIMEOUT,
        req_schema=(
            t.Param("TSN", t.uint8_t, "Transmission Sequence Number"),
        ),
        rsp_schema=t.STATUS_SCHEMA + (
            t.Param(
                "Timeout", t.TimeoutIndex, "0x00 - 10s otherwise 2^N minutes"),
        ),
    )
    SetEDTimeout = t.CommandDef(
        t.ControlType.REQ,
        NcpConfigCommandCode.SET_ED_TIMEOUT,
        req_schema=(
            t.Param("TSN", t.uint8_t, "Transmission Sequence Number"),
            t.Param(
                "Timeout", t.TimeoutIndex, "0x00 - 10s otherwise 2^N minutes"),
        ),
        rsp_schema=t.STATUS_SCHEMA,
    )
    SetNwkKey = t.CommandDef(
        t.ControlType.REQ,
        NcpConfigCommandCode.SET_NWK_KEY,
        req_schema=(
            t.Param("TSN", t.uint8_t, "Transmission Sequence Number"),
            t.Param("NwkKey", t.KeyData, "NWK Key"),
            t.Param("KeyNumber", t.uint8_t, "Number of NWK Key"),
        ),
        rsp_schema=t.STATUS_SCHEMA,
    )
    GetNwkKeys = t.CommandDef(
        t.ControlType.REQ,
        NcpConfigCommandCode.GET_NWK_KEYS,
        req_schema=(
            t.Param("TSN", t.uint8_t, "Transmission Sequence Number"),
        ),
        rsp_schema=t.STATUS_SCHEMA + (
            t.Param("NwkKey1", t.KeyData, "NWK Key"),
            t.Param("KeyNumber1", t.uint8_t, "Number of NWK Key"),
            t.Param("NwkKey2", t.KeyData, "NWK Key"),
            t.Param("KeyNumber2", t.uint8_t, "Number of NWK Key"),
            t.Param("NwkKey3", t.KeyData, "NWK Key"),
            t.Param("KeyNumber3", t.uint8_t, "Number of NWK Key"),
        ),
    )
    GetAPSKeyByIEEE = t.CommandDef(
        t.ControlType.REQ,
        NcpConfigCommandCode.GET_APS_KEY_BY_IEEE,
        req_schema=(
            t.Param("TSN", t.uint8_t, "Transmission Sequence Number"),
            t.Param("IEEE", t.EUI64, "IEEE address of remote device"),
        ),
        rsp_schema=t.STATUS_SCHEMA + (
            t.Param("APSKey", t.KeyData, "APS Key"),
        ),
    )
    GetParentAddr = t.CommandDef(
        t.ControlType.REQ,
        NcpConfigCommandCode.GET_PARENT_ADDRESS,
        blocking=True,
        req_schema=(
            t.Param("TSN", t.uint8_t, "Transmission Sequence Number"),
        ),
        rsp_schema=t.STATUS_SCHEMA + (
            t.Param("NWKParentAddr", t.NWK, "NWK PArent address"),
        ),
    )
    GetExtendedPANID = t.CommandDef(
        t.ControlType.REQ,
        NcpConfigCommandCode.GET_EXTENDED_PAN_ID,
        blocking=True,
        req_schema=(
            t.Param("TSN", t.uint8_t, "Transmission Sequence Number"),
        ),
        rsp_schema=t.STATUS_SCHEMA + (
            t.Param("ExtendedPANID", t.EUI64, "Extended PAN ID"),
        ),
    )
    GetCoordinatorVersion = t.CommandDef(
        t.ControlType.REQ,
        NcpConfigCommandCode.GET_COORDINATOR_VERSION,
        blocking=True,
        req_schema=(
            t.Param("TSN", t.uint8_t, "Transmission Sequence Number"),
        ),
        rsp_schema=t.STATUS_SCHEMA + (
            t.Param("CoordinatorVersion", t.uint8_t, "Coordinator version"),
        ),
    )
    GetShortAddr = t.CommandDef(
        t.ControlType.REQ,
        NcpConfigCommandCode.GET_SHORT_ADDRESS,
        blocking=True,
        req_schema=(
            t.Param("TSN", t.uint8_t, "Transmission Sequence Number"),
        ),
        rsp_schema=t.STATUS_SCHEMA + (
            t.Param("NWKAddr", t.NWK, "NWK address of the device"),
        ),
    )
    GetTrustCenterAddr = t.CommandDef(
        t.ControlType.REQ,
        NcpConfigCommandCode.GET_TRUST_CENTER_ADDRESS,
        blocking=True,
        req_schema=(
            t.Param("TSN", t.uint8_t, "Transmission Sequence Number"),
        ),
        rsp_schema=t.STATUS_SCHEMA + (
            t.Param("TCIEEE", t.EUI64, "TC IEEE address"),
        ),
    )
    DeviceResetIndication = t.CommandDef(
        t.ControlType.IND,
        NcpConfigCommandCode.NCP_RESET_IND,
        req_schema=None,
        rsp_schema=(
            t.Param(
                "ResetSrc",
                t.ResetSource,
                "Reset source which triggered reset"
            ),
        ),
    )
    WriteNVRAM = t.CommandDef(
        t.ControlType.REQ,
        NcpConfigCommandCode.NVRAM_WRITE,
        blocking=True,
        req_schema=(
            t.Param("TSN", t.uint8_t, "Transmission Sequence Number"),
            t.Param(
                "DatasetCnt",
                t.uint8_t,
                "A number of datasets contained in this request"
            ),
            t.Param("DatasetId", t.DatasetId, "Requested dataset type"),
            t.Param("Version", t.uint16_t, "Requested dataset type"),
            t.Param("Dataset", t.NVRAMDataset, "Data bytes array"),
        ),
        rsp_schema=t.STATUS_SCHEMA,
    )
    ReadNVRAM = t.CommandDef(
        t.ControlType.REQ,
        NcpConfigCommandCode.NVRAM_READ,
        blocking=True,
        req_schema=(
            t.Param("TSN", t.uint8_t, "Transmission Sequence Number"),
            t.Param("DatasetId", t.uint16_t, "A dataset type to read"),
        ),
        rsp_schema=t.STATUS_SCHEMA + (
            t.Param("NVRAMVersion", t.uint16_t, "Current NVRAM version"),
            t.Param("DatasetId", t.DatasetId, "Requested dataset type"),
            t.Param("DatasetVersion", t.uint16_t, "Current dataset version"),
            t.Param("Dataset", t.NVRAMDataset, "Data bytes array"),
        ),
    )
    EraseNVRAM = t.CommandDef(
        t.ControlType.REQ,
        NcpConfigCommandCode.NVRAM_ERASE,
        blocking=True,
        req_schema=(
            t.Param("TSN", t.uint8_t, "Transmission Sequence Number"),
        ),
        rsp_schema=t.STATUS_SCHEMA,
    )
    ClearNVRAM = t.CommandDef(
        t.ControlType.REQ,
        NcpConfigCommandCode.NVRAM_CLEAR,
        blocking=True,
        req_schema=(
            t.Param("TSN", t.uint8_t, "Transmission Sequence Number"),
        ),
        rsp_schema=t.STATUS_SCHEMA,
    )
    SetTCPolicy = t.CommandDef(
        t.ControlType.REQ,
        NcpConfigCommandCode.SET_TC_POLICY,
        blocking=True,
        req_schema=(
            t.Param("TSN", t.uint8_t, "Transmission Sequence Number"),
            t.Param("PolicyType", t.PolicyType, "A policy type to set"),
            t.Param("PolicyValue", t.uint8_t, "A policy value to set"),
        ),
        rsp_schema=t.STATUS_SCHEMA,
    )
    SetExtendedPANID = t.CommandDef(
        t.ControlType.REQ,
        NcpConfigCommandCode.SET_EXTENDED_PAN_ID,
        blocking=True,
        req_schema=(
            t.Param("TSN", t.uint8_t, "Transmission Sequence Number"),
            t.Param("ExtendedPANID", t.EUI64, "Extended PAN ID to set"),
        ),
        rsp_schema=t.STATUS_SCHEMA,
    )
    SetMaxChildren = t.CommandDef(
        t.ControlType.REQ,
        NcpConfigCommandCode.SET_MAX_CHILDREN,
        blocking=True,
        req_schema=(
            t.Param("TSN", t.uint8_t, "Transmission Sequence Number"),
            t.Param(
                "ChildrenNbr",
                t.uint8_t,
                "Number of children to set as a maximum allowed"
            ),
        ),
        rsp_schema=t.STATUS_SCHEMA,
    )
    GetMaxChildren = t.CommandDef(
        t.ControlType.REQ,
        NcpConfigCommandCode.GET_MAX_CHILDREN,
        blocking=True,
        req_schema=(
            t.Param("TSN", t.uint8_t, "Transmission Sequence Number"),
        ),
        rsp_schema=t.STATUS_SCHEMA + (
            t.Param(
                "ChildrenNbr",
                t.uint8_t,
                "The maximum number of children currently allowed"
            ),
        ),
    )
