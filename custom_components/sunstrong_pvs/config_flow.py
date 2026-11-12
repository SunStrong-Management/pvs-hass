"""Config flow for Enphase PVS integration."""

from __future__ import annotations

from collections.abc import Mapping
import logging
from typing import Any

from pypvs.exceptions import PVSAuthenticationError, PVSError
from pypvs.pvs import PVS
import voluptuous as vol

from homeassistant.components import zeroconf
from homeassistant.config_entries import (
    SOURCE_REAUTH,
    SOURCE_RECONFIGURE,
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlowWithReload,
)
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PASSWORD
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.typing import VolDictType

from .const import (
    DOMAIN,
    INVALID_AUTH_ERRORS,
    OPTION_ENABLE_LIVE_DATA,
    OPTION_ENABLE_LIVE_DATA_DEFAULT_VALUE,
    OPTION_UPDATE_PERIOD_S,
    OPTION_UPDATE_PERIOD_S_DEFAULT_VALUE,
    OPTION_UPDATE_PERIOD_S_MIN_VALUE,
)

_LOGGER = logging.getLogger(__name__)

PVS_NAME = "PVS"

CONF_SERIAL = "serial"

INSTALLER_AUTH_USERNAME = "installer"


async def validate_input(
    hass: HomeAssistant, host: str, client_id: str = None, token_secret: str = None
) -> PVS:
    """Validate the user input allows us to connect."""
    pvs = PVS(session=async_get_clientsession(hass, False), host=host)
    await pvs.validate()
    return pvs


async def validate_password(hass: HomeAssistant, host: str, password: str) -> None:
    """Validate the password by reading a variable that requires a login."""
    pvs = PVS(
        session=async_get_clientsession(hass, False),
        host=host,
        user="ssm_owner",
        password=password,
    )
    await pvs.setup()


class PVSConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for a PVS."""

    VERSION = 1

    _reauth_entry: ConfigEntry
    _reconnect_entry: ConfigEntry

    def __init__(self) -> None:
        """Initialize an PVS flow."""
        self.ip_address: str | None = None
        self.client_id: str | None = None
        self.password: str | None = None

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> PVSOptionsFlowHandler:
        """Options flow handler for PVS."""
        return PVSOptionsFlowHandler()

    @callback
    def _async_generate_schema_host(self) -> vol.Schema:
        """Generate schema."""
        schema: VolDictType = {}

        if self.source == SOURCE_RECONFIGURE:
            schema[vol.Required(CONF_HOST, default=self.ip_address)] = str
        elif self.ip_address:
            schema[vol.Required(CONF_HOST, default=self.ip_address)] = vol.In(
                [self.ip_address]
            )
        else:
            schema[vol.Required(CONF_HOST)] = str

        return vol.Schema(schema)

    @callback
    def _async_generate_schema_password(self) -> vol.Schema:
        """Generate schema."""
        schema: VolDictType = {}

        schema[vol.Required(CONF_PASSWORD, default=self.password)] = str

        return vol.Schema(schema)

    @callback
    def _async_current_hosts(self) -> set[str]:
        """Return a set of hosts."""
        return {
            entry.data[CONF_HOST]
            for entry in self._async_current_entries(include_ignore=False)
            if CONF_HOST in entry.data
        }

    async def async_step_zeroconf(
        self, discovery_info: zeroconf.ZeroconfServiceInfo
    ) -> ConfigFlowResult:
        """Handle a flow initialized by zeroconf discovery."""
        if _LOGGER.isEnabledFor(logging.DEBUG):
            current_hosts = self._async_current_hosts()
            _LOGGER.debug(
                "Zeroconf ip %s processing %s, current hosts: %s",
                discovery_info.ip_address.version,
                discovery_info.host,
                current_hosts,
            )
        if discovery_info.ip_address.version != 4:
            return self.async_abort(reason="not_ipv4_address")
        # A PVS can advertise the serial numbers of other PVS units on the
        # network, so the serial number is read from the PVS itself
        try:
            pvs = await validate_input(self.hass, discovery_info.host)
        except PVSError:
            return self.async_abort(reason="cannot_connect")
        serial = pvs.serial_number
        await self.async_set_unique_id(serial)
        self.ip_address = discovery_info.host
        self._abort_if_unique_id_configured({CONF_HOST: self.ip_address})
        _LOGGER.debug(
            "Zeroconf ip %s, no existing entry with serial %s",
            self.ip_address,
            serial,
        )
        for entry in self._async_current_entries(include_ignore=False):
            if (
                entry.unique_id is None
                and CONF_HOST in entry.data
                and entry.data[CONF_HOST] == self.ip_address
            ):
                _LOGGER.debug(
                    "Zeroconf update PVS with this ip and blank serial in unique_id",
                )
                title = f"{PVS_NAME} {serial}" if entry.title == PVS_NAME else PVS_NAME
                return self.async_update_reload_and_abort(
                    entry, title=title, unique_id=serial, reason="already_configured"
                )

        _LOGGER.debug("Zeroconf ip %s to step user", self.ip_address)
        return await self.async_step_user()

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Handle configuration by re-auth."""
        self._reauth_entry = self._get_reauth_entry()
        self.password = self._reauth_entry.data.get(CONF_PASSWORD)
        if unique_id := self._reauth_entry.unique_id:
            await self.async_set_unique_id(unique_id, raise_on_progress=False)
        return await self.async_step_user()

    def _async_pvs_name(self) -> str:
        """Return the name of the pvs."""
        return f"{PVS_NAME} {self.unique_id}" if self.unique_id else PVS_NAME

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        description_placeholders: dict[str, str] = {}

        if self.source == SOURCE_REAUTH:
            host = self._reauth_entry.data[CONF_HOST]
        else:
            host = (user_input or {}).get(CONF_HOST) or self.ip_address or ""

        if user_input is not None:
            try:
                pvs = await validate_input(self.hass, host)
            except INVALID_AUTH_ERRORS:
                errors["base"] = "cannot_connect"
            except PVSError as e:
                errors["base"] = "cannot_connect"
                description_placeholders = {"reason": str(e)}
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                self.ip_address = host
                name = self._async_pvs_name()

                if self.source in (SOURCE_REAUTH, SOURCE_RECONFIGURE):
                    await self.async_set_unique_id(
                        pvs.serial_number, raise_on_progress=False
                    )
                    self._abort_if_unique_id_mismatch()
                elif not self.unique_id:
                    await self.async_set_unique_id(pvs.serial_number)
                    self._abort_if_unique_id_configured()
                    name = self._async_pvs_name()

                if CONF_PASSWORD not in user_input:
                    return await self.async_step_need_password()

                if self.unique_id:
                    # If PVS exists in configuration update fields and exit
                    self._abort_if_unique_id_configured(
                        {CONF_HOST: host},
                        error="reauth_successful",
                    )

                # CONF_NAME is still set for legacy backwards compatibility
                return self.async_create_entry(
                    title=name, data={CONF_NAME: name, CONF_HOST: host} | user_input
                )

        if self.unique_id:
            self.context["title_placeholders"] = {
                CONF_SERIAL: self.unique_id,
                CONF_HOST: host,
            }

        return self.async_show_form(
            step_id="user",
            data_schema=self._async_generate_schema_host(),
            description_placeholders=description_placeholders,
            errors=errors,
            last_step=False,
        )

    async def async_step_need_password(
        self, user_input: dict[str, str] | None = None
    ) -> ConfigFlowResult:
        """Handle a flow initialized by the user."""

        errors: dict[str, str] = {}
        description_placeholders: dict[str, str] = {}

        if user_input is not None:
            if CONF_PASSWORD not in user_input:
                return await self.async_step_need_password()
            try:
                await validate_password(
                    self.hass, self.ip_address, user_input[CONF_PASSWORD]
                )
            except PVSAuthenticationError:
                errors["base"] = "invalid_auth"
            except PVSError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                data_updates = {CONF_HOST: self.ip_address} | user_input
                if self.source == SOURCE_REAUTH:
                    return self.async_update_reload_and_abort(
                        self._get_reauth_entry(), data_updates=data_updates
                    )
                if self.source == SOURCE_RECONFIGURE:
                    return self.async_update_reload_and_abort(
                        self._get_reconfigure_entry(), data_updates=data_updates
                    )

                name = self._async_pvs_name()
                # CONF_NAME is still set for legacy backwards compatibility
                return self.async_create_entry(
                    title=name, data={CONF_NAME: name} | data_updates
                )

        return self.async_show_form(
            step_id="need_password",
            data_schema=self._async_generate_schema_password(),
            description_placeholders=description_placeholders,
            errors=errors,
            last_step=True,
        )

    async def async_step_reconfigure(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Perform a reconfiguration."""
        config_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )
        assert config_entry is not None
        self.ip_address = config_entry.data[CONF_HOST]
        self.password = config_entry.data.get(CONF_PASSWORD)
        return await self.async_step_user()


class PVSOptionsFlowHandler(OptionsFlowWithReload):
    """PVS config flow options handler."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        _LOGGER.debug(f"Options input {user_input} {self.config_entry}")
        options = dict(self.config_entry.options)

        errors = {}

        if user_input is not None:
            if user_input[OPTION_UPDATE_PERIOD_S] < OPTION_UPDATE_PERIOD_S_MIN_VALUE:
                errors[OPTION_UPDATE_PERIOD_S] = "MIN_INTERVAL"
            if len(errors) == 0:
                options[OPTION_UPDATE_PERIOD_S] = user_input[OPTION_UPDATE_PERIOD_S]
                options[OPTION_ENABLE_LIVE_DATA] = user_input[OPTION_ENABLE_LIVE_DATA]
                return self.async_create_entry(title="", data=user_input)

        current_update_period_s = options.get(
            OPTION_UPDATE_PERIOD_S, OPTION_UPDATE_PERIOD_S_DEFAULT_VALUE
        )
        current_enable_live_data = options.get(
            OPTION_ENABLE_LIVE_DATA, OPTION_ENABLE_LIVE_DATA_DEFAULT_VALUE
        )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        OPTION_UPDATE_PERIOD_S, default=current_update_period_s
                    ): int,
                    vol.Required(
                        OPTION_ENABLE_LIVE_DATA, default=current_enable_live_data
                    ): bool,
                },
            ),
            errors=errors,
        )
