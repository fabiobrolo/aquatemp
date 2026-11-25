from dataclasses import dataclass

from custom_components.aqua_temp.common.consts import (
    API_STATUS,
    BUTTON_MEASURE_TEMPERATURE,
    BUTTON_REFRESH_DATA,
    POWER_MODE_OFF,
    POWER_MODE_ON,
)
from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntityDescription,
)
from homeassistant.components.button import ButtonEntityDescription
from homeassistant.components.climate import ClimateEntityDescription, HVACMode
from homeassistant.components.number import NumberEntityDescription
from homeassistant.components.select import SelectEntityDescription
from homeassistant.components.sensor import SensorEntityDescription
from homeassistant.components.switch import SwitchEntityDescription
from homeassistant.components.time import TimeEntityDescription
from homeassistant.const import EntityCategory, Platform, UnitOfTemperature
from homeassistant.helpers.entity import EntityDescription


@dataclass(frozen=True, kw_only=True)
class AquaTempEntityDescription(EntityDescription):
    platform: Platform | None = None
    is_protocol_code: bool = True


@dataclass(frozen=True, kw_only=True)
class AquaTempClimateEntityDescription(
    ClimateEntityDescription, AquaTempEntityDescription
):
    platform: Platform | None = Platform.CLIMATE
    fan_modes: list[str] | None = None
    hvac_modes: list[HVACMode] | list[str] = None


@dataclass(frozen=True, kw_only=True)
class AquaTempBinarySensorEntityDescription(
    BinarySensorEntityDescription, AquaTempEntityDescription
):
    platform: Platform | None = Platform.BINARY_SENSOR
    on_value: str | bool | None = None
    attributes: list[str] | None = None


@dataclass(frozen=True, kw_only=True)
class AquaTempSensorEntityDescription(
    SensorEntityDescription, AquaTempEntityDescription
):
    platform: Platform | None = Platform.SENSOR


@dataclass(frozen=True, kw_only=True)
class AquaTempSelectEntityDescription(
    SelectEntityDescription, AquaTempEntityDescription
):
    platform: Platform | None = Platform.SELECT


@dataclass(frozen=True, kw_only=True)
class AquaTempNumberEntityDescription(
    NumberEntityDescription, AquaTempEntityDescription
):
    platform: Platform | None = Platform.NUMBER


@dataclass(frozen=True, kw_only=True)
class AquaTempButtonEntityDescription(
    ButtonEntityDescription, AquaTempEntityDescription
):
    platform: Platform | None = Platform.BUTTON


@dataclass(frozen=True, kw_only=True)
class AquaTempSwitchEntityDescription(
    SwitchEntityDescription, AquaTempEntityDescription
):
    platform: Platform | None = Platform.SWITCH
    on_value: str = POWER_MODE_ON
    off_value: str = POWER_MODE_OFF


@dataclass(frozen=True, kw_only=True)
class AquaTempTimeEntityDescription(
    TimeEntityDescription, AquaTempEntityDescription
):
    platform: Platform | None = Platform.TIME
    is_protocol_code: bool = False
    hour_key: str = ""
    minute_key: str | None = None
    minute_step: int = 1


DEFAULT_ENTITY_DESCRIPTIONS: list[AquaTempEntityDescription] = [
    AquaTempBinarySensorEntityDescription(
        key=API_STATUS,
        entity_category=EntityCategory.DIAGNOSTIC,
        is_protocol_code=False,
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        on_value=True,
        translation_key=API_STATUS,
    ),
    AquaTempSelectEntityDescription(
        key="temperature_unit",
        options=[UnitOfTemperature.CELSIUS, UnitOfTemperature.FAHRENHEIT],
        entity_category=EntityCategory.CONFIG,
        is_protocol_code=False,
        translation_key="temperature_unit",
    ),
    AquaTempButtonEntityDescription(
        key=BUTTON_MEASURE_TEMPERATURE,
        is_protocol_code=False,
        icon="mdi:thermometer-water",
        translation_key=BUTTON_MEASURE_TEMPERATURE,
    ),
    AquaTempButtonEntityDescription(
        key=BUTTON_REFRESH_DATA,
        is_protocol_code=False,
        icon="mdi:refresh",
        translation_key=BUTTON_REFRESH_DATA,
    ),
    AquaTempBinarySensorEntityDescription(
        key="is_fault",
        on_value=POWER_MODE_ON,
        is_protocol_code=False,
        device_class=BinarySensorDeviceClass.PROBLEM,
        attributes=["fault"],
        translation_key="is_fault",
    ),
    AquaTempBinarySensorEntityDescription(
        key="device_status",
        on_value="ONLINE",
        is_protocol_code=False,
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        translation_key="device_status",
    ),
    AquaTempClimateEntityDescription(key="Mode", name=None),
]
