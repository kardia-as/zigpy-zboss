import asyncio

import pytest

import zigpy_zboss.types as t
import zigpy_zboss.commands as c
from zigpy_zboss.utils import deduplicate_commands


def test_command_deduplication_simple():
    c1 = c.NcpConfig.GetModuleVersion.Req(TSN=10)
    c2 =  c.NcpConfig.NCPModuleReset.Req(TSN=10,Option=t.ResetOptions(0))

    assert deduplicate_commands([]) == ()
    assert deduplicate_commands([c1]) == (c1,)
    assert deduplicate_commands([c1, c1]) == (c1,)
    assert deduplicate_commands([c1, c2]) == (c1, c2)
    assert deduplicate_commands([c2, c1, c2]) == (c2, c1)


def test_command_deduplication_complex():
    result = deduplicate_commands(
        [
            c.NcpConfig.GetModuleVersion.Rsp(
                TSN=10,
                StatusCat=t.StatusCategory(1),
                StatusCode=20,
                FWVersion=1,
                StackVersion=2,
                ProtocolVersion=3,
            ),
            # Duplicating matching commands shouldn't do anything
            c.NcpConfig.GetModuleVersion.Rsp(partial=True),
            c.NcpConfig.GetModuleVersion.Rsp(partial=True),
            # Matching against different command types should also work
            c.NcpConfig.GetZigbeeRole.Rsp(
                TSN=10,
                StatusCat=t.StatusCategory(1),
                StatusCode=20,
                DeviceRole=t.DeviceRole(1)
            ),
            c.NcpConfig.GetZigbeeRole.Rsp(
                TSN=11,
                StatusCat=t.StatusCategory(2),
                StatusCode=10,
                DeviceRole=t.DeviceRole(2)
            ),
            c.NcpConfig.GetNwkKeys.Rsp(
                partial=True,
                TSN=11,
                StatusCat=t.StatusCategory(2),
                StatusCode=10,
                KeyNumber1=10,
            ),
            c.NcpConfig.GetNwkKeys.Rsp(
                partial=True,
                TSN=11,
                StatusCat=t.StatusCategory(2),
                StatusCode=10,
                KeyNumber1=10,
                KeyNumber2=20,
            ),
            c.NcpConfig.GetNwkKeys.Rsp(
                partial=True,
                TSN=11,
                StatusCat=t.StatusCategory(2),
                StatusCode=10,
                KeyNumber1=10,
                KeyNumber2=20,
                KeyNumber3=30,
            ),
            c.NcpConfig.GetNwkKeys.Rsp(
                partial=True,
                TSN=11,
                StatusCat=t.StatusCategory(2),
                KeyNumber3=30,
            ),
        ]
    )

    assert set(result) == {
        c.NcpConfig.GetModuleVersion.Rsp(partial=True),
        c.NcpConfig.GetZigbeeRole.Rsp(
            TSN=10,
            StatusCat=t.StatusCategory(1),
            StatusCode=20,
            DeviceRole=t.DeviceRole(1)
        ),
        c.NcpConfig.GetZigbeeRole.Rsp(
            TSN=11,
            StatusCat=t.StatusCategory(2),
            StatusCode=10,
            DeviceRole=t.DeviceRole(2)
        ),
        c.NcpConfig.GetNwkKeys.Rsp(
            partial=True,
            TSN=11,
            StatusCat=t.StatusCategory(2),
            StatusCode=10,
            KeyNumber1=10,
        ),
        c.NcpConfig.GetNwkKeys.Rsp(
            partial=True,
            TSN=11,
            StatusCat=t.StatusCategory(2),
            KeyNumber3=30,
        ),
    }