"""Test named types."""
import zigpy_zboss.types as t


def test_channel_entry():
    """Test channel entry.

    ChannelEntry class for proper serialization,
    deserialization, equality, and representation.
    """
    # Sample data for testing
    page_data = b"\x01"  # Page number as bytes
    channel_mask_data = b"\x00\x10\x00\x00"  # Sample channel mask as bytes

    data = page_data + channel_mask_data

    # Test deserialization
    channel_entry, remaining_data = t.ChannelEntry.deserialize(data)
    assert remaining_data == b''  # no extra data should remain
    assert channel_entry.page == 1
    assert channel_entry.channel_mask == 0x00001000

    # Test serialization
    assert channel_entry.serialize() == data

    # Test equality
    another_entry = t.ChannelEntry(page=1, channel_mask=0x00001000)
    assert channel_entry == another_entry
    assert channel_entry != t.ChannelEntry(page=0, channel_mask=0x00002000)

    # Test __repr__
    expected_repr = \
        "ChannelEntry(page=1, channel_mask=<Channels.CHANNEL_12: 4096>)"
    assert repr(channel_entry) == expected_repr
