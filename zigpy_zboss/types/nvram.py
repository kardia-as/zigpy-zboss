"""Module defining zboss nvram types."""
from __future__ import annotations
import zigpy.types as t
from . import basic


class NVRAMDataset(
        basic.LVList, item_type=basic.uint8_t, length_type=basic.uint16_t):
    """Class representing a NVRAM dataset."""


class NwkAddrMapHeader(t.Struct):
    """Class representing a NVRAM network address map header."""

    length: t.uint8_t
    version: t.uint8_t
    _align: t.uint16_t


class NwkAddrMapRecord(t.Struct):
    """Class representing a NVRAM network address map record v2."""

    ieee_addr: t.EUI64
    nwk_addr: t.NWK
    index: t.uint8_t
    redirect_type: t.uint8_t
    redirect_ref: t.uint8_t
    _align: t.uint24_t


class NwkAddrMap(
        basic.LVList,
        item_type=NwkAddrMapRecord,
        length_type=NwkAddrMapHeader):
    """Class representing a NVRAM network address map."""

    @classmethod
    def deserialize(
            cls, data: bytes, *, align=False) -> tuple[basic.LVList, bytes]:
        """Deserialize object."""
        header, data = cls._header.deserialize(data)
        r = cls()
        for i in range(header.length):
            item, data = cls._deserialize_item(data, align=align)
            r.append(item)
        return r, data
