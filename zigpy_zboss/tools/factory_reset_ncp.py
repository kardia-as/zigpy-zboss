"""Script to factory reset the coordinator."""
import serial
import asyncio

from zigpy_zboss.api import NRF
from zigpy_zboss import types as t

from zigpy_zboss.tools.config import get_config


async def factory_reset_ncp(config):
    """Send factory reset command to NCP."""
    nrf = NRF(config)
    await nrf.connect()
    await nrf.reset(option=t.ResetOptions(2))


if __name__ == "__main__":
    config = get_config()
    try:
        asyncio.run(factory_reset_ncp(config))
        print("Coordinator successfully factory reset!")
    except serial.serialutil.SerialException as exc:
        print(f"Failed to factory reset coordinator! {exc}")
    except RuntimeError as exc2:
        print(
            f"Failed to factory reset coordinator! {exc2}\n"
            "Power cycle the module and try again."
        )
