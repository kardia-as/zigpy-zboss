"""Test frame."""
import pytest

import zigpy_zboss.types as t
from zigpy_zboss.frames import (CRC8, ZBNCP_LL_BODY_SIZE_MAX, Frame, HLPacket,
                                InvalidFrame, LLHeader)


def test_frame_deserialization():
    """Test frame deserialization."""
    ll_signature = t.uint16_t(0xADDE).serialize()

    # Create an HLCommonHeader with specific fields
    hl_data = t.Bytes(b"test_data").serialize()
    hl_packet = hl_data

    ll_size = t.uint16_t(len(hl_packet) + 5).serialize()
    ll_type = t.uint8_t(0x01).serialize()
    ll_flags = t.LLFlags(0x00).serialize()

    ll_header_without_crc = ll_signature + ll_size + ll_type + ll_flags
    ll_crc = CRC8(ll_header_without_crc[2:6]).digest().serialize()
    ll_header = ll_header_without_crc + ll_crc

    frame_data = ll_header + hl_packet
    extra_data = b"extra_data"

    # Deserialize frame
    frame, rest = Frame.deserialize(frame_data + extra_data)

    # Assertions
    assert rest == extra_data
    assert frame.ll_header.signature == 0xADDE
    assert frame.ll_header.size == len(hl_packet) + 5
    assert frame.ll_header.frame_type == 0x01
    assert frame.ll_header.flags == 0x00
    assert frame.ll_header.crc8 == CRC8(ll_header_without_crc[2:6]).digest()
    assert frame.hl_packet.data == b"test_data"

    # Invalid frame signature
    invalid_signature_frame_data = t.uint16_t(0xFFFF).serialize() + frame_data[
                                                                    2:]
    with pytest.raises(InvalidFrame,
                       match="Expected frame to start with Signature"):
        Frame.deserialize(invalid_signature_frame_data)

    # Invalid CRC8
    ll_header = ll_header_without_crc

    frame_data_without_crc = ll_header + hl_packet
    with pytest.raises(InvalidFrame, match="Invalid frame checksum"):
        Frame.deserialize(frame_data_without_crc)


def test_ack_flag_deserialization():
    """Test frame deserialization with ACK flag."""
    ll_signature = t.uint16_t(0xADDE).serialize()
    ll_size = t.uint16_t(5).serialize()  # Only LLHeader size
    ll_type = t.uint8_t(0x01).serialize()
    ll_flags = t.LLFlags(t.LLFlags.isACK).serialize()

    ll_header_without_crc = ll_signature + ll_size + ll_type + ll_flags
    ll_crc = CRC8(ll_header_without_crc[2:6]).digest().serialize()
    ll_header = ll_header_without_crc + ll_crc

    frame_data = ll_header
    extra_data = b"extra_data"

    frame, rest = Frame.deserialize(frame_data + extra_data)

    assert rest == extra_data
    assert frame.ll_header.signature == 0xADDE
    assert frame.ll_header.size == 5
    assert frame.ll_header.frame_type == 0x01
    assert frame.ll_header.flags == t.LLFlags.isACK
    assert frame.ll_header.crc8 == CRC8(ll_header_without_crc[2:6]).digest()
    assert frame.hl_packet is None


def test_first_frag_flag_deserialization():
    """Test frame deserialization with FirstFrag flag."""
    ll_signature = t.uint16_t(0xADDE).serialize()

    # Create an HLCommonHeader with specific fields
    hl_header = t.HLCommonHeader(
        version=0x01, type=t.ControlType.RSP, id=0x1234
    )
    hl_data = t.Bytes(b"test_data")

    # Create HLPacket and serialize
    hl_packet = HLPacket(header=hl_header, data=hl_data)
    hl_packet_data = hl_packet.serialize()

    # Create LLHeader with FirstFrag flag
    ll_size = t.uint16_t(len(hl_packet_data) + 5).serialize()
    ll_type = t.uint8_t(0x01).serialize()
    ll_flags = t.LLFlags(t.LLFlags.FirstFrag).serialize()

    ll_header_without_crc = ll_signature + ll_size + ll_type + ll_flags
    ll_crc = CRC8(ll_header_without_crc[2:6]).digest().serialize()
    ll_header = ll_header_without_crc + ll_crc

    frame_data = ll_header + hl_packet_data
    extra_data = b"extra_data"

    frame, rest = Frame.deserialize(frame_data + extra_data)

    assert rest == extra_data
    assert frame.ll_header.signature == 0xADDE
    assert frame.ll_header.size == len(hl_packet_data) + 5
    assert frame.ll_header.frame_type == 0x01
    assert frame.ll_header.flags == t.LLFlags.FirstFrag
    assert frame.ll_header.crc8 == CRC8(ll_header_without_crc[2:6]).digest()
    assert frame.hl_packet.header.version == 0x01
    assert frame.hl_packet.header.control_type == t.ControlType.RSP
    assert frame.hl_packet.header.id == 0x1234
    assert frame.hl_packet.data == b"test_data"


def test_handle_tx_fragmentation():
    """Test the handle_tx_fragmentation method for proper fragmentation."""
    # Create an HLCommonHeader with specific fields
    hl_header = t.HLCommonHeader(
        version=0x01, type=t.ControlType.RSP, id=0x1234
    )
    large_data = b"a" * (ZBNCP_LL_BODY_SIZE_MAX * 2 + 50)
    hl_data = t.Bytes(large_data)

    # Create an HLPacket with the large data
    hl_packet = HLPacket(header=hl_header, data=hl_data)
    frame = Frame(ll_header=LLHeader(), hl_packet=hl_packet)

    fragments = frame.handle_tx_fragmentation()

    total_fragments = frame.count_fragments()
    assert len(fragments) == total_fragments

    # Calculate the expected size of the first fragment
    # Exclude the CRC16 for size calculation
    serialized_hl_packet = hl_packet.serialize()[2:]
    first_frag_size = (
            len(serialized_hl_packet) % ZBNCP_LL_BODY_SIZE_MAX
            or ZBNCP_LL_BODY_SIZE_MAX
    )

    # Check the first fragment
    first_fragment = fragments[0]
    assert first_fragment.ll_header.flags == t.LLFlags.FirstFrag
    assert first_fragment.ll_header.size == first_frag_size + 7
    assert len(first_fragment.hl_packet.data) == first_frag_size - 4

    # Check the middle fragments
    for middle_fragment in fragments[1:-1]:
        assert middle_fragment.ll_header.flags == 0
        assert middle_fragment.ll_header.size == ZBNCP_LL_BODY_SIZE_MAX + 7
        assert len(middle_fragment.hl_packet.data) == ZBNCP_LL_BODY_SIZE_MAX

    # Check the last fragment
    last_fragment = fragments[-1]
    last_frag_size = (
            len(serialized_hl_packet) -
            (first_frag_size + (total_fragments - 2) * ZBNCP_LL_BODY_SIZE_MAX)
    )
    assert last_fragment.ll_header.flags == t.LLFlags.LastFrag
    assert last_fragment.ll_header.size == last_frag_size + 7
    assert len(last_fragment.hl_packet.data) == last_frag_size


def test_handle_tx_fragmentation_edge_cases():
    """Test the handle_tx_fragmentation method for various edge cases."""
    # Data size exactly equal to ZBNCP_LL_BODY_SIZE_MAX
    exact_size_data = b"a" * (ZBNCP_LL_BODY_SIZE_MAX - 2 - 2)
    hl_header = t.HLCommonHeader(version=0x01, type=t.ControlType.RSP,
                                 id=0x1234)
    hl_packet = HLPacket(header=hl_header, data=t.Bytes(exact_size_data))
    frame = Frame(ll_header=LLHeader(), hl_packet=hl_packet)

    # Perform fragmentation
    fragments = frame.handle_tx_fragmentation()
    assert len(fragments) == 1  # Should not fragment

    # Test with data size just above ZBNCP_LL_BODY_SIZE_MAX
    just_above_size_data = b"a" * (ZBNCP_LL_BODY_SIZE_MAX + 1 - 2 - 2)
    hl_packet = HLPacket(header=hl_header, data=t.Bytes(just_above_size_data))
    frame = Frame(ll_header=LLHeader(), hl_packet=hl_packet)
    fragments = frame.handle_tx_fragmentation()
    assert len(fragments) == 2  # Should fragment into two

    # Test with data size much larger than ZBNCP_LL_BODY_SIZE_MAX
    large_data = b"a" * ((ZBNCP_LL_BODY_SIZE_MAX * 5) + 50 - 2 - 2)
    hl_packet = HLPacket(header=hl_header, data=t.Bytes(large_data))
    frame = Frame(ll_header=LLHeader(), hl_packet=hl_packet)
    fragments = frame.handle_tx_fragmentation()
    assert len(fragments) == 6  # 5 full fragments and 1 partial fragment

    # Test with very small data
    small_data = b"a" * 10
    hl_packet = HLPacket(header=hl_header, data=t.Bytes(small_data))
    frame = Frame(ll_header=LLHeader(), hl_packet=hl_packet)
    fragments = frame.handle_tx_fragmentation()
    assert len(fragments) == 1  # Should not fragment


def test_handle_rx_fragmentation():
    """Test the handle_rx_fragmentation method for.

    proper reassembly of fragments.
    """
    # Create an HLCommonHeader with specific fields
    hl_header = t.HLCommonHeader(
        version=0x01, type=t.ControlType.RSP, id=0x1234
    )
    large_data = b"a" * (ZBNCP_LL_BODY_SIZE_MAX * 2 + 50)
    hl_data = t.Bytes(large_data)

    # Create an HLPacket with the large data
    hl_packet = HLPacket(header=hl_header, data=hl_data)
    frame = Frame(ll_header=LLHeader(), hl_packet=hl_packet)

    # Perform fragmentation
    fragments = frame.handle_tx_fragmentation()

    # Verify that the correct number of fragments was created
    total_fragments = frame.count_fragments()
    assert len(fragments) == total_fragments

    # Reassemble the fragments using handle_rx_fragmentation
    reassembled_frame = Frame.handle_rx_fragmentation(fragments)

    # Verify the reassembled frame
    assert (
            reassembled_frame.ll_header.frame_type == t.TYPE_ZBOSS_NCP_API_HL
    )
    assert (
            reassembled_frame.ll_header.flags ==
            (t.LLFlags.FirstFrag | t.LLFlags.LastFrag)
    )

    # Verify the reassembled data matches the original data
    reassembled_data = reassembled_frame.hl_packet.data
    assert reassembled_data == large_data
