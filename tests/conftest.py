"""Fixtures for the PVS integration tests."""

from collections.abc import Generator
from dataclasses import dataclass
from http import HTTPStatus
import json
from pathlib import Path
import re
from unittest.mock import AsyncMock, patch

from aiohttp import ClientError
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.syrupy import HomeAssistantSnapshotExtension
from pytest_homeassistant_custom_component.test_util.aiohttp import (
    AiohttpClientMocker,
    AiohttpClientMockResponse,
)
from syrupy.assertion import SnapshotAssertion
from yarl import URL

from custom_components.sunstrong_pvs.const import DOMAIN
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PASSWORD
from homeassistant.core import HomeAssistant

HOST = "192.168.1.10"

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Enable custom integrations in all tests."""


@pytest.fixture
def snapshot(snapshot: SnapshotAssertion) -> SnapshotAssertion:
    """Return the snapshot fixture with the Home Assistant extension.

    The Home Assistant plugin overrides the syrupy fixture only when it is
    loaded after syrupy, which depends on the order of the installed packages.
    """
    return snapshot.use_extension(HomeAssistantSnapshotExtension)


@pytest.fixture(params=["pvs6"])
def pvs_variables(request: pytest.FixtureRequest) -> dict[str, str]:
    """Return the varserver variables of a PVS, PVS6 unless parametrized."""
    return json.loads((FIXTURES / f"{request.param}.json").read_text())


@pytest.fixture
def serial_number(pvs_variables: dict[str, str]) -> str:
    """Return the serial number of the PVS."""
    return pvs_variables["/sys/info/serialnum"]


@dataclass
class MockPVS:
    """A PVS answering the login and varserver requests of pypvs.

    Variables missing from the fixture are answered with HTTP 400, like a
    PVS5 answers the flash wear variable.
    """

    variables: dict[str, str]
    reachable: bool = True
    login_status: HTTPStatus = HTTPStatus.OK

    async def handle_login(
        self, method: str, url: URL, data: None
    ) -> AiohttpClientMockResponse:
        """Answer a login request."""
        if not self.reachable:
            return AiohttpClientMockResponse(method, url, exc=ClientError())
        return AiohttpClientMockResponse(
            method, url, status=self.login_status, cookies={"session": "1"}
        )

    async def handle_vars(
        self, method: str, url: URL, data: str
    ) -> AiohttpClientMockResponse:
        """Answer a varserver request for one variable or a prefix."""
        if not self.reachable:
            return AiohttpClientMockResponse(method, url, exc=ClientError())
        key, _, value = data.partition("=")
        if key == "name":
            if value not in self.variables:
                return AiohttpClientMockResponse(
                    method, url, status=HTTPStatus.BAD_REQUEST
                )
            names = [value]
        else:
            names = [name for name in self.variables if name.startswith(value)]
        values = [{"name": name, "value": self.variables[name]} for name in names]
        return AiohttpClientMockResponse(
            method, url, json={"count": len(values), "values": values}
        )


@pytest.fixture
def mock_pvs(
    aioclient_mock: AiohttpClientMocker, pvs_variables: dict[str, str]
) -> MockPVS:
    """Mock the HTTP API of a PVS."""
    pvs = MockPVS(pvs_variables)
    aioclient_mock.get(re.compile(r"/auth\?login$"), side_effect=pvs.handle_login)
    aioclient_mock.post(re.compile(r"/vars$"), side_effect=pvs.handle_vars)
    return pvs


@pytest.fixture
def mock_config_entry(serial_number: str) -> MockConfigEntry:
    """Return a config entry for the PVS."""
    return MockConfigEntry(
        domain=DOMAIN,
        unique_id=serial_number,
        title=f"PVS {serial_number}",
        data={
            CONF_NAME: f"PVS {serial_number}",
            CONF_HOST: HOST,
            CONF_PASSWORD: serial_number[-5:],
        },
    )


@pytest.fixture
async def init_integration(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_pvs: MockPVS
) -> MockConfigEntry:
    """Set up the integration with a mocked PVS."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    return mock_config_entry


@pytest.fixture
def mock_websocket() -> Generator[AsyncMock]:
    """Mock the live data websocket connection."""
    with (
        patch("pypvs.pvs_websocket.PVSWebSocket.connect") as mock_connect,
        patch("pypvs.pvs_websocket.PVSWebSocket.disconnect"),
    ):
        yield mock_connect


@pytest.fixture
def mock_setup_entry() -> Generator[AsyncMock]:
    """Prevent setting up the config entry created by a config flow."""
    with patch(
        "custom_components.sunstrong_pvs.async_setup_entry", return_value=True
    ) as mock_setup:
        yield mock_setup
