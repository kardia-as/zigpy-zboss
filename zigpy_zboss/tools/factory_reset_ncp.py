"""Script to factory reset the coordinator."""
import asyncio
import sys

import serialx

from zigpy_zboss import types as t
from zigpy_zboss.api import ZBOSS
from zigpy_zboss.tools.config import get_config


async def factory_reset_ncp(config):
    """Send factory reset command to NCP."""
    zboss = ZBOSS(config)
    await zboss.connect()
    # The NCP reboots after factory reset; no need to wait for reconnect.
    await zboss.reset(
        option=t.ResetOptions.FactoryReset,
        wait_for_reset=False,
    )


async def main(argv):
    """Get config and factory reset NCP."""
    config = get_config(argv)

    try:
        await factory_reset_ncp(config)
        print("Coordinator successfully factory reset!")
    except serialx.SerialException as exc:
        print(f"Failed to factory reset coordinator! {exc}")
    except (RuntimeError, asyncio.TimeoutError) as exc2:
        print(
            f"Failed to factory reset coordinator! {exc2}\n"
            "Power cycle the module and try again."
        )


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1:]))
