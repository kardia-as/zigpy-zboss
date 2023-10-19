"""Tools config."""
import os

DEFAULT_SERIAL_ID_DONGLE = 'usb-ZEPHYR_Zigbee_NCP'
PATH_ACM0 = '/dev/ttyACM0'

CONFIG = {
        'device': {
            'path': PATH_ACM0,
            'flow_control': None,
            'baudrate': 115200
        },
    }


def get_serial_by_id_path():
    """Return a /dev/serial/by-id match for given device if available."""
    by_id = "/dev/serial/by-id/"
    if not os.path.isdir(by_id):
        return None

    for path in (
            entry.path for entry in os.scandir(by_id) if entry.is_symlink()):
        if path.startswith(by_id + DEFAULT_SERIAL_ID_DONGLE):
            return path
    return None


def get_config(argv=None):
    """Return the config used to connect to NCP."""
    if argv:
        CONFIG['device']['path'] = argv[0]
    else:
        if path := get_serial_by_id_path():
            CONFIG['device']['path'] = path
    print(f"Path used to connect to NCP: {CONFIG['device']['path']}\n")
    return CONFIG
