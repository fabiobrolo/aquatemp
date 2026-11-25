"""Switch platform for writable boolean Aqua Temp protocol parameters."""

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback

from .common.base_entity import BaseEntity, async_setup_base_entry
from .common.entity_descriptions import AquaTempSwitchEntityDescription
from .managers.aqua_temp_coordinator import AquaTempCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
) -> None:
    """Set up Aqua Temp switch entities from a config entry."""
    await async_setup_base_entry(
        hass,
        entry,
        Platform.SWITCH,
        AquaTempSwitchEntity,
        async_add_entities,
    )


class AquaTempSwitchEntity(BaseEntity, SwitchEntity):
    """Representation of a writable boolean protocol parameter."""

    entity_description: AquaTempSwitchEntityDescription

    def __init__(
        self,
        entity_description: AquaTempSwitchEntityDescription,
        coordinator: AquaTempCoordinator,
        device_code: str,
    ) -> None:
        super().__init__(entity_description, coordinator, device_code)
        self._attr_is_on = self._read_is_on()

    def _read_is_on(self) -> bool | None:
        device_data = self.local_coordinator.get_device_data(self._device_code) or {}
        raw_value = device_data.get(self.entity_description.key)
        if raw_value in (None, ""):
            return None
        return str(raw_value).strip() == str(self.entity_description.on_value)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable the parameter on the device."""
        await self.local_coordinator.set_protocol_code(
            self._device_code,
            self.entity_description.key,
            self.entity_description.on_value,
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable the parameter on the device."""
        await self.local_coordinator.set_protocol_code(
            self._device_code,
            self.entity_description.key,
            self.entity_description.off_value,
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        """Fetch updated boolean state from coordinator."""
        self._attr_is_on = self._read_is_on()
        self.async_write_ha_state()
