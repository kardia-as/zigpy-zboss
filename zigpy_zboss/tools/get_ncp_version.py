"""Script to print the NCP firmware version."""
import asyncio
import sys

import serialx

from zigpy_zboss.api import ZBOSS
from zigpy_zboss.tools.config import get_config


async def get_ncp_version(config):
    """Get the NCP firmware version."""
    zboss = ZBOSS(config)
    await zboss.connect()
    version = await zboss.version()
    print("Current NCP versions: \n"
          f"FW: {version[0]}\n"
          f"Stack: {version[1]}\n"
          f"Protocol: {version[2]}\n")


async def main(argv):
    """Get config and print NCP firmware version."""
    config = get_config(argv)

    try:
        await get_ncp_version(config)
    except serialx.SerialException as exc:
        print(f"Failed to get NCP version! {exc}")
    except RuntimeError as exc2:
        print(
            f"Failed to get NCP version! {exc2}\n"
            "Power cycle the module and try again."
        )


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1:]))
