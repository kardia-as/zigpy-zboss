"""Module defining all Security commands."""
import zigpy_zboss.types as t


class SecurityCommandCode(t.enum16):
    """Enum class for Security command_ids."""

    SECUR_SET_LOCAL_IC = 0x0501
    SECUR_ADD_IC = 0x0502
    SECUR_DEL_IC = 0x0503
    SECUR_GET_LOCAL_IC = 0x050d
    SECUR_TCLK_IND = 0x050e
    SECUR_TCLK_EXCHANGE_FAILED_IND = 0x050f
    SECUR_NWK_INITIATE_KEY_SWITCH_PROCEDURE = 0x0517
    SECUR_GET_IC_LIST = 0x0518
    SECUR_GET_IC_BY_IDX = 0x0519
    SECUR_REMOVE_ALL_IC = 0x051a


class SEC(t.CommandsBase):
    """SEC commands."""

    # SetLocalDeviceInstallcode = t.CommandDef(
    #     t.ControlType.REQ,
    #     SecurityCommandCode.SECUR_SET_LOCAL_IC,
    #     req_schema=(
    #         t.Param("TSN", t.uint8_t, "Transmission Sequence Number"),
    #         t.Param(
    #             "InstallCode",
    #             ???,
    #             "Installcode, including trailing 2 bytes of CRC",
    #         ),
    #     ),
    #     rsp_schema=t.STATUS_SCHEMA,
    # )
    # AddInstallcode = t.CommandDef(
    #     t.ControlType.REQ,
    #     SecurityCommandCode.SECUR_ADD_IC,
    #     req_schema=(
    #         t.Param("TSN", t.uint8_t, "Transmission Sequence Number"),
    #         t.Param("IEEE", t.EUI64, "IEEE address of the remote device"),
    #         t.Param(
    #             "InstallCode",
    #             ???,
    #             "Installcode, including trailing 2 bytes of CRC",
    #         ),
    #     ),
    #     rsp_schema=t.STATUS_SCHEMA,
    # )
    DeleteInstallcode = t.CommandDef(
        t.ControlType.REQ,
        SecurityCommandCode.SECUR_DEL_IC,
        req_schema=(
            t.Param("TSN", t.uint8_t, "Transmission Sequence Number"),
            t.Param("IEEE", t.EUI64, "IEEE address of the remote device"),
        ),
        rsp_schema=t.STATUS_SCHEMA,
    )
    # GetLocalInstallcode = t.CommandDef(
    #     t.ControlType.REQ,
    #     SecurityCommandCode.SECUR_GET_LOCAL_IC,
    #     req_schema=(
    #         t.Param("TSN", t.uint8_t, "Transmission Sequence Number"),
    #     ),
    #     rsp_schema=t.STATUS_SCHEMA + (
    #         t.Param(
    #             "InstallCode",
    #             ???,
    #             "Installcode, including trailing 2 bytes of CRC",
    #         ),
    #     ),
    # )
    TCLKIndication = t.CommandDef(
        t.ControlType.IND,
        SecurityCommandCode.SECUR_TCLK_IND,
        req_schema=None,
        rsp_schema=(
            t.Param("TCAddr", t.EUI64, "Trust Center Address"),
            t.Param("KeyType", t.uint8_t, "Key type"),
        ),
    )
    TCLKExchangeFailedIndication = t.CommandDef(
        t.ControlType.IND,
        SecurityCommandCode.SECUR_TCLK_EXCHANGE_FAILED_IND,
        req_schema=None,
        rsp_schema=(
            t.Param("StatusCat", t.uint8_t, "Status category"),
            t.Param("StatusCode", t.uint8_t, "Status code"),
        ),
    )
    InitKeySwitchProcedure = t.CommandDef(
        t.ControlType.REQ,
        SecurityCommandCode.SECUR_NWK_INITIATE_KEY_SWITCH_PROCEDURE,
        req_schema=(
            t.Param("TSN", t.uint8_t, "Transmission Sequence Number"),
        ),
        rsp_schema=t.STATUS_SCHEMA,
    )
    # GetICList = t.CommandDef(
    #     t.ControlType.REQ,
    #     SecurityCommandCode.SECUR_GET_IC_LIST,
    #     req_schema=(
    #         t.Param("TSN", t.uint8_t, "Transmission Sequence Number"),
    #         t.Param(
    #             "StartIdx",
    #             t.uint8_t,
    #             "SoC will return IC Table entries starting with this index"
    #         ),
    #     ),
    #     rsp_schema=t.STATUS_SCHEMA + (
    #         t.Param(
    #             "ICTableSize",
    #             t.uint8_t,
    #             "The total number of entries in the IC table"
    #         ),
    #         t.Param("StartIdx", t.uint8_t, "Start index"),
    #         t.Param(
    #             "EntryCount",
    #             t.uint8_t,
    #             "The number of entries in this response"
    #         ),
    #         t.Param(
    #             "Entries",
    #             ???,
    #             "Array containing IC entries"
    #         ),
    #     ),
    # )
    # GetICbyIdx = t.CommandDef(
    #     t.ControlType.REQ,
    #     SecurityCommandCode.SECUR_GET_IC_BY_IDX,
    #     req_schema=(
    #         t.Param("TSN", t.uint8_t, "Transmission Sequence Number"),
    #         t.Param(
    #             "ICEntryIdx",
    #             t.uint8_t,
    #             "the index of the entry to get"
    #         ),
    #     ),
    #     rsp_schema=t.STATUS_SCHEMA + (
    #         t.Param(
    #             "Entry",
    #             ???,
    #             "Array containing IC entries"
    #         ),
    #     ),
    # )
    RemoveAllIC = t.CommandDef(
        t.ControlType.REQ,
        SecurityCommandCode.SECUR_REMOVE_ALL_IC,
        req_schema=(
            t.Param("TSN", t.uint8_t, "Transmission Sequence Number"),
        ),
        rsp_schema=t.STATUS_SCHEMA,
    )
