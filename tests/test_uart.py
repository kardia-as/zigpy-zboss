"""Test uart."""
import pytest
from serial_asyncio import SerialTransport

import zigpy_zboss.commands as c
import zigpy_zboss.config as conf
import zigpy_zboss.types as t
from zigpy_zboss import uart as zboss_uart
from zigpy_zboss.checksum import CRC8
from zigpy_zboss.frames import Frame


@pytest.fixture
def connected_uart(mocker):
    """Uart connected fixture."""
    zboss = mocker.Mock()
    config = {
        conf.CONF_DEVICE_PATH: "/dev/ttyFAKE0",
        conf.CONF_DEVICE_BAUDRATE: 115200,
        conf.CONF_DEVICE_FLOW_CONTROL: None}

    uart = zboss_uart.ZbossNcpProtocol(config, zboss)
    uart.connection_made(mocker.Mock())

    yield zboss, uart


def ll_checksum(frame):
    """Return frame with new crc8 checksum calculation."""
    crc = CRC8(frame.ll_header.serialize()[2:6]).digest()
    frame.ll_header = frame.ll_header.with_crc8(crc)
    return frame


@pytest.fixture
def dummy_serial_conn(event_loop, mocker):
    """Connect serial dummy."""
    device = "/dev/ttyACM0"

    serial_interface = mocker.Mock()
    serial_interface.name = device

    def create_serial_conn(loop, protocol_factory, url, *args, **kwargs):
        fut = event_loop.create_future()
        assert url == device

        protocol = protocol_factory()

        # Our event loop doesn't really do anything
        event_loop.add_writer = lambda *args, **kwargs: None
        event_loop.add_reader = lambda *args, **kwargs: None
        event_loop.remove_writer = lambda *args, **kwargs: None
        event_loop.remove_reader = lambda *args, **kwargs: None

        transport = SerialTransport(event_loop, protocol, serial_interface)

        protocol.connection_made(transport)

        fut.set_result((transport, protocol))

        return fut

    mocker.patch(
        "zigpy.serial.pyserial_asyncio.create_serial_connection",
        new=create_serial_conn
    )

    return device, serial_interface


def test_uart_rx_basic(connected_uart):
    """Test UART basic receive."""
    zboss, uart = connected_uart

    test_command = c.NcpConfig.GetZigbeeRole.Rsp(
            TSN=10,
            StatusCat=t.StatusCategory(1),
            StatusCode=t.StatusCodeGeneric.OK,
            DeviceRole=t.DeviceRole(1)
        )
    test_frame = test_command.to_frame()
    test_frame = ll_checksum(test_frame)
    test_frame_bytes = Frame(
        test_frame.ll_header, test_frame.hl_packet
    ).serialize()

    uart.data_received(test_frame_bytes)

    zboss.frame_received.assert_called_once_with(test_frame)


def test_uart_str_repr(connected_uart):
    """Test uart representation."""
    zboss, uart = connected_uart

    str(uart)
    repr(uart)


def test_uart_rx_byte_by_byte(connected_uart):
    """Test uart RX byte by byte."""
    zboss, uart = connected_uart

    test_command = c.NcpConfig.GetZigbeeRole.Rsp(
            TSN=10,
            StatusCat=t.StatusCategory(1),
            StatusCode=t.StatusCodeGeneric.OK,
            DeviceRole=t.DeviceRole(1)
        )
    test_frame = test_command.to_frame()
    test_frame = ll_checksum(test_frame)
    test_frame_bytes = Frame(
        test_frame.ll_header, test_frame.hl_packet
    ).serialize()

    for byte in test_frame_bytes:
        uart.data_received(bytes([byte]))

    zboss.frame_received.assert_called_once_with(test_frame)


def test_uart_rx_byte_by_byte_garbage(connected_uart):
    """Test uart RX byte by byte garbage."""
    zboss, uart = connected_uart

    test_command = c.NcpConfig.GetZigbeeRole.Rsp(
            TSN=10,
            StatusCat=t.StatusCategory(1),
            StatusCode=t.StatusCodeGeneric.OK,
            DeviceRole=t.DeviceRole(1)
        )
    test_frame = test_command.to_frame()
    test_frame = ll_checksum(test_frame)
    test_frame_bytes = Frame(
        test_frame.ll_header, test_frame.hl_packet
    ).serialize()

    data = b""
    data += bytes.fromhex("58 4a 72 35 51 da 60 ed 1f")
    data += bytes.fromhex("03 6d b6")
    data += bytes.fromhex("ee 90")
    data += test_frame_bytes
    data += bytes.fromhex("00 00")
    data += bytes.fromhex("e4 4f 51 b2 39 4b 8d e3 ca 61")
    data += bytes.fromhex("8c 56 8a 2c d8 22 64 9e 9d 7b")

    # The frame should be parsed identically regardless of framing
    for byte in data:
        uart.data_received(bytes([byte]))

    zboss.frame_received.assert_called_once_with(test_frame)


def test_uart_rx_big_garbage(connected_uart):
    """Test uart RX big garbage."""
    zboss, uart = connected_uart

    test_command = c.NcpConfig.GetZigbeeRole.Rsp(
            TSN=10,
            StatusCat=t.StatusCategory(1),
            StatusCode=t.StatusCodeGeneric.OK,
            DeviceRole=t.DeviceRole(1)
        )
    test_frame = test_command.to_frame()
    test_frame = ll_checksum(test_frame)
    test_frame_bytes = Frame(
        test_frame.ll_header, test_frame.hl_packet
    ).serialize()

    data = b""
    data += bytes.fromhex("58 4a 72 35 51 da 60 ed 1f")
    data += bytes.fromhex("03 6d b6")
    data += bytes.fromhex("ee 90")
    data += test_frame_bytes
    data += bytes.fromhex("00 00")
    data += bytes.fromhex("e4 4f 51 b2 39 4b 8d e3 ca 61")
    data += bytes.fromhex("8c 56 8a 2c d8 22 64 9e 9d 7b")

    # The frame should be parsed identically regardless of framing
    uart.data_received(data)

    zboss.frame_received.assert_called_once_with(test_frame)


def test_uart_rx_corrupted_fcs(connected_uart):
    """Test uart RX corrupted."""
    zboss, uart = connected_uart

    test_command = c.NcpConfig.GetZigbeeRole.Rsp(
            TSN=10,
            StatusCat=t.StatusCategory(1),
            StatusCode=t.StatusCodeGeneric.OK,
            DeviceRole=t.DeviceRole(1)
        )
    test_frame = test_command.to_frame()
    test_frame = ll_checksum(test_frame)
    test_frame_bytes = Frame(
        test_frame.ll_header, test_frame.hl_packet
    ).serialize()

    # Almost, but not quite
    uart.data_received(test_frame_bytes[:-1])
    uart.data_received(b"\x00")

    assert not zboss.frame_received.called


def test_uart_rx_sof_stress(connected_uart):
    """Test uart RX signature stress."""
    zboss, uart = connected_uart

    test_command = c.NcpConfig.GetZigbeeRole.Rsp(
            TSN=10,
            StatusCat=t.StatusCategory(1),
            StatusCode=t.StatusCodeGeneric.OK,
            DeviceRole=t.DeviceRole(1)
        )
    test_frame = test_command.to_frame()
    test_frame = ll_checksum(test_frame)
    test_frame_bytes = Frame(
        test_frame.ll_header, test_frame.hl_packet
    ).serialize()

    # We include an almost-valid frame and many stray SoF markers
    uart.data_received(
        b"\xFE" + b"\xFE" + b"\xFE" + test_frame_bytes[:-1] + b"\x00"
    )
    uart.data_received(b"\xFE\xFE\x00\xFE\x01")
    uart.data_received(
        b"\xFE" + b"\xFE" + b"\xFE" + test_frame_bytes + b"\x00\x00"
    )

    # We should see the valid frame exactly once
    zboss.frame_received.assert_called_once_with(test_frame)


def test_uart_frame_received_error(connected_uart, mocker):
    """Test uart frame received error."""
    zboss, uart = connected_uart
    zboss.frame_received = mocker.Mock(side_effect=RuntimeError("An error"))

    test_command = c.NcpConfig.GetZigbeeRole.Rsp(
            TSN=10,
            StatusCat=t.StatusCategory(1),
            StatusCode=t.StatusCodeGeneric.OK,
            DeviceRole=t.DeviceRole(1)
        )
    test_frame = test_command.to_frame()
    test_frame = ll_checksum(test_frame)
    test_frame_bytes = Frame(
        test_frame.ll_header, test_frame.hl_packet
    ).serialize()

    # Errors thrown by zboss.frame_received should
    # not impact how many frames are handled
    uart.data_received(test_frame_bytes * 3)

    # We should have received all three frames
    assert zboss.frame_received.call_count == 3


@pytest.mark.asyncio
async def test_connection_lost(dummy_serial_conn, mocker, event_loop):
    """Test connection lost."""
    device, _ = dummy_serial_conn

    zboss = mocker.Mock()
    conn_lost_fut = event_loop.create_future()
    zboss.connection_lost = conn_lost_fut.set_result

    protocol = await zboss_uart.connect(
        conf.SCHEMA_DEVICE({conf.CONF_DEVICE_PATH: device}), api=zboss
    )

    exception = RuntimeError("Uh oh, something broke")
    protocol.connection_lost(exception)

    # Losing a connection propagates up to the ZBOSS object
    assert (await conn_lost_fut) == exception


# ToFix: this is not testing the uart test_connection_made method
# @pytest.mark.asyncio
# async def test_connection_made(dummy_serial_conn, mocker):
#     """Test connection made."""
#     device, _ = dummy_serial_conn
#     zboss = mocker.Mock()

#     await zboss_uart.connect(
#         conf.SCHEMA_DEVICE({conf.CONF_DEVICE_PATH: device}), api=zboss
#     )

#     zboss._uart.connection_made.assert_called_once_with()
