"""Module defining struct types."""
import zigpy.types as t
from . import basic


class SimpleDescriptor(t.Struct):
    """Class representing a zigbee simple descriptor."""

    endpoint: t.uint8_t
    profile: t.uint16_t
    device_type: t.uint16_t
    device_version: t.uint8_t
    input_clusters_count: t.uint8_t
    output_clusters_count: t.uint8_t
    input_clusters: t.List[t.uint16_t]
    output_clusters: t.List[t.uint16_t]

    @classmethod
    def deserialize(cls, data):
        """Deserialize data."""
        desc, data = super().deserialize(data)
        data = t.List[t.uint16_t](
            desc.input_clusters[
                desc.input_clusters_count + desc.output_clusters_count:
            ]
        ).serialize()
        desc.output_clusters = desc.input_clusters[
            desc.input_clusters_count:
                desc.input_clusters_count + desc.output_clusters_count
        ]
        desc.input_clusters = desc.input_clusters[0: desc.input_clusters_count]
        return (desc, data)


class KeyType(basic.enum8):
    """Enum class for a key type."""

    NONE = 0

    # Standard Network Key
    NWK = 1
    # Application Master Key
    APP_MASTER = 2
    # Application Link Key
    APP_LINK = 3
    # Trust Center Link Key
    TC_LINK = 4

    # XXX: just "6" in the Z-Stack source
    UNKNOWN_6 = 6
