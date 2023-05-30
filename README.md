# Home-Assistant-Weather.com
Home Assistant custom integration for Weather.com.
Includes a native Home Assistant Weather Entity and a variety of weather sensors.  

This is a fork of the excellent [wundergroundpws integration by @cytech](https://github.com/cytech/Home-Assistant-wundergroundpws) - if you
find this software useful, feel free to make a donation to them.

-------------------

# Installation Prerequisites
Please review the minimum requirements below to determine whether you will be able to
install and use the software.

- This integration requires Home Assistant Version 2023.1 or greater
- A Weather.com API Key is required (see below for how to get this)

[Back to top](#top) 

# Weather.com API Key
1) Open https://www.wunderground.com (Wunderground is owned by Weather.com and uses some of the Weather.com APIs)
2) View the page source in your browser.
3) In the source, search for "apiKey" and copy/paste that into the integration

Important notes:
* Wunderground PWS API Keys will not work for this integration, as they do not have access to the Weather.com APIs that this integration uses.
* It is unclear how long these API keys from the wunderground.com HTML source are valid for - you may need to change the API key regularly.

[Back to top](#top)

# Installation

Add this repository as a custom repository in HACS and install from there. Then:

1. In Home Assistant Settings, select DEVICES & SERVICES, then ADD INTEGRATION.  
2. Select the "Weather.com" integration.  
3. Enter your Weather.com API key and submit.  

[Back to top](#top)

# Sensors Created By This Integration
The following Weather.com data is available in the `weather.<LOCATION_NAME>` entity:

Current conditions:
- Condition (icon)
- Temperature
- Barometric pressure
- Wind speed
- Wind bearing (cardinal direction)
- Visibility

Forecast (daily):
- Date/time of forecast
- Temperature (high)
- Temperature (low)
- Condition (icon)
- Precipitation quantity
- Precipitation probability
- Wind speed
- Wind bearing (cardinal direction)

Additionally, a `weather.<LOCATION_NAME>_hourly` entity will be created that contains hourly forecast data.

Templates can be created to access these values such as:
```
{% for state in states.weather -%}
  {%- if loop.first %}The {% elif loop.last %} and the {% else %}, the {% endif -%}
  {{ state.name | lower }} is {{state.state_with_unit}}
{%- endfor %}.

Wind is {{ states.weather.<LOCATION_NAME>.attributes.forecast[0].wind_bearing }} at {{ states.weather.<LOCATION_NAME>.attributes.forecast[0].wind_speed }} {{ states.weather.<LOCATION_NAME>.attributes.wind_speed_unit }}

```

In addition to the Weather entity, these additional sensors will be created by this integration:

* `sensor.<LOCATION_NAME>_dewpoint` - the current dew point
* `sensor.<LOCATION_NAME>_heat_index` - the current heat index, which is what the current temperature "feels like" when combined with the current humidity
* `sensor.<LOCATION_NAME>_local_observation_time` - the time that the Weather.com data was generated
* `sensor.<LOCATION_NAME>_precipitation_last_hour` - the quantity of precipitation in the last hour
* `sensor.<LOCATION_NAME>_precipitation_last_6_hours` - the quantity of precipitation in the last 6 hours
* `sensor.<LOCATION_NAME>_precipitation_last_24_hours` - the quantity of precipitation in the last 24 hours
* `sensor.<LOCATION_NAME>_pressure` - the current barometric pressure
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

Additional details about the API are available [here](https://docs.google.com/document/d/14OK6NG5GRwezb6-5C1vQJoRdStrGnXUiXBDCmQP9T9s/edit).  

[Back to top](#top)

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

[Back to top](#top)