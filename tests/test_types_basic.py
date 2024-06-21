"""Test basic types."""
import pytest

import zigpy_zboss.types as t


def test_enum():
    """Test enum."""
    class TestEnum(t.bitmap16):
        ALL = 0xFFFF
        CH_1 = 0x0001
        CH_2 = 0x0002
        CH_3 = 0x0004
        CH_5 = 0x0008
        CH_6 = 0x0010
        CH_Z = 0x8000

    extra = b"The rest of the data\x55\xaa"
    data = b"\x12\x80"

    r, rest = TestEnum.deserialize(data + extra)
    assert rest == extra
    assert r == 0x8012
    assert r == (TestEnum.CH_2 | TestEnum.CH_6 | TestEnum.CH_Z)

    assert r.serialize() == data
    assert TestEnum(0x8012).serialize() == data


def test_int_too_short():
    """Test int too short."""
    with pytest.raises(ValueError):
        t.uint8_t.deserialize(b"")

    with pytest.raises(ValueError):
        t.uint16_t.deserialize(b"\x00")


def test_int_out_of_bounds():
    """Test int out of bounds."""
    with pytest.raises(ValueError):
        t.uint8_t(-1)

    with pytest.raises(ValueError):
        t.uint8_t(0xFF + 1)


def test_bytes():
    """Test bytes."""
    data = b"abcde\x00\xff"

    r, rest = t.Bytes.deserialize(data)
    assert rest == b""
    assert r == data

    assert r.serialize() == data

    assert str(r) == repr(r) == "b'61:62:63:64:65:00:FF'"

    # Ensure we don't make any mistakes formatting the bytes
    all_bytes = t.Bytes(bytes(range(0, 255 + 1)))
    assert str(all_bytes) == (
        "b'00:01:02:03:04:05:06:07:08:09:0A:0B:0C:0D:0E:"
        "0F:10:11:12:13:14:15:16:17:18:19:1A:1B:1C:1D:1E"
        ":1F:20:21:22:23:24:25:26:27:28:29:2A:2B:2C:2D:2"
        "E:2F:30:31:32:33:34:35:36:37:38:39:3A:3B:3C:3D:"
        "3E:3F:40:41:42:43:44:45:46:47:48:49:4A:4B:4C:4D"
        ":4E:4F:50:51:52:53:54:55:56:57:58:59:5A:5B:5C:5"
        "D:5E:5F:60:61:62:63:64:65:66:67:68:69:6A:6B:6C:"
        "6D:6E:6F:70:71:72:73:74:75:76:77:78:79:7A:7B:7C"
        ":7D:7E:7F:80:81:82:83:84:85:86:87:88:89:8A:8B:8"
        "C:8D:8E:8F:90:91:92:93:94:95:96:97:98:99:9A:9B:"
        "9C:9D:9E:9F:A0:A1:A2:A3:A4:A5:A6:A7:A8:A9:AA:AB"
        ":AC:AD:AE:AF:B0:B1:B2:B3:B4:B5:B6:B7:B8:B9:BA:"
        "BB:BC:BD:BE:BF:C0:C1:C2:C3:C4:C5:C6:C7:C8:C9:CA"
        ":CB:CC:CD:CE:CF:D0:D1:D2:D3:D4:D5:D6:D7:D8:D9:"
        "DA:DB:DC:DD:DE:DF:E0:E1:E2:E3:E4:E5:E6:E7:E8:"
        "E9:EA:EB:EC:ED:EE:EF:F0:F1:F2:F3:F4:F5:F6:"
        "F7:F8:F9:FA:FB:FC:FD:FE:FF'"
    )


def test_longbytes():
    """Test long bytes."""
    data = b"abcde\x00\xff" * 50
    extra = b"\xffrest of the data\x00"

    r, rest = t.LongBytes.deserialize(
        len(data).to_bytes(2, "little") + data + extra
    )
    assert rest == extra
    assert r == data

    assert r.serialize() == len(data).to_bytes(
        2, "little"
    ) + data

    with pytest.raises(ValueError):
        t.LongBytes.deserialize(b"\x01")

    with pytest.raises(ValueError):
        t.LongBytes.deserialize(b"\x01\x00")

    with pytest.raises(ValueError):
        t.LongBytes.deserialize(
            len(data).to_bytes(2, "little") + data[:-1]
        )


def test_lvlist():
    """Test lvlist."""
    class TestList(t.LVList, item_type=t.uint8_t, length_type=t.uint8_t):
        pass

    d, r = TestList.deserialize(b"\x0412345")
    assert r == b"5"
    assert d == list(map(ord, "1234"))
    assert TestList.serialize(d) == b"\x041234"

    assert isinstance(d, TestList)

    with pytest.raises(ValueError):
        TestList([1, 2, 0xFFFF, 4]).serialize()


def test_lvlist_too_short():
    """Test lvlist too short."""
    class TestList(t.LVList, item_type=t.uint8_t, length_type=t.uint8_t):
        pass

    with pytest.raises(ValueError):
        TestList.deserialize(b"")

    with pytest.raises(ValueError):
        TestList.deserialize(b"\x04123")


def test_fixed_list():
    """Test fixed list."""
    class TestList(t.FixedList, item_type=t.uint16_t, length=3):
        pass

    with pytest.raises(ValueError):
        r = TestList([1, 2, 3, 0x55AA])
        r.serialize()

    with pytest.raises(ValueError):
        r = TestList([1, 2])
        r.serialize()

    r = TestList([1, 2, 3])

    assert r.serialize() == b"\x01\x00\x02\x00\x03\x00"


def test_fixed_list_deserialize():
    """Test fixed list deserialize."""
    class TestList(t.FixedList, length=3, item_type=t.uint16_t):
        pass

    data = b"\x34\x12\x55\xaa\x89\xab"
    extra = b"\x00\xff"

    r, rest = TestList.deserialize(data + extra)
    assert rest == extra
    assert r[0] == 0x1234
    assert r[1] == 0xAA55
    assert r[2] == 0xAB89


def test_enum_instance_types():
    """Test enum instance."""
    class TestEnum(t.enum8):
        Member = 0x00

    assert TestEnum._member_type_ is t.uint8_t
    assert type(TestEnum.Member.value) is t.uint8_t
