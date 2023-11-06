"""Module defining zboss nvram types."""
from __future__ import annotations
import zigpy.types as t
import zigpy_zboss.types as zboss_t
from . import basic


class DatasetId(zboss_t.enum16):
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
    """Class representing a generic NVRAM dataset."""


class NVRAMStruct(t.Struct):
    """Class representing struct used for NVRAM interaction."""

    @classmethod
    def get_byte_size(cls):
        """Return the sum of the byte size of the fields in the struct."""
        # Since some types are a list of basic types, they use _length
        # attribute instead of the _size attribute (e.g t.EUI64).
        size = 0
        for structfield in cls.fields:
            try:
                size += structfield.type._size
            except AttributeError:
                size += structfield.type._length
        return size


class NwkAddrMapHeader(NVRAMStruct):
    """Class representing a NVRAM network address map header."""

    byte_count: t.uint16_t
    entry_count: t.uint8_t
    version: t.uint8_t
    _align: t.uint16_t


class NwkAddrMapRecord(NVRAMStruct):
    """Class representing a NVRAM network address map record v2."""

    ieee_addr: t.EUI64
    nwk_addr: t.NWK
    index: t.uint8_t
    redirect_type: t.uint8_t
    redirect_ref: t.uint8_t
    _align: t.uint24_t


class DSNwkAddrMap(
        basic.LVList,
        item_type=NwkAddrMapRecord,
        length_type=NwkAddrMapHeader):
    """Class representing a NVRAM network address map dataset."""

    version = 2

    @classmethod
    def deserialize(
            cls, data: bytes, *, align=False) -> tuple[basic.LVList, bytes]:
        """Deserialize object."""
        header, data = cls._header.deserialize(data)
        r = cls()
        for _ in range(header.entry_count):
            item, data = cls._deserialize_item(data, align=align)
            r.append(item)
        return r, data

    def serialize(self, *, align=False) -> bytes:
        """Serialize object."""
        assert self._item_type is not None
        serialized_items = b"".join(
            [self._serialize_item(i, align=align) for i in self])
        # Remove 2 bytes from the size because byte_count is not counted
        byte_count = len(serialized_items) + self._header.get_byte_size() - 2
        header = self._header(
            byte_count=byte_count,
            entry_count=len(self),
            version=t.uint8_t(0x02),
            _align=t.uint16_t(0x0000),
        )
        return header.serialize() + serialized_items


class ApsSecureEntry(NVRAMStruct):
    """Class representing a NVRAM APS Secure key entry."""

    ieee_addr: t.EUI64
    key: t.KeyData
    _unknown_1: basic.uint32_t


class DSApsSecureKeys(
        basic.LVList,
        item_type=ApsSecureEntry,
        length_type=basic.uint16_t):
    """Class representing a list of APS secure keys dataset."""

    version = 0

    @classmethod
    def deserialize(
            cls, data: bytes, *, align=False) -> tuple[basic.LVList, bytes]:
        """Deserialize object."""
        length, data = cls._header.deserialize(data)
        r = cls()
        data = data[4:]  # Dropping the 4 first bytes from the list
        entry_cnt = (length - 4) / ApsSecureEntry.get_byte_size()
        for _ in range(int(entry_cnt)):
            item, data = cls._deserialize_item(data, align=align)
            r.append(item)
        return r, data

    def serialize(self, *, align=False) -> bytes:
        """Serialize object."""
        assert self._item_type is not None
        serialized_items = b"".join(
            [self._serialize_item(i, align=align) for i in self])
        return self._header(
            len(self) * self._item_type.get_byte_size()
            ).serialize() + serialized_items


class DSIbCounters(t.Struct):
    """Class representing NIB and AIB counters dataset."""

    version = 1

    byte_count: t.uint16_t
    nib_counter: t.uint32_t
    aib_counter: t.uint32_t


class MacInterfaceTable(t.Struct):
    """Class representing the NIB nwkMacInteraceTable."""

    bitfield_0: t.uint8_t
    bitfield_1: t.uint8_t
    link_pwr_data_rate: t.uint16_t
    channel_in_use: t.uint32_t
    supported_channels: t.Channels


class DSCommonData(t.Struct):
    """Class representing the common data dataset."""

    version = 3

    byte_count: t.uint16_t
    bitfield: t.uint8_t
    depth: t.uint8_t
    nwk_manager_addr: t.NWK
    panid: t.PanId
    network_addr: t.NWK
    channel_mask: t.Channels
    aps_extended_panid: t.EUI64
    nwk_extended_panid: t.EUI64
    parent_addr: t.EUI64
    tc_addr: t.EUI64
    nwk_key: t.KeyData
    nwk_key_seq: t.uint8_t
    tc_standard_key: t.KeyData
    channel: t.uint8_t
    page: t.uint8_t
    mac_interface_table: MacInterfaceTable
    reserved: t.uint8_t
