import keyword

from collections import defaultdict

import pytest

import zigpy_zboss.commands as c
from zigpy_zboss import types as t


def _validate_schema(schema):
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
    # Example for GetModuleVersion which only requires TSN
    c.NcpConfig.GetModuleVersion.Req(TSN=1)

    # Example for invalid param name
    with pytest.raises(KeyError):
        c.NcpConfig.GetModuleVersion.Rsp(asd=123)

    # Example for valid param name but incorrect value (invalid type)
    with pytest.raises(ValueError):
        c.NcpConfig.GetModuleVersion.Rsp(TSN="invalid",
                                         StatusCat=t.StatusCategory(1),
                                         StatusCode=20,
                                         FWVersion=123456,
                                         StackVersion=789012,
                                         ProtocolVersion=345678
                                         )

    # Example for correct command invocation
    valid_rsp = c.NcpConfig.GetModuleVersion.Rsp(TSN=10,
                                                 StatusCat=t.StatusCategory(1),
                                                 StatusCode=20,
                                                 FWVersion=123456,
                                                 StackVersion=789012,
                                                 ProtocolVersion=345678)
    assert isinstance(valid_rsp.FWVersion, t.uint32_t)
    assert isinstance(valid_rsp.StackVersion, t.uint32_t)
    assert isinstance(valid_rsp.ProtocolVersion, t.uint32_t)

    # Example for checking overflow in integer type
    with pytest.raises(ValueError):
        c.NcpConfig.GetModuleVersion.Rsp(TSN=10,
                                         StatusCat=t.StatusCategory(1),
                                         StatusCode=20, FWVersion=10 ** 20,
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
    zigbee_role = c.NcpConfig.GetZigbeeRole.Rsp(TSN=10,
                                                StatusCat=t.StatusCategory(1),
                                                StatusCode=20,
                                                DeviceRole=t.DeviceRole.ZC)
    assert zigbee_role.DeviceRole == t.DeviceRole.ZC

    # Invalid ones cannot
    with pytest.raises(AttributeError):
        print(zigbee_role.Oops)


def test_command_optional_params():
    # Basic response with required parameters only
    basic_ieee_addr_rsp = c.ZDO.IeeeAddrReq.Rsp(
        TSN=10,
        StatusCat=t.StatusCategory(1),
        StatusCode=20,
        RemoteDevIEEE=t.EUI64([00, 11, 22, 33, 44, 55, 66, 77]),
        RemoteDevNWK=t.NWK(0x1234)
    )

    # Full response including optional parameters
    full_ieee_addr_rsp = c.ZDO.IeeeAddrReq.Rsp(
        TSN=10,
        StatusCat=t.StatusCategory(1),
        StatusCode=20,
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
    with pytest.raises(KeyError):
        # Optional params cannot be skipped over
        c.ZDO.IeeeAddrReq.Rsp(
            TSN=10,
            StatusCat=t.StatusCategory(1),
            StatusCode=20,
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
        StatusCode=20,
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
