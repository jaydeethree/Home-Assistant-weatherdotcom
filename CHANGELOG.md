v1.1.8
* Merge https://github.com/cytech/Home-Assistant-wundergroundpws/commit/36e33bf17e07fa342e1e66d9ab007382d5b1b9ea to fix "Detected blocking call" error

v1.1.7
* Change forecast API endpoints so that we have 15 days of forecast data (this applies to both hourly and daily forecasts)

v1.1.6
* Fix bug where cloud coverage data was incorrect for hourly forecasts
* Add more data to daily and hourly forecasts - see [this feature request](https://github.com/jaydeethree/Home-Assistant-weatherdotcom/issues/27) for details

v1.1.5
* Add the following properties to the weather.LOCATION_NAME entity: native_apparent_temperature, native_dew_point, native_wind_gust_speed, and uv_index

v1.1.4.1
* Fix "Error doing job: Task exception was never retrieved" error for latitude/longitude sensors

v1.1.4
* Add sensors for latitude/longitude - these make it easier to figure out which exact location is being used by a given set of weather sensors

v1.1.3
* Add one new sensor for current conditions - cloud cover phrase (see README for details of what this is)

v1.1.2
* Hopefully improve error handling so that if we fail to retrieve data from Weather.com, we'll just keep using the previous data
* Fix a unit of measurement issue that was causing errors to be logged and some long-term statistics problems

v1.1.1
* Add two new current conditions sensors - cloud ceiling and pressure tendency trend (see the README for details of what these sensors are measuring)

v1.1.0
* BREAKING CHANGE: Switch to [new Home Assistant weather entity format](https://developers.home-assistant.io/blog/2023/08/07/weather_entity_forecast_types/). This has been tested with Home Assistant 2023.9 and 2023.10, but probably will not work with older versions of Home Assistant. This also removes the weather.LOCATION_hourly sensor, as all forecast data has been combined into a single sensor.

v1.0.8.1
* Add Slovak translation. Thank you @misa1515!

v1.0.8
* Fix the integration not working when the Weather.com API returns a Content-Type other than `application/json`

v1.0.7
* Fix the integration not working with Home Assistant 2023.9

v1.0.6.1
* Add Portuguese translation. Thank you @ViPeR5000!

v1.0.6
* Add cloud cover information to forecasts

v1.0.5
* Switch from 5-day forecasts to 10-day forecasts

v1.0.4
* Fix hourly weather forecast for Home Assistant 2023.8. Thank you @klopyrev!

v1.0.3
* Fix humidity in weather.<LOCATION_NAME> entities - the field was named incorrectly so it wasn't working

v1.0.2
* Fix "has state class total_increasing, but its state is not strictly increasing" for precipitation sensors - they were using the wrong state class

v1.0.1
* Icons: Map 'haze' (Weather.com) to 'fog' (Home Assistant), and map 'blizzard' (Weather.com) to 'snowy' (Home Assistant)
* Add a new Weather Description sensor that contains a detailed description of the current weather conditions

v1.0.0
* No real changes, just minor adjustments to get this ready to add to the default HACS repo

v1.0.0-RC2
* Lots of refactoring/code clean-up - removed dead code, migrated strings to constants, renamed variables, and more
* Actually fixed wind gust sensor
* New sensors/data:
  * Added temperature "feels like" sensor
  * Added precipitation in last 6 hours sensor
  * Added visibility data to weather entities
* Current condition is now retrieved from the current data instead of the forecast data
* Removed reconfiguration flow - it was broken and seems unnecessary since it makes more sense to set up the integration again if the location needs to be changed
* Rewrote the README

v1.0.0-RC1
* Add hourly forecasts
* Lots of refactoring/code clean-up to support hourly forecasts

v1.0.0b3
* Simplify wind cardinal direction sensor
* Fix precipitation entries using wrong names and units
* Fix local observation time being incorrect

v1.0.0b2
* Properly handle windGust being null
* Fix JSON trailing commas that were causing log spam
* Various code clean-up (redundant README, remaining references to Wunderground PWS)
* Add hacs.json

v1.0.0b1
* Initial beta release - mostly functional, missing hourly forecast, may still be somewhat buggy