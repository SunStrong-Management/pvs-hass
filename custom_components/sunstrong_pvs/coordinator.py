"""The PVS coordinator component."""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any

from pypvs.pvs import PVS
from pypvs.pvs_websocket import ConnectionState
from pypvs.exceptions import PVSError

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_HOST,
    CONF_NAME,
    EVENT_HOMEASSISTANT_STOP,
    EVENT_HOMEASSISTANT_STARTED,
)
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    INVALID_AUTH_ERRORS,
    OPTION_UPDATE_PERIOD_S,
    OPTION_UPDATE_PERIOD_S_DEFAULT_VALUE,
    OPTION_ENABLE_LIVE_DATA,
    OPTION_ENABLE_LIVE_DATA_DEFAULT_VALUE,
)

_LOGGER = logging.getLogger(__name__)


type PVSConfigEntry = ConfigEntry[PVSUpdateCoordinator]


class PVSUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """DataUpdateCoordinator to gather data from any PVS."""

    pvs_serial_number: str
    pvs_firmware: str

    def __init__(self, hass: HomeAssistant, pvs: PVS, entry: PVSConfigEntry) -> None:
        """Initialize DataUpdateCoordinator for the PVS."""
        self.pvs = pvs
        entry_data = entry.data
        self.entry = entry
        self._setup_complete = False
        self.pvs_firmware = ""

        # WebSocket for live data — use pvs.get_websocket() so the
        # enable_callback is wired up and telemetry is re-enabled on
        # each connection attempt.
        self._websocket = pvs.get_websocket() if entry.data.get(CONF_HOST) else None
        self._websocket_listener_remove: CALLBACK_TYPE | None = None
        self._websocket_state_listener_remove: CALLBACK_TYPE | None = None
        self._stop_listener: CALLBACK_TYPE | None = None
        self._started_listener_remove: CALLBACK_TYPE | None = None
        self._websocket_task: asyncio.Task | None = None

        # Track live data entity listeners by var_name for granular updates
        self._live_data_listeners: dict[str, list[CALLBACK_TYPE]] = {}

        super().__init__(
            hass,
            _LOGGER,
            name=entry_data[CONF_NAME],
            update_interval=self._get_update_interval(),
            always_update=False,
        )

        # Listen for Home Assistant stop event to ensure cleanup
        self._stop_listener = hass.bus.async_listen_once(
            EVENT_HOMEASSISTANT_STOP, self._async_ha_stop_listener
        )

    def _get_update_interval(self) -> timedelta:
        """Get new update interval."""
        scan_interval_s = self.entry.options.get(
            OPTION_UPDATE_PERIOD_S, OPTION_UPDATE_PERIOD_S_DEFAULT_VALUE
        )
        return timedelta(seconds=scan_interval_s)

    @property
    def live_data(self):
        """Return current live data from websocket."""
        if self._websocket:
            return self._websocket.live_data
        return None

    @property
    def websocket_connected(self) -> bool:
        """Return True if websocket is connected."""
        return self._websocket is not None and self._websocket.is_connected

    @callback
    def _async_mark_setup_complete(self) -> None:
        """Mark setup as complete and setup live data if needed."""
        self._setup_complete = True
        self._async_setup_live_data_tracker()

    @callback
    def _async_setup_live_data_tracker(self) -> None:
        """Set up live data tracking if enabled."""
        live_data_enabled = self.entry.options.get(
            OPTION_ENABLE_LIVE_DATA, OPTION_ENABLE_LIVE_DATA_DEFAULT_VALUE
        )

        if live_data_enabled and self._websocket:
            # Only start if not already connected
            if not self._websocket.is_connected:
                if self.hass.is_running:
                    self._websocket_task = self.hass.async_create_task(
                        self._async_start_websocket()
                    )
                else:
                    # Cancel any existing listener before adding new one
                    if self._started_listener_remove:
                        self._started_listener_remove()
                    self._started_listener_remove = self.hass.bus.async_listen_once(
                        EVENT_HOMEASSISTANT_STARTED,
                        self._async_ha_started_listener,
                    )
        else:
            # Live data disabled, stop websocket if running
            self._async_stop_live_data_tracking()

    @callback
    def _async_stop_live_data_tracking(self) -> None:
        """Stop live data tracking."""
        # Cancel pending startup task
        if self._websocket_task and not self._websocket_task.done():
            self._websocket_task.cancel()
            self._websocket_task = None

        # Cancel started listener
        if self._started_listener_remove:
            self._started_listener_remove()
            self._started_listener_remove = None

        # Remove websocket listeners
        if self._websocket_listener_remove:
            self._websocket_listener_remove()
            self._websocket_listener_remove = None

        if self._websocket_state_listener_remove:
            self._websocket_state_listener_remove()
            self._websocket_state_listener_remove = None

        # Schedule disconnect (don't await in callback)
        if self._websocket and self._websocket.is_connected:
            self.hass.async_create_task(self._async_disconnect_websocket())

    async def _async_disconnect_websocket(self) -> None:
        """Disconnect websocket and wait for completion."""
        if self._websocket:
            await self._websocket.disconnect()

    async def _async_start_websocket(self) -> None:
        """Start WebSocket connection."""
        if not self._websocket:
            return

        # Remove any existing listeners before adding new ones
        if self._websocket_listener_remove:
            self._websocket_listener_remove()
        if self._websocket_state_listener_remove:
            self._websocket_state_listener_remove()

        # Add listeners and track removal functions
        self._websocket_listener_remove = self._websocket.add_listener(
            self._handle_live_data_update
        )
        self._websocket_state_listener_remove = self._websocket.add_state_listener(
            self._handle_websocket_state_change
        )

        await self._websocket.connect()

    @callback
    def _handle_websocket_state_change(self, state: ConnectionState) -> None:
        """Handle websocket connection state changes."""
        if state == ConnectionState.CONNECTED:
            _LOGGER.info("Live data websocket connected")
        elif state == ConnectionState.DISCONNECTED:
            _LOGGER.debug("Live data websocket disconnected")
        elif state == ConnectionState.CONNECTING:
            _LOGGER.debug("Live data websocket connecting...")

    @callback
    def _handle_live_data_update(self, changed_vars: set[str]) -> None:
        """Handle live data updates from websocket."""
        self._async_notify_live_data_listeners(changed_vars)

    @callback
    def async_add_live_data_listener(
        self, var_name: str, update_callback: CALLBACK_TYPE
    ) -> CALLBACK_TYPE:
        """Add a listener for a specific live data variable.

        Returns a callback to remove the listener.
        """
        if var_name not in self._live_data_listeners:
            self._live_data_listeners[var_name] = []

        self._live_data_listeners[var_name].append(update_callback)

        def remove_listener() -> None:
            if var_name in self._live_data_listeners:
                try:
                    self._live_data_listeners[var_name].remove(update_callback)
                except ValueError:
                    pass  # Already removed
                if not self._live_data_listeners[var_name]:
                    del self._live_data_listeners[var_name]

        return remove_listener

    @callback
    def _async_notify_live_data_listeners(self, changed_vars: set[str]) -> None:
        """Notify only the listeners for variables that changed."""
        for var_name in changed_vars:
            if var_name in self._live_data_listeners:
                # Iterate over a copy to handle removals during iteration
                for update_callback in list(self._live_data_listeners[var_name]):
                    try:
                        update_callback()
                    except Exception:
                        _LOGGER.exception("Error in live data listener callback")

    async def _async_setup_and_authenticate(self) -> None:
        """Set up and authenticate with the PVS."""
        pvs = self.pvs

        await pvs.setup()

        assert pvs._firmware.serial is not None
        self.pvs_serial_number = pvs._firmware.serial

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch all device and sensor data from api."""
        pvs = self.pvs

        # get new update interval if changed
        self.update_interval = self._get_update_interval()

        for tries in range(2):
            try:
                if not self._setup_complete:
                    await self._async_setup_and_authenticate()
                    self._async_mark_setup_complete()
                pvs_data = await pvs.update()
            except INVALID_AUTH_ERRORS as err:
                if self._setup_complete and tries == 0:
                    self._setup_complete = False
                    continue
                raise ConfigEntryAuthFailed from err
            except PVSError as err:
                raise UpdateFailed(f"Error communicating with API: {err}") from err

            _LOGGER.debug("PVS data: %s", pvs_data)
            return pvs_data.raw

        raise RuntimeError("Unreachable code in _async_update_data")

    async def async_shutdown(self) -> None:
        """Shutdown the coordinator."""
        # Stop live data tracking (removes listeners, cancels tasks)
        self._async_stop_live_data_tracking()

        # Wait for websocket disconnect to complete
        if self._websocket:
            await self._websocket.disconnect()

        # Remove stop listener
        if self._stop_listener:
            self._stop_listener()
            self._stop_listener = None

        await super().async_shutdown()

    @callback
    def _async_ha_started_listener(self, event) -> None:
        """Handle Home Assistant started event."""
        self._started_listener_remove = None  # Listener auto-removes after firing
        self._websocket_task = self.hass.async_create_task(
            self._async_start_websocket()
        )

    @callback
    def _async_ha_stop_listener(self, event) -> None:
        """Handle Home Assistant stop event."""
        self.hass.async_create_task(self.async_shutdown())

    @callback
    def should_reload_on_options_update(self) -> bool:
        """Return True if the live data option changed (requires entity reload)."""
        new_live_data = self.entry.options.get(
            OPTION_ENABLE_LIVE_DATA, OPTION_ENABLE_LIVE_DATA_DEFAULT_VALUE
        )
        return new_live_data != self.websocket_connected

    @callback
    def async_update_options(self) -> None:
        """Update options that don't require a reload (e.g. poll interval)."""
        self.update_interval = self._get_update_interval()
