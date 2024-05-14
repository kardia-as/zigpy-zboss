import zigpy_zboss.types as t
from zigpy_zboss.types import nvids
from zigpy_zboss.types.nvids import ApsSecureEntry, DSApsSecureKeys
from struct import pack


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
