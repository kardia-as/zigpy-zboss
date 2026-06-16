"""Probe the NCP's network keys.

Reads the active network key(s) from the live stack via GetNwkKeys and, for
contrast, attempts to read the ZB_NVRAM_COMMON_DATA dataset directly. Use this
to confirm GetNwkKeys returns a usable key on your hardware - the COMMON_DATA
NVRAM read is the one that intermittently fails with GENERIC/ERROR and leaves
zigpy with a blank network key.

Usage:
    python -m zigpy_zboss.tools.get_nwk_keys [/dev/ttyACM0]
"""
import asyncio
import sys

import serialx

from zigpy_zboss import commands as c
from zigpy_zboss import types as t
from zigpy_zboss.api import ZBOSS
from zigpy_zboss.tools.config import get_config


def _is_blank(key) -> bool:
    """Return True if the key is unset (all 0x00 or all 0xFF) or missing."""
    return key is None or key.serialize() in (b"\xff" * 16, b"\x00" * 16)


async def get_nwk_keys(config):
    """Print the NCP network keys and contrast with the NVRAM read."""
    zboss = ZBOSS(config)
    await zboss.connect()
    try:
        rsp = await zboss.request(c.NcpConfig.GetNwkKeys.Req(TSN=1))
        print(f"GetNwkKeys status: {rsp.StatusCat} {rsp.StatusCode}")
        for idx, (key, num) in enumerate(
            (
                (rsp.NwkKey1, rsp.KeyNumber1),
                (rsp.NwkKey2, rsp.KeyNumber2),
                (rsp.NwkKey3, rsp.KeyNumber3),
            ),
            start=1,
        ):
            tag = "blank" if _is_blank(key) else "REAL"
            print(f"  NwkKey{idx} (seq {num}): {key}  [{tag}]")

        usable = not _is_blank(rsp.NwkKey1)
        print(
            "\nVerdict: GetNwkKeys "
            + (
                "returns a usable network key - the fix will work."
                if usable
                else "did NOT return a usable key on this firmware."
            )
        )

        # Contrast: the COMMON_DATA NVRAM read that intermittently fails.
        nv = await zboss.request(
            c.NcpConfig.ReadNVRAM.Req(
                TSN=2, DatasetId=t.DatasetId.ZB_NVRAM_COMMON_DATA
            )
        )
        print(
            f"\nZB_NVRAM_COMMON_DATA read status: {nv.StatusCat} "
            f"{nv.StatusCode}"
            + ("  (OK)" if nv.StatusCode == 0 else "  (this is the failure)")
        )
    finally:
        zboss.close()


async def main(argv):
    """Get config and print the NCP network keys."""
    config = get_config(argv)

    try:
        await get_nwk_keys(config)
    except serialx.SerialException as exc:
        print(f"Failed to read NCP network keys! {exc}")
    except RuntimeError as exc2:
        print(
            f"Failed to read NCP network keys! {exc2}\n"
            "Power cycle the module and try again."
        )


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1:]))
