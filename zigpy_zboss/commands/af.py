"""Module defining all AF commands."""
import zigpy_zboss.types as t


class AFCommandCode(t.enum16):
    """Enum class for AF command_ids."""

    AF_SET_SIMPLE_DESC = 0x0101
    AF_DEL_SIMPLE_DESC = 0x0102
    AF_SET_NODE_DESC = 0x0103
    AF_SET_POWER_DESC = 0x0104


class AF(t.CommandsBase):
    """AF commands.

    This category of the API provides an access to the
    Application Framework part resided at the NCP.
    """

    SetSimpleDesc = t.CommandDef(
        t.ControlType.REQ,
        AFCommandCode.AF_SET_SIMPLE_DESC,
        blocking=True,
        req_schema=(
            t.Param("TSN", t.uint8_t, "Transmission Sequence Number"),
            t.Param("SimpleDesc", t.SimpleDescriptor, "Simple descriptor"),
        ),
        rsp_schema=t.STATUS_SCHEMA,
    )
    DelSimpleDesc = t.CommandDef(
        t.ControlType.REQ,
        AFCommandCode.AF_DEL_SIMPLE_DESC,
        req_schema=(
            t.Param("TSN", t.uint8_t, "Transmission Sequence Number"),
            t.Param(
                "Endpoint",
                t.uint8_t,
                "Endpoint number to delete simple descriptor for"
            ),
        ),
        rsp_schema=t.STATUS_SCHEMA,
    )
    SetNodeDesc = t.CommandDef(
        t.ControlType.REQ,
        AFCommandCode.AF_SET_NODE_DESC,
        req_schema=(
            t.Param("TSN", t.uint8_t, "Transmission Sequence Number"),
            t.Param(
                "DeviceType",
                t.DeviceRole,
                "Device type: 0 - ZC, 1 - ZR, 2 - ZED"
            ),
            t.Param("MACCap", t.MACCapability, "MAC Capabilities bitfield"),
            t.Param("ManufacturerCode", t.uint16_t, "Manufacturer code"),
        ),
        rsp_schema=t.STATUS_SCHEMA,
    )
    SetPowerDesc = t.CommandDef(
        t.ControlType.REQ,
        AFCommandCode.AF_SET_POWER_DESC,
        req_schema=(
            t.Param("TSN", t.uint8_t, "Transmission Sequence Number"),
            t.Param("CurrentMode", t.PowerMode, "Current power mode value"),
            t.Param(
                "AvailablePowerSrc",
                t.PowerSource,
                "Available power sources bits"
            ),
            t.Param(
                "CurrentPowerSrc", t.PowerSource, "Current power source bit"),
            t.Param(
                "CurrentPowerSrcLevel",
                t.PowerSourceLevel,
                "Current power source level value"
            ),
        ),
        rsp_schema=t.STATUS_SCHEMA,
    )
