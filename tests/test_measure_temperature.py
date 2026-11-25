"""Self-check tests for P01/P02/P03 controls, measure_temperature, recovery, and i18n."""
import asyncio
from dataclasses import dataclass
from enum import StrEnum
import glob
import json
from pathlib import Path
import sys
import types
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
    ha_core.callback = lambda fn: fn

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

    class FakeCoordinatorEntity:
        def __init__(self, coordinator):
            self.coordinator = coordinator

        @property
        def available(self):
            return True

        def async_write_ha_state(self):
            pass

        async def async_added_to_hass(self):
            pass

    ha_uc.DataUpdateCoordinator = FakeCoordinator
    ha_uc.CoordinatorEntity = FakeCoordinatorEntity
    ha_uc.UpdateFailed = Exception

    ha_aiohttp = types.ModuleType("homeassistant.helpers.aiohttp_client")
    ha_aiohttp.async_create_clientsession = lambda hass: None
    ha_disp = types.ModuleType("homeassistant.helpers.dispatcher")
    ha_disp.async_dispatcher_send = lambda *a, **k: None
    ha_disp.async_dispatcher_connect = lambda *a, **k: (lambda: None)
    ha_json = types.ModuleType("homeassistant.helpers.json")
    ha_json.JSONEncoder = object
    ha_storage = types.ModuleType("homeassistant.helpers.storage")
    ha_storage.Store = object
    ha_util = types.ModuleType("homeassistant.util")
    ha_util.slugify = lambda s: str(s).lower().replace(" ", "_")

    ha_bin = types.ModuleType("homeassistant.components.binary_sensor")
    ha_bin.BinarySensorDeviceClass = types.SimpleNamespace(
        CONNECTIVITY="connectivity", PROBLEM="problem"
    )
    ha_bin.BinarySensorEntityDescription = BinarySensorEntityDescription
    class _StubEntity:
        pass

    ha_btn = types.ModuleType("homeassistant.components.button")
    ha_btn.ButtonEntityDescription = ButtonEntityDescription
    ha_btn.ButtonEntity = _StubEntity
    ha_num = types.ModuleType("homeassistant.components.number")
    ha_num.NumberEntityDescription = NumberEntityDescription
    ha_num.NumberEntity = _StubEntity
    ha_num.NumberMode = types.SimpleNamespace(BOX="box")
    ha_sel = types.ModuleType("homeassistant.components.select")
    ha_sel.SelectEntityDescription = SelectEntityDescription
    ha_sel.SelectEntity = _StubEntity
    ha_sen = types.ModuleType("homeassistant.components.sensor")
    ha_sen.SensorEntityDescription = SensorEntityDescription
    ha_clim.ClimateEntityDescription = ClimateEntityDescription

    aiohttp = types.ModuleType("aiohttp")
    aiohttp.ClientResponseError = Exception
    aiohttp.ClientSession = object
    aiohttp.ClientTimeout = lambda **kw: kw
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
        "homeassistant.util": ha_util,
        "aiohttp": aiohttp,
        "aiofiles": aiofiles,
    }.items():
        sys.modules[name] = mod

    return HVACMode


HVACMode = _install_ha_stubs()

from custom_components.aqua_temp.common.entity_descriptions import (  # noqa: E402
    DEFAULT_ENTITY_DESCRIPTIONS,
    AquaTempNumberEntityDescription,
    AquaTempSelectEntityDescription,
)
from custom_components.aqua_temp.managers.aqua_temp_config_manager import (  # noqa: E402
    AquaTempConfigManager,
)
from custom_components.aqua_temp.managers.aqua_temp_coordinator import (  # noqa: E402
    AquaTempCoordinator,
)
from custom_components.aqua_temp.number import AquaTempNumberEntity  # noqa: E402
from custom_components.aqua_temp.select import AquaTempSelectEntity  # noqa: E402


class FakeHass:
    def async_create_task(self, coro):
        return asyncio.create_task(coro)


class FakeAPI:
    def __init__(self, device_data=None, fail_protocol_code=False):
        self.events = []
        self.online = True
        self.power = False
        self.target = 29.0
        self.min_temp = 15.0
        self.device_data = (
            dict(device_data)
            if device_data is not None
            else {"P01": "2", "P02": "60", "P03": "7"}
        )
        self.fail_protocol_code = fail_protocol_code
        self.login_details = {}

    @property
    def devices(self):
        return {"dev1": self.device_data}

    async def update(self):
        pass

    def get_device_data(self, dc):
        return dict(self.device_data)

    def get_device_is_online(self, dc):
        return self.online

    def get_device_power(self, dc):
        return self.power

    def get_device_target_temperature(self, dc):
        return self.target

    def get_device_minimum_temperature(self, dc):
        return self.min_temp

    async def set_protocol_code(self, dc, code, value):
        if self.fail_protocol_code:
            raise RuntimeError("protocol code rejected")
        self.events.append(("set_protocol_code", code, value))
        self.device_data[code] = value

    async def set_temperature(self, dc, temp):
        self.events.append(("set_temperature", temp))
        self.target = temp

    async def set_hvac_mode(self, dc, mode, target_temperature=None):
        self.events.append(("set_hvac_mode", mode))
        if target_temperature is not None:
            self.target = target_temperature
        self.power = mode != HVACMode.OFF


def _make_coordinator(device_data=None, fail_protocol_code=False):
    cm = AquaTempConfigManager(None, None)
    cm._data = cm._get_defaults()
    cm._api_config = {"Nickname": "name", "DeviceId": "id", "CustomModel": "model"}
    cm._hvac_modes["default"] = {"off": None, "heat": "1"}
    cm.set_device("dev1", "default")
    coord = AquaTempCoordinator(FakeHass(), cm)
    coord._api = FakeAPI(
        device_data=device_data, fail_protocol_code=fail_protocol_code
    )
    return coord


def _test_translations():
    root = REPO_ROOT / "custom_components" / "aqua_temp"
    strings = json.loads((root / "strings.json").read_text(encoding="utf-8"))
    en = json.loads((root / "translations" / "en.json").read_text(encoding="utf-8"))
    pt_br = json.loads(
        (root / "translations" / "pt-BR.json").read_text(encoding="utf-8")
    )

    assert strings == en, "strings.json and translations/en.json must stay identical"

    def _keys(obj):
        return {k: _keys(v) if isinstance(v, dict) else None for k, v in obj.items()}

    assert _keys(en) == _keys(pt_br), "en.json and pt-BR.json key trees diverged"

    for desc in DEFAULT_ENTITY_DESCRIPTIONS:
        if desc.translation_key:
            assert desc.translation_key in en["entity"][desc.platform], (
                f"Missing default translation {desc.platform}.{desc.translation_key}"
            )

    for path in glob.glob(str(root / "parameters" / "entity_description.*.json")):
        pid = Path(path).name.removeprefix("entity_description.").removesuffix(".json")
        for item in json.loads(Path(path).read_text(encoding="utf-8")):
            plat = item.get("platform")
            if plat not in ("sensor", "binary_sensor", "select", "number"):
                continue
            tk = item.get("translation_key") or f"{pid}_{item['key']}".replace("/", "").lower()
            assert tk in en["entity"][plat], f"Missing en translation {plat}.{tk}"
            assert tk in pt_br["entity"][plat], f"Missing pt-BR translation {plat}.{tk}"


async def run_tests():
    _test_translations()

    async def fake_sleep(sec):
        slept.append(sec)

    # 1. Measure duration reads P03, clamps to 2..20, falls back to 5 when absent
    coord = _make_coordinator(device_data={"P01": "2", "P03": "7"})
    assert coord.get_measure_duration("dev1") == 7
    coord._api.device_data["P03"] = "1"
    assert coord.get_measure_duration("dev1") == 2
    coord._api.device_data["P03"] = "99"
    assert coord.get_measure_duration("dev1") == 20
    coord._api.device_data.pop("P03")
    assert coord.get_measure_duration("dev1") == 5

    # 2. P01 select entity + P02/P03 number entities read/write & clamping
    coord = _make_coordinator(device_data={"P01": "2", "P02": "60", "P03": "5"})
    p01_desc = AquaTempSelectEntityDescription(
        key="P01",
        options=["continuous", "with_compressor", "intermittent"],
        translation_key="pump_mode_p01",
    )
    p01_ent = AquaTempSelectEntity(p01_desc, coord, "dev1")
    assert p01_ent._attr_has_entity_name is True
    assert p01_ent._attr_current_option == "intermittent"

    slept = []
    with patch("asyncio.sleep", side_effect=fake_sleep):
        await p01_ent.async_select_option("continuous")
    p01_ent._handle_coordinator_update()
    assert p01_ent._attr_current_option == "continuous"
    assert coord._api.events[-1] == ("set_protocol_code", "P01", "0")

    p02_desc = AquaTempNumberEntityDescription(
        key="P02", native_min_value=30, native_max_value=120, native_step=1
    )
    p02_ent = AquaTempNumberEntity(p02_desc, coord, "dev1")
    assert p02_ent._attr_native_value == 60.0
    with patch("asyncio.sleep", side_effect=fake_sleep):
        await p02_ent.async_set_native_value(10.0)  # clamped to 30
        await p02_ent.async_set_native_value(200.0)  # clamped to 120
    assert coord._api.events[-2:] == [
        ("set_protocol_code", "P02", "30"),
        ("set_protocol_code", "P02", "120"),
    ]

    p03_desc = AquaTempNumberEntityDescription(
        key="P03", native_min_value=2, native_max_value=20, native_step=1
    )
    p03_ent = AquaTempNumberEntity(p03_desc, coord, "dev1")
    assert p03_ent._attr_native_value == 5.0
    with patch("asyncio.sleep", side_effect=fake_sleep):
        await p03_ent.async_set_native_value(1.0)  # clamped to 2
        await p03_ent.async_set_native_value(30.0)  # clamped to 20
    assert coord._api.events[-2:] == [
        ("set_protocol_code", "P03", "2"),
        ("set_protocol_code", "P03", "20"),
    ]

    # 3. Normal flow with P01=2, P03=7: P01->0 -> low setpoint -> heat -> sleep 7*60 -> OFF -> 29.0 -> P01->2
    coord = _make_coordinator(device_data={"P01": "2", "P03": "7"})
    slept = []
    with patch("asyncio.sleep", side_effect=fake_sleep):
        await coord.measure_temperature("dev1")
        task = coord._measure_tasks["dev1"]
        await coord.measure_temperature("dev1")
        assert coord._measure_tasks["dev1"] is task
        await task

    assert coord._api.events == [
        ("set_protocol_code", "P01", "0"),
        ("set_temperature", 15.0),
        ("set_hvac_mode", HVACMode.HEAT),
        ("set_hvac_mode", HVACMode.OFF),
        ("set_temperature", 29.0),
        ("set_protocol_code", "P01", "2"),
    ], f"Unexpected event order: {coord._api.events}"
    assert 420 in slept
    assert coord.refresh_count == 3
    assert "dev1" not in coord._measure_tasks
    assert coord.config_manager.get_pending_measure_restore("dev1") is None

    # 4. Already running: only refreshes, no commands sent
    coord = _make_coordinator()
    coord._api.power = True
    await coord.measure_temperature("dev1")
    assert coord._api.events == []
    assert coord.refresh_count == 1

    # 5. User raises target temperature mid-cycle: do not turn off or overwrite target, still restore P01
    coord = _make_coordinator()

    async def user_takeover_sleep(sec):
        if sec >= 60:
            coord._api.target = 31.0

    with patch("asyncio.sleep", side_effect=user_takeover_sleep):
        await coord.measure_temperature("dev1")
        await coord._measure_tasks["dev1"]

    assert coord._api.events == [
        ("set_protocol_code", "P01", "0"),
        ("set_temperature", 15.0),
        ("set_hvac_mode", HVACMode.HEAT),
        ("set_protocol_code", "P01", "2"),
    ], f"User takeover overwritten: {coord._api.events}"

    # 6. Cancelled mid-cycle (unload): turns OFF before restoring 29.0 and P01
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
        ("set_protocol_code", "P01", "0"),
        ("set_temperature", 15.0),
        ("set_hvac_mode", HVACMode.HEAT),
        ("set_hvac_mode", HVACMode.OFF),
        ("set_temperature", 29.0),
        ("set_protocol_code", "P01", "2"),
    ], f"Unsafe cancellation order: {coord._api.events}"

    # 7. Crash recovery: stays pending while offline, restores when back online
    coord = _make_coordinator(device_data={"P01": "0", "P03": "5"})
    coord._api.online = False
    coord._api.power = True
    coord._api.target = 15.0
    await coord.config_manager.set_pending_measure_restore(
        "dev1", {"min_temp": 15.0, "target_temp": 29.0, "p01": "2"}
    )
    with patch("asyncio.sleep", side_effect=fake_sleep):
        await coord._async_update_data()
        assert coord._api.events == []
        assert coord.config_manager.get_pending_measure_restore("dev1") is not None

        coord._api.online = True
        await coord._async_update_data()

    assert coord._api.events == [
        ("set_hvac_mode", HVACMode.OFF),
        ("set_temperature", 29.0),
        ("set_protocol_code", "P01", "2"),
    ], f"Unexpected recovery events: {coord._api.events}"
    assert coord.config_manager.get_pending_measure_restore("dev1") is None

    # 8. Initial P01 switch throws after delivery (e.g. response timeout): finally still restores P01
    coord = _make_coordinator(device_data={"P01": "2", "P03": "5"})
    p01_calls = []

    async def flaky_p01(dc, code, value):
        p01_calls.append((code, value))
        if len(p01_calls) == 1:
            coord._api.device_data[code] = value
            raise TimeoutError("timed out after delivery")
        coord._api.events.append(("set_protocol_code", code, value))
        coord._api.device_data[code] = value

    coord._api.set_protocol_code = flaky_p01
    with patch("asyncio.sleep", side_effect=fake_sleep):
        await coord.measure_temperature("dev1")
        await coord._measure_tasks["dev1"]

    assert p01_calls == [("P01", "0"), ("P01", "2")], f"P01 not restored: {p01_calls}"
    assert coord._api.device_data["P01"] == "2"

    # 9. _perform_action clears token and re-connects on transient failure, and _post_request closes connection + sets timeout
    from custom_components.aqua_temp.managers.aqua_temp_api import (
        API_REQUEST_TIMEOUT,
        AquaTempAPI,
    )

    cm = AquaTempConfigManager(None, None)
    cm._api_config = {
        "url": "https://example.invalid",
        "suffix": "",
        "error_msg": "error_msg",
        "error_code": "error_code",
    }
    api = AquaTempAPI(None, cm)
    api.set_token("stale-token")
    connects = []

    async def fake_connect():
        connects.append(api._token)
        api.set_token("fresh-token")

    post_calls = []

    class _FakeResp:
        def __init__(self, payload):
            self._payload = payload

        def raise_for_status(self):
            pass

        async def json(self):
            return self._payload

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

    class _FakeSession:
        def post(self, url, headers=None, json=None, ssl=None, timeout=None):
            post_calls.append({"headers": dict(headers or {}), "timeout": timeout})
            if len(post_calls) == 1:
                raise ConnectionResetError("stale keep-alive")
            return _FakeResp({"error_msg": "Success", "error_code": "0"})

    api._session = _FakeSession()
    api._connect = fake_connect
    with patch("custom_components.aqua_temp.managers.aqua_temp_api.sleep", side_effect=fake_sleep):
        await api._perform_action({"param": []}, "Power")

    assert connects == [None], f"Token was not cleared before retry: {connects}"
    assert len(post_calls) == 2
    assert post_calls[0]["headers"].get("Connection") == "close"
    assert post_calls[0]["timeout"] == API_REQUEST_TIMEOUT

    print("ALL TESTS PASSED")


if __name__ == "__main__":
    asyncio.run(run_tests())
