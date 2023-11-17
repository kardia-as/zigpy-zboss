"""NCP NVRAM related helpers."""
import logging

import zigpy_zboss.types as t
import zigpy_zboss.commands as c

LOGGER = logging.getLogger(__name__)
WRITE_DS_LENGTH = 280


class NVRAMHelper:
    """Class used for NVRAM read/write."""

    def __init__(self, zboss):
        """Create class object."""
        self.zboss = zboss

    async def read(self, nv_id: t.DatasetId, item_type):
        """Read a NVRAM dataset."""
        res = await self.zboss.request(
            c.NcpConfig.ReadNVRAM.Req(
                TSN=self.zboss._app.get_sequence(),
                DatasetId=nv_id
            )
        )
        if res.StatusCode != 0:
            return

        if not res.DatasetId == nv_id:
            raise

        if item_type:
            value, _ = item_type.deserialize(res.Dataset.serialize())
            LOGGER.debug('Read NVRAM [0x%04x] = %r', nv_id.value, value)
            return value

    async def write(self, nv_id: t.DatasetId, dataset_obj):
        """Try to write a NVRAM dataset."""
        padding = bytes()
        serialized_ds_obj = dataset_obj.serialize()[2:]
        for _ in range(WRITE_DS_LENGTH - len(serialized_ds_obj)):
            padding += b'\x00'
        dataset = t.NVRAMDataset(serialized_ds_obj + padding)

        await self.zboss.request(
            c.NcpConfig.WriteNVRAM.Req(
                TSN=self.zboss._app.get_sequence(),
                DatasetCnt=1,
                DatasetId=nv_id,
                Version=dataset_obj.version,
                Dataset=dataset
            )
        )
