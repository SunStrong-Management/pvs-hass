"""Tests for setting up the PVS integration."""

from http import HTTPStatus

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.sunstrong_pvs.const import DOMAIN
from homeassistant.config_entries import SOURCE_REAUTH, ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from .conftest import MockPVS


@pytest.mark.parametrize("pvs_variables", ["pvs6", "pvs5"], indirect=True)
async def test_setup_and_unload(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Test setting up and unloading a PVS6 and a PVS5."""
    assert init_integration.state is ConfigEntryState.LOADED

    await hass.config_entries.async_unload(init_integration.entry_id)
    await hass.async_block_till_done()

    assert init_integration.state is ConfigEntryState.NOT_LOADED


@pytest.mark.parametrize("pvs_variables", ["pvs6", "pvs5"], indirect=True)
@pytest.mark.usefixtures("init_integration")
async def test_gateway_device(
    hass: HomeAssistant,
    device_registry: dr.DeviceRegistry,
    mock_config_entry: MockConfigEntry,
    serial_number: str,
) -> None:
    """Test the gateway device is named after the serial number."""
    device = device_registry.async_get_device_by_identifier(
        (DOMAIN, serial_number), mock_config_entry.entry_id
    )

    assert device is not None
    assert device.name == f"PVS {serial_number}"
    assert device.serial_number == serial_number


async def test_setup_cannot_connect(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_pvs: MockPVS
) -> None:
    """Test setup is retried when the PVS cannot be reached."""
    mock_pvs.reachable = False
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.SETUP_RETRY


async def test_setup_invalid_auth(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_pvs: MockPVS
) -> None:
    """Test a rejected password starts a reauth flow."""
    mock_pvs.login_status = HTTPStatus.UNAUTHORIZED
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.SETUP_ERROR
    flows = hass.config_entries.flow.async_progress_by_handler(DOMAIN)
    assert [flow["context"]["source"] for flow in flows] == [SOURCE_REAUTH]
