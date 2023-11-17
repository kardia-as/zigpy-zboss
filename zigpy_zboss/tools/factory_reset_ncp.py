"""Script to factory reset the coordinator."""
import sys
import serial
import asyncio

from zigpy_zboss.api import ZBOSS
from zigpy_zboss import types as t

from zigpy_zboss.tools.config import get_config


async def factory_reset_ncp(config):
    """Send factory reset command to NCP."""
    zboss = ZBOSS(config)
    await zboss.connect()
    await zboss.reset(option=t.ResetOptions(2))


async def main(argv):
    """Get config and factory reset NCP."""
    config = get_config(argv)

    try:
        await factory_reset_ncp(config)
        print("Coordinator successfully factory reset!")
    except serial.serialutil.SerialException as exc:
        print(f"Failed to factory reset coordinator! {exc}")
    except RuntimeError as exc2:
        print(
            f"Failed to factory reset coordinator! {exc2}\n"
            "Power cycle the module and try again."
        )


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1:]))
