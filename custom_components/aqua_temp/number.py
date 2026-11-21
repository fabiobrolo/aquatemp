from abc import ABC
import logging

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback

from .common.base_entity import BaseEntity, async_setup_base_entry
from .common.entity_descriptions import AquaTempNumberEntityDescription
from .managers.aqua_temp_coordinator import AquaTempCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
):
    await async_setup_base_entry(
        hass,
        entry,
        Platform.NUMBER,
        AquaTempNumberEntity,
        async_add_entities,
    )


class AquaTempNumberEntity(BaseEntity, NumberEntity, ABC):
    """Representation of a number entity."""

    def __init__(
        self,
        entity_description: AquaTempNumberEntityDescription,
        coordinator: AquaTempCoordinator,
        device_code: str,
    ):
        super().__init__(entity_description, coordinator, device_code)

        self._attr_mode = NumberMode.BOX
        self._attr_native_value = float(
            coordinator.get_circulation_duration(self._device_code)
        )

    async def async_set_native_value(self, value: float) -> None:
        """Update the circulation duration."""
        await self.local_coordinator.set_circulation_duration(
            self._device_code, int(round(value))
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        """Fetch updated configuration value."""
        self._attr_native_value = float(
            self.local_coordinator.get_circulation_duration(self._device_code)
        )
        self.async_write_ha_state()
