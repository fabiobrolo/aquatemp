"""Self-check tests for circulation duration config and measure_temperature flow."""
import asyncio
from dataclasses import dataclass
import sys
import types
from enum import StrEnum
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))


def _install_ha_stubs():
    class HVACMode(StrEnum):
        OFF = "off"
        HEAT = "heat"
        COOL = "cool"
        AUTO = "auto"

    ha = types.ModuleType("homeassistant")
    ha_comp = types.ModuleType("homeassistant.components")
    ha_clim = types.ModuleType("homeassistant.components.climate")
    ha_clim_const = types.ModuleType("homeassistant.components.climate.const")
    ha_clim.HVACMode = HVACMode
    ha_clim_const.HVACMode = HVACMode
    ha_clim_const.FAN_AUTO = "auto"
    ha_clim_const.FAN_LOW = "low"

    ha_core = types.ModuleType("homeassistant.core")
    ha_core.Event = object
    ha_core.HomeAssistant = object

    ha_const = types.ModuleType("homeassistant.const")
    ha_const.CONF_PASSWORD = "password"
    ha_const.CONF_TEMPERATURE_UNIT = "temperature_unit"
    ha_const.CONF_USERNAME = "username"
    ha_const.EVENT_HOMEASSISTANT_START = "homeassistant_start"
    ha_const.EntityCategory = types.SimpleNamespace(CONFIG="config", DIAGNOSTIC="diagnostic")
    ha_const.Platform = types.SimpleNamespace(
        BINARY_SENSOR="binary_sensor",
        BUTTON="button",
        CLIMATE="climate",
        NUMBER="number",
        SELECT="select",
        SENSOR="sensor",
    )
    ha_const.UnitOfTemperature = types.SimpleNamespace(CELSIUS="°C", FAHRENHEIT="°F")
    ha_const.UnitOfTime = types.SimpleNamespace(MINUTES="min")

    ha_cfg = types.ModuleType("homeassistant.config_entries")
    ha_cfg.STORAGE_VERSION = 1
    ha_cfg.ConfigEntry = object

    @dataclass(frozen=True, kw_only=True)
    class EntityDescription:
        key: str
        name: str | None = None
        entity_category: str | None = None
        device_class: str | None = None
        icon: str | None = None
        translation_key: str | None = None

    @dataclass(frozen=True, kw_only=True)
    class BinarySensorEntityDescription(EntityDescription):
        pass

    @dataclass(frozen=True, kw_only=True)
    class ButtonEntityDescription(EntityDescription):
        pass

    @dataclass(frozen=True, kw_only=True)
    class ClimateEntityDescription(EntityDescription):
        pass

    @dataclass(frozen=True, kw_only=True)
    class NumberEntityDescription(EntityDescription):
        native_min_value: float | None = None
        native_max_value: float | None = None
        native_step: float | None = None
        native_unit_of_measurement: str | None = None

    @dataclass(frozen=True, kw_only=True)
    class SelectEntityDescription(EntityDescription):
        options: list[str] | None = None

    @dataclass(frozen=True, kw_only=True)
    class SensorEntityDescription(EntityDescription):
        native_unit_of_measurement: str | None = None

    ha_helpers = types.ModuleType("homeassistant.helpers")
    ha_helpers.selector = types.SimpleNamespace(
        SelectSelector=lambda *a, **k: None,
        SelectSelectorConfig=lambda *a, **k: None,
        SelectSelectorMode=types.SimpleNamespace(DROPDOWN="dropdown"),
    )
    ha_entity = types.ModuleType("homeassistant.helpers.entity")
    ha_entity.DeviceInfo = dict
    ha_entity.EntityDescription = EntityDescription

    ha_uc = types.ModuleType("homeassistant.helpers.update_coordinator")

    class FakeCoordinator:
        def __init__(self, hass, logger, name, update_interval, update_method):
            self.hass = hass
            self.refresh_count = 0
            self.listener_updates = 0

        async def async_request_refresh(self):
            self.refresh_count += 1

        def async_update_listeners(self):
            self.listener_updates += 1

    ha_uc.DataUpdateCoordinator = FakeCoordinator
    ha_uc.UpdateFailed = Exception

    ha_aiohttp = types.ModuleType("homeassistant.helpers.aiohttp_client")
    ha_aiohttp.async_create_clientsession = lambda hass: None
    ha_disp = types.ModuleType("homeassistant.helpers.dispatcher")
    ha_disp.async_dispatcher_send = lambda *a, **k: None
    ha_json = types.ModuleType("homeassistant.helpers.json")
    ha_json.JSONEncoder = object
    ha_storage = types.ModuleType("homeassistant.helpers.storage")
    ha_storage.Store = object
    ha_trans = types.ModuleType("homeassistant.helpers.translation")
    ha_bin = types.ModuleType("homeassistant.components.binary_sensor")
    ha_bin.BinarySensorDeviceClass = types.SimpleNamespace(CONNECTIVITY="connectivity", PROBLEM="problem")
    ha_bin.BinarySensorEntityDescription = BinarySensorEntityDescription
    ha_btn = types.ModuleType("homeassistant.components.button")
    ha_btn.ButtonEntityDescription = ButtonEntityDescription
    ha_num = types.ModuleType("homeassistant.components.number")
    ha_num.NumberEntityDescription = NumberEntityDescription
    ha_sel = types.ModuleType("homeassistant.components.select")
    ha_sel.SelectEntityDescription = SelectEntityDescription
    ha_sen = types.ModuleType("homeassistant.components.sensor")
    ha_sen.SensorEntityDescription = SensorEntityDescription
    ha_clim.ClimateEntityDescription = ClimateEntityDescription

    aiohttp = types.ModuleType("aiohttp")
    aiohttp.ClientResponseError = Exception
    aiohttp.ClientSession = object
    aiofiles = types.ModuleType("aiofiles")
    crypto = types.ModuleType("cryptography")
    crypto_fernet = types.ModuleType("cryptography.fernet")
    crypto_fernet.InvalidToken = Exception
    crypto_fernet.Fernet = object
    vol = types.ModuleType("voluptuous")
    vol.Required = lambda *a, **k: None
    vol.Optional = lambda *a, **k: None
    vol.Schema = lambda *a, **k: None

    for name, mod in {
        "voluptuous": vol,
        "cryptography": crypto,
        "cryptography.fernet": crypto_fernet,
        "homeassistant": ha,
        "homeassistant.components": ha_comp,
        "homeassistant.components.climate": ha_clim,
        "homeassistant.components.climate.const": ha_clim_const,
        "homeassistant.components.binary_sensor": ha_bin,
        "homeassistant.components.button": ha_btn,
        "homeassistant.components.number": ha_num,
        "homeassistant.components.select": ha_sel,
        "homeassistant.components.sensor": ha_sen,
        "homeassistant.core": ha_core,
        "homeassistant.const": ha_const,
        "homeassistant.config_entries": ha_cfg,
        "homeassistant.helpers": ha_helpers,
        "homeassistant.helpers.entity": ha_entity,
        "homeassistant.helpers.update_coordinator": ha_uc,
        "homeassistant.helpers.aiohttp_client": ha_aiohttp,
        "homeassistant.helpers.dispatcher": ha_disp,
        "homeassistant.helpers.json": ha_json,
        "homeassistant.helpers.storage": ha_storage,
        "homeassistant.helpers.translation": ha_trans,
        "aiohttp": aiohttp,
        "aiofiles": aiofiles,
    }.items():
        sys.modules[name] = mod

    return HVACMode


HVACMode = _install_ha_stubs()

from custom_components.aqua_temp.managers.aqua_temp_config_manager import (  # noqa: E402
    AquaTempConfigManager,
)
from custom_components.aqua_temp.managers.aqua_temp_coordinator import (  # noqa: E402
    AquaTempCoordinator,
)


class FakeHass:
    def async_create_task(self, coro):
        return asyncio.create_task(coro)


class FakeAPI:
    def __init__(self):
        self.events = []
        self.online = True
        self.power = False
        self.target = 29.0
        self.min_temp = 15.0

    def get_device_is_online(self, dc):
        return self.online

    def get_device_power(self, dc):
        return self.power

    def get_device_target_temperature(self, dc):
        return self.target

    def get_device_minimum_temperature(self, dc):
        return self.min_temp

    async def set_temperature(self, dc, temp):
        self.events.append(("set_temperature", temp))
        self.target = temp

    async def set_hvac_mode(self, dc, mode):
        self.events.append(("set_hvac_mode", mode))
        self.power = mode != HVACMode.OFF


def _make_coordinator():
    cm = AquaTempConfigManager(None, None)
    cm._data = cm._get_defaults()
    cm._hvac_modes["default"] = {"off": None, "heat": "1"}
    cm.set_device("dev1", "default")
    coord = AquaTempCoordinator(FakeHass(), cm)
    coord._api = FakeAPI()
    return coord


async def run_tests():
    # 1. Default and clamping of circulation duration
    coord = _make_coordinator()
    assert coord.get_circulation_duration("dev1") == 5
    await coord.set_circulation_duration("dev1", 0)
    assert coord.get_circulation_duration("dev1") == 1
    await coord.set_circulation_duration("dev1", 120)
    assert coord.get_circulation_duration("dev1") == 60
    await coord.set_circulation_duration("dev1", 7)
    assert coord.get_circulation_duration("dev1") == 7

    # 2. Normal flow: low setpoint -> heat -> sleep 7*60 -> refresh -> OFF -> restore 29.0
    slept = []

    async def fake_sleep(sec):
        slept.append(sec)

    with patch("asyncio.sleep", side_effect=fake_sleep):
        await coord.measure_temperature("dev1")
        # Duplicate press while running must be ignored
        task = coord._measure_tasks["dev1"]
        await coord.measure_temperature("dev1")
        assert coord._measure_tasks["dev1"] is task
        await task

    assert coord._api.events == [
        ("set_temperature", 15.0),
        ("set_hvac_mode", HVACMode.HEAT),
        ("set_hvac_mode", HVACMode.OFF),
        ("set_temperature", 29.0),
    ], f"Unexpected event order: {coord._api.events}"
    assert 420 in slept
    assert coord.refresh_count == 3
    assert "dev1" not in coord._measure_tasks

    # 3. Already running: only refreshes, no commands sent
    coord = _make_coordinator()
    coord._api.power = True
    await coord.measure_temperature("dev1")
    assert coord._api.events == []
    assert coord.refresh_count == 1

    # 4. User raises target temperature mid-cycle: do not turn off or overwrite
    coord = _make_coordinator()

    async def user_takeover_sleep(sec):
        if sec >= 60:
            coord._api.target = 31.0

    with patch("asyncio.sleep", side_effect=user_takeover_sleep):
        await coord.measure_temperature("dev1")
        await coord._measure_tasks["dev1"]

    assert coord._api.events == [
        ("set_temperature", 15.0),
        ("set_hvac_mode", HVACMode.HEAT),
    ], f"User takeover overwritten: {coord._api.events}"
    assert coord._api.power is True
    assert coord._api.target == 31.0

    # 5. Cancelled mid-cycle (unload): still safely turns OFF before restoring 29.0
    coord = _make_coordinator()
    started = asyncio.Event()

    async def cancel_sleep(sec):
        if sec >= 60:
            started.set()
            await asyncio.Future()

    with patch("asyncio.sleep", side_effect=cancel_sleep):
        await coord.measure_temperature("dev1")
        await started.wait()
        await coord.cancel_tasks()

    assert coord._api.events == [
        ("set_temperature", 15.0),
        ("set_hvac_mode", HVACMode.HEAT),
        ("set_hvac_mode", HVACMode.OFF),
        ("set_temperature", 29.0),
    ], f"Unsafe cancellation order: {coord._api.events}"

    print("ALL TESTS PASSED")


if __name__ == "__main__":
    asyncio.run(run_tests())
