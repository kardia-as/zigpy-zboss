"""Module defining zboss nvram types."""
from __future__ import annotations
import zigpy.types as t
import zigpy_zboss.types as zboss_t
from . import basic


class DatasetType(zboss_t.enum_uint16):
    """NVRAM dataset types."""

    ZB_NVRAM_RESERVED = 0
    ZB_NVRAM_COMMON_DATA = 1
    ZB_NVRAM_HA_DATA = 2
    ZB_NVRAM_ZCL_REPORTING_DATA = 3
    ZB_NVRAM_APS_SECURE_DATA_GAP = 4
    ZB_NVRAM_APS_BINDING_DATA_GAP = 5
    ZB_NVRAM_HA_POLL_CONTROL_DATA = 6
    ZB_IB_COUNTERS = 7,
    ZB_NVRAM_DATASET_GRPW_DATA = 8
    ZB_NVRAM_APP_DATA1 = 9
    ZB_NVRAM_APP_DATA2 = 10
    ZB_NVRAM_ADDR_MAP = 11
    ZB_NVRAM_NEIGHBOUR_TBL = 12
    ZB_NVRAM_INSTALLCODES = 13
    ZB_NVRAM_APS_SECURE_DATA = 14
    ZB_NVRAM_APS_BINDING_DATA = 15
    ZB_NVRAM_DATASET_GP_PRPOXYT = 16
    ZB_NVRAM_DATASET_GP_SINKT = 17
    ZB_NVRAM_DATASET_GP_CLUSTER = 18
    ZB_NVRAM_APS_GROUPS_DATA = 19
    ZB_NVRAM_DATASET_SE_CERTDB = 20
    ZB_NVRAM_ZCL_WWAH_DATA = 21
    ZB_NVRAM_APP_DATA3 = 27
    ZB_NVRAM_APP_DATA4 = 28


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


class ApsSecureRecord(t.Struct):
    """Class representing a NVRAM APS Secure key record."""

    version: basic.uint16_t
    _align: basic.uint16_t
    ieee_addr: t.EUI64
    key: t.KeyData
