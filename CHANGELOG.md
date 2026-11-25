# Changelog

## 3.2.0

- Expose on-board **Local Timer** controls for product ID `1442284873216843776` (`PC1001`) as editable `CONFIG` entities (`switch` and `time`) with full `en` and `pt-BR` localization:
  - Start timer (`1510`) and Timer start time (`1511` / `1512`, 10-minute increments)
  - End timer (`1509`) and Timer end time (`1513` / `1514`, 10-minute increments)
  - Silent mode timer (`H05`), Silent mode start time (`F15`), and Silent mode end time (`F17`, whole hours)
- Add atomic multi-code writes (`set_protocol_codes`) and immediate coordinator listener updates after parameter changes

## 3.1.1

- Prevent multi-minute stalls on idle keep-alive sockets by closing HTTP connections and enforcing a 20s request timeout (`ClientTimeout(total=20, connect=10)`)
- Re-authenticate on any `DeviceControl` retry (and handle numeric `-100` error codes) so expired/kicked sessions recover on the first button press
- Always restore `P01` in `Measure temperature` cleanup even if the initial `P01` switch timed out after delivery
- Preserve minimum target temperature across `set_hvac_mode` during `Measure temperature` and notify HA entities immediately on turn-on/off

## 3.1.0

- Expose water pump controller parameters as editable configuration entities: `Water pump mode [P01]` (`select`: continuous / with_compressor / intermittent), `Water pump interval [P02]` (`number`: 30–120 min), and `Water pump duration [P03]` (`number`: 2–20 min)
- Replace local `circulation_duration` number with `P03` for the `Measure temperature` button duration (with `5 min` fallback for models without `P03`)
- Adopt modern Home Assistant localization (`has_entity_name = True`, `translation_key`, translated select states) with full `en` and `pt-BR` translations
- Document `P01`, `P02`, `P03`, and `Measure temperature` in `README.md`

## 3.0.44

- Persist `pending_measure_restore` before starting `Measure temperature` so `P01`, power state, and target temperature are automatically recovered on startup or when the device returns online after an interruption

## 3.0.43

- Automatically switch `P01` to continuous (`0`) during `Measure temperature` and restore original `P01` afterward

## 3.0.42

- Add `Measure temperature` button to circulate pool water at minimum setpoint without engaging the compressor

## 3.0.37

- Initialize data using `async_request_refresh` instead of `async_config_entry_first_refresh` to remove warning message

## 3.0.36

- Add support for more products [PR #83](https://github.com/radical-squared/aquatemp/pull/83) by [@Know1](https://github.com/Know1)

## 3.0.35

- Fix minimum / maximum values according to HVAC mode

## 3.0.34

- Fix relative path of config files

## 3.0.33

- Fix "detected blocking call to open inside the event loop by custom integration" error

## 3.0.32

- Fix warning - StrEnum is a deprecated alias which will be removed in HA Core 2025.5. Use enum.StrEnum instead

## 3.0.31

- Disable climate backwards compatibility flag

## 3.0.30

- Fix error message `implicitly supporting turn_on/turn_off` introduced in v2024.2

## 3.0.29

- Replaced soon (2025) to get deprecated SUPPORT\_\* constant with ClimateEntityFeature

## 3.0.28

_Minimum HA Version: 2024.1.0b0_

- Set minimum HA version for component to 2024.1.0b0

## 3.0.27

_Minimum HA Version: 2024.1.0_

- Adjust code to HA 2024.1.0

## v3.0.26

- Change API update from 30 seconds to 5 minutes, will update also when action is being performed
- Redact sensitive details from diagnostic file
- Fix diagnostic file creation process

## v3.0.25

### Breaking Change!

Password store format changed, up until now, password saved as the hash being send to the API,

To allow the enhanced functionality added, to edit Credentials and API Type, the password is now being saved encrypted and decrypted in 2 flows:

1. Edit integration details
2. On startup (hashed and sent to the API)

As result of that process, you need to re-setup the integration.

### Changes

- Add to set up configuration form new field of title to define the name of the integration
- Add edit integration details - Title, Credentials and API Type
- Refactor component initialization code to simplify process
- Fix `UndefinedType._singleton` name for climate entity

## v3.0.24

- Add missing configuration for API param 'error_code'

## v3.0.23

- Fix APIParam class, caused corrupted data on component creation and error code handling

## v3.0.22

- Fix binary sensor state evaluation

## v3.0.21

- Fix vacuum entity name
- Fix add integration (config) error handling

## v3.0.20

- Fix error handling when performing an action
- Optimize components loading

## v3.0.19

- Fix error handling when fetch data failed

## v3.0.18

- Add more parameters to API type configuration
- Extract model for HA DeviceInfo from API
- Add translation key to all components with name ready for translation

## v3.0.17

- Fix logic to extract protocol codes
- Fix mappings of product ID 1442284873216843776

## v3.0.16

- Optimize error handling for fetch device data

## v3.0.15

- Add log to update device

## v3.0.14

- Fix for the new capability of AquaTemp of single app to login, will re-login on every attempt to perform action / refresh
- Add new binary sensor of `API Status` represents whether the API is authenticated (logged in) or not

## v3.0.13

- Add API Type drop-down to configuration (Aqua Temp, Hitemp, Aqua Temp [=<1.5.8])
- Update authentication process

## v3.0.12

- Fix config flow, API manager constructor requires three parameters but only two are passed when creating it

## v3.0.11

- Per device's product ID parameters support

## v3.0.10

- Handling expired token error (401) more gracefully (re-login)

## v3.0.9

- Add support for product ID `1245226668902080512` [#25](https://github.com/radical-squared/aquatemp/issues/25)

## v3.0.8

- Fix missing `Off` mode for climate

## v3.0.7

- Improve support for devices of product ID `1442284873216843776`

## v3.0.6

- Fix device's empty values as `None` handling

## v3.0.5

- Set device's empty values as `None`

## v3.0.4

- Add device discovery for new devices without need to reload integration
- Fix integration reload issue
- Entities code clean up
- API stabilization after timeout
- Fix target temperature parameter mapping (Heat, Cool and Auto)
- Fix parameter mapping for P01 (Water pump mode)

## v3.0.3

- Fix setting HVAC mode
- Support shared devices
- Support multiple product IDs, Solution provided by [sjtrny](https://github.com/sjtrny) for issue [#25](https://github.com/radical-squared/aquatemp/issues/25)

## v3.0.2

- Fix configuration saving, without credentials
- Fix socket timeouts
- Add `suggested_unit_of_measurement=UnitOfElectricPotential.VOLT` to sensors of `SensorDeviceClass.VOLTAGE`
- Fix token clean-up
- Code clean up for entities
- HVAC Mode Mapping in v3.0.1 is mixed up [#29](https://github.com/radical-squared/aquatemp/issues/29)
- Block API operations if initial login failed

## v3.0.1

- Refactor entity's creation (using EntityDescription)
- Mapped all protocol codes to `EntityDescription`
- Add more entities (updated list in README)
- Create [Protocol Codes](https://github.com/radical-squared/aquatemp/blob/master/PROTOCOL_CODES.md) document
- Fix `climate` HVAC Modes

## v3.0.0

- Major refactor to the code - Breaking changes
- Configuration is available only from UI
- Supports multiple accounts (different credentials)
- Supports multiple devices (different devices on the same account)
- Add centralized `DataUpdateCoordinator` to communicate with the API and post updates to HA components
- Set minimum and maximum temperature based on the current HVAC mode relevant for the device (from API)
- Add `diagnostic` component to output data from API and configuration for troubleshooting (replacing the need for extra codes attributes)
- Add `binary_sensor` components for Power (Is on), Status (Is online) and Fault (Has fault)
- Add `select` component for choosing the Temperature Unit (C/F)
- Add `sensor` components for each of the temperature reading (T01-T03)
- Simplified `climate` component to include just its functionality without additional attributes (moved to dedicated components)
- Add mapping of more Protocol Codes (Parameters) for later support of more sensors/binary_sensors
