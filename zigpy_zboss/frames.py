"""Frame serialization/deserialization."""
from __future__ import annotations

import dataclasses

import zigpy_zboss.types as t
from zigpy_zboss.exceptions import InvalidFrame
from zigpy_zboss.checksum import CRC8
from zigpy_zboss.checksum import CRC16


ZBNCP_LL_BODY_SIZE_MAX = 247  # Check zbncp_ll_pkt.h in ZBOSS NCP host src


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
        if self.header is None:
            pass
        elif not isinstance(self.header, t.HLCommonHeader):
            object.__setattr__(
                self, "header", t.HLCommonHeader(self.header))

        if not isinstance(self.data, t.Bytes):
            object.__setattr__(self, "data", t.Bytes(self.data))

    @property
    def length(self) -> t.uint16_t:
        """Length of the frame (including HL checksum)."""
        return t.uint16_t(len(self.serialize()))

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
        serialized_data = self.data.serialize()
        if self.header:
            serialized_header = self.header.serialize()
            serialized_hl_packet = serialized_header + serialized_data
        else:
            serialized_hl_packet = serialized_data

        hl_checksum = CRC16(serialized_hl_packet).digest()
        return hl_checksum.serialize() + serialized_hl_packet


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
        flags = ll_header.flags

        if flags & t.LLFlags.isACK:
            return cls(ll_header, None), data

        length = ll_header.size - 5
        payload, data = data[:length], data[length:]
        if flags & t.LLFlags.FirstFrag:
            hl_packet = HLPacket.deserialize(payload)
            return cls(ll_header, hl_packet), data

        hl_packet = HLPacket(None, payload)
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

    @classmethod
    def handle_rx_fragmentation(cls, fragments):
        """Return a frame containing merged data from fragments."""
        data = bytes()
        for frag in fragments:
            data += frag.hl_packet.serialize()[2:]
        # Concatenate new CRC.
        data = t.uint16_t(CRC16(data).digest()).serialize() + data
        ll_header = (
            LLHeader()
            .with_signature(Frame.signature)
            .with_size(len(data) + 5)
            .with_type(t.TYPE_ZBOSS_NCP_API_HL)
            .with_flags(t.LLFlags.FirstFrag | t.LLFlags.LastFrag)
        )
        hl_packet = HLPacket.deserialize(data)
        return cls(ll_header, hl_packet)

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

    @property
    def fragmentation_needed(self):
        """Return True if frame fragmentation is needed.

        If a frame is too long, the low level protocol is using fragmentation
        in order to seperate the long frame into smaller fragments.
        """
        return self.count_fragments() > 1

    def count_fragments(self):
        """Count the number of frame fragments."""
        ll_body_size = len(self.hl_packet.serialize()[2:])
        return int(-(-ll_body_size // ZBNCP_LL_BODY_SIZE_MAX))

    def handle_tx_fragmentation(self):
        """Handle frame fragmentation."""
        if not self.fragmentation_needed:
            return [self]

        # Store initial hl packet data without crc.
        serialized_hl_packet = self.hl_packet.serialize()[2:]
        total_size = len(serialized_hl_packet)
        first_frag_size = \
            total_size % ZBNCP_LL_BODY_SIZE_MAX or ZBNCP_LL_BODY_SIZE_MAX

        fragments = []
        frag_idxs = range(first_frag_size, total_size, ZBNCP_LL_BODY_SIZE_MAX)

        for frag_nbr in range(1, self.count_fragments() + 1):
            if frag_nbr == 1:
                frag = self._create_first_frag(first_frag_size)
            elif frag_nbr == self.count_fragments():
                frag = self._create_last_frag(serialized_hl_packet)
            else:
                idx = frag_idxs[frag_nbr - 2]
                frag = self._create_frag(idx, serialized_hl_packet)
            fragments.append(frag)
        return fragments

    def _create_first_frag(self, frag_size):
        """Create the first fragment of a frame."""
        # Sequence flag and CRC8 are set later before sending frame over uart.
        ll_header = (
            LLHeader()
            .with_signature(Frame.signature)
            .with_size(frag_size + 7)
            .with_type(t.TYPE_ZBOSS_NCP_API_HL)
            .with_flags(t.LLFlags.FirstFrag)
        )
        # CRC16 is automatically added when serialize() is called.
        hl_packet = HLPacket(
            self.hl_packet.header, self.hl_packet.data[:(frag_size - 4)])
        return Frame(ll_header, hl_packet)

    def _create_last_frag(self, serialized_hl_packet):
        """Create the last fragment of a frame."""
        # Sequence flag and CRC8 are set later before sending frame over uart.
        ll_header = (
            LLHeader()
            .with_signature(Frame.signature)
            .with_size(ZBNCP_LL_BODY_SIZE_MAX + 7)
            .with_type(t.TYPE_ZBOSS_NCP_API_HL)
            .with_flags(t.LLFlags.LastFrag)
        )
        hl_packet = HLPacket(
            None, serialized_hl_packet[-ZBNCP_LL_BODY_SIZE_MAX:])
        return Frame(ll_header, hl_packet)

    def _create_frag(self, idx, serialized_hl_packet):
        """Create a fragment that is not the first nor the last."""
        # Sequence flag and CRC8 are set later before sending frame over uart.
        ll_header = (
            LLHeader()
            .with_signature(Frame.signature)
            .with_size(ZBNCP_LL_BODY_SIZE_MAX + 7)
            .with_type(t.TYPE_ZBOSS_NCP_API_HL)
        )
        hl_packet = HLPacket(
            None, serialized_hl_packet[idx:(idx + ZBNCP_LL_BODY_SIZE_MAX)])
        return Frame(ll_header, hl_packet)
