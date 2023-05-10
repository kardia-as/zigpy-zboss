"""Zigpy nrf exceptions."""


class InvalidFrame(ValueError):
    """Invalid frame."""


class SecurityError(Exception):
    """Security error."""


class CommandNotRecognized(Exception):
    """Command not recognized."""


class ModuleHardwareResetError(Exception):
    """Module hardware reset error."""


class NrfResponseError(Exception):
    """nRF response error."""
