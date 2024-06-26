"""Test commands."""
import dataclasses
import keyword
from collections import defaultdict

import pytest

import zigpy_zboss.commands as c
from zigpy_zboss import types as t


def _validate_schema(schema):
    """Validate the schema for command parameters."""
    for index, param in enumerate(schema):
        assert isinstance(param.name, str)
        assert param.name.isidentifier()
        assert not keyword.iskeyword(param.name)
        assert isinstance(param.type, type)
        assert isinstance(param.description, str)

        # All optional params must be together at the end
        if param.optional:
            assert all(p.optional for p in schema[index:])


def test_commands_schema():
    """Test the schema of all commands."""
    commands_by_id = defaultdict(list)

    for commands in c.ALL_COMMANDS:
        for cmd in commands:
            if cmd.definition.control_type == t.ControlType.REQ:
                assert cmd.type == cmd.Req.header.control_type
                assert cmd.Rsp.header.control_type == t.ControlType.RSP

                assert isinstance(cmd.Req.header, t.HLCommonHeader)
                assert isinstance(cmd.Rsp.header, t.HLCommonHeader)

                assert cmd.Req.Rsp is cmd.Rsp
                assert cmd.Rsp.Req is cmd.Req
                assert cmd.Ind is None

                _validate_schema(cmd.Req.schema)
                _validate_schema(cmd.Rsp.schema)

                commands_by_id[cmd.Req.header].append(cmd.Req)
                commands_by_id[cmd.Rsp.header].append(cmd.Rsp)

            elif cmd.type == t.ControlType.IND:
                assert cmd.Req is None
                assert cmd.Rsp is None

                assert cmd.type == cmd.Ind.header.control_type

                assert cmd.Ind.header.control_type == t.ControlType.IND

                assert isinstance(cmd.Ind.header, t.HLCommonHeader)

                _validate_schema(cmd.Ind.schema)

                commands_by_id[cmd.Ind.header].append(cmd.Ind)
            else:
                assert False, "Command has unknown type"  # noqa: B011

    duplicate_commands = {
        cmd: commands for cmd,
        commands in commands_by_id.items() if len(commands) > 1
    }
    assert not duplicate_commands

    assert len(commands_by_id.keys()) == len(c.COMMANDS_BY_ID.keys())


def test_command_param_binding():
    """Test if commands match correctly."""
    # Example for GetModuleVersion which only requires TSN
    c.NcpConfig.GetModuleVersion.Req(TSN=1)

    # Example for invalid param name
    with pytest.raises(KeyError):
        c.NcpConfig.GetModuleVersion.Rsp(asd=123)

    # Example for valid param name but incorrect value (invalid type)
    with pytest.raises(ValueError):
        c.NcpConfig.GetModuleVersion.Rsp(TSN="invalid",
                                         StatusCat=t.StatusCategory(1),
                                         StatusCode=t.StatusCodeGeneric.OK,
                                         FWVersion=123456,
                                         StackVersion=789012,
                                         ProtocolVersion=345678
                                         )

    # Example for correct command invocation
    valid_rsp = c.NcpConfig.GetModuleVersion.Rsp(
        TSN=10,
        StatusCat=t.StatusCategory(1),
        StatusCode=t.StatusCodeGeneric.OK,
        FWVersion=123456,
        StackVersion=789012,
        ProtocolVersion=345678
    )
    assert isinstance(valid_rsp.FWVersion, t.uint32_t)
    assert isinstance(valid_rsp.StackVersion, t.uint32_t)
    assert isinstance(valid_rsp.ProtocolVersion, t.uint32_t)

    # Example for checking overflow in integer type
    with pytest.raises(ValueError):
        c.NcpConfig.GetModuleVersion.Rsp(TSN=10,
                                         StatusCat=t.StatusCategory(1),
                                         StatusCode=t.StatusCodeGeneric.OK,
                                         FWVersion=10 ** 20,
                                         StackVersion=789012,
                                         ProtocolVersion=345678)

    # Invalid type in a parameter that expects a specific enum or struct
    with pytest.raises(ValueError):
        c.NcpConfig.SetZigbeeRole.Req(TSN=10,
                                      DeviceRole="invalid type")

    # Coerced numerical type for a command expecting specific struct or uint
    a = c.NcpConfig.SetZigbeeRole.Req(TSN=10,
                                      DeviceRole=t.DeviceRole.ZR)
    b = c.NcpConfig.SetZigbeeRole.Req(TSN=10,
                                      DeviceRole=t.DeviceRole(1))

    assert a == b
    assert a.DeviceRole == b.DeviceRole

    assert (
            type(a.DeviceRole) ==  # noqa: E721
            type(b.DeviceRole) == t.DeviceRole  # noqa: E721
    )

    # Parameters can be looked up by name
    zigbee_role = c.NcpConfig.GetZigbeeRole.Rsp(
        TSN=10,
        StatusCat=t.StatusCategory(1),
        StatusCode=t.StatusCodeGeneric.OK,
        DeviceRole=t.DeviceRole.ZC
    )
    assert zigbee_role.DeviceRole == t.DeviceRole.ZC

    # Invalid ones cannot
    with pytest.raises(AttributeError):
        print(zigbee_role.Oops)


def test_command_optional_params():
    """Test optional parameters."""
    # Basic response with required parameters only
    basic_ieee_addr_rsp = c.ZDO.IeeeAddrReq.Rsp(
        TSN=10,
        StatusCat=t.StatusCategory(1),
        StatusCode=t.StatusCodeGeneric.OK,
        RemoteDevIEEE=t.EUI64([00, 11, 22, 33, 44, 55, 66, 77]),
        RemoteDevNWK=t.NWK(0x1234)
    )

    # Full response including optional parameters
    full_ieee_addr_rsp = c.ZDO.IeeeAddrReq.Rsp(
        TSN=10,
        StatusCat=t.StatusCategory(1),
        StatusCode=t.StatusCodeGeneric.OK,
        RemoteDevIEEE=t.EUI64([00, 11, 22, 33, 44, 55, 66, 77]),
        RemoteDevNWK=t.NWK(0x1234),
        NumAssocDev=5,
        StartIndex=0,
        AssocDevNWKList=[t.NWK(0x0001), t.NWK(0x0002)]
    )

    basic_data = basic_ieee_addr_rsp.to_frame().hl_packet.data
    full_data = full_ieee_addr_rsp.to_frame().hl_packet.data

    # Check if full data contains optional parameters
    assert len(full_data) >= len(basic_data)

    # Basic data should be a prefix of full data
    assert full_data.startswith(basic_data)

    # Deserialization checks
    IeeeAddrReq = c.ZDO.IeeeAddrReq.Rsp
    assert (
            IeeeAddrReq.from_frame(basic_ieee_addr_rsp.to_frame())
            == basic_ieee_addr_rsp
    )
    assert (
            IeeeAddrReq.from_frame(full_ieee_addr_rsp.to_frame())
            == full_ieee_addr_rsp
    )


def test_command_optional_params_failures():
    """Test optional parameters failures."""
    with pytest.raises(KeyError):
        # Optional params cannot be skipped over
        c.ZDO.IeeeAddrReq.Rsp(
            TSN=10,
            StatusCat=t.StatusCategory(1),
            StatusCode=t.StatusCodeGeneric.OK,
            RemoteDevIEEE=t.EUI64([00, 11, 22, 33, 44, 55, 66, 77]),
            RemoteDevNWK=t.NWK(0x1234),
            NumAssocDev=5,
            # StartIndex=0,
            AssocDevNWKList=[t.NWK(0x0001), t.NWK(0x0002)]
        )

    # Unless it's a partial command
    partial = c.ZDO.IeeeAddrReq.Rsp(
        TSN=10,
        StatusCat=t.StatusCategory(1),
        StatusCode=t.StatusCodeGeneric.OK,
        RemoteDevIEEE=t.EUI64([00, 11, 22, 33, 44, 55, 66, 77]),
        RemoteDevNWK=t.NWK(0x1234),
        NumAssocDev=5,
        # StartIndex=0,
        AssocDevNWKList=[t.NWK(0x0001), t.NWK(0x0002)],
        partial=True
    )

    # In which case, it cannot be serialized
    with pytest.raises(ValueError):
        partial.to_frame()


def test_simple_descriptor():
    """Test simple descriptor."""
    lvlist16_type = t.LVList[t.uint16_t]

    simple_descriptor = t.SimpleDescriptor()
    simple_descriptor.endpoint = t.uint8_t(1)
    simple_descriptor.profile = t.uint16_t(260)
    simple_descriptor.device_type = t.uint16_t(257)
    simple_descriptor.device_version = t.uint8_t(0)
    simple_descriptor.input_clusters = lvlist16_type(
        [0, 3, 4, 5, 6, 8, 2821, 1794]
    )
    simple_descriptor.output_clusters_count = t.uint8_t(2)
    simple_descriptor.input_clusters_count = t.uint8_t(8)
    simple_descriptor.output_clusters = lvlist16_type([0x0001, 0x0002])

    c1 = c.ZDO.SimpleDescriptorReq.Rsp(
        TSN=10,
        StatusCat=t.StatusCategory(1),
        StatusCode=t.StatusCodeGeneric.OK,
        SimpleDesc=simple_descriptor,
        NwkAddr=t.NWK(0x1234)
    )

    sp_simple_descriptor = t.SimpleDescriptor()
    sp_simple_descriptor.endpoint = t.uint8_t(1)
    sp_simple_descriptor.profile = t.uint16_t(260)
    sp_simple_descriptor.device_type = t.uint16_t(257)
    sp_simple_descriptor.device_version = t.uint8_t(0)
    sp_simple_descriptor.input_clusters = lvlist16_type(
        [0, 3, 4, 5, 6, 8, 2821, 1794]
    )
    sp_simple_descriptor.output_clusters_count = t.uint8_t(2)
    sp_simple_descriptor.input_clusters_count = t.uint8_t(8)
    sp_simple_descriptor.output_clusters = lvlist16_type([0x0001, 0x0002])

    c2 = c.ZDO.SimpleDescriptorReq.Rsp(
        TSN=10,
        StatusCat=t.StatusCategory(1),
        StatusCode=t.StatusCodeGeneric.OK,
        SimpleDesc=sp_simple_descriptor,
        NwkAddr=t.NWK(0x1234)
    )

    assert c1.to_frame() == c2.to_frame()
    # assert c1 == c2


def test_command_str_repr():
    """Test __str__ and __repr__ methods for commands."""
    command = c.NcpConfig.GetModuleVersion.Req(TSN=1)

    assert repr(command) == str(command)
    assert str([command]) == f"[{str(command)}]"


def test_command_immutability():
    """Test that commands are immutable."""
    command1 = c.ZDO.IeeeAddrReq.Rsp(
        TSN=10,
        StatusCat=t.StatusCategory(1),
        StatusCode=t.StatusCodeGeneric.OK,
        RemoteDevNWK=t.NWK(0x1234),
        NumAssocDev=5,
        StartIndex=0,
        partial=True
    )

    command2 = c.ZDO.IeeeAddrReq.Rsp(
        TSN=10,
        StatusCat=t.StatusCategory(1),
        StatusCode=t.StatusCodeGeneric.OK,
        RemoteDevNWK=t.NWK(0x1234),
        NumAssocDev=5,
        StartIndex=0,
        partial=True
    )

    d = {command1: True}

    assert command1 == command2
    assert command2 in d
    assert {command1: True} == {command2: True}

    with pytest.raises(RuntimeError):
        command1.partial = False

    with pytest.raises(RuntimeError):
        command1.StatusCode = t.StatusCodeGeneric.OK

    with pytest.raises(RuntimeError):
        command1.NumAssocDev = 5

    with pytest.raises(RuntimeError):
        del command1.StartIndex

    assert command1 == command2


def test_command_serialization():
    """Test command serialization."""
    command = c.NcpConfig.GetModuleVersion.Rsp(
        TSN=10,
        StatusCat=t.StatusCategory(1),
        StatusCode=t.StatusCodeGeneric.OK,
        FWVersion=123456,
        StackVersion=789012,
        ProtocolVersion=345678
    )
    frame = command.to_frame()

    assert frame.hl_packet.data == bytes.fromhex(
        "0A010040E20100140A0C004E460500"
    )

    # Partial frames cannot be serialized
    with pytest.raises(ValueError):
        partial1 = c.NcpConfig.GetModuleVersion.Rsp(
            TSN=10,
            StatusCat=t.StatusCategory(1),
            StatusCode=t.StatusCodeGeneric.OK,
            FWVersion=123456,
            # StackVersion=789012,
            ProtocolVersion=345678,
            partial=True
        )

        partial1.to_frame()

    # Partial frames cannot be serialized, even if all params are filled out
    with pytest.raises(ValueError):
        partial2 = c.NcpConfig.GetModuleVersion.Rsp(
            TSN=10,
            StatusCat=t.StatusCategory(1),
            StatusCode=t.StatusCodeGeneric.OK,
            FWVersion=123456,
            StackVersion=789012,
            ProtocolVersion=345678,
            partial=True
        )
        partial2.to_frame()


def test_command_equality():
    """Test command equality."""
    command1 = c.NcpConfig.GetModuleVersion.Rsp(
        TSN=10,
        StatusCat=t.StatusCategory(1),
        StatusCode=t.StatusCodeGeneric.OK,
        FWVersion=123456,
        StackVersion=789012,
        ProtocolVersion=345678
    )

    command2 = c.NcpConfig.GetModuleVersion.Rsp(
        TSN=10,
        StatusCat=t.StatusCategory(1),
        StatusCode=t.StatusCodeGeneric.OK,
        FWVersion=123456,
        StackVersion=789012,
        ProtocolVersion=345678
    )

    command3 = c.NcpConfig.GetModuleVersion.Rsp(
        TSN=20,
        StatusCat=t.StatusCategory(1),
        StatusCode=t.StatusCodeGeneric.OK,
        FWVersion=123456,
        StackVersion=789012,
        ProtocolVersion=345678
    )

    assert command1 == command1
    assert command1.matches(command1)
    assert command2 == command1
    assert command1 == command2

    assert command1 != command3
    assert command3 != command1

    assert command1.matches(command2)  # Matching is a superset of equality
    assert command2.matches(command1)
    assert not command1.matches(command3)
    assert not command3.matches(command1)

    assert not command1.matches(
        c.NcpConfig.GetModuleVersion.Rsp(
            TSN=10,
            StatusCat=t.StatusCategory(1),
            StatusCode=t.StatusCodeGeneric.OK,
            partial=True
        )
    )
    assert c.NcpConfig.GetModuleVersion.Rsp(
        TSN=10,
        StatusCat=t.StatusCategory(1),
        StatusCode=t.StatusCodeGeneric.OK,
        partial=True
    ).matches(command1)

    # parameters can be specified explicitly as None
    assert c.NcpConfig.GetModuleVersion.Rsp(
        TSN=10,
        StatusCat=t.StatusCategory(1),
        StatusCode=t.StatusCodeGeneric.OK,
        StackVersion=None,
        partial=True
    ).matches(command1)
    assert c.NcpConfig.GetModuleVersion.Rsp(
        TSN=10,
        StatusCat=t.StatusCategory(1),
        StatusCode=t.StatusCodeGeneric.OK,
        StackVersion=789012,
        partial=True
    ).matches(command1)
    assert not c.NcpConfig.GetModuleVersion.Rsp(
        TSN=10,
        StatusCat=t.StatusCategory(1),
        StatusCode=t.StatusCodeGeneric.OK,
        StackVersion=79000,
        partial=True
    ).matches(command1)

    # Different frame types do not match, even if they have the same structure
    assert not c.ZDO.MgtLeave.Rsp(TSN=10,
                                  StatusCat=t.StatusCategory(1),
                                  StatusCode=t.StatusCodeGeneric.OK).matches(
        c.ZDO.PermitJoin.Rsp(partial=True)
    )


def test_command_deserialization():
    """Test command deserialization."""
    command = c.NcpConfig.GetModuleVersion.Rsp(
        TSN=10,
        StatusCat=t.StatusCategory(1),
        StatusCode=t.StatusCodeGeneric.OK,
        FWVersion=123456,
        StackVersion=789012,
        ProtocolVersion=345678
    )

    assert type(command).from_frame(command.to_frame()) == command
    assert (
            command.to_frame() ==
            type(command).from_frame(command.to_frame()).to_frame()
    )

    # Deserialization fails if there is unparsed data at the end of the frame
    frame = command.to_frame()
    new_hl_packet = dataclasses.replace(
        frame.hl_packet, data=frame.hl_packet.data + b"\x01"
    )

    # Create a new Frame instance with the updated hl_packet
    bad_frame = dataclasses.replace(frame, hl_packet=new_hl_packet)

    with pytest.raises(ValueError):
        type(command).from_frame(bad_frame)

    # Deserialization fails if you attempt to deserialize the wrong frame
    with pytest.raises(ValueError):
        c.ZDO.MgtLeave.Rsp(TSN=10,
                           StatusCat=t.StatusCategory(1),
                           StatusCode=t.StatusCodeGeneric.OK).from_frame(
            c.ZDO.PermitJoin.Rsp(TSN=10,
                                 StatusCat=t.StatusCategory(1),
                                 StatusCode=t.StatusCodeGeneric.OK).to_frame()
        )
