# QA Testing Plan for v2.0.0 release

This checklist covers end-to-end manual verification in a live Home Assistant instance, focusing on **new installation setup flows**, **upgrades from existing installations**, **localization/translations**, and **core functional regressions**.

## 0. Preparation

1. **Enable Debug Logging**
   Add the following to `configuration.yaml` (or call `logger.set_level` in **Developer Tools → Actions**) so you can observe coordinator refreshes, storage reads/writes, coordinate resolution, and error redaction in **Settings → System → Logs**:
   ```yaml
   logger:
     logs:
       custom_components.weatherdotcom: debug
   ```
2. **Back Up `.storage/` Before Testing Upgrades**
   Before upgrading an existing Home Assistant instance (or test container), back up:
   - `.storage/core.config_entries`
   - `.storage/core.device_registry`
   - `.storage/core.entity_registry`
   - `.storage/weatherdotcom_data_*`

   Keeping a copy of `.storage/` lets you restore and repeat multiple upgrade scenarios (e.g., legacy entries without `location_source`, entries with custom titles, and entries with extra attributes enabled).

## 1. New Installation Setup Flows (`config_flow.py`)

### 1.1 Step 1 (`user`) — Defaults & Validation
- [ ] **Default Values:** Start adding the **Weather.com** integration (**Settings → Devices & Services → Add Integration**). Verify:
  - **Location Name** defaults to your Home Assistant instance's configured name (`hass.config.location_name`).
  - **Language** defaults to the best match for your Home Assistant language/country via `_get_default_lang`
  - **Location Source** defaults to **Latitude/Longitude**.
- [ ] **Invalid API Key (`401`) & Input Retention:** Enter a custom **Location Name** (e.g., `Vacation`), a non-default **Language**, and a bogus API key, then submit.
  - Confirm the form stays on Step 1, displays `"The API key is invalid."` (`invalid_api_key`), and **preserves your entered values** (`Vacation`, selected language, and API key) via `add_suggested_values_to_schema`.
- [ ] **Network Error & API Key Redaction:** Temporarily block outbound access to `api.weather.com` (or disconnect network) and submit a key.
  - Confirm the form displays `"Failed to connect to Weather.com..."` (`cannot_connect`).
  - Check **Settings → System → Logs** and verify the raw API key is replaced with `REDACTED` if an exception message included the request URL.
- [ ] **Duplicate Name Prevention:** After creating an entry named `Home`, start a new config flow and test:
  - Exact match: `Home` → rejected with `"A Weather.com integration with this name already exists..."` (`already_configured`).
  - Case-insensitive match: `home` or `HOME` → rejected with `already_configured`.
  - Slug collision: if an entry is named `My Home`, try `my_home` → rejected with `already_configured`.

### 1.2 Step 2A — Fixed Coordinates (`latlong`)
- [ ] **Default Coordinates:** Choose **Latitude/Longitude** on Step 1. Confirm Step 2 pre-fills Home Assistant's configured latitude and longitude.
- [ ] **Coordinate Range Validation:** Try submitting `latitude: 95` or `longitude: -195` (note: the UI numeric input accepts floats).
  - Confirm it rejects out-of-range coordinates with `"Latitude must be between -90 and 90, and longitude must be between -180 and 180."` (`invalid_coordinates`).
- [ ] **Successful Entry & Entity Creation:** Submit valid coordinates and verify:
  - One service device (`Weather.com`) is created under the integration.
  - **1 weather entity** (`weather.<location_slug>`) and **27 sensor entities** (`sensor.<location_slug>_*`) are registered.
  - **25 sensors** are enabled by default; **2 sensors** (`sensor.<location_slug>_icon_code` and `sensor.<location_slug>_forecast_details`) are disabled by default (`disabled_by: integration`).

### 1.3 Step 2B — Tracked Entity (`entity`)
- [ ] **Entity Selector Filtering:** Choose **Entity (zone, device_tracker, or person)** on Step 1.
  - Confirm the entity picker only lists `zone.*`, `device_tracker.*`, and `person.*` entities.
- [ ] **Missing Coordinates Validation:** Select a `device_tracker` or `person` entity whose state currently lacks `latitude`/`longitude` attributes (or create a helper/template state via **Developer Tools → States** without coordinates).
  - Confirm the form displays `"The selected entity does not have valid latitude and longitude attributes."` (`invalid_location_entity`).
- [ ] **Coordinate Rounding (Privacy/Obfuscation):** Select `zone.home` (or a `person` entity with high-precision GPS coordinates like `33.748995, -84.387982`).
  - After setup completes, inspect `sensor.<location_slug>_latitude` and `sensor.<location_slug>_longitude` and confirm the values are rounded to **2 decimal places** (`33.75`, `-84.39`).


## 2. Upgrade Flows for an Existing Installation

### 2.1 Seamless In-Place Upgrade (Entity & History Continuity)
- [ ] **Upgrade with Existing Entries Configured:** Install the updated integration over an existing setup and restart Home Assistant.
- [ ] **Verify Registry Continuity:**
  - Confirm no `_2` duplicate entities are created.
  - Confirm all existing entity customizations (custom entity names, areas, labels, dashboards, and long-term statistics/history) remain attached to the original entities.
  - Confirm `weather.<location_slug>` has `has_entity_name: true` and uses the device name as its friendly name.
  - Confirm `.storage/weatherdotcom_data_<location>` loads cleanly on startup without warnings in the log.

### 2.2 Legacy Config Entries (Pre-`location_source`)
- [ ] **Legacy Entry Without `location_source` Key:** If upgrading from an older version (or testing by removing `"location_source"` from an entry in `.storage/core.config_entries`), restart Home Assistant.
  - Confirm `WeatherUpdateCoordinator` falls back to the existing `latitude`/`longitude` (or `entity_id`) seamlessly and updates normally.

### 2.3 Entries with Stale Location Keys from Older Reconfigures
- [ ] **Stale Key Isolation:** Older versions of the integration merged `user_input` during reconfigure, which could leave both `entity_id` and `latitude`/`longitude` in `entry.data`.
  - Confirm that when `location_source` is `"latlong"`, any lingering `entity_id` in `entry.data` is ignored by the coordinator, and when `location_source` is `"entity"`, any lingering `latitude`/`longitude` in `entry.data` is ignored.

### 2.4 Reconfigure Flow (`async_step_reconfigure`)
- [ ] **Preserve Custom Entry Title & Internal `CONF_NAME`:**
  1. Rename a config entry's title in the UI (**three-dots menu → Rename**) from `Home` to `Atlanta Weather`.
  2. Open **three-dots menu → Reconfigure** on that entry.
  3. Confirm current `api_key`, `lang`, and `location_source` are pre-populated as defaults.
  4. Complete the reconfigure flow and verify:
     - The entry's custom title (`Atlanta Weather`) is preserved.
     - `entry.data["name"]` remains `Home` so device identifiers, entity unique IDs, and storage keys do not break.
- [ ] **Switch Location Source (`latlong` ↔ `entity`) & Clean Stale Keys:**
  1. Reconfigure an entry from **Latitude/Longitude** to **Entity** (`zone.home`).
  2. Confirm the entry automatically reloads and shows `"The Weather.com integration was reconfigured successfully."`
  3. Inspect `.storage/core.config_entries` for this entry and confirm `latitude` and `longitude` were removed and replaced by `entity_id: "zone.home"`.
  4. Reconfigure the same entry back to **Latitude/Longitude** and confirm `entity_id` is removed and replaced by `latitude` and `longitude`.

### 2.5 Options Flow (`Extra Weather Attributes` & `Forecast Details` Sensor)
- [ ] **Auto-Enable `Forecast Details` When Selecting Attributes:**
  1. On a newly created entry (where `sensor.<location_slug>_forecast_details` is disabled by the integration), click **Configure**.
  2. Select at least one attribute from **Daily Attributes** (e.g., `daily_narrative`, `sunrise`), **Day Attributes** (e.g., `day_icon_code`), and **Daypart Attributes** (e.g., `daypart_narrative`) and submit.
  3. Verify the config entry reloads automatically (`OptionsFlowWithReload`).
  4. Verify `sensor.<location_slug>_forecast_details` is **automatically enabled** in the Entity Registry (`disabled_by: null`) and transitions to a valid ISO UTC timestamp state with the selected lists in its `extra_state_attributes`.
- [ ] **Auto-Disable When Clearing All Attributes:**
  1. Open **Configure** again, deselect all attributes across all three lists, and submit.
  2. Verify `sensor.<location_slug>_forecast_details` is automatically disabled again (`disabled_by: integration`).
- [ ] **Respect User-Disabled State:**
  1. Manually disable `sensor.<location_slug>_forecast_details` via the Home Assistant UI (so `disabled_by` is `user`).
  2. Open **Configure** and select extra attributes.
  3. Verify the options flow does **not** override the user's explicit disable (`disabled_by` remains `user`).

## 3. Localization & Translation Verification

### 3.1 UI Translations Across Supported Languages
The integration includes 12 translation files (`de`, `en`, `es`, `es-419`, `fr`, `hu`, `it`, `pl`, `pt-BR`, `sk`, `zh-Hans`, `zh-Hant`) plus [`icons.json`].
- [ ] **Switch User Profile Language:** In **Profile → Language**, switch to a non-English language (e.g., **Español**, **Deutsch**, **Français**, or **简体中文**) and hard-refresh the browser:
  - **Setup & Reconfigure Forms:** Verify step descriptions, field labels (`api_key`, `name`, `lang`, `location_source`, `latitude`, `longitude`, `entity_id`), and the **Location Source** radio options (`latlong` / `entity`) are translated.
  - **Options Flow Form:** Click **Configure** and verify the title, description, and attribute group labels (`Daily Attributes`, `Day Attributes`, `Daypart Attributes`) are translated.
  - **Sensor Names & Icons:** View the device page and confirm all 27 sensor friendly names are localized (e.g., `<Location> <Translated Sensor Name>`) and display their expected Material Design icons from [`icons.json`].

### 3.2 Stable English Entity IDs Under Non-English UI
- [ ] **Create Entry While UI is Non-English:** While your Home Assistant profile/system language is set to a non-English language (e.g., German or Chinese), add a new Weather.com location named `TestCity`.
  - Verify that the **friendly names** in the UI are localized, while the **entity IDs** remain deterministic English slugs derived from `translation_key` (e.g., `sensor.testcity_temperature`, `sensor.testcity_wind_direction_cardinal`, `sensor.testcity_forecast_details`).

### 3.3 Smart Default API Language Selection (`_get_default_lang`)
- [ ] Verify the **Language** dropdown default in Step 1 of the config flow under different HA language/country settings:
  - `en` with country `US` → `en-US`; `en` with country `GB` → `en-GB`
  - `es` with country `MX` → `es-MX`; `es` with country `ES` → `es-ES`
  - `zh-Hans` → `zh-CN`; `zh-Hant` → `zh-TW`
  - `nb` or `nn` → `no-NO`

### 3.4 Localized Weather.com API Content
- [ ] Reconfigure an entry's **Language** to a non-English code (e.g., `es-ES` or `fr-FR`) and verify that text-based sensors update to the target language:
  - `sensor.<location>_weather_description` (e.g., `"Parcialmente nublado"`)
  - `sensor.<location>_cloud_cover_phrase`
  - `sensor.<location>_pressure_tendency_trend`
  - `sensor.<location>_wind_direction_cardinal`
  - `daily_narrative` / `daypart_narrative` on `sensor.<location>_forecast_details`

## 4. Core Functional & Regression Verification

### 4.1 Weather Entity & `weather.get_forecasts` (`weather.py`)
- [ ] **Weather Entity State & Attributes:** Inspect `weather.<location>` in **Developer Tools → States** and on a Lovelace Weather Forecast card:
  - State matches a valid Home Assistant weather condition (`sunny`, `partlycloudy`, `rainy`, `clear-night`, etc.).
  - Attributes populate accurately: `temperature`, `apparent_temperature`, `dew_point`, `humidity`, `pressure`, `wind_speed`, `wind_gust_speed`, `wind_bearing`, `visibility`, `uv_index`, and `attribution` (`"Data provided by Weather.com"`).
- [ ] **Forecast Service Calls (`daily`, `twice_daily`, `hourly`):** In **Developer Tools → Actions**, call `weather.get_forecasts` targeting `weather.<location>` for each `type`:
  - `type: daily`: Returns 15 daily forecast items with `datetime`, `condition`, `temperature` (high), `templow`, `precipitation`, `precipitation_probability` (max of day & night when daytime is active), `wind_speed`, `wind_bearing`, `humidity`, `uv_index`, and `cloud_coverage`.
  - `type: twice_daily`: Returns 30 items (daytime) or 29 items (after 15:00 local time), alternating `is_daytime: true` and `is_daytime: false` (with nighttime `datetime` offset by +12 hours).
  - `type: hourly`: Returns ~360 hourly items including `apparent_temperature`, `dew_point`, `wind_gust_speed`, `temperature`, `precipitation`, `precipitation_probability`, `wind_speed`, `wind_bearing`, `humidity`, `uv_index`, and `cloud_coverage`.

### 4.2 Evening Expired-Daypart Behavior (After ~15:00 Local Time)
After ~15:00 local time at the forecasted location, the Weather.com API returns `null` for `temperatureMax[0]` and all `daypart[0]` index `0` fields.
- [ ] **High Temperature Restoration from Storage:**
  - Verify `.storage/weatherdotcom_data_<location>` contains `high_temp_today` and `high_temp_today_timestamp` matching today's `validTimeUtc[0]`.
  - Call `weather.get_forecasts` (`type: daily`) after 15:00 local time and confirm today's forecast (`forecast[0]["temperature"]`) still reports today's daytime high temperature from storage instead of `null`.
  - Restart Home Assistant after 15:00 local time and confirm the stored high temperature is loaded from disk and still appears in `forecast[0]["temperature"]`.
- [ ] **Daypart Index Shifting (`get_first_daypart_index`):**
  - Confirm `daily` forecast item `0` pulls condition, humidity, wind, and precipitation probability from tonight's daypart (`period = 1`) rather than returning `null`.
  - Confirm `twice_daily` forecast starts with tonight (`is_daytime: false`).
  - Confirm `day_icon_code`, `day_cloud_cover`, and `day_relative_humidity` on `sensor.<location>_forecast_details` use index `1` for their first element rather than `null`.

### 4.3 Unit Systems (Imperial vs. Metric)
- [ ] **US Customary / Imperial (`units=e`):** Verify native units match `°F`, `in` (precipitation & snowfall), `mph`, `inHg`, `ft` (cloud ceiling), and `mi` (visibility).
- [ ] **Metric (`units=m`):** Switch Home Assistant's unit system to **Metric** (**Settings → System → General**), reload the integration, and verify native units match `°C`, `mm` (precipitation), `cm` (snowfall), `km/h`, `mbar`, `m` (cloud ceiling), and `km` (visibility).

### 4.4 Calm Wind & Recorder Database Hygiene
- [ ] **Calm Wind (`windSpeed == 0` or `CALM`):** When wind speed is `0`, verify:
  - `weather.<location>` has `wind_bearing: null`.
  - `sensor.<location>_wind_direction_degrees` and `sensor.<location>_wind_direction_cardinal` report `unknown` rather than a stale bearing or `"CALM"`.
- [ ] **Unrecorded Forecast Details Attributes:** With `sensor.<location>_forecast_details` enabled and extra attributes selected, verify that state updates do not trigger Home Assistant Recorder warnings about state attributes exceeding 16 KB (as `_unrecorded_attributes` excludes all `EXTRA_ATTRIBUTE_KEYS_*` from Recorder history).

### 4.5 Resilience, Coordinate Fallback, & Storage Cleanup
- [ ] **Tracked Entity Coordinate Updates & Fallback:**
  - Update the coordinates of the tracked `zone` or `person` entity in **Developer Tools → States**, trigger `homeassistant.update_entity` on `weather.<location>`, and confirm `sensor.<location>_latitude` and `sensor.<location>_longitude` update to the new rounded coordinates.
  - Temporarily set the tracked entity's state without `latitude`/`longitude` attributes and trigger a refresh: confirm the coordinator logs a warning (`"Could not determine latitude/longitude from ...; using last known coordinates"`) and continues using `current_latitude`/`current_longitude` without failing.
- [ ] **Diagnostics Download & Redaction (`diagnostics.py`):**
  - On the Weather.com integration page, click the **three-dots menu → Download diagnostics**.
  - Open the downloaded JSON file and verify:
    - `entry_data` shows `"**REDACTED**"` for `api_key`, `latitude`, `longitude`, and `entity_id`.
    - `coordinator_data` and `stored_data` are present and any `lat`/`lon` fields are redacted.
- [ ] **Storage Cleanup on Entry Removal (`async_remove_entry`):**
  - Delete a test Weather.com integration entry from **Settings → Devices & Services**.
  - Check the `.storage/` directory on disk and confirm `.storage/weatherdotcom_data_<test_location>` has been deleted.
