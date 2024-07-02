"""Module defining named types."""
from __future__ import annotations

import dataclasses
import logging
import typing

from zigpy.types import (EUI64, NWK, Bool, Channels,  # noqa: F401
                         CharacterString, ClusterId, ExtendedPanId, KeyData,
                         List, PanId, Struct, bitmap8)

from . import basic

LOGGER = logging.getLogger(__name__)

JSONType = typing.Union[typing.Dict[str, typing.Any], typing.List[typing.Any]]


class BindAddrMode(basic.enum8):
    """Address mode for bind related requests."""

    Reserved_1 = 0x00
    Group = 0x01
    Reserved_2 = 0x02
    IEEE = 0x03


class ChannelEntry(Struct):
    """Class representing a channel entry."""

    page: basic.uint8_t
    channel_mask: Channels


@dataclasses.dataclass(frozen=True)
class Param:
    """Schema parameter."""

    name: str
    type: type = None
    description: str = ""
    optional: bool = False


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


class DeviceUpdateStatus(basic.enum8):
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
