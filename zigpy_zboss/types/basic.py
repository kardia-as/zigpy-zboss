"""Module defining basic types."""
from __future__ import annotations
import typing

from zigpy.types import int8s, uint8_t, enum_factory  # noqa: F401

from zigpy_zboss.types.cstruct import CStruct

if typing.TYPE_CHECKING:
    import enum

    class enum8(int, enum.Enum):
        """Enum with 8 bits value."""

    class enum16(int, enum.Enum):
        """Enum with 16 bits value."""

    class enum24(int, enum.Enum):
        """Enum with 24 bits value."""

    class enum40(int, enum.Enum):
        """Enum with 40 bits value."""

    class enum64(int, enum.Enum):
        """Enum with 64 bits value."""

    class bitmap8(enum.IntFlag):
        """Bitmap with 8 bits value."""

    class bitmap16(enum.IntFlag):
        """Bitmap with 16 bits value."""

else:
    from zigpy.types import (  # noqa: F401
        enum8,
        enum16,
        bitmap8,
        bitmap16,
        uint16_t,
        uint24_t,
        uint32_t,
        uint40_t,
        uint56_t,
        uint64_t,
    )

    class enum24(enum_factory(uint24_t)):
        """Enum with 24 bits value."""

    class enum40(enum_factory(uint40_t)):
        """Enum with 40 bits value."""

    class enum64(enum_factory(uint64_t)):
        """Enum with 64 bits value."""


class Bytes(bytes):
    """Class for Bytes representation."""

    def serialize(self) -> Bytes:
        """Serialize object."""
        return self

    @classmethod
    def deserialize(cls, data: bytes) -> tuple[Bytes, bytes]:
        """Deserialize object."""
        return cls(data), b""

    def __repr__(self) -> str:
        """Redefine Bytes representation."""
        # Reading byte sequences like \x200\x21 is extremely annoying
        # compared to \x20\x30\x21
        escaped = "".join(f":{b:02X}" for b in self)[1:]

        return f"b'{escaped}'"

    __str__ = __repr__


class ShortBytes(Bytes):
    """Class representing Bytes with 1 byte header."""

    _header = uint8_t

    def serialize(self) -> Bytes:
        """Serialize object."""
        return self._header(len(self)).serialize() + self

    @classmethod
    def deserialize(cls, data: bytes) -> tuple[Bytes, bytes]:
        """Deserialize object."""
        length, data = cls._header.deserialize(data)
        if length > len(data):
            raise ValueError(
                f"Data is too short to contain {length} bytes of data")
        return cls(data[:length]), data[length:]


class LongBytes(ShortBytes):
    """Class representing Bytes with 2 bytes header."""

    _header = uint16_t


class BaseListType(list):
    """Class defining the list type base."""

    _item_type = None

    @classmethod
    def _serialize_item(cls, item, *, align):
        if not isinstance(item, cls._item_type):
            item = cls._item_type(item)

        if issubclass(cls._item_type, CStruct):
            return item.serialize(align=align)
        else:
            return item.serialize()

    @classmethod
    def _deserialize_item(cls, data, *, align):
        if issubclass(cls._item_type, CStruct):
            return cls._item_type.deserialize(data, align=align)
        else:
            return cls._item_type.deserialize(data)


class LVList(BaseListType):
    """Class representing a list of type with a length header."""

    _header = None

    def __init_subclass__(cls, *, item_type, length_type) -> None:
        """Set class parameter when the class is used as parent."""
        super().__init_subclass__()
        cls._item_type = item_type
        cls._header = length_type

    def serialize(self, *, align=False) -> bytes:
        """Serialize object."""
        assert self._item_type is not None
        return self._header(len(self)).serialize() + b"".join(
            [self._serialize_item(i, align=align) for i in self]
        )

    @classmethod
    def deserialize(cls, data: bytes, *, align=False) -> tuple[LVList, bytes]:
        """Deserialize object."""
        length, data = cls._header.deserialize(data)
        r = cls()
        for i in range(length):
            item, data = cls._deserialize_item(data, align=align)
            r.append(item)
        return r, data


class FixedList(BaseListType):
    """Class representing a fixed list."""

    _length = None

    def __init_subclass__(cls, *, item_type, length) -> None:
        """Set the length when the class is used as parent."""
        super().__init_subclass__()
        cls._item_type = item_type
        cls._length = length

    def serialize(self, *, align=False) -> bytes:
        """Serialize object."""
        assert self._length is not None

        if len(self) != self._length:
            raise ValueError(
                f"Invalid length for {self!r}: expected "
                f"{self._length}, got {len(self)}"
            )

        return b"".join([self._serialize_item(i, align=align) for i in self])

    @classmethod
    def deserialize(
            cls, data: bytes, *, align=False) -> tuple[FixedList, bytes]:
        """Deserialize object."""
        r = cls()
        for i in range(cls._length):
            item, data = cls._deserialize_item(data, align=align)
            r.append(item)
        return r, data


class CompleteList(BaseListType):
    """Class representing a complete list."""

    def __init_subclass__(cls, *, item_type) -> None:
        """Set class parameter when the class is used as parent."""
        super().__init_subclass__()
        cls._item_type = item_type

    def serialize(self, *, align=False) -> bytes:
        """Serialize object."""
        return b"".join([self._serialize_item(i, align=align) for i in self])

    @classmethod
    def deserialize(
            cls, data: bytes, *, align=False) -> tuple[CompleteList, bytes]:
        """Deserialize object."""
        r = cls()
        while data:
            item, data = cls._deserialize_item(data, align=align)
            r.append(item)
        return r, data
