"""Script to print the NCP firmware version."""
import serial
import asyncio

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


if __name__ == "__main__":
    config = get_config()
    try:
        asyncio.run(get_ncp_version(config))
    except serial.serialutil.SerialException as exc:
        print(f"Failed to get NCP version! {exc}")
    except RuntimeError as exc2:
        print(
            f"Failed to get NCP version! {exc2}\n"
            "Power cycle the module and try again."
        )
