"""Test NVIDS."""
from struct import pack

import zigpy_zboss.types as t
from zigpy_zboss.types import nvids
from zigpy_zboss.types.nvids import (ApsSecureEntry, DSApsSecureKeys,
                                     DSNwkAddrMap, NwkAddrMapHeader,
                                     NwkAddrMapRecord)


def test_nv_ram_get_byte_size():
    """Test the get_byte_size method of the NVRAMStruct class."""
    class TestStruct(nvids.NVRAMStruct):
        a: t.uint8_t
        b: t.EUI64
        c: t.uint8_t

    data = TestStruct(a=1, b=[2], c=3)

    byte_size = data.get_byte_size()

    assert byte_size == 10, f"Expected byte size to be 10, but got {byte_size}"


def test_dsapssecurekeys():
    """Test the serialize/deserialize method of the DSApsSecureKeys class."""
    ieee_addr1 = t.EUI64([0, 1, 2, 3, 4, 5, 6, 7])
    key1 = t.KeyData([0x10] * 16)
    unknown_1_1 = t.basic.uint32_t(12345678)
    entry1 = ApsSecureEntry(
        ieee_addr=ieee_addr1, key=key1, _unknown_1=unknown_1_1
    )
    entry_data1 = entry1.serialize()

    ieee_addr2 = t.EUI64([8, 9, 10, 11, 12, 13, 14, 15])
    key2 = t.KeyData([0x20] * 16)
    unknown_1_2 = t.basic.uint32_t(87654321)
    entry2 = ApsSecureEntry(
        ieee_addr=ieee_addr2, key=key2, _unknown_1=unknown_1_2
    )
    entry_data2 = entry2.serialize()

    # Calculate total length for the LVList
    entry_size = ApsSecureEntry.get_byte_size()
    total_length = (entry_size * 2) + 4

    length_bytes = pack("<H", total_length)
    # module for some reason returns 4 redundant bytes
    # so need to include those foe test cse
    redundant_bytes = pack("<HH", 0xAABB, 0xAABB)
    data = length_bytes + redundant_bytes + entry_data1 + entry_data2

    # Call the deserialize method
    result, remaining_data = DSApsSecureKeys.deserialize(data)

    # Verify the type of the deserialized result
    assert isinstance(result, DSApsSecureKeys)

    assert remaining_data == b''  # Assuming no remaining data
    assert len(result) == 2

    deserialized_entry1 = result[0]
    assert deserialized_entry1.ieee_addr == ieee_addr1
    assert deserialized_entry1.key == key1
    assert deserialized_entry1._unknown_1 == unknown_1_1

    deserialized_entry2 = result[1]
    assert deserialized_entry2.ieee_addr == ieee_addr2
    assert deserialized_entry2.key == key2
    assert deserialized_entry2._unknown_1 == unknown_1_2

    # Test the serialization
    serialized_data = result.serialize()
    total_length = (entry_size * 2)
    length_bytes = pack("<H", total_length)
    expected_data = length_bytes + entry_data1 + entry_data2
    assert serialized_data == expected_data


def test_dsnwkaddrmap():
    """Test the serialize/deserialize method of the DSNwkAddrMap class."""
    ieee_addr = t.EUI64([0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08])
    nwk_addr = t.NWK(0x1234)
    index = t.uint8_t(1)
    redirect_type = t.uint8_t(0)
    redirect_ref = t.uint8_t(5)
    dummy_map_record1 = NwkAddrMapRecord(
        ieee_addr=ieee_addr, nwk_addr=nwk_addr,
        index=index, redirect_type=redirect_type,
        redirect_ref=redirect_ref, _align=0
    )
    ieee_addr2 = t.EUI64([0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x0E, 0x0F, 0x10])
    nwk_addr2 = t.NWK(0x5678)
    index2 = t.uint8_t(2)
    redirect_type2 = t.uint8_t(1)
    redirect_ref2 = t.uint8_t(6)
    dummy_map_record2 = NwkAddrMapRecord(
        ieee_addr=ieee_addr2, nwk_addr=nwk_addr2,
        index=index2, redirect_type=redirect_type2,
        redirect_ref=redirect_ref2, _align=0
    )
    # Assume byte_count excludes itself
    header = NwkAddrMapHeader(
        byte_count=36, entry_count=2, version=2, _align=t.uint16_t(0x0000)
    )
    header_bytes = header.serialize()

    record_bytes = (
            dummy_map_record1.serialize() + dummy_map_record2.serialize()
    )

    data = header_bytes + record_bytes

    # Test Deserialize
    result, remaining_data = DSNwkAddrMap.deserialize(data)

    assert remaining_data == b''
    assert len(result) == 2

    assert result[0].ieee_addr == dummy_map_record1.ieee_addr
    assert result[0].nwk_addr == dummy_map_record1.nwk_addr
    assert result[0].index == dummy_map_record1.index
    assert result[0].redirect_type == dummy_map_record1.redirect_type
    assert result[0].redirect_ref == dummy_map_record1.redirect_ref

    assert result[1].ieee_addr == dummy_map_record2.ieee_addr
    assert result[1].nwk_addr == dummy_map_record2.nwk_addr
    assert result[1].index == dummy_map_record2.index
    assert result[1].redirect_type == dummy_map_record2.redirect_type
    assert result[1].redirect_ref == dummy_map_record2.redirect_ref

    # Test Serialize
    serialized_data = result.serialize()
    expected_data = header_bytes + record_bytes
    assert serialized_data == expected_data
