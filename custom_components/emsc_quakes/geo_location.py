"""EMSC (seismicportal.eu) earthquakes as geo_location entities, plus an `emsc_quake` event per new quake."""
from datetime import datetime, timedelta, timezone
import logging

import voluptuous as vol

from homeassistant.components.geo_location import PLATFORM_SCHEMA as BASE_SCHEMA, GeolocationEvent
from homeassistant.const import CONF_LATITUDE, CONF_LONGITUDE, CONF_RADIUS, UnitOfLength
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.util.location import distance

_LOGGER = logging.getLogger(__name__)
DOMAIN = "emsc_quakes"
URL = "https://www.seismicportal.eu/fdsnws/event/1/query"
CONF_DAYS = "days"
KM_PER_DEGREE = 111.195

PLATFORM_SCHEMA = BASE_SCHEMA.extend(
    {
        vol.Optional(CONF_LATITUDE): cv.latitude,
        vol.Optional(CONF_LONGITUDE): cv.longitude,
        vol.Optional(CONF_RADIUS, default=250): vol.Coerce(float),  # km; 250 km radius = 500 km circle
        vol.Optional(CONF_DAYS, default=30): cv.positive_int,  # history kept on the map
    }
)


def query_params(lat, lon, radius_km, days, now):
    return {
        "format": "json",
        "lat": lat,
        "lon": lon,
        "maxradius": round(radius_km / KM_PER_DEGREE, 4),  # FDSN wants degrees
        "starttime": (now - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%S"),
        "limit": 1000,
    }


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    home = (config.get(CONF_LATITUDE, hass.config.latitude), config.get(CONF_LONGITUDE, hass.config.longitude))
    session = async_get_clientsession(hass)
    entities: dict[str, Quake] = {}
    first_run = True

    async def update(_now=None):
        nonlocal first_run
        params = query_params(*home, config[CONF_RADIUS], config[CONF_DAYS], datetime.now(timezone.utc))
        try:
            async with session.get(URL, params=params, timeout=30) as resp:
                if resp.status == 204:  # FDSN: no events in window
                    features = []
                else:
                    resp.raise_for_status()
                    features = (await resp.json(content_type=None))["features"]
        except Exception as err:  # keep last known quakes on network/API errors
            _LOGGER.warning("EMSC fetch failed: %s", err)
            return

        seen = set()
        new = []
        for feature in features:
            fid = feature["id"]
            seen.add(fid)
            if fid in entities:
                entities[fid].set_feature(feature, home)
                entities[fid].async_write_ha_state()
            else:
                entities[fid] = Quake(feature, home)
                new.append(entities[fid])
        if new:
            async_add_entities(new)
        for fid in set(entities) - seen:
            await entities.pop(fid).async_remove()
        # first fetch after start loads history silently; alert only on quakes seen later
        if not first_run:
            for quake in new:
                hass.bus.async_fire(f"{DOMAIN}_new", quake.event_data())
        first_run = False

    await update()
    async_track_time_interval(hass, update, timedelta(minutes=2))


class Quake(GeolocationEvent):
    _attr_should_poll = False
    _attr_icon = "mdi:pulse"
    _attr_source = DOMAIN
    _attr_unit_of_measurement = UnitOfLength.KILOMETERS

    def __init__(self, feature, home):
        self.set_feature(feature, home)

    def set_feature(self, feature, home):
        p = feature["properties"]
        self._p = p
        self._attr_name = f"M{p['mag']} {p['flynn_region'].title()}"
        self._attr_latitude = p["lat"]
        self._attr_longitude = p["lon"]
        self._attr_distance = round(distance(*home, p["lat"], p["lon"]) / 1000, 1)
        self._attr_extra_state_attributes = {
            "magnitude": p["mag"],
            "magnitude_type": p.get("magtype"),
            "depth_km": p.get("depth"),
            "region": p["flynn_region"],
            "time": p["time"],
            "external_id": feature["id"],
            "url": f"https://www.seismicportal.eu/eventdetails.html?unid={feature['id']}",
        }

    def event_data(self):
        return {
            **self._attr_extra_state_attributes,
            "name": self._attr_name,
            "latitude": self._attr_latitude,
            "longitude": self._attr_longitude,
            "distance_km": self._attr_distance,
        }
