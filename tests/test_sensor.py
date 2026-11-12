"""Tests for the PVS sensors."""

import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    snapshot_platform,
)
from syrupy.assertion import SnapshotAssertion

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er


@pytest.mark.parametrize("pvs_variables", ["pvs6", "pvs5"], indirect=True)
async def test_sensors(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
    init_integration: MockConfigEntry,
) -> None:
    """Test the sensors of a PVS6 and a PVS5."""
    await snapshot_platform(hass, entity_registry, snapshot, init_integration.entry_id)
