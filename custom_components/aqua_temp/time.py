"""Time platform for writable Aqua Temp on-board local timer schedules."""

from datetime import time as dt_time

from homeassistant.components.time import TimeEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback

from .common.base_entity import BaseEntity, async_setup_base_entry
from .common.entity_descriptions import AquaTempTimeEntityDescription
from .managers.aqua_temp_coordinator import AquaTempCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
) -> None:
    """Set up Aqua Temp time entities from a config entry."""
    await async_setup_base_entry(
        hass,
        entry,
        Platform.TIME,
        AquaTempTimeEntity,
        async_add_entities,
    )


def _parse_int(raw_value, minimum: int, maximum: int) -> int | None:
    if raw_value in (None, ""):
        return None
    try:
        parsed = int(round(float(str(raw_value))))
    except (ValueError, TypeError):
        return None
    if not (minimum <= parsed <= maximum):
        return None
    return parsed


class AquaTempTimeEntity(BaseEntity, TimeEntity):
    """Representation of a writable local timer schedule time."""

    entity_description: AquaTempTimeEntityDescription

    def __init__(
        self,
        entity_description: AquaTempTimeEntityDescription,
        coordinator: AquaTempCoordinator,
        device_code: str,
    ) -> None:
        super().__init__(entity_description, coordinator, device_code)
        self._attr_native_value = self._read_native_value()

    def _read_native_value(self) -> dt_time | None:
        device_data = self.local_coordinator.get_device_data(self._device_code) or {}
        hour = _parse_int(device_data.get(self.entity_description.hour_key), 0, 23)
        if hour is None:
            return None

        if self.entity_description.minute_key:
            minute = _parse_int(
                device_data.get(self.entity_description.minute_key), 0, 59
            )
            if minute is None:
                return None
        else:
            minute = 0

        return dt_time(hour=hour, minute=minute)

    async def async_set_value(self, value: dt_time) -> None:
        """Update the timer schedule time on the device."""
        hour = max(0, min(23, int(value.hour)))
        payload: dict[str, str] = {self.entity_description.hour_key: str(hour)}

        if self.entity_description.minute_key:
            step = max(1, int(self.entity_description.minute_step))
            raw_min = max(0, min(59, int(value.minute)))
            # Snap downward to controller granularity without rolling over the hour
            minute = 0 if step >= 60 else (raw_min // step) * step
            payload[self.entity_description.minute_key] = str(minute)

        await self.local_coordinator.set_protocol_codes(self._device_code, payload)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Fetch updated time value from coordinator."""
        self._attr_native_value = self._read_native_value()
        self.async_write_ha_state()
