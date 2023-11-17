"""Zigpy Zboss exceptions."""


class InvalidFrame(ValueError):
    """Invalid frame."""


class SecurityError(Exception):
    """Security error."""


class CommandNotRecognized(Exception):
    """Command not recognized."""


class ModuleHardwareResetError(Exception):
    """Module hardware reset error."""


class ZbossResponseError(Exception):
    """ZBOSS response error."""
