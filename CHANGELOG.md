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