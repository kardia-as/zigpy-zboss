import pytest
import zigpy_zboss.types as t
from zigpy_zboss.frames import Frame, InvalidFrame, CRC8, HLPacket


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
