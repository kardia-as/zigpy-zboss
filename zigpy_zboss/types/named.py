"""Module defining named types."""
from __future__ import annotations

import sys
import typing
import logging
import dataclasses

from zigpy.types import (  # noqa: F401
    NWK,
    List,
    Bool,
    PanId,
    EUI64,
    Struct,
    bitmap8,
    KeyData,
    Channels,
    ClusterId,
    ExtendedPanId,
    CharacterString,
)

from . import basic

LOGGER = logging.getLogger(__name__)

JSONType = typing.Union[typing.Dict[str, typing.Any], typing.List[typing.Any]]


class BindAddrMode(basic.enum_uint8):
    """Address mode for bind related requests."""

    Reserved_1 = 0x00
    Group = 0x01
    Reserved_2 = 0x02
    IEEE = 0x03


class ChannelEntry:
    """Class representing a channel entry."""

    def __new__(cls, page=None, channel_mask=None):
        """Create a channel entry instance."""
        instance = super().__new__(cls)

        instance.page = basic.uint8_t(page)
        instance.channel_mask = channel_mask

        return instance

    @classmethod
    def deserialize(cls, data: bytes) -> "ChannelEntry":
        """Deserialize the object."""
        page, data = basic.uint8_t.deserialize(data)
        channel_mask, data = Channels.deserialize(data)

        return cls(page=page, channel_mask=channel_mask), data

    def serialize(self) -> bytes:
        """Serialize the object."""
        return self.page.serialize() + self.channel_mask.serialize()

    def __eq__(self, other):
        """Return True if channel_masks and pages are equal."""
        if not isinstance(other, type(self)):
            return NotImplemented

        return self.page == other.page and \
            self.channel_mask == other.channel_mask

    def __repr__(self) -> str:
        """Return a representation of a channel entry."""
        return f"{type(self).__name__}(page={self.page!r}," \
            f" channels={self.channel_mask!r})"


class GroupId(basic.uint16_t, hex_repr=True):
    """Group ID class."""


@dataclasses.dataclass(frozen=True)
class Param:
    """Schema parameter."""

    name: str
    type: type = None
    description: str = ""
    optional: bool = False


class MissingEnumMixin:
    """Mixin class for enum."""

    @classmethod
    def _missing_(cls, value):
        if not isinstance(value, int):
            raise ValueError(f"{value} is not a valid {cls.__name__}")

        new_member = cls._member_type_.__new__(cls, value)
        new_member._name_ = f"unknown_0x{value:02X}"
        new_member._value_ = cls._member_type_(value)

        if sys.version_info >= (3, 8):
            # Show the warning in the calling code, not in this function
            LOGGER.warning(
                "Unhandled %s value: %s",
                cls.__name__,
                new_member,
                stacklevel=2
            )
        else:
            LOGGER.warning("Unhandled %s value: %s", cls.__name__, new_member)

        return new_member


class ChannelEntryList(
        basic.LVList, item_type=ChannelEntry, length_type=basic.uint8_t):
    """Class representing a list of channel entries."""


class NWKList(basic.LVList, item_type=NWK, length_type=basic.uint8_t):
    """Class representing a list of NWK addresses."""


class GrpList(
        basic.LVList, item_type=basic.uint16_t, length_type=basic.uint8_t):
    """Class representing a list of group addresses."""


class Payload(List, item_type=basic.uint8_t):
    """Class representing a payload."""


class DeviceUpdateStatus(basic.enum_uint8):
    """Enum class for device update status."""

    secured_rejoin = 0x00
    unsecured_join = 0x01
    device_left = 0x02
    tc_rejoin = 0x03


class ApsAttributes(bitmap8):
    """Bitmap class for aps attributes."""

    key_source = 0b00000001
    key_attributes_0 = 0b00000010
    key_attributes_2 = 0b00000100
    key_from_trust_center = 0b00001000
    extended_frame_control_0 = 0b00010000
    extended_frame_control_1 = 0b00100000
    reserved_0 = 0b01000000
    reserved_1 = 0b10000000
