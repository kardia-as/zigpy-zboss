import pytest

import zigpy_zboss.types as t


def test_channel_entry():
    """Test ChannelEntry class for proper serialization,
     deserialization, equality, and representation."""
    # Sample data for testing
    page_data = b"\x01"  # Page number as bytes
    channel_mask_data = b"\x00\x01\x00\x00"  # Sample channel mask as bytes

    data = page_data + channel_mask_data

    # Test deserialization
    channel_entry, remaining_data = t.ChannelEntry.deserialize(data)
    assert remaining_data == b''  # no extra data should remain
    assert channel_entry.page == 1
    assert channel_entry.channel_mask == 0x0100

    # Test serialization
    assert channel_entry.serialize() == data

    # Test equality
    another_entry = t.ChannelEntry(page=1, channel_mask=0x0100)
    assert channel_entry == another_entry
    assert channel_entry != t.ChannelEntry(page=0, channel_mask=0x0200)

    # Test __repr__
    expected_repr = "ChannelEntry(page=1, channels=<Channels: 256>)"
    assert repr(channel_entry) == expected_repr

    # Test handling of None types for page or channel_mask
    with pytest.raises(AttributeError):
        t.ChannelEntry(page=None, channel_mask=None)
