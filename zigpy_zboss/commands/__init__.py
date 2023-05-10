"""Module importing all the commands."""
from .af import AF
from .aps import APS
from .zdo import ZDO
from .security import SEC
from .nwk_mgmt import NWK
from .ncp_config import NcpConfig

ALL_COMMANDS = [
    AF,
    APS,
    ZDO,
    SEC,
    NWK,
    NcpConfig
]

COMMANDS_BY_ID = {}

for cmds in ALL_COMMANDS:
    for command in cmds:
        if command.Req is not None:
            COMMANDS_BY_ID[command.Req.header] = command.Req

        if command.Rsp is not None:
            COMMANDS_BY_ID[command.Rsp.header] = command.Rsp

        if command.Ind is not None:
            COMMANDS_BY_ID[command.Ind.header] = command.Ind
