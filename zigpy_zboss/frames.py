"""Frame serialization/deserialization."""
from __future__ import annotations

import dataclasses

import zigpy_zboss.types as t
from zigpy_zboss.exceptions import InvalidFrame
from zigpy_zboss.checksum import CRC8
from zigpy_zboss.checksum import CRC16


class LLHeader(t.uint56_t):
    """Low Level Header class."""

    def __new__(
            cls,
            value: int = 0x00000000000000,
            *,
            sign=None,
            size=None,
            frame_type=None,
            flags=None,
            crc8=None) -> "LLHeader":
        """Create a new low level header object."""
        instance = super().__new__(cls, value)

        if sign is not None:
            instance = instance.with_signature(sign)

        if size is not None:
            instance = instance.with_size(size)

        if frame_type is not None:
            instance = instance.with_type(frame_type)

        if flags is not None:
            instance = instance.with_flags(flags)

        if crc8 is not None:
            instance = instance.with_crc8(crc8)

        return instance

    @property
    def signature(self) -> t.uint16_t:
        """Return the frame signature."""
        return t.uint16_t(self & 0xFFFF)

    @property
    def size(self) -> t.uint16_t:
        """Return the frame size."""
        return t.uint16_t((self >> 16) & 0xFFFF)

    @property
    def frame_type(self) -> t.uint8_t:
        """Return the type of api."""
        return t.uint8_t((self >> 32) & 0xFF)

    @property
    def flags(self) -> t.LLFlags:
        """Return 8 bit flag enum."""
        return t.LLFlags((self >> 40) & 0xFF)

    @property
    def crc8(self) -> t.uint8_t:
        """Return the calculated CRC8 starting from size."""
        return t.uint8_t(self >> 48)

    def with_signature(self, value) -> "LLHeader":
        """Set the frame signature."""
        return type(self)(self & 0xFFFFFFFFFF0000 | (value & 0xFFFF))

    def with_size(self, value) -> "LLHeader":
        """Set the frame size."""
        return type(self)(self & 0xFFFFFF0000FFFF | (value & 0xFFFF) << 16)

    def with_type(self, value) -> "LLHeader":
        """Set the frame type."""
        return type(self)(self & 0xFFFF00FFFFFFFF | (value & 0xFF) << 32)

    def with_flags(self, value) -> "LLHeader":
        """Set the frame flags."""
        return type(self)(self & 0xFF00FFFFFFFFFF | (value & 0xFF) << 40)

    def with_crc8(self, value) -> "LLHeader":
        """Set the header crc8."""
        return type(self)(self & 0x00FFFFFFFFFFFF | (value & 0xFF) << 48)

    def __str__(self) -> str:
        """Return a string representation."""
        return (
            f"{type(self).__name__}("
            f"signature=0x{self.signature:04X}, "
            f"size=0x{self.size:04X}, "
            f"frame_type=0x{self.frame_type:02X}, "
            f"flags=0x{self.flags:02X}, "
            f"crc8=0x{self.crc8:02X}"
            ")"
        )

    __repr__ = __str__


@dataclasses.dataclass(frozen=True)
class HLPacket:
    """High level part of the frame."""

    header: t.HLCommonHeader
    data: t.Bytes

    def __post_init__(self) -> None:
        """Magic method."""
        # We're frozen so `self.header = ...` is disallowed
        if not isinstance(self.header, t.HLCommonHeader):
            object.__setattr__(
                self, "header", t.HLCommonHeader(self.header))

        if not isinstance(self.data, t.Bytes):
            object.__setattr__(self, "data", t.Bytes(self.data))

    @property
    def length(self) -> t.uint8_t:
        """Length of the frame (including HL checksum)."""
        return t.uint8_t(len(self.serialize()))

    @classmethod
    def deserialize(cls, data):
        """Deserialize frame and sanity checks."""
        check, data = t.uint16_t.deserialize(data)

        if not check == CRC16(data).digest():
            raise InvalidFrame("Crc calculation error.")

        header, payload = t.HLCommonHeader.deserialize(data)
        return cls(header, payload)

    def serialize(self) -> bytes:
        """Serialize frame and calculate CRC."""
        hl_checksum = CRC16(
            self.header.serialize() + self.data.serialize()).digest()
        return hl_checksum.serialize() + self.header.serialize() + \
            self.data.serialize()


@dataclasses.dataclass
class Frame:
    """Frame containing low level header and high level packet."""

    ll_header: LLHeader
    hl_packet: HLPacket
    signature: t.uint16_t = dataclasses.field(
        default=t.uint16_t(0xADDE), repr=False)

    @classmethod
    def deserialize(cls, data: bytes) -> tuple[Frame, bytes]:
        """Deserialize frame and sanity check."""
        ll_header, data = LLHeader.deserialize(data)
        if ll_header.signature != cls.signature:
            raise InvalidFrame(
                "Expected frame to start with Signature "
                f"0x{cls.signature:04X}, got 0x{ll_header.signature:04X}"
            )

        ll_checksum = CRC8(ll_header.serialize()[2:6]).digest()
        if ll_checksum != ll_header.crc8:
            raise InvalidFrame(
                f"Invalid frame checksum for data {ll_header}: "
                f"expected 0x{ll_header.crc8:02X}, got 0x{ll_checksum:02X}"
            )
        if ll_header.flags & t.LLFlags.isACK:
            return cls(ll_header, None), data

        length = ll_header.size - 5
        payload, data = data[:length], data[length:]
        hl_packet = HLPacket.deserialize(payload)

        return cls(ll_header, hl_packet), data

    @classmethod
    def ack(cls, ack_seq, retransmit=False):
        """Return an ACK frame."""
        flag = t.LLFlags(ack_seq << 4)
        flag |= t.LLFlags.isACK
        if retransmit:
            flag |= t.LLFlags.Retransmit

        ll_header = (
            LLHeader()
            .with_signature(cls.signature)
            .with_size(5)
            .with_type(t.TYPE_ZBOSS_NCP_API_HL)
            .with_flags(flag)
        )
        crc = CRC8(ll_header.serialize()[2:6]).digest()
        ll_header = ll_header.with_crc8(crc)
        return cls(ll_header, None)

    def serialize(self) -> bytes:
        """Serialize the frame."""
        if self.hl_packet is None:
            return self.ll_header.serialize()
        return self.ll_header.serialize() + self.hl_packet.serialize()

    @property
    def is_ack(self) -> bool:
        """Return True if the frame is an acknowelgement frame."""
        return True if (
            self.ll_header.flags & t.LLFlags.isACK) else False
