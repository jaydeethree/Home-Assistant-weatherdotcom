# Home-Assistant-Weather.com
Home Assistant custom integration for Weather.com.
Includes a native Home Assistant Weather Entity and a variety of weather sensors.  

This is a fork of the excellent [wundergroundpws integration by @cytech](https://github.com/cytech/Home-Assistant-wundergroundpws) - if you
find this software useful, feel free to make a donation to them.

-------------------

# Installation Prerequisites
Please review the minimum requirements below to determine whether you will be able to
install and use the software.

- This integration requires Home Assistant Version 2023.9 or greater
- A Weather.com API Key is required (see below for how to get this)

# Weather.com API Key
1) Open https://www.wunderground.com (Wunderground is owned by Weather.com and uses some of the Weather.com APIs)
2) View the page source in your browser.
3) In the source, search for "apiKey" and copy/paste that into the integration

Important notes:
* It seems like Wunderground may provide different API keys depending on which country you are located in, and that the API keys for some countries may not be compatible with this integration. This integration has only been tested with the US API key which ends in `96f525` - if your API key isn't working, you may need to connect to a US VPN to retrieve the US API key.
* It also seems like Weather.com blocks traffic from certain countries. If this integration does not work for you, make sure that you can access Weather.com in your browser.
* Wunderground PWS (Personal Weather Station) API Keys will not work for this integration, as they do not have access to the Weather.com APIs that this integration uses.
* While there have been no reports of API keys being blocked or changing over time, it's always possible that Weather.com will eventually block them. If that happens you will need to find an API key from another source.

# Installation

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=jaydeethree&repository=Home-Assistant-weatherdotcom)

This integration is available in HACS, so just install it from there and then:

1. In Home Assistant Settings, select DEVICES & SERVICES, then ADD INTEGRATION.  
2. Select the "Weather.com" integration.  
3. Enter your Weather.com API key and submit.  

When choosing your location you have the option to use either a fixed latitude/longitude or to follow the location of a device, person, or zone.

# Sensors Created By This Integration
The following Weather.com data is available in the `weather.<LOCATION_NAME>` entity:

Current conditions:
- Condition (icon)
- Temperature
- Barometric pressure
- Wind speed
- Wind bearing (cardinal direction)
- Visibility

Forecast (daily and hourly):
- Date/time of forecast
- Temperature (high)
- Temperature (low)
- Condition (icon)
- Precipitation quantity
- Precipitation probability
- Wind speed
- Wind bearing (cardinal direction)

To access these values in automations, scripts, etc. you will need to create triggered template sensors for them. [This post](https://community.home-assistant.io/t/customising-the-bom-weather-and-lovelace-now-in-hacs/123549/1465) on the Home Assistant forums provides details about how to do that.

In addition to the Weather entity, these additional sensors will be created by this integration:

* `sensor.<LOCATION_NAME>_cloud_ceiling` - distance to the lowest cloud layer, or 0 if there are no clouds
* `sensor.<LOCATION_NAME>_cloud_cover_phrase` - a description of the current cloud cover, e.g. "Clear" or "Mostly Cloudy"
* `sensor.<LOCATION_NAME>_dewpoint` - the current dew point
* `sensor.<LOCATION_NAME>_heat_index` - the current heat index, which is what the current temperature "feels like" when combined with the current humidity
* `sensor.<LOCATION_NAME>_latitude` - the latitude that is configured for this location
* `sensor.<LOCATION_NAME>_local_observation_time` - the time that the Weather.com data was generated
* `sensor.<LOCATION_NAME>_longitude` - the longitude that is configured for this location
* `sensor.<LOCATION_NAME>_precipitation_last_hour` - the quantity of precipitation in the last hour
* `sensor.<LOCATION_NAME>_precipitation_last_6_hours` - the quantity of precipitation in the last 6 hours
* `sensor.<LOCATION_NAME>_precipitation_last_24_hours` - the quantity of precipitation in the last 24 hours
* `sensor.<LOCATION_NAME>_pressure` - the current barometric pressure
* `sensor.<LOCATION_NAME>_pressure_tendency_trend` - the current trend for barometric pressure, e.g. "Rising" or "Falling"
* `sensor.<LOCATION_NAME>_relative_humidity` - the current relative humidity
* `sensor.<LOCATION_NAME>_temperature` - the current temperature
* `sensor.<LOCATION_NAME>_temperature_feels_like` - what the current temperature "feels like" when combined with the current heat index and wind chill
* `sensor.<LOCATION_NAME>_uv_index` - the current UV index, ranging from 0 (very low) to 10 (very high)
* `sensor.<LOCATION_NAME>_weather_description` - the current weather description, e.g. "Freezing Rain" or "Scattered Showers"
* `sensor.<LOCATION_NAME>_wind_chill` - the current wind chill, which is what the current temperature "feels like" when combined with the current wind
* `sensor.<LOCATION_NAME>_wind_direction_cardinal` - the current cardinal wind direction - for example: North
* `sensor.<LOCATION_NAME>_wind_direction_degrees` - the current cardinal wind direction in degrees
* `sensor.<LOCATION_NAME>_wind_gust` - the current wind gust speed
* `sensor.<LOCATION_NAME>_wind_speed` - the current wind speed

All of the data listed above will be updated every 20 minutes.  

Additional details about the APIs used by this integration are available through these links:

* [Current weather](https://developer.weather.com/docs/openapi/currents-on-demand-3-0/get-wx-observations-current-by-geocode)
* [Forecast (Daily)](https://developer.weather.com/docs/openapi/daily-forecast-3-0-0/get-wx-forecast-daily-duration-by-geocode)
* [Forecast (Hourly)](https://developer.weather.com/docs/openapi/hourly-forecast-3-0/get-v3-wx-forecast-hourly-duration-by-geocode)

# Localization

Sensor "friendly names" are set via translation files.  
Weather.com translation files are located in the 'weatherdotcom/weather_translations' directory.
Files were translated, using 'en.json' as the base, via https://translate.i18next.com.  
Translations only use the base language code and not the variant (i.e. zh-CN/zh-HK/zh-TW uses zh).  
The default is en-US (translations/en.json) if the lang: option is not set in the Weather.com config.  
If lang: is set (i.e.  lang: de-DE), then the translations/de.json file is loaded, and the Weather.com API is queried with de-DE.    
The translation file applies to all sensor friendly names.    
Available lang: options are:  
```
'am-ET', 'ar-AE', 'az-AZ', 'bg-BG', 'bn-BD', 'bn-IN', 'bs-BA', 'ca-ES', 'cs-CZ', 'da-DK', 'de-DE', 'el-GR', 'en-GB',
'en-IN', 'en-US', 'es-AR', 'es-ES', 'es-LA', 'es-MX', 'es-UN', 'es-US', 'et-EE', 'fa-IR', 'fi-FI', 'fr-CA', 'fr-FR',
'gu-IN', 'he-IL', 'hi-IN', 'hr-HR', 'hu-HU', 'in-ID', 'is-IS', 'it-IT', 'iw-IL', 'ja-JP', 'jv-ID', 'ka-GE', 'kk-KZ',
'km-KH', 'kn-IN', 'ko-KR', 'lo-LA', 'lt-LT', 'lv-LV', 'mk-MK', 'mn-MN', 'mr-IN', 'ms-MY', 'my-MM', 'ne-IN', 'ne-NP',
'nl-NL', 'no-NO', 'om-ET', 'pa-IN', 'pa-PK', 'pl-PL', 'pt-BR', 'pt-PT', 'ro-RO', 'ru-RU', 'si-LK', 'sk-SK', 'sl-SI',
'sq-AL', 'sr-BA', 'sr-ME', 'sr-RS', 'sv-SE', 'sw-KE', 'ta-IN', 'ta-LK', 'te-IN', 'ti-ER', 'ti-ET', 'tg-TJ', 'th-TH',
'tk-TM', 'tl-PH', 'tr-TR', 'uk-UA', 'ur-PK', 'uz-UZ', 'vi-VN', 'zh-CN', 'zh-HK', 'zh-TW'
```
Weather Entity translations are handled by Home Assistant and configured under the User -> Language setting.

# Advanced Configuration

The integration exposes all daily and daypart forecast data as attributes of a disabled-by-default sensor, "Forecast Details". The benefits of this are:

1. Gives access to non-conforming data available from the weather.com API, but not available in the `<weather.get_forecasts>` method
2. Limits the need to manually configure sensors/attributes to gain access to data

> [!TIP]
> Home Assistant’s guidance recommends limiting attribute data in frequently updated entities. It is advised to configure entity exclusion in your recorder configuration to limit database writes.
>
> ```yaml
> recorder:
>   exclude:
>     entities:
>       - sensor.[name]_forecast_details
> ```

## Attribute Options

<details>

<summary><b>Daily forecast options</b></summary>

<br>

Daily options are native API forecast values that return a 15 item array:
`day`, `daily_temp_max`, `daily_temp_min`, `daily_precip_qpf`, `daily_rain_qpf`, `daily_snow_qpf`, `daily_ice_qpf`, `daily_narrative` `sunrise`, `sunset`, `moon_phase`, `moon_phase_code`, `moon_phase_day`, `moonrise`, `moonset`.

</details>

<details>

<summary><b>Day forecast options</b></summary>

<br>

Day options are synthetic API forecast values that return a 15 item array. Data is derived from the day values in daypart array, when there is no value for the current day the night value is returned:
`day_icon_code`, `day_cloud_cover`, `day_relative_humidity`.

</details>

<details>

<summary><b>Daypart forecast options</b></summary>

<br>

Daypart options are native API forecast values that return a 30 item array; 1 item for day, 1 item for night:
`daypart_cloud_cover`, `daypart_name`, `daypart_icon_code`, `daypart_precip_chance`, `daypart_precip_type`, `daypart_total_qpf` `daypart_rain_qpf`, `daypart_snow_qpf`, `daypart_ice_qpf`, `daypart_snow_range`, `daypart_relative_humidity`, `daypart_heat_index`, `daypart_wind_chill`, `daypart_thunder_category`, `daypart_thunder_index`, `daypart_uv_description`, `daypart_uv_index`, `daypart_wind_dir`, `daypart_wind_dir_cardinal`, `daypart_wind_speed`, `daypart_wind_phrase`, `daypart_wx_phrase_long`, `daypart_wx_phrase_short`, `daypart_qualifier_phrase`, `daypart_narrative`.

</details>