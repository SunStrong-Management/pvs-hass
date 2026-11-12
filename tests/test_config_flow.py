"""Tests for the PVS config flow."""

from http import HTTPStatus
from ipaddress import ip_address
from unittest.mock import AsyncMock

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.sunstrong_pvs.const import (
    DOMAIN,
    OPTION_ENABLE_LIVE_DATA,
    OPTION_UPDATE_PERIOD_S,
)
from homeassistant.config_entries import SOURCE_USER, SOURCE_ZEROCONF
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo

from .conftest import HOST, MockPVS

NEW_HOST = "192.168.1.20"

OTHER_SERIAL = "ZT000000000000X9999"

RELOAD_WARNING = "has an update listener"


def zeroconf_info(host: str) -> ZeroconfServiceInfo:
    """Return a zeroconf announcement with the serial number of another PVS."""
    return ZeroconfServiceInfo(
        ip_address=ip_address(host),
        ip_addresses=[ip_address(host)],
        hostname="pvs.local.",
        name="pvs._pvs6._tcp.local.",
        port=443,
        properties={"serialnum": OTHER_SERIAL},
        type="_pvs6._tcp.local.",
    )


@pytest.mark.usefixtures("mock_pvs")
async def test_user_flow(
    hass: HomeAssistant, mock_setup_entry: AsyncMock, serial_number: str
) -> None:
    """Test adding a PVS by its IP address."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: HOST}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "need_password"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_PASSWORD: "T0001"}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == f"PVS {serial_number}"
    assert result["data"] == {
        CONF_NAME: f"PVS {serial_number}",
        CONF_HOST: HOST,
        CONF_PASSWORD: "T0001",
    }
    assert result["result"].unique_id == serial_number
    assert len(mock_setup_entry.mock_calls) == 1


@pytest.mark.usefixtures("mock_pvs")
async def test_user_flow_already_configured(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Test adding an already configured PVS aborts."""
    mock_config_entry.add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: HOST}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert len(hass.config_entries.async_entries(DOMAIN)) == 1


@pytest.mark.usefixtures("mock_setup_entry")
async def test_user_flow_cannot_connect(hass: HomeAssistant, mock_pvs: MockPVS) -> None:
    """Test an unreachable PVS shows an error and the flow can recover."""
    mock_pvs.reachable = False
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: HOST}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {"base": "cannot_connect"}

    mock_pvs.reachable = True
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: HOST}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_PASSWORD: "T0001"}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY


@pytest.mark.usefixtures("mock_setup_entry")
async def test_user_flow_invalid_auth(hass: HomeAssistant, mock_pvs: MockPVS) -> None:
    """Test a wrong password shows an error and the flow can recover."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: HOST}
    )
    mock_pvs.login_status = HTTPStatus.UNAUTHORIZED
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_PASSWORD: "WRONG"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "need_password"
    assert result["errors"] == {"base": "invalid_auth"}

    mock_pvs.login_status = HTTPStatus.OK
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_PASSWORD: "T0001"}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY


@pytest.mark.usefixtures("mock_pvs")
async def test_zeroconf_flow(
    hass: HomeAssistant, mock_setup_entry: AsyncMock, serial_number: str
) -> None:
    """Test a discovered PVS is added with the serial number it reports itself.

    A PVS can announce the serial number of another PVS on the network.
    """
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_ZEROCONF}, data=zeroconf_info(HOST)
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: HOST}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_PASSWORD: "T0001"}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["result"].unique_id == serial_number
    assert len(mock_setup_entry.mock_calls) == 1


async def test_zeroconf_new_host(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test a configured PVS discovered at a new IP address is updated."""
    coordinator = init_integration.runtime_data
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_ZEROCONF}, data=zeroconf_info(NEW_HOST)
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert init_integration.data[CONF_HOST] == NEW_HOST
    assert init_integration.runtime_data is not coordinator
    assert RELOAD_WARNING not in caplog.text


async def test_zeroconf_cannot_connect(hass: HomeAssistant, mock_pvs: MockPVS) -> None:
    """Test discovery is aborted when the PVS cannot be reached."""
    mock_pvs.reachable = False
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_ZEROCONF}, data=zeroconf_info(HOST)
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "cannot_connect"


async def test_zeroconf_ipv6(hass: HomeAssistant) -> None:
    """Test discovery over IPv6 is ignored."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_ZEROCONF}, data=zeroconf_info("fe80::1")
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "not_ipv4_address"


async def test_reauth_flow(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test reauth stores the new password and reloads the entry."""
    coordinator = init_integration.runtime_data
    result = await init_integration.start_reauth_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: HOST}
    )
    assert result["step_id"] == "need_password"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_PASSWORD: "NEW01"}
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert init_integration.data[CONF_PASSWORD] == "NEW01"
    assert init_integration.runtime_data is not coordinator
    assert RELOAD_WARNING not in caplog.text


async def test_reconfigure_flow(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test reconfigure stores the new host and reloads the entry."""
    coordinator = init_integration.runtime_data
    result = await init_integration.start_reconfigure_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: NEW_HOST}
    )
    assert result["step_id"] == "need_password"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_PASSWORD: "T0001"}
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert init_integration.data[CONF_HOST] == NEW_HOST
    assert init_integration.runtime_data is not coordinator
    assert RELOAD_WARNING not in caplog.text


@pytest.mark.usefixtures("mock_pvs")
async def test_reconfigure_other_pvs(hass: HomeAssistant) -> None:
    """Test reconfigure is aborted when the host is another PVS."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=OTHER_SERIAL,
        data={CONF_NAME: "PVS", CONF_HOST: HOST, CONF_PASSWORD: "X9999"},
    )
    entry.add_to_hass(hass)
    result = await entry.start_reconfigure_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: NEW_HOST}
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "unique_id_mismatch"
    assert entry.data[CONF_HOST] == HOST


@pytest.mark.parametrize(
    "user_input",
    [
        pytest.param(
            {OPTION_UPDATE_PERIOD_S: 60, OPTION_ENABLE_LIVE_DATA: False},
            id="update_period",
        ),
        pytest.param(
            {OPTION_UPDATE_PERIOD_S: 10, OPTION_ENABLE_LIVE_DATA: True},
            id="live_data",
        ),
    ],
)
@pytest.mark.usefixtures("mock_websocket")
async def test_options_flow_reloads(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    user_input: dict[str, int | bool],
) -> None:
    """Test changing an option saves it and reloads the entry."""
    coordinator = init_integration.runtime_data
    result = await hass.config_entries.options.async_init(init_integration.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert init_integration.options == user_input
    assert init_integration.runtime_data is not coordinator


async def test_options_flow_unchanged(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Test saving the default options does not reload the entry."""
    hass.config_entries.async_update_entry(
        init_integration,
        options={OPTION_UPDATE_PERIOD_S: 10, OPTION_ENABLE_LIVE_DATA: False},
    )
    coordinator = init_integration.runtime_data
    result = await hass.config_entries.options.async_init(init_integration.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {OPTION_UPDATE_PERIOD_S: 10, OPTION_ENABLE_LIVE_DATA: False},
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert init_integration.runtime_data is coordinator


async def test_options_flow_min_interval(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Test an update interval below the minimum is rejected."""
    result = await hass.config_entries.options.async_init(init_integration.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {OPTION_UPDATE_PERIOD_S: 0, OPTION_ENABLE_LIVE_DATA: False},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {OPTION_UPDATE_PERIOD_S: "MIN_INTERVAL"}
