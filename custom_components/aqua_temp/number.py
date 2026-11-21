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
    """Representation of a writable numeric protocol parameter."""

    def __init__(
        self,
        entity_description: AquaTempNumberEntityDescription,
        coordinator: AquaTempCoordinator,
        device_code: str,
    ):
        super().__init__(entity_description, coordinator, device_code)
        self._attr_mode = NumberMode.BOX
        self._attr_native_value = self._read_native_value()

    def _read_native_value(self) -> float | None:
        device_data = self.local_coordinator.get_device_data(self._device_code) or {}
        raw_value = device_data.get(self.entity_description.key)
        if raw_value in (None, ""):
            return None
        try:
            return float(str(raw_value))
        except (ValueError, TypeError):
            return None

    async def async_set_native_value(self, value: float) -> None:
        """Update the parameter on the device."""
        min_val = self.entity_description.native_min_value
        max_val = self.entity_description.native_max_value
        clamped = float(value)
        if min_val is not None:
            clamped = max(float(min_val), clamped)
        if max_val is not None:
            clamped = min(float(max_val), clamped)

        await self.local_coordinator.set_protocol_code(
            self._device_code, self.entity_description.key, str(int(round(clamped)))
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        """Fetch updated numeric value from coordinator."""
        self._attr_native_value = self._read_native_value()
        self.async_write_ha_state()
