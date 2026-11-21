import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .common.base_entity import BaseEntity, async_setup_base_entry
from .common.entity_descriptions import AquaTempButtonEntityDescription
from .managers.aqua_temp_coordinator import AquaTempCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
):
    await async_setup_base_entry(
        hass,
        entry,
        Platform.BUTTON,
        AquaTempButtonEntity,
        async_add_entities,
    )


class AquaTempButtonEntity(BaseEntity, ButtonEntity):
    """Representation of a button entity."""

    def __init__(
        self,
        entity_description: AquaTempButtonEntityDescription,
        coordinator: AquaTempCoordinator,
        device_code: str,
    ):
        super().__init__(entity_description, coordinator, device_code)

    async def async_press(self) -> None:
        """Handle button press."""
        await self.local_coordinator.measure_temperature(self._device_code)
