"""Support for PVS gateway."""

from __future__ import annotations
from typing import Any

from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import PVSUpdateCoordinator


class PVSBaseEntity(CoordinatorEntity[PVSUpdateCoordinator]):
    """Defines a base PVS entity."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: PVSUpdateCoordinator,
        description: EntityDescription,
    ) -> None:
        """Init the PVS base entity."""
        self.entity_description = description
        serial_number = coordinator.pvs.serial_number
        assert serial_number is not None
        self.pvs_serial_num = serial_number
        self.pvs_device_id = dr.async_get_device_id_by_identifier(
            coordinator.hass,
            (DOMAIN, serial_number),
            config_entry_id=coordinator.entry.entry_id,
        )
        super().__init__(coordinator)

    @property
    def data(self) -> dict[str, Any]:
        """Return PVS data."""
        data = self.coordinator.pvs.data
        assert data is not None
        return data
