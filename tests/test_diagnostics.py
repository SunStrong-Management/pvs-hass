"""Tests for the PVS diagnostics."""

import json

from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.components.diagnostics import (
    get_diagnostics_for_config_entry,
)
from pytest_homeassistant_custom_component.typing import ClientSessionGenerator
from syrupy.assertion import SnapshotAssertion
from syrupy.filters import props

from homeassistant.core import HomeAssistant


async def test_diagnostics(
    hass: HomeAssistant,
    hass_client: ClientSessionGenerator,
    init_integration: MockConfigEntry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test the diagnostics of a PVS6."""
    assert await get_diagnostics_for_config_entry(
        hass, hass_client, init_integration
    ) == snapshot(exclude=props("created_at", "modified_at", "entry_id"))


async def test_diagnostics_redacted(
    hass: HomeAssistant,
    hass_client: ClientSessionGenerator,
    init_integration: MockConfigEntry,
    pvs_variables: dict[str, str],
) -> None:
    """Test the diagnostics contain no serial numbers or MAC addresses."""
    identifiers = [
        value
        for name, value in pvs_variables.items()
        if name.endswith(("/sn", "/serialnum", "/lmac"))
    ]
    diagnostics = json.dumps(
        await get_diagnostics_for_config_entry(hass, hass_client, init_integration)
    )

    assert [identifier for identifier in identifiers if identifier in diagnostics] == []
