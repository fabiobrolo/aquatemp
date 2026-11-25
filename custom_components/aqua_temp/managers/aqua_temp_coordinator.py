import asyncio
import logging

from homeassistant.components.climate import HVACMode
from homeassistant.core import Event
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from ..common.api_types import APIParam
from ..common.consts import (
    DATA_ITEM_CONFIG,
    DATA_ITEM_DEVICES,
    DATA_ITEM_LOGIN_DETAILS,
    DEFAULT_CIRCULATION_DURATION,
    DOMAIN,
    PROTOCOL_CODE_PUMP_DURATION,
    PROTOCOL_CODE_PUMP_MODE,
    PUMP_DURATION_MAX,
    PUMP_DURATION_MIN,
    PUMP_MODE_CONTINUOUS,
    UPDATE_API_INTERVAL,
)
from ..models.exceptions import LoginError
from .aqua_temp_api import AquaTempAPI
from .aqua_temp_config_manager import AquaTempConfigManager

_LOGGER = logging.getLogger(__name__)


class AquaTempCoordinator(DataUpdateCoordinator):
    """My custom coordinator."""

    def __init__(
        self,
        hass,
        config_manager: AquaTempConfigManager,
    ):
        """Initialize my coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=config_manager.entry_title,
            update_interval=UPDATE_API_INTERVAL,
            update_method=self._async_update_data,
        )

        self._api = AquaTempAPI(hass, config_manager)
        self._config_manager = config_manager
        self._measure_tasks: dict[str, asyncio.Task] = {}

    @property
    def api_status(self):
        return self._api.is_connected

    @property
    def config_manager(self):
        return self._config_manager

    @property
    def devices(self):
        return self._api.devices

    @property
    def login_details(self):
        return self._api.login_details

    async def on_home_assistant_start(self, _event_data: Event):
        await self.initialize()

    async def initialize(self):
        """Initialize the integration.

        LoginError (bad credentials) is allowed to propagate so async_setup_entry
        can mark the integration as failed. Any other exception (DNS timeout,
        transient network error, AquaTemp cloud blip) is caught and logged so
        platform setup still proceeds and the regular 5-min update tick retries.
        """
        _LOGGER.debug("Initializing coordinator")

        entry = self.config_manager.entry
        platforms = self.config_manager.platforms

        try:
            await self._api.initialize(throw_error=True)

        except LoginError:
            raise

        except Exception as ex:
            _LOGGER.warning(
                f"Initial API connect failed; coordinator will retry on next "
                f"update. Error: {ex}"
            )

        await self.hass.config_entries.async_forward_entry_setups(entry, platforms)

        _LOGGER.info(f"Start loading {DOMAIN} integration, Entry ID: {entry.entry_id}")

        await self.async_request_refresh()

    def get_device(self, device_code: str) -> DeviceInfo:
        param_nickname = self._config_manager.get_api_param(APIParam.Nickname)
        param_device_id = self._config_manager.get_api_param(APIParam.DeviceId)
        param_custom_model = self._config_manager.get_api_param(APIParam.CustomModel)

        device_data = self.get_device_data(device_code) or {}
        device_nickname = device_data.get(param_nickname)
        device_model = device_data.get(param_custom_model)
        device_id = device_data.get(param_device_id)

        if param_custom_model in device_data:
            device_model = device_data.get(param_custom_model)

        device_info = DeviceInfo(
            identifiers={(DOMAIN, device_id)},
            name=device_nickname,
            model=device_model,
        )

        return device_info

    def get_debug_data(self) -> dict:
        config_data = self._config_manager.get_debug_data()

        data = {
            DATA_ITEM_DEVICES: self.devices,
            DATA_ITEM_CONFIG: config_data,
            DATA_ITEM_LOGIN_DETAILS: self._api.login_details,
        }

        return data

    async def _async_update_data(self):
        """Fetch parameters from API endpoint.

        This is the place to pre-process the parameters to lookup tables
        so entities can quickly look up their parameters.
        """
        try:
            await self._api.update()
            await self._restore_pending_measurements()

            config_data = self._config_manager.get_debug_data()

            return {
                DATA_ITEM_DEVICES: self.devices,
                DATA_ITEM_LOGIN_DETAILS: self._api.login_details,
                DATA_ITEM_CONFIG: config_data,
            }

        except Exception as err:
            raise UpdateFailed(f"Error communicating with API: {err}")

    def get_temperature_unit(self, device_code: str):
        return self._config_manager.get_temperature_unit(device_code)

    async def set_hvac_mode(self, device_code: str, hvac_mode: HVACMode):
        await self._api.set_hvac_mode(device_code, hvac_mode)
        await asyncio.sleep(1)
        await self.async_request_refresh()

    async def set_temperature(self, device_code: str, temperature: float):
        await self._api.set_temperature(device_code, temperature)
        await asyncio.sleep(1)
        await self.async_request_refresh()

    async def set_fan_mode(self, device_code: str, fan_mode):
        await self._api.set_fan_mode(device_code, fan_mode)
        await asyncio.sleep(1)
        await self.async_request_refresh()

    async def set_temperature_unit(self, device_code: str, option: str):
        await self._config_manager.update_temperature_unit(device_code, option)

        await self.async_request_refresh()

    async def set_protocol_code(
        self, device_code: str, protocol_code: str, value: str
    ):
        await self._api.set_protocol_code(device_code, protocol_code, value)
        self.async_update_listeners()
        await asyncio.sleep(1)
        await self.async_request_refresh()

    async def set_protocol_codes(
        self, device_code: str, values: dict[str, str]
    ):
        await self._api.set_protocol_codes(device_code, values)
        self.async_update_listeners()
        await asyncio.sleep(1)
        await self.async_request_refresh()

    def get_measure_duration(self, device_code: str) -> int:
        device_data = self.get_device_data(device_code) or {}
        raw_value = device_data.get(PROTOCOL_CODE_PUMP_DURATION)
        if raw_value not in (None, ""):
            try:
                parsed = int(round(float(str(raw_value))))
                return max(PUMP_DURATION_MIN, min(PUMP_DURATION_MAX, parsed))
            except (ValueError, TypeError):
                pass
        return DEFAULT_CIRCULATION_DURATION

    async def cancel_tasks(self):
        for task in list(self._measure_tasks.values()):
            if not task.done():
                task.cancel()
        if self._measure_tasks:
            await asyncio.gather(*self._measure_tasks.values(), return_exceptions=True)
        self._measure_tasks.clear()

    async def measure_temperature(self, device_code: str):
        """Circulate water with minimum setpoint so the heat pump reads pool temperature."""
        if not self.get_device_is_online(device_code):
            _LOGGER.warning(
                f"Cannot measure temperature for {device_code}: device is offline"
            )
            return

        existing = self._measure_tasks.get(device_code)
        if existing and not existing.done():
            _LOGGER.warning(
                f"Temperature measurement already running for {device_code}"
            )
            return

        if self.get_device_power(device_code):
            _LOGGER.info(
                f"Device {device_code} is already running; refreshing temperature only"
            )
            await self.async_request_refresh()
            return

        self._measure_tasks[device_code] = self.hass.async_create_task(
            self._run_measure_temperature(device_code)
        )

    async def _restore_pending_measurements(self):
        """Restore P01 / setpoint if an earlier measurement was interrupted."""
        for device_code in list(self.devices):
            task = self._measure_tasks.get(device_code)
            if task and not task.done():
                continue

            pending = self._config_manager.get_pending_measure_restore(device_code)
            if not pending or not self.get_device_is_online(device_code):
                continue

            await self._restore_pending_for_device(device_code, pending)

    async def _restore_pending_for_device(self, device_code: str, pending: dict):
        min_temp = float(pending.get("min_temp", 15.0))
        original_target = pending.get("target_temp")
        original_p01 = pending.get("p01")

        device_data = self.get_device_data(device_code) or {}
        raw_p01 = device_data.get(PROTOCOL_CODE_PUMP_MODE)
        current_p01 = str(raw_p01).strip() if raw_p01 not in (None, "") else None
        current_target = self.get_device_target_temperature(device_code)
        user_took_over = (
            current_target is not None and current_target > min_temp + 0.5
        )

        _LOGGER.warning(
            f"Recovering interrupted temperature measurement for {device_code}: "
            f"pending={pending}, current_p01={current_p01}, current_target={current_target}"
        )

        restored_ok = True
        try:
            if not user_took_over and self.get_device_power(device_code):
                await self._api.set_hvac_mode(device_code, HVACMode.OFF)
                await asyncio.sleep(2)

            if (
                not user_took_over
                and original_target is not None
                and current_target is not None
                and current_target <= min_temp + 0.5
                and original_target != min_temp
            ):
                await self._api.set_temperature(device_code, float(original_target))
                await asyncio.sleep(1)
        except Exception as err:
            restored_ok = False
            _LOGGER.error(
                f"Failed to recover power/setpoint for {device_code}: {err}"
            )

        if original_p01 is not None and current_p01 != str(original_p01):
            try:
                await self._api.set_protocol_code(
                    device_code, PROTOCOL_CODE_PUMP_MODE, str(original_p01)
                )
                await asyncio.sleep(1)
            except Exception as err:
                restored_ok = False
                _LOGGER.error(
                    f"Failed to recover {PROTOCOL_CODE_PUMP_MODE} to "
                    f"{original_p01} for {device_code}: {err}"
                )

        if restored_ok:
            await self._config_manager.clear_pending_measure_restore(device_code)
            _LOGGER.info(
                f"Recovered interrupted temperature measurement for {device_code}"
            )

    async def _run_measure_temperature(self, device_code: str):
        duration_minutes = self.get_measure_duration(device_code)
        original_target = self.get_device_target_temperature(device_code)
        min_temp = self.get_device_minimum_temperature(device_code) or 15.0

        device_data = self.get_device_data(device_code) or {}
        raw_pump_mode = device_data.get(PROTOCOL_CODE_PUMP_MODE)
        original_pump_mode = (
            str(raw_pump_mode).strip() if raw_pump_mode not in (None, "") else None
        )

        modes = [m for m in self.get_hvac_modes(device_code) if m != HVACMode.OFF]
        target_mode = modes[0] if modes else HVACMode.HEAT

        turned_on = False
        setpoint_lowered = False
        pump_mode_changed = False
        cancelled = False

        pending_restore = {"min_temp": min_temp}
        if original_target is not None and original_target != min_temp:
            pending_restore["target_temp"] = original_target
        if (
            original_pump_mode is not None
            and original_pump_mode != PUMP_MODE_CONTINUOUS
        ):
            pending_restore["p01"] = original_pump_mode

        await self._config_manager.set_pending_measure_restore(
            device_code, pending_restore
        )

        _LOGGER.info(
            f"Starting temperature measurement for {device_code}: "
            f"duration={duration_minutes}min, low_setpoint={min_temp}, "
            f"original_setpoint={original_target}, original_p01={original_pump_mode}"
        )

        try:
            if (
                original_pump_mode is not None
                and original_pump_mode != PUMP_MODE_CONTINUOUS
            ):
                # Mark before sending so finally still restores P01 if a response times out after delivery
                pump_mode_changed = True
                try:
                    await self._api.set_protocol_code(
                        device_code, PROTOCOL_CODE_PUMP_MODE, PUMP_MODE_CONTINUOUS
                    )
                    await asyncio.sleep(1)
                except Exception as pump_err:
                    _LOGGER.warning(
                        f"Could not switch {PROTOCOL_CODE_PUMP_MODE} to "
                        f"{PUMP_MODE_CONTINUOUS} for {device_code}: {pump_err}"
                    )

            await self._api.set_temperature(device_code, min_temp)
            setpoint_lowered = True
            await asyncio.sleep(2)

            await self._api.set_hvac_mode(
                device_code, target_mode, target_temperature=min_temp
            )
            turned_on = True
            self.async_update_listeners()
            await asyncio.sleep(1)
            await self.async_request_refresh()

            await asyncio.sleep(duration_minutes * 60)

            await self.async_request_refresh()
        except asyncio.CancelledError:
            cancelled = True
            raise
        except Exception as err:
            _LOGGER.error(
                f"Error during temperature measurement for {device_code}: {err}"
            )
        finally:
            restored_ok = True
            try:
                current_target = self.get_device_target_temperature(device_code)
                user_took_over = (
                    not cancelled
                    and current_target is not None
                    and current_target > min_temp + 0.5
                )

                # Turn off BEFORE restoring original setpoint so compressor never triggers
                if turned_on and not user_took_over and self.get_device_power(device_code):
                    await self._api.set_hvac_mode(device_code, HVACMode.OFF)
                    await asyncio.sleep(2)

                if (
                    setpoint_lowered
                    and not user_took_over
                    and original_target is not None
                    and original_target != min_temp
                ):
                    await self._api.set_temperature(device_code, original_target)
                    await asyncio.sleep(1)
            except Exception as cleanup_err:
                restored_ok = False
                _LOGGER.error(
                    f"Failed to restore power/setpoint after temperature measurement "
                    f"for {device_code}: {cleanup_err}"
                )

            if pump_mode_changed and original_pump_mode is not None:
                try:
                    await self._api.set_protocol_code(
                        device_code, PROTOCOL_CODE_PUMP_MODE, original_pump_mode
                    )
                    await asyncio.sleep(1)
                except Exception as pump_restore_err:
                    restored_ok = False
                    _LOGGER.error(
                        f"Failed to restore {PROTOCOL_CODE_PUMP_MODE} to "
                        f"{original_pump_mode} for {device_code}: {pump_restore_err}"
                    )

            if restored_ok:
                await self._config_manager.clear_pending_measure_restore(device_code)

            try:
                if not cancelled:
                    self.async_update_listeners()
                    await self.async_request_refresh()
            except Exception as refresh_err:
                _LOGGER.error(
                    f"Failed final refresh after temperature measurement "
                    f"for {device_code}: {refresh_err}"
                )
            finally:
                self._measure_tasks.pop(device_code, None)

    def get_device_data(self, device_code: str) -> dict | None:
        device_data = self._api.get_device_data(device_code)

        return device_data

    def get_device_status(self, device_code: str) -> str:
        return self._api.get_device_status(device_code)

    def get_device_is_online(self, device_code: str) -> bool:
        return self._api.get_device_is_online(device_code)

    def get_device_target_temperature(self, device_code: str) -> float | None:
        target_temperature = self._api.get_device_target_temperature(device_code)

        return target_temperature

    def get_device_current_temperature(self, device_code: str) -> float | None:
        current_temperature = self._api.get_device_current_temperature(device_code)

        return current_temperature

    def get_device_minimum_temperature(self, device_code: str) -> float | None:
        minimum_temperature = self._api.get_device_minimum_temperature(device_code)

        return minimum_temperature

    def get_device_maximum_temperature(self, device_code: str) -> float | None:
        maximum_temperature = self._api.get_device_maximum_temperature(device_code)

        return maximum_temperature

    def get_device_hvac_mode(self, device_code: str) -> HVACMode:
        hvac_mode = self._api.get_device_hvac_mode(device_code)

        return hvac_mode

    def get_device_fan_mode(self, device_code: str) -> str:
        fan_mode = self._api.get_device_fan_mode(device_code)

        return fan_mode

    def get_device_power(self, device_code: str) -> bool:
        power = self._api.get_device_power(device_code)

        return power

    def get_hvac_modes(self, device_code: str) -> list[HVACMode]:
        modes = self._config_manager.get_hvac_modes(device_code)

        result = [HVACMode(mode) for mode in modes]

        return result

    def get_fan_modes(self, device_code: str) -> list[str]:
        modes = self._config_manager.get_fan_modes(device_code)

        return modes
