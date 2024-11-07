"""Module responsible for configuration."""
import typing

import voluptuous as vol
from zigpy.config import (CONF_DEVICE, CONF_DEVICE_PATH,  # noqa: F401
                          CONF_NWK, CONF_NWK_CHANNEL, CONF_NWK_CHANNELS,
                          CONF_NWK_EXTENDED_PAN_ID, CONF_NWK_KEY,
                          CONF_NWK_KEY_SEQ, CONF_NWK_PAN_ID,
                          CONF_NWK_TC_ADDRESS, CONF_NWK_TC_LINK_KEY,
                          CONF_NWK_UPDATE_ID, CONFIG_SCHEMA, SCHEMA_DEVICE,
                          cv_boolean)

LOG_FILE_NAME = "zigpy-zboss.log"
SERIAL_LOG_FILE_NAME = "serial-zigpy-zboss.log"

ConfigType = typing.Dict[str, typing.Any]

CONF_ZBOSS_CONFIG = "zboss_config"
CONFIG_SCHEMA = CONFIG_SCHEMA.extend(
    {
        vol.Optional(CONF_ZBOSS_CONFIG, default={}): vol.Schema(),
    }
)
