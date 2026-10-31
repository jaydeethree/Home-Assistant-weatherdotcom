"""
Support for Weather.com weather service.
For more details about this platform, please refer to the documentation at
https://github.com/jaydeethree/Home-Assistant-weatherdotcom
"""
from typing import Final

from homeassistant.components.weather import (
    ATTR_CONDITION_CLEAR_NIGHT,
    ATTR_CONDITION_CLOUDY,
    ATTR_CONDITION_EXCEPTIONAL,
    ATTR_CONDITION_FOG,
    ATTR_CONDITION_HAIL,
    ATTR_CONDITION_LIGHTNING,
    ATTR_CONDITION_LIGHTNING_RAINY,
    ATTR_CONDITION_PARTLYCLOUDY,
    ATTR_CONDITION_POURING,
    ATTR_CONDITION_RAINY,
    ATTR_CONDITION_SNOWY,
    ATTR_CONDITION_SNOWY_RAINY,
    ATTR_CONDITION_SUNNY,
    ATTR_CONDITION_WINDY,
    ATTR_CONDITION_WINDY_VARIANT
)

DOMAIN: Final = 'weatherdotcom'
ATTRIBUTION: Final = 'Data provided by the Weather.com weather service'
CONF_LANG: Final = 'lang'
CONF_LOCATION_SOURCE: Final = 'location_source'

LOCATION_TYPE_ENTITY: Final = 'entity'
LOCATION_TYPE_LATLONG: Final = 'latlong'

# Language Supported Codes
LANG_CODES: Final[list[str]] = [
    'am-ET', 'ar-AE', 'az-AZ', 'bg-BG', 'bn-BD', 'bn-IN', 'bs-BA', 'ca-ES', 'cs-CZ', 'da-DK', 'de-DE', 'el-GR', 'en-AU',
    'en-CA', 'en-GB', 'en-IN', 'en-US', 'es-AR', 'es-ES', 'es-LA', 'es-MX', 'es-UN', 'es-US', 'et-EE', 'fa-IR', 'fi-FI',
    'fr-CA', 'fr-FR', 'gu-IN', 'he-IL', 'hi-IN', 'hr-HR', 'hu-HU', 'id-ID', 'is-IS', 'it-IT', 'iw-IL', 'ja-JP', 'jv-ID',
    'ka-GE', 'kk-KZ', 'km-KH', 'kn-IN', 'ko-KR', 'lo-LA', 'lt-LT', 'lv-LV', 'mk-MK', 'mn-MN', 'mr-IN', 'ms-MY', 'my-MM',
    'ne-IN', 'ne-NP', 'nl-NL', 'no-NO', 'om-ET', 'pa-IN', 'pa-PK', 'pl-PL', 'pt-BR', 'pt-PT', 'ro-RO', 'ru-RU', 'si-LK',
    'sk-SK', 'sl-SI', 'sq-AL', 'sr-BA', 'sr-ME', 'sr-RS', 'sv-SE', 'sw-KE', 'ta-IN', 'ta-LK', 'te-IN', 'tg-TJ', 'th-TH',
    'ti-ER', 'ti-ET', 'tk-TM', 'tl-PH', 'tr-TR', 'uk-UA', 'ur-PK', 'uz-UZ', 'vi-VN', 'zh-CN', 'zh-HK', 'zh-TW'
]
# Only the TWC  5-day forecast API handles the translation of phrases for values of the following data.
# However, when formatting a request URL a valid language must be passed along.
# dayOfWeek,daypartName,moonPhase,qualifierPhrase,uvDescription,windDirectionCardinal,windPhrase,wxPhraseLong

ICON_CONDITION_MAP: Final[dict[str, list[int]]] = {
    ATTR_CONDITION_CLEAR_NIGHT: [31, 33],
    ATTR_CONDITION_CLOUDY: [26, 27, 28],
    ATTR_CONDITION_EXCEPTIONAL: [0, 1, 2, 19, 22, 36],  # 44 is Not Available (N/A)
    ATTR_CONDITION_FOG: [20, 21],
    ATTR_CONDITION_HAIL: [17],
    ATTR_CONDITION_LIGHTNING: [],
    ATTR_CONDITION_LIGHTNING_RAINY: [3, 4, 37, 38, 47],
    ATTR_CONDITION_PARTLYCLOUDY: [29, 30],
    ATTR_CONDITION_POURING: [40],
    ATTR_CONDITION_RAINY: [9, 11, 12, 39, 45],
    ATTR_CONDITION_SNOWY: [13, 14, 15, 16, 41, 42, 43, 46],
    ATTR_CONDITION_SNOWY_RAINY: [5, 6, 7, 8, 10, 18, 25, 35],
    ATTR_CONDITION_SUNNY: [32, 34],
    ATTR_CONDITION_WINDY: [23, 24],
    ATTR_CONDITION_WINDY_VARIANT: []
}
ICON_CODE_MAP: Final[dict[int, str]] = {
    code: condition
    for condition, codes in ICON_CONDITION_MAP.items()
    for code in codes
}

DEFAULT_LANG: Final = 'en-US'
API_URL_IMPERIAL: Final = "e"
API_URL_METRIC: Final = "m"

RESOURCE_CURRENT: Final = "https://api.weather.com/v3/wx/observations/current"
RESOURCE_FORECAST_DAILY: Final = "https://api.weather.com/v3/wx/forecast/daily/15day"
RESOURCE_FORECAST_HOURLY: Final = "https://api.weather.com/v3/wx/forecast/hourly/15day"

RESULTS_CURRENT: Final = 'current'
RESULTS_FORECAST_DAILY: Final = 'daily'
RESULTS_FORECAST_HOURLY: Final = 'hourly'

FIELD_CLOUD_CEILING: Final = 'cloudCeiling'
FIELD_CLOUD_COVER: Final = 'cloudCover'
FIELD_CLOUD_COVER_PHRASE: Final = 'cloudCoverPhrase'
FIELD_DAYPART: Final = 'daypart'
FIELD_DESCRIPTION: Final = 'wxPhraseLong'
FIELD_DEW_POINT: Final = 'temperatureDewPoint'
FIELD_FEELS_LIKE: Final = 'temperatureFeelsLike'
FIELD_HEAT_INDEX: Final = 'temperatureHeatIndex'
FIELD_HUMIDITY: Final = 'relativeHumidity'
FIELD_ICONCODE: Final = 'iconCode'
FIELD_PRECIPCHANCE: Final = 'precipChance'
FIELD_PRECIP_1HOUR: Final = 'precip1Hour'
FIELD_PRECIP_6HOUR: Final = 'precip6Hour'
FIELD_PRECIP_24HOUR: Final = 'precip24Hour'
FIELD_PRESSURE: Final = 'pressureAltimeter'
FIELD_PRESSURE_TENDENCY_TREND: Final = 'pressureTendencyTrend'
FIELD_QPF: Final = 'qpf'
FIELD_SNOW_1HOUR: Final = 'snow1Hour'
FIELD_SNOW_6HOUR: Final = 'snow6Hour'
FIELD_SNOW_24HOUR: Final = 'snow24Hour'
FIELD_TEMPERATUREMAX: Final = 'temperatureMax'
FIELD_TEMPERATUREMIN: Final = 'temperatureMin'
FIELD_TEMP: Final = 'temperature'
FIELD_UV_INDEX: Final = 'uvIndex'
FIELD_VALIDTIMELOCAL: Final = 'validTimeLocal'
FIELD_VALIDTIMEUTC: Final = 'validTimeUtc'
FIELD_VISIBILITY: Final = 'visibility'
FIELD_WINDDIRECTIONCARDINAL: Final = 'windDirectionCardinal'
FIELD_WINDDIR: Final = 'windDirection'
FIELD_WINDGUST: Final = 'windGust'
FIELD_WINDSPEED: Final = 'windSpeed'
FIELD_WIND_CHILL: Final = 'temperatureWindChill'

HIGH_TEMP_TODAY_STORAGE: Final = 'high_temp_today'
HIGH_TEMP_TODAY_TIMESTAMP_STORAGE: Final = 'high_temp_today_timestamp'

CONF_EXTRA_ATTRIBUTES: Final = "extra_attributes"
EXTRA_ATTRIBUTE_KEYS_DAILY: Final[list[str]] = [
    "day",
    "daily_temp_max",
    "daily_temp_min",
    "daily_precip_qpf",
    "daily_rain_qpf",
    "daily_snow_qpf",
    "daily_ice_qpf",
    "daily_narrative",
    "sunrise",
    "sunset",
    "moon_phase",
    "moon_phase_code",
    "moon_phase_day",
    "moonrise",
    "moonset",
]
EXTRA_ATTRIBUTE_KEYS_DAY: Final[list[str]] = [
    "day_icon_code",
    "day_cloud_cover",
    "day_relative_humidity",
]
EXTRA_ATTRIBUTE_KEYS_DAYPART: Final[list[str]] = [
    "daypart_cloud_cover",
    "daypart_name",
    "daypart_icon_code",
    "daypart_precip_chance",
    "daypart_precip_type",
    "daypart_total_qpf",
    "daypart_rain_qpf",
    "daypart_snow_qpf",
    "daypart_ice_qpf",
    "daypart_snow_range",
    "daypart_relative_humidity",
    "daypart_heat_index",
    "daypart_wind_chill",
    "daypart_thunder_category",
    "daypart_thunder_index",
    "daypart_uv_description",
    "daypart_uv_index",
    "daypart_wind_dir",
    "daypart_wind_dir_cardinal",
    "daypart_wind_speed",
    "daypart_wind_phrase",
    "daypart_wx_phrase_long",
    "daypart_wx_phrase_short",
    "daypart_qualifier_phrase",
    "daypart_narrative",
]

HEADERS: Final[dict[str, str]] = {
    "Accept-Encoding": "gzip",
    "user-agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/155.0.0.0 Safari/537.36"
    ),
}