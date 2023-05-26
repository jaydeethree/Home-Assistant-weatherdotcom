# Home-Assistant-Weather.com

Home Assistant custom integration for Weather.com.
Includes a native Home Assistant Weather Entity and a variety of weather sensors.  

:+1: If you find this software useful, feel free to make a donation to the original author (@cytech): [Paypal.me Donation Link](https://paypal.me/cytecheng)  

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
4. After the integration setup is complete, you can select "Configure" to change:  

* Create Forecast Sensors, language, and override latitude and longitude for forecast.  
* Observation and condition sensors will be created and enabled.  
* Forecast sensors are not created by default. They will be created if you enable "Create Forecast Sensors" in the integration "Configure".  
* Forecast sensors will then be created but are disabled. To enable, goto the integration - entities and select the sensors you would like and enable them.

[Back to top](#top)

# Available Sensors
```yaml
# description: Conditions to display in the frontend. The following conditions can be monitored.
#
# Observations (current)
 validTimeLocal:
   unique_id: <location_name>,obstimelocal
   entity_id: sensor.<location_name>_local_observation_time   
   description: Text summary of local observation time
 relativeHumidity:
   unique_id: <location_name>,humidity
   entity_id: sensor.<location_name>_relative_humidity   
   description: Relative humidity    
 uvIndex:
   unique_id: <location_name>,uv
   entity_id: sensor.<location_name>_uv_index   
   description: Current levels of UV radiation.
 windDirection:
   unique_id: <location_name>,winddir
   entity_id: sensor.<location_name>_wind_direction_degrees   
   description: Wind degrees
 windDirectionCardinal:
   unique_id: <location_name>,winddirectioncardinal
   entity_id: sensor.<location_name>_wind_direction_cardinal   
   description: Wind cardinal direction (N, NE, NNE, S, E, W, etc)
# conditions (current)       
 temperatureDewPoint:
   unique_id: <location_name>,dewpt
   entity_id: sensor.<location_name>_dewpoint
   description: Temperature below which water droplets begin to condense and dew can form
 temperatureHeatIndex:
   unique_id: <location_name>,heatindex
   entity_id: sensor.<location_name>_heat_index   
   description: Heat index (combined effects of the temperature and humidity of the air)
 precip1Hour:
   unique_id: <location_name>,preciprate
   entity_id: sensor.<location_name>_precipitation_rate   
   description: Rain intensity
 precip24Hour:
   unique_id: <location_name>,preciptotal
   entity_id: sensor.<location_name>_precipitation_today   
   description: Today Total precipitation
 pressureAltimeter:
   unique_id: <location_name>,pressure
   entity_id: sensor.<location_name>_pressure   
   description: Atmospheric air pressure
 temperature:
   unique_id: <location_name>,temp
   entity_id: sensor.<location_name>_temperature   
   description: Current temperature
 temperatureWindChill:
   unique_id: <location_name>,windchill
   entity_id: sensor.<location_name>_wind_chill   
   description: Wind Chill (combined effects of the temperature and wind)      
 windGust:
   unique_id: <location_name>,windgust
   entity_id: sensor.<location_name>_wind_gust   
   description: Wind gusts speed
 windSpeed:
   unique_id: <location_name>,windspeed
   entity_id: sensor.<location_name>_wind_speed   
   description: Current wind speed      
#   Forecast
 narrative:
   unique_id: <location_name>,narrative_<day>f
   entity_id: sensor.<location_name>_weather_summary_<day>
   description: A human-readable weather forecast for Day. (<day> Variations 0, 1, 2, 3, 4)
 qpfSnow:
   unique_id: <location_name>,qpfsnow_<day>f
   entity_id: sensor.<location_name>_snow_amount_<day>
   description: Forecasted snow intensity. (<day> Variations 0, 1, 2, 3, 4)
#   Forecast daypart
 narrative:
   unique_id: <location_name>,narrative_<daypart>fdp
   entity_id: sensor.<location_name>_forecast_summary_<suffix>
   description: A human-readable weather forecast for Day. (suffix Variations 0d, 1n, 2d, 3n, 4d, 5n, 6d, 7n, 8d, 9n)
 qpf:
   unique_id: <location_name>,qpf_<daypart>fdp
   entity_id: sensor.<location_name>_precipitation_amount_<suffix>
   description: Forecasted precipitation intensity. (suffix Variations 0d, 1n, 2d, 3n, 4d, 5n, 6d, 7n, 8d, 9n)
 precipChance:
   unique_id: <location_name>,precipchance_<daypart>fdp
   entity_id: sensor.<location_name>_precipitation_probability_<suffix>
   description: Forecasted precipitation probability in %. (suffix Variations 0d, 1n, 2d, 3n, 4d, 5n, 6d, 7n, 8d, 9n)      
 temperature:
   unique_id: <location_name>,temperature<daypart>fdp
   entity_id: sensor.<location_name>_forecast_temperature_<suffix>
   description: Forecasted temperature. (suffix Variations 0d, 1n, 2d, 3n, 4d, 5n, 6d, 7n, 8d, 9n)
 windSpeed:
   unique_id: <location_name>,windspeed_<daypart>fdp
   entity_id: sensor.<location_name>_average_wind_<suffix>
   description: Forecasted wind speed. (suffix Variations 0d, 1n, 2d, 3n, 4d, 5n, 6d, 7n, 8d, 9n)
```

All the conditions listed above will be updated every 5 minutes.  

**_Weather.com API caveat:   
The daypart object as well as the temperatureMax field OUTSIDE of the daypart object will appear as null in the API after 3:00pm Local Apparent Time.  
The affected sensors will return as "Today Expired" with a value of "—" when this condition is met._**


Variations above marked with "#d" are daily forecasts.
Variations above marked with "#n" are nightly forecasts.


Note: While the platform is called weatherdotcom the sensors will show up in Home Assistant as  
```sensor.<location_name>_forecast_temperature_<suffix>```  
(eg: sensor.sanfrancisco_forecast_temperature_0d).

Additional details about the API are available [here](https://docs.google.com/document/d/14OK6NG5GRwezb6-5C1vQJoRdStrGnXUiXBDCmQP9T9s/edit).  
[Back to top](#top)

# Weather Entity
Weather.com data returned to weather entity (HASS weather forecast card):  
Current:
- temperature
- pressure
- humidity
- wind_speed
- wind_bearing

Forecast:
- datetime
- temperature (max)
- temperature (low)
- condition (icon)
- precipitation
- precipitation_probability
- wind_bearing
- wind_speed

templates can be created to access these values such as:
```
{% for state in states.weather -%}
  {%- if loop.first %}The {% elif loop.last %} and the {% else %}, the {% endif -%}
  {{ state.name | lower }} is {{state.state_with_unit}}
{%- endfor %}.

Wind is {{ states.weather.<STATIONID>.attributes.forecast[0].wind_bearing }} at {{ states.weather.<STATIONID>.attributes.forecast[0].wind_speed }} {{ states.weather.<STATIONID>.attributes.wind_speed_unit }}

```
[Back to top](#top)

# Sensors available in statistics
The following are Weather.com sensors exposed to the statistics card in Lovelace.  
Note that only sensors of like units can be combined in a single card.  

* **class NONE**
* sensor.sanfrancisco_uv_index
* 
* **class DEGREE**
* sensor.sensor.sanfrancisco_wind_direction_degrees

* 
* **class RATE & SPEED**
* sensor.sanfrancisco_precipitation_rate
* sensor.sanfrancisco_wind_gust
* sensor.sanfrancisco_wind_speed
* 
* **class LENGTH**
* sensor.sanfrancisco_precipitation_today
* 
* **class PRESSURE**
* sensor.sanfrancisco_pressure
* 
* **class HUMIDITY**
* sensor.sanfrancisco_relative_humidity
* 
* **class TEMPERATURE**
* sensor.sanfrancisco_dewpoint
* sensor.sanfrancisco_heat_index
* sensor.sanfrancisco_wind_chill
* sensor.sanfrancisco_temperature

[Back to top](#top)


# Localization

Sensor "friendly names" are set via translation files.  
Weather.com translation files are located in the 'weatherdotcom/weather_translations' directory.
Files were translated, using 'en.json' as the base, via https://translate.i18next.com.  
Translations only use the base language code and not the variant (i.e. zh-CN/zh-HK/zh-TW uses zh).  
The default is en-US (translations/en.json) if the lang: option is not set in the weather.com config.  
If lang: is set (i.e.  lang: de-DE), then the translations/de.json file is loaded, and the Weather.com API is queried with de-DE.    
The translation file applies to all sensor friendly names.   
Forecast-narrative, forecast-dayOfWeek, forecast-daypart-narrative and forecast-daypart-daypartName are translated by the api. 
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
Weather Entity (hass weather card) translations are handled by Home Assistant and configured under the user -> language setting.  
[Back to top](#top)