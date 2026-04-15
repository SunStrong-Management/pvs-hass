"""Constants for the Detailed Hello World Push integration."""

from typing import Final
from homeassistant.const import Platform
from pypvs.pvs import PVSAuthenticationError, PVSCommunicationError

# This is the internal name of the integration, it should also match the directory
# name for the integration.
DOMAIN: Final = "sunstrong_pvs"

DEFAULT_NAME: Final = "PVS"

PLATFORMS = [
    # Platform.BINARY_SENSOR,
    Platform.SENSOR,
]

INVALID_AUTH_ERRORS = (PVSAuthenticationError, PVSCommunicationError)

OPTION_UPDATE_PERIOD_S = "update_period_s"
OPTION_UPDATE_PERIOD_S_DEFAULT_VALUE = 10
OPTION_UPDATE_PERIOD_S_MIN_VALUE = 1

OPTION_ENABLE_LIVE_DATA = "enable_live_data"
OPTION_ENABLE_LIVE_DATA_DEFAULT_VALUE = False
