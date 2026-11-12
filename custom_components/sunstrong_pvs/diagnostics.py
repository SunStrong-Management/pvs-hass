"""Diagnostics support for PVS."""

from __future__ import annotations

from dataclasses import asdict
import logging
from typing import Any

from homeassistant.components.diagnostics import REDACTED, async_redact_data
from homeassistant.const import CONF_NAME, CONF_PASSWORD
from homeassistant.core import HomeAssistant

from .coordinator import PVSConfigEntry

_LOGGER = logging.getLogger(__name__)

# The name, title and unique ID contain the serial number of the PVS
TO_REDACT_CONFIG = {CONF_NAME, CONF_PASSWORD, "title", "unique_id"}

TO_REDACT_DATA = {"mac", "serial_number", "sn", "/sys/info/lmac"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: PVSConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = entry.runtime_data
    pvs_data = coordinator.pvs.data

    diag: dict[str, Any] = {
        "config_entry": async_redact_data(entry.as_dict(), TO_REDACT_CONFIG),
        "pvs_serial": REDACTED,
        "pvs_firmware": coordinator.pvs_firmware,
        "websocket_connected": coordinator.websocket_connected,
    }

    if pvs_data is None:
        diag["data"] = None
        return diag

    data: dict[str, Any] = {}

    if pvs_data.gateway:
        data["gateway"] = asdict(pvs_data.gateway)

    # Listed instead of keyed by their serial number, which is redacted
    if pvs_data.inverters:
        data["inverters"] = [asdict(inv) for inv in pvs_data.inverters.values()]

    if pvs_data.meters:
        data["meters"] = [asdict(meter) for meter in pvs_data.meters.values()]

    if pvs_data.ess:
        data["ess"] = [asdict(ess) for ess in pvs_data.ess.values()]

    if pvs_data.transfer_switches:
        data["transfer_switches"] = [
            asdict(ts) for ts in pvs_data.transfer_switches.values()
        ]

    data["raw"] = pvs_data.raw

    # Include live data snapshot if websocket is active
    live_data = coordinator.live_data
    if live_data is not None:
        data["live_data"] = asdict(live_data)

    # Fetch telemetry websocket enable state directly from the PVS
    try:
        telemetry_enabled = await coordinator.pvs.getVarserverVar(
            "/sys/telemetryws/enable"
        )
    except Exception:
        _LOGGER.debug("Could not fetch telemetry websocket state", exc_info=True)
        telemetry_enabled = "error"

    diag["telemetry_websocket_enabled"] = telemetry_enabled
    diag["data"] = async_redact_data(data, TO_REDACT_DATA)
    return diag
