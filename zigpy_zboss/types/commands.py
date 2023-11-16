"""Module defining types used for commands."""
from __future__ import annotations
import enum
import logging
import dataclasses

import zigpy.zdo.types

import zigpy_zboss.types as t

LOGGER = logging.getLogger(__name__)
TYPE_ZBOSS_NCP_API_HL = t.uint8_t(0x06)


class ControlType(t.enum8):
    """Control Type."""

    REQ = 0x00
    RSP = 0x01
    IND = 0x02


class StatusCategory(t.enum8):
    """Status Category."""

    GENERIC = 0
    MAC = 2
    NWK = 3
    APS = 4
    ZDO = 5
    CBKE = 6


class StatusCodeGeneric(t.enum8):
    """Status Code for the Generic category."""

    OK = 0
    ERROR = 1
    BLOCKED = 2
    EXIT = 3
    BUSY = 4
    EOF = 5
    OUT_OF_RANGE = 6
    EMPTY = 7
    CANCELLED = 8
    INVALID_PARAMETER_1 = 10
    INVALID_PARAMETER_2 = 11
    INVALID_PARAMETER_3 = 12
    INVALID_PARAMETER_4 = 13
    INVALID_PARAMETER_5 = 14
    INVALID_PARAMETER_6 = 15
    INVALID_PARAMETER_7 = 16
    INVALID_PARAMETER_8 = 17
    INVALID_PARAMETER_9 = 18
    INVALID_PARAMETER_10 = 19
    INVALID_PARAMETER_11_OR_MORE = 20
    PENDING = 21
    NO_MEMORY = 22
    INVALID_PARAMETER = 23
    OPERATION_FAILED = 24
    BUFFER_TOO_SMALL = 25
    END_OF_LIST = 26
    ALREADY_EXISTS = 27
    NOT_FOUND = 28
    OVERFLOW = 29
    TIMEOUT = 30
    NOT_IMPLEMENTED = 31
    NO_RESOURCES = 32
    UNINITIALIZED = 33
    NO_SERVER = 34
    INVALID_STATE = 35
    CONNECTION_FAILED = 37
    CONNECTION_LOST = 38
    UNAUTHORIZED = 40
    CONFLICT = 41
    INVALID_FORMAT = 42
    NO_MATCH = 43
    PROTOCOL_ERROR = 44
    VERSION = 45
    MALFORMED_ADDRESS = 46
    COULD_NOT_READ_FILE = 47
    FILE_NOT_FOUND = 48
    DIRECTORY_NOT_FOUND = 49
    CONVERSION_ERROR = 50
    INCOMPATIBLE_TYPES = 51
    FILE_CORRUPTED = 56
    PAGE_NOT_FOUND = 57
    ILLEGAL_REQUEST = 62
    INVALID_GROUP = 64
    TABLE_FULL = 65
    IGNORE = 69
    AGAIN = 70
    DEVICE_NOT_FOUND = 71
    OBSOLETE = 72


class StatusCodeAPS(t.enum8):
    """Status Code for the APS category."""

    # A request has been executed successfully.
    SUCCESS = 0x00
    # A transmit request failed since the ASDU is too large and fragmentation
    # is not supported.
    ASDU_TOO_LONG = 0xa0
    # A received fragmented frame could not be defragmented at the current
    # time.
    DEFRAG_DEFERRED = 0xa1
    # A received fragmented frame could not be defragmented since the device
    # does not support fragmentation.
    DEFRAG_UNSUPPORTED = 0xa2
    # A parameter value was out of range.
    ILLEGAL_REQUEST = 0xa3
    # An APSME-UNBIND.request failed due to the requested binding link not
    # existing in the binding table.
    INVALID_BINDING = 0xa4
    # An APSME-REMOVE-GROUP.request has been issued with a group identifier
    # that does not appear in the group table.
    INVALID_GROUP = 0xa5
    # A parameter value was invalid or out of range.
    INVALID_PARAMETER = 0xa6
    # An APSDE-DATA.request requesting acknowledged trans- mission failed due
    # to no acknowledgement being received.
    NO_ACK = 0xa7
    # An APSDE-DATA.request with a destination addressing mode set to 0x00
    # failed due to there being no devices bound to this device.
    NO_BOUND_DEVICE = 0xa8
    # An APSDE-DATA.request with a destination addressing mode set to 0x03
    # failed due to no corresponding short address found in the address map
    # table.
    NO_SHORT_ADDRESS = 0xa9
    # An APSDE-DATA.request with a destination addressing mode set to 0x00
    # failed due to a binding table not being supported on the device.
    NOT_SUPPORTED = 0xaa
    # An ASDU was received that was secured using a link key.
    SECURED_LINK_KEY = 0xab
    # An ASDU was received that was secured using a network key.
    SECURED_NWK_KEY = 0xac
    # An APSDE-DATA.request requesting security has resulted in an error
    # during the corresponding security processing.
    SECURITY_FAIL = 0xad
    # An APSME-BIND.request or APSME.ADD-GROUP.request issued when the
    # binding or group tables, respectively, were full.
    TABLE_FULL = 0xae
    # An ASDU was received without any security.
    UNSECURED = 0xaf
    # An APSME-GET.request or APSME-SET.request has been issued with an
    # unknown attribute identifier.
    UNSUPPORTED_ATTRIBUTE = 0xb0


class StatusCodeCBKE(t.enum8):
    """Status Code for the CBKE category."""

    # The Issuer field within the key establishment partner's certificate is
    # unknown to the sending device
    UNKNOWN_ISSUER = 1
    # The device could not confirm that it shares the same key with the
    # corresponding device
    BAD_KEY_CONFIRM = 2
    # The device received a bad message from the corresponding device
    BAD_MESSAGE = 3
    # The device does not currently have the internal resources necessary to
    # perform key establishment
    NO_RESOURCES = 4
    # The device does not support the specified key establishment suite in the
    # partner's Initiate Key Establishment message
    UNSUPPORTED_SUITE = 5
    # The received certificate specifies a type, curve, hash, or other
    # parameter that is either unsupported by the device or invalid
    INVALID_CERTIFICATE = 6
    # Non-standard ZBOSS extension: SE KE endpoint not found
    NO_KE_EP = 7


class LLFlags(t.bitmap8):
    """Flags in low level header."""

    isACK = 0x01
    Retransmit = 0x02
    PacketSeq = 0x0C
    ACKSeq = 0x30
    FirstFrag = 0x40
    LastFrag = 0x80


class HLCommonHeader(t.uint32_t):
    """High Level Common Header class."""

    def __new__(
        cls, value: int = 0x00000000, *, version=None, type=None, id=None
    ) -> "HLCommonHeader":
        """Create high level common header."""
        instance = super().__new__(cls, value)

        if version is not None:
            instance = instance.with_version(version)

        if type is not None:
            instance = instance.with_type(type)

        if id is not None:
            instance = instance.with_id(id)

        return instance

    @property
    def version(self) -> t.uint8_t:
        """Return protocol version."""
        return t.uint8_t(self & 0x000000FF)

    @property
    def control_type(self) -> ControlType:
        """Return control type."""
        return ControlType((self & 0x0000FF00) >> 8)

    @property
    def id(self) -> t.uint16_t:
        """Return high level command id."""
        return t.uint16_t((self & 0xFFFF0000) >> 16)

    def with_id(self, value: int) -> "HLCommonHeader":
        """Set the command ID."""
        return type(self)(self & 0xFFFF | (value & 0xFFFF) << 16)

    def with_type(self, value: ControlType) -> "HLCommonHeader":
        """Set the control type."""
        return type(self)(self & 0xFFFF00FF | (value & 0xFF) << 8)

    def with_version(self, value: t.uint8_t) -> "HLCommonHeader":
        """Set the protocol version in use."""
        return type(self)(self & 0xFFFFFF00 | (value & 0xFF))

    def __str__(self) -> str:
        """Set the string representation of the high level common header."""
        return (
            f"{type(self).__name__}("
            f"version=0x{self.version:02X}, "
            f"type={self.control_type!s}, "
            f"command_id=0x{self.id:04X}"
            ")"
        )

    __repr__ = __str__


@dataclasses.dataclass(frozen=True)
class CommandDef:
    """Class used to define a command."""

    control_type: ControlType
    command_id: t.uint16_t
    blocking: bool = False
    req_schema: tuple | None = None
    rsp_schema: tuple | None = None


class CommandsMeta(type):
    """Metaclass for commands.

    Metaclass that creates `Command` subclasses out of the `CommandDef`
    definitions.
    """

    def __new__(cls, name: str, bases, classdict):
        """Create new class instance."""
        # Ignore CommandsBase
        if not bases:
            return type.__new__(cls, name, bases, classdict)

        classdict["_commands"] = []

        for command, definition in classdict.items():
            if not isinstance(definition, CommandDef):
                continue

            # We manually create the qualname to match the final obj structure
            qualname = classdict["__qualname__"] + "." + command

            # The commands class is dynamically created from the definition
            helper_class_dict = {
                "definition": definition,
                "type": definition.control_type,
                "__qualname__": qualname,
                "Req": None,
                "Rsp": None,
                "Ind": None,
            }

            header = (
                HLCommonHeader()
                .with_id(definition.command_id)
                .with_type(definition.control_type)
            )

            if definition.req_schema is not None:
                req_header = header
                rsp_header = req_header.with_type(ControlType.RSP)

                class Req(
                    CommandBase, header=req_header,
                    schema=definition.req_schema,
                    blocking=definition.blocking
                ):
                    pass

                class Rsp(
                    CommandBase, header=rsp_header,
                    schema=definition.rsp_schema
                ):
                    pass

                Req.__qualname__ = qualname + ".Req"
                Req.Req = Req
                Req.Rsp = Rsp
                Req.Ind = None
                helper_class_dict["Req"] = Req

                Rsp.__qualname__ = qualname + ".Rsp"
                Rsp.Rsp = Rsp
                Rsp.Req = Req
                Rsp.Ind = None
                helper_class_dict["Rsp"] = Rsp
            else:
                assert definition.rsp_schema is not None, definition

                if definition.control_type == ControlType.IND:
                    # If there is no request schema, this is an indication
                    class Ind(
                        CommandBase, header=header,
                        schema=definition.rsp_schema
                    ):
                        pass

                    Ind.__qualname__ = qualname + ".Ind"
                    Ind.Req = None
                    Ind.Rsp = None
                    Ind.Ind = Ind
                    helper_class_dict["Ind"] = Ind
                else:
                    raise RuntimeError(
                        f"Invalid command definition {command} = {definition}"
                    )  # pragma: no cover

            classdict[command] = type(command, (), helper_class_dict)
            classdict["_commands"].append(classdict[command])

        return type.__new__(cls, name, bases, classdict)

    def __iter__(self):
        """Overwrite iteration."""
        return iter(self._commands)


class CommandsBase(metaclass=CommandsMeta):
    """Parent class for commands type (APS, AF, NWK, ...)."""


class CommandBase:
    """Class containing required objects for a command."""

    Req = None
    Rsp = None
    Ind = None

    def __init_subclass__(cls, *, header, schema, blocking=False):
        """Set class parameters when the class is used as parent."""
        super().__init_subclass__()
        cls.header = header
        cls.schema = schema
        cls.blocking = blocking

    def __init__(self, *, partial=False, **params):
        """Initialize object."""
        super().__setattr__("_partial", partial)
        super().__setattr__("_bound_params", {})

        all_params = [p.name for p in self.schema]
        optional_params = [p.name for p in self.schema if p.optional]
        given_params = set(params.keys())
        given_optional = [p for p in params.keys() if p in optional_params]

        unknown_params = given_params - set(all_params)
        missing_params = (
            set(all_params) - set(optional_params)) - given_params

        if unknown_params:
            raise KeyError(
                f"Unexpected parameters: {unknown_params}. "
                f"Expected one of {missing_params}"
            )

        if not partial:
            # Optional params must be passed without any skips
            if optional_params[: len(given_optional)] != given_optional:
                raise KeyError(
                    f"Optional parameters cannot be skipped: "
                    f"expected order {optional_params}, got {given_optional}."
                )

            if missing_params:
                raise KeyError(
                    f"Missing parameters: {set(all_params) - given_params}")

        bound_params = {}

        for param in self.schema:
            if params.get(param.name) is None and (partial or param.optional):
                bound_params[param.name] = (param, None)
                continue

            value = params[param.name]

            if not isinstance(value, param.type):
                # fmt: off
                is_coercible_type = [
                    isinstance(value, int) and  # noqa: W504
                    issubclass(param.type, int) and  # noqa: W504
                    not issubclass(param.type, enum.Enum),

                    isinstance(value, bytes) and  # noqa: W504
                    issubclass(param.type, (t.ShortBytes, t.LongBytes)),

                    isinstance(value, list) and issubclass(param.type, list),
                    isinstance(value, bool) and issubclass(param.type, t.Bool),
                ]
                # fmt: on

                if any(is_coercible_type):
                    value = param.type(value)
                elif type(value) is zigpy.zdo.types.SimpleDescriptor and \
                        param.type is \
                        zigpy.zdo.types.SizePrefixedSimpleDescriptor:
                    data = value.serialize()
                    value, _ = param.type.deserialize(
                        bytes([len(data)]) + data)
                else:
                    raise ValueError(
                        f"In {type(self)}, param {param.name} is "
                        f"type {param.type}, got {type(value)}"
                    )

            try:
                value.serialize()
            except Exception as e:
                raise ValueError(
                    f"Invalid parameter value: {param.name}={value!r}"
                ) from e

            bound_params[param.name] = (param, value)

        super().__setattr__("_bound_params", bound_params)

    def to_frame(self, *, align=False):
        """Return a Frame object."""
        if self._partial:
            raise ValueError(f"Cannot serialize a partial frame: {self}")

        from zigpy_zboss.frames import HLPacket
        from zigpy_zboss.frames import LLHeader
        from zigpy_zboss.frames import Frame

        chunks = []

        for param, value in self._bound_params.values():
            if value is None:
                continue

            if issubclass(param.type, t.CStruct):
                chunks.append(value.serialize(align=align))
            else:
                chunks.append(value.serialize())

        hl_packet = HLPacket(self.header, b"".join(chunks))

        # Sequence flag and CRC8 are set later before sending frame over uart.
        ll_header = (
            LLHeader()
            .with_signature(Frame.signature)
            .with_size(hl_packet.length + 5)
            .with_type(TYPE_ZBOSS_NCP_API_HL)
            .with_flags(LLFlags.LastFrag | LLFlags.FirstFrag)
        )

        return Frame(ll_header, hl_packet)

    @classmethod
    def from_frame(cls, frame, *, align=False) -> "CommandBase":
        """Return a CommandBase object."""
        if frame.hl_packet.header != cls.header:
            raise ValueError(
                f"Wrong frame header in {cls}: {cls.header} != "
                f"{frame.hl_packet.header}"
            )

        data = frame.hl_packet.data
        params = {}

        for param in cls.schema:
            try:
                if issubclass(param.type, t.CStruct):
                    params[param.name], data = param.type.deserialize(
                        data, align=align)
                else:
                    params[param.name], data = param.type.deserialize(data)
            except ValueError:
                if frame.hl_packet.header.control_type == ControlType.RSP:
                    # If the response to a request failed, the status code
                    # is different from 0 and the NCP does not send more data.
                    # Return a partial command object including the status.
                    status_code = params["StatusCode"]
                    if status_code != 0:
                        return cls(**params, partial=True)
                if not data and param.optional:
                    # If we're out of data and the parameter is optional,
                    # we're done
                    break
                elif not data and not param.optional:
                    # If we're out of data but the parameter is required,
                    # this is bad
                    raise ValueError(
                        f"Frame data is truncated (parsed {params}),"
                        f" required parameter remains: {param}"
                    )
                else:
                    # Otherwise, let the exception happen
                    raise
        return cls(**params)

    def matches(self, other: "CommandBase") -> bool:
        """Match parameters and values with other CommandBase."""
        if type(self) is not type(other):
            return False

        assert self.header == other.header

        param_pairs = zip(
            self._bound_params.values(), other._bound_params.values())

        for (
            (expected_param, expected_value),
            (actual_param, actual_value),
        ) in param_pairs:
            assert expected_param == actual_param

            # Only non-None bound params are considered
            if expected_value is not None and expected_value != actual_value:
                return False

        return True

    def __eq__(self, other):
        """Return True if bound parameters are equal."""
        return type(self) is type(other) and \
            self._bound_params == other._bound_params

    def __hash__(self):
        """Return a hash from tuple made of command parameters."""
        params = tuple(self._bound_params.items())
        return hash((type(self), self.header, self.schema, params))

    def __getattribute__(self, key):
        """Try to return the attribute of the command."""
        try:
            return object.__getattribute__(self, key)
        except AttributeError:
            pass

        try:
            param, value = object.__getattribute__(self, "_bound_params")[key]
            return value
        except KeyError:
            pass

        raise AttributeError(f"{self} has no attribute {key!r}")

    def __setattr__(self, key, value):
        """Prevent attributes to be changed."""
        raise RuntimeError("Command instances are immutable")

    def __delattr__(self, key):
        """Prevent attributes to be deleted."""
        raise RuntimeError("Command instances are immutable")

    def __repr__(self):
        """Return a command representation."""
        params = [f"{p.name}={v!r}" for p, v in self._bound_params.values()]

        return f'{self.__class__.__qualname__}({", ".join(params)})'

    __str__ = __repr__


class PolicyType(t.enum16):
    """Class representing the policy type of the trust center."""

    TC_Link_Keys_Required = 0x0000
    IC_Required = 0x0001
    TC_Rejoin_Enabled = 0x0002
    Ignore_TC_Rejoin = 0x0003
    APS_Insecure_Join = 0x0004
    Disable_NWK_MGMT_Channel_Update = 0x0005


class ResetOptions(t.enum8):
    """Enum class for the reset options."""

    NoOptions = 0
    EraseNVRAM = 1
    FactoryReset = 2
    LockReadingKeys = 3


class ResetSource(t.enum8):
    """Enum class for the reset source."""

    RESET_SRC_POWER_ON = 0
    RESET_SRC_SW_RESET = 1
    RESET_SRC_RESET_PIN = 2
    RESET_SRC_BROWN_OUT = 3
    RESET_SRC_CLOCK_LOSS = 4
    RESET_SRC_OTHER = 5


class DeviceRole(t.enum8):
    """Enum class for the device role."""

    ZC = 0
    ZR = 1
    ZED = 2
    NONE = 3


class TimeoutIndex(t.enum8):
    """Enum for the timeout index."""

    Seconds_10 = 0x00

    Minutes_2 = 0x01
    Minutes_4 = 0x02
    Minutes_8 = 0x03
    Minutes_16 = 0x04
    Minutes_32 = 0x05
    Minutes_64 = 0x06
    Minutes_128 = 0x07
    Minutes_256 = 0x08
    Minutes_512 = 0x09
    Minutes_1024 = 0x0A
    Minutes_2048 = 0x0B
    Minutes_4096 = 0x0C
    Minutes_8192 = 0x0D
    Minutes_16384 = 0x0E


class PowerMode(t.enum8):
    """Enum class for power mode."""

    # Receiver synchronized with the receiver on when idle subfield of the
    # node descriptor
    Sync = 0x00
    # Receiver comes on periodically as defined by the node power descriptor
    Perio = 0x01
    # Receiver comes on when stimulated, for example, by a user pressing a
    # button
    Stim = 0x02


class PowerSourceLevel(t.enum8):
    """Enum class for the power source level."""

    Critical = 0
    Percent_33 = 4
    Percent_66 = 8
    Percent_100 = 12


class APSFrameFC(t.bitmap8):
    """Enum class for APS frame flags."""

    Unicast = 1 << 0
    Broadcast = 1 << 2
    Group = 1 << 3
    Secure = 1 << 5
    Retransmit = 1 << 6


class MACCapability(t.bitmap8):
    """Enum class for MAC capabilities."""

    AlternatePANCoordinator = 1 << 0
    DeviceType = 1 << 1
    PowerSource = 1 << 2
    ReceiveOnWhenIdle = 1 << 3
    SecurityCapability = 1 << 6
    AllocateAddress = 1 << 7


class PowerSource(t.bitmap8):
    """Enum class for power source."""

    Mains = 1 << 0
    RechargeableBattery = 1 << 1
    DisposableBattery = 1 << 2
    Reserved = 1 << 3


STATUS_SCHEMA = (
    t.Param("TSN", t.uint8_t, "Transmit Sequence Number"),
    t.Param("StatusCat", StatusCategory, "Status category code"),
    t.Param("StatusCode", t.uint8_t, "Status code inside category"),
)
