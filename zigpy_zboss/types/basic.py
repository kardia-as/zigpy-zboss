"""Module defining basic types."""
from __future__ import annotations

import enum

from zigpy_zboss.types.cstruct import CStruct


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


class FixedIntType(int):
    """Class for fized int type."""

    _signed = None
    _size = None

    def __new__(cls, *args, **kwargs):
        """Instantiate object."""
        if cls._signed is None or cls._size is None:
            raise TypeError(f"{cls} is abstract and cannot be created")

        instance = super().__new__(cls, *args, **kwargs)
        instance.serialize()

        return instance

    def __init_subclass__(cls, signed=None, size=None, hex_repr=None) -> None:
        """Define parameters when the class is used as parent."""
        super().__init_subclass__()

        if signed is not None:
            cls._signed = signed

        if size is not None:
            cls._size = size

        if hex_repr:
            fmt = f"0x{{:0{cls._size * 2}X}}"
            cls.__str__ = cls.__repr__ = lambda self: fmt.format(self)
        elif hex_repr is not None and not hex_repr:
            cls.__str__ = super().__str__
            cls.__repr__ = super().__repr__

        # XXX: The enum module uses the first class with __new__ in its
        #      __dict__ as the member type.
        #      We have to ensure this is true for every subclass.
        if "__new__" not in cls.__dict__:
            cls.__new__ = cls.__new__

    def serialize(self) -> bytes:
        """Serialize object."""
        try:
            return self.to_bytes(self._size, "little", signed=self._signed)
        except OverflowError as e:
            # OverflowError is not a subclass of ValueError,
            # making it annoying to catch
            raise ValueError(str(e)) from e

    @classmethod
    def deserialize(cls, data: bytes) -> tuple[FixedIntType, bytes]:
        """Deserialize object."""
        if len(data) < cls._size:
            raise ValueError(f"Data is too short to contain {cls._size} bytes")

        r = cls.from_bytes(data[: cls._size], "little", signed=cls._signed)
        data = data[cls._size:]
        return r, data


class uint_t(FixedIntType, signed=False):
    """Class representing the uint_t type."""


class int_t(FixedIntType, signed=True):
    """Class representing int_t type."""


class int8s(int_t, size=1):
    """Class representing the int8s type."""


class int16s(int_t, size=2):
    """Class representing the int16s type."""


class int24s(int_t, size=3):
    """Class representing the int24s type."""


class int32s(int_t, size=4):
    """Class representing the int32s type."""


class int40s(int_t, size=5):
    """Class representing the int40s type."""


class int48s(int_t, size=6):
    """Class representing the int48s type."""


class int56s(int_t, size=7):
    """Class representing the int56s type."""


class int64s(int_t, size=8):
    """Class representing the int64s type."""


class uint8_t(uint_t, size=1):
    """Class representing the uint8_t type."""


class uint16_t(uint_t, size=2):
    """Class representing the uint16_t type."""


class uint24_t(uint_t, size=3):
    """Class representing the uint24_t type."""


class uint32_t(uint_t, size=4):
    """Class representing the uint32_t type."""


class uint40_t(uint_t, size=5):
    """Class representing the uint40_t type."""


class uint48_t(uint_t, size=6):
    """Class representing the uint48_t type."""


class uint56_t(uint_t, size=7):
    """Class representing the uint56_t type."""


class uint64_t(uint_t, size=8):
    """Class representing the uint64_t type."""


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


def enum_flag_factory(int_type: FixedIntType) -> enum.Flag:
    """Enum flag factory.

    Mixins are broken by Python 3.8.6 so we must dynamically create the enum
    with the appropriate methods but with only one non-Enum parent class.
    """
    class _NewEnum(int_type, enum.Flag):
        # Rebind classmethods to our own class
        _missing_ = classmethod(enum.IntFlag._missing_.__func__)
        _create_pseudo_member_ = classmethod(
            enum.IntFlag._create_pseudo_member_.__func__
        )

        __or__ = enum.IntFlag.__or__
        __and__ = enum.IntFlag.__and__
        __xor__ = enum.IntFlag.__xor__
        __ror__ = enum.IntFlag.__ror__
        __rand__ = enum.IntFlag.__rand__
        __rxor__ = enum.IntFlag.__rxor__
        __invert__ = enum.IntFlag.__invert__

    return _NewEnum


class enum_uint8(uint8_t, enum.Enum):
    """Class representing the enum_uint8 type."""


class enum_uint16(uint16_t, enum.Enum):
    """Class representing the enum_uint16 type."""


class enum_uint24(uint24_t, enum.Enum):
    """Class representing the enum_uint24 type."""


class enum_uint32(uint32_t, enum.Enum):
    """Class representing the enum_uint32 type."""


class enum_uint40(uint40_t, enum.Enum):
    """Class representing the enum_uint40 type."""


class enum_uint48(uint48_t, enum.Enum):
    """Class representing the enum_uint48 type."""


class enum_uint56(uint56_t, enum.Enum):
    """Class representing the enum_uint56 type."""


class enum_uint64(uint64_t, enum.Enum):
    """Class representing the enum_uint64 type."""


class enum_flag_uint8(enum_flag_factory(uint8_t)):
    """Class representing the enum_flag_uint8 type."""


class enum_flag_uint16(enum_flag_factory(uint16_t)):
    """Class representing the enum_flag_uint16 type."""


class enum_flag_uint24(enum_flag_factory(uint24_t)):
    """Class representing the enum_flag_uint24 type."""


class enum_flag_uint32(enum_flag_factory(uint32_t)):
    """Class representing the enum_flag_uint32 type."""


class enum_flag_uint40(enum_flag_factory(uint40_t)):
    """Class representing the enum_flag_uint40 type."""


class enum_flag_uint48(enum_flag_factory(uint48_t)):
    """Class representing the enum_flag_uint48 type."""


class enum_flag_uint56(enum_flag_factory(uint56_t)):
    """Class representing the enum_flag_uint56 type."""


class enum_flag_uint64(enum_flag_factory(uint64_t)):
    """Class representing the enum_flag_uint64 type."""
