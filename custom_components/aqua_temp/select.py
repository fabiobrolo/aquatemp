from abc import ABC
import logging

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback

from .common.base_entity import BaseEntity, async_setup_base_entry
from .common.consts import API_TO_PUMP_MODE, PROTOCOL_CODE_PUMP_MODE, PUMP_MODE_TO_API
from .common.entity_descriptions import AquaTempSelectEntityDescription
from .managers.aqua_temp_coordinator import AquaTempCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
):
    await async_setup_base_entry(
        hass,
        entry,
        Platform.SELECT,
        AquaTempSelectEntity,
        async_add_entities,
    )


class AquaTempSelectEntity(BaseEntity, SelectEntity, ABC):
    """Representation of a select entity."""

    def __init__(
        self,
        entity_description: AquaTempSelectEntityDescription,
        coordinator: AquaTempCoordinator,
        device_code: str,
    ):
        super().__init__(entity_description, coordinator, device_code)
        self._attr_current_option = self._get_current_option()

    def _get_current_option(self) -> str | None:
        if self.entity_description.key == PROTOCOL_CODE_PUMP_MODE:
            device_data = self.local_coordinator.get_device_data(self._device_code) or {}
            raw_value = device_data.get(PROTOCOL_CODE_PUMP_MODE)
            if raw_value in (None, ""):
                return None
            return API_TO_PUMP_MODE.get(str(raw_value).strip())

        return self.local_coordinator.get_temperature_unit(self._device_code)

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        if self.entity_description.key == PROTOCOL_CODE_PUMP_MODE:
            api_value = PUMP_MODE_TO_API.get(option)
            if api_value is None:
                _LOGGER.warning(
                    f"Unsupported {PROTOCOL_CODE_PUMP_MODE} option '{option}' "
                    f"for {self._device_code}"
                )
                return
            await self.local_coordinator.set_protocol_code(
                self._device_code, PROTOCOL_CODE_PUMP_MODE, api_value
            )
            return

        await self.local_coordinator.set_temperature_unit(self._device_code, option)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Fetch updated option from coordinator."""
        self._attr_current_option = self._get_current_option()
        self.async_write_ha_state()
