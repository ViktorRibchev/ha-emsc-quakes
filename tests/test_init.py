from datetime import timedelta
from unittest.mock import patch

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_capture_events,
    async_fire_time_changed,
)

from custom_components.emsc_quakes.const import DOMAIN
from custom_components.emsc_quakes.geo_location import URL

OPTIONS = {"latitude": 42.7, "longitude": 23.3, "radius": 250, "days": 30}


def feature(fid, mag, region, lat=42.5, lon=23.1):
    return {
        "type": "Feature",
        "id": fid,
        "geometry": {"type": "Point", "coordinates": [lon, lat, -10.0]},
        "properties": {
            "mag": mag,
            "magtype": "ml",
            "flynn_region": region,
            "lat": lat,
            "lon": lon,
            "depth": 10.0,
            "time": "2026-11-18T00:48:56.38Z",
        },
    }


async def test_user_flow(hass):
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert result["type"] is FlowResultType.FORM

    with patch("custom_components.emsc_quakes.async_setup_entry", return_value=True):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"location": {"latitude": 42.7, "longitude": 23.3}, "radius": 300, "days": 7},
        )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["options"] == {"latitude": 42.7, "longitude": 23.3, "radius": 300, "days": 7}


async def test_entities_events_and_options(hass, aioclient_mock):
    aioclient_mock.get(URL, json={"features": [feature("a", 3.5, "BULGARIA")]})
    entry = MockConfigEntry(domain=DOMAIN, options=OPTIONS)
    entry.add_to_hass(hass)
    events = async_capture_events(hass, f"{DOMAIN}_new")

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    state = hass.states.get("geo_location.m3_5_bulgaria")
    assert state.attributes["magnitude"] == 3.5
    assert state.attributes["source"] == DOMAIN
    assert events == []  # history loaded at startup does not alert

    aioclient_mock.clear_requests()
    aioclient_mock.get(
        URL, json={"features": [feature("b", 4.1, "ROMANIA", 45.7, 26.5), feature("a", 3.5, "BULGARIA")]}
    )
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(minutes=3))
    await hass.async_block_till_done()
    assert [e.data["external_id"] for e in events] == ["b"]
    assert hass.states.get("geo_location.m4_1_romania")

    aioclient_mock.clear_requests()
    aioclient_mock.get(URL, status=204)  # quakes aged out of the window
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(minutes=6))
    await hass.async_block_till_done()
    assert hass.states.get("geo_location.m3_5_bulgaria") is None

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"location": {"latitude": 44.5, "longitude": 25.5}, "radius": 100, "days": 1}
    )
    await hass.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options == {"latitude": 44.5, "longitude": 25.5, "radius": 100, "days": 1}
    assert "maxradius=0.8993" in str(aioclient_mock.mock_calls[-1][1])  # reloaded with 100 km

    assert await hass.config_entries.async_unload(entry.entry_id)
