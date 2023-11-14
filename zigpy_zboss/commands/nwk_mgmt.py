"""Module defining all NWK commands."""
import zigpy_zboss.types as t


class NWKCommandCode(t.enum16):
    """Enum class for NWK command_ids."""

    NWK_FORMATION = 0x0401
    NWK_DISCOVERY = 0x0402
    NWK_NLME_JOIN = 0x0403
    NWK_PERMIT_JOINING = 0x0404
    NWK_GET_IEEE_BY_SHORT = 0x0405
    NWK_GET_SHORT_BY_IEEE = 0x0406
    NWK_GET_NEIGHBOR_BY_IEEE = 0x0407
    NWK_REJOINED_IND = 0x0409
    NWK_REJOIN_FAILED_IND = 0x040a
    NWK_LEAVE_IND = 0x040b
    PIM_SET_FAST_POLL_INTERVAL = 0x040e
    PIM_SET_LONG_POLL_INTERVAL = 0x040f
    PIM_START_FAST_POLL = 0x0410
    PIM_START_LONG_POLL = 0x0411
    PIM_START_POLL = 0x0412
    PIM_STOP_FAST_POLL = 0x0414
    PIM_STOP_POLL = 0x0415
    PIM_ENABLE_TURBO_POLL = 0x0416
    PIM_DISABLE_TURBO_POLL = 0x0417
    NWK_PAN_ID_CONFLICT_RESOLVE = 0x041a
    NWK_PAN_ID_CONFLICT_IND = 0x041b
    NWK_ADDRESS_UPDATE_IND = 0x041c
    NWK_START_WITHOUT_FORMATION = 0x041d
    NWK_NLME_ROUTER_START = 0x041e
    PARENT_LOST_IND = 0x0420
    PIM_START_TURBO_POLL_PACKETS = 0x0424
    PIM_START_TURBO_POLL_CONTINUOUS = 0x0425
    PIM_TURBO_POLL_CONTINUOUS_LEAVE = 0x0426
    PIM_TURBO_POLL_PACKETS_LEAVE = 0x0427
    PIM_PERMIT_TURBO_POLL = 0x0428
    PIM_SET_FAST_POLL_TIMEOUT = 0x0429
    PIM_GET_LONG_POLL_INTERVAL = 0x042a
    PIM_GET_IN_FAST_POLL_FLAG = 0x042b
    SET_KEEPALIVE_MOVE = 0x042c
    START_CONCENTRATOR_MODE = 0x042d
    STOP_CONCENTRATOR_MODE = 0x042e
    NWK_ENABLE_PAN_ID_CONFLICT_RESOLUTION = 0x042f
    NWK_ENABLE_AUTO_PAN_ID_CONFLICT_RESOLUTION = 0x0430
    PIM_TURBO_POLL_CANCEL_PACKET = 0x0431


class NWK(t.CommandsBase):
    """Commands for network management.

    This category of the API enables to manage Network Layer at the NCP.
    """

    Formation = t.CommandDef(
        t.ControlType.REQ,
        NWKCommandCode.NWK_FORMATION,
        blocking=True,
        req_schema=(
            (
                t.Param("TSN", t.uint8_t, "Transmission Sequence Number"),
                t.Param(
                    "ChannelList",
                    t.ChannelEntryList,
                    "Array of ChannelListEntry structures."
                ),
                t.Param(
                    "ScanDuration",
                    t.uint8_t,
                    "The time spent scanning each channel is "
                    "(aBaseSuperframeDuration * (2^n + 1)) symbols, "
                    "n = ScanDuration parameter."
                ),
                t.Param(
                    "DistributedNetFlag",
                    t.uint8_t,
                    "If 0, create a Centralized network, device is ZC."
                    " If 1, create a Distributed network, device is ZR"
                ),
                t.Param(
                    "DistributedNetAddr",
                    t.NWK,
                    "The address the device will use when forming a "
                    "distributed network"
                ),
                t.Param(
                    "ExtPanId",
                    t.EUI64,
                    "The network extended PAN ID."
                ),
            )
        ),
        rsp_schema=t.STATUS_SCHEMA + (
            t.Param("NWKAddr", t.NWK, "NWK address"),
        ),
    )
    # Discovery = t.CommandDef(
    #     t.ControlType.REQ,
    #     NWKCommandCode.NWK_DISCOVERY,
    #     blocking=True,
    #     req_schema=(
    #         (
    #             t.Param("TSN", t.uint8_t, "Transmission Sequence Number"),
    #             t.Param(
    #                 "ChannelListLen",
    #                 t.uint8_t,
    #                 "Number of entries in the following Channel List array."
    #                 " Must be 1 for 2.4GHz-only build."
    #             ),
    #             t.Param(
    #                 "ChannelList",
    #                 ???,
    #                 "Array of ChannelListEntry structures."
    #             ),
    #             t.Param(
    #                 "ScanDuration",
    #                 t.uint8_t,
    #                 "The time spent scanning each channel is "
    #                 "(aBaseSuperframeDuration * (2^n + 1)) symbols, "
    #                 "n = ScanDuration parameter."
    #             ),
    #         )
    #     ),
    #     rsp_schema=t.STATUS_SCHEMA + (
    #         t.Param(
    #             "NetworkCount",
    #             t.uint8_t,
    #             "Length of Network descriptors array followed"
    #         ),
    #         t.Param("NetworkDesc", ???, "Array of Network descriptors"),
    #     ),
    # )
    PermitJoin = t.CommandDef(
        t.ControlType.REQ,
        NWKCommandCode.NWK_PERMIT_JOINING,
        blocking=True,
        req_schema=(
            (
                t.Param("TSN", t.uint8_t, "Transmission Sequence Number"),
                t.Param(
                    "PermitDuration",
                    t.uint8_t,
                    "Permit join duration, in seconds. 0 == 'disable',"
                    " 0xff == 0xfe"
                ),
            )
        ),
        rsp_schema=t.STATUS_SCHEMA,
    )
    NwkLeaveInd = t.CommandDef(
        t.ControlType.IND,
        NWKCommandCode.NWK_LEAVE_IND,
        rsp_schema=(
            t.Param("IEEE", t.EUI64, "IEEE address"),
            t.Param(
                "Rejoin", t.uint8_t, "0 - No rejoin, 1 - Rejoin requested"),
        ),
    )
    StartWithoutFormation = t.CommandDef(
        t.ControlType.REQ,
        NWKCommandCode.NWK_START_WITHOUT_FORMATION,
        req_schema=(
            (
                t.Param("TSN", t.uint8_t, "Transmission Sequence Number"),
            )
        ),
        rsp_schema=t.STATUS_SCHEMA,
    )
