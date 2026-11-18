# EMSC Earthquakes for Home Assistant

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/docs/faq/custom_repositories/)
[![Validate](https://github.com/ViktorRibchev/ha-emsc-quakes/actions/workflows/validate.yml/badge.svg)](https://github.com/ViktorRibchev/ha-emsc-quakes/actions/workflows/validate.yml)

Earthquakes from the [EMSC](https://www.seismicportal.eu/) (European-Mediterranean Seismological Centre) catalogue,
shown on a Home Assistant map with history and an event for every new quake. EMSC covers small quakes in
Bulgaria, Romania and the rest of Europe far better than USGS.

- Polls EMSC every 2 minutes for quakes within a radius of your home (default 250 km = 500 km circle).
- Each quake is a `geo_location` entity, e.g. `M3.5 Bulgaria`, with magnitude, depth, time, distance and an EMSC link.
- Quakes from the last `days` (default 30) stay on the map.
- Fires an `emsc_quakes_new` event for every new quake, for alerts.

## Installation

### HACS

1. HACS → ⋮ → **Custom repositories** → add `https://github.com/ViktorRibchev/ha-emsc-quakes`, category **Integration**.
2. Install **EMSC Earthquakes** and restart Home Assistant.

### Manual

Copy `custom_components/emsc_quakes` into your `config/custom_components/` folder and restart Home Assistant.

## Configuration

[![Add integration](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=emsc_quakes)

**Settings → Devices & services → Add integration → EMSC Earthquakes**, then pick:

| Option | Default | Description |
| --- | --- | --- |
| Centre | home location | Centre of the search circle (pick on the map) |
| Radius | `250` km | 250 km radius = 500 km circle |
| History | `30` days | How far back quakes stay on the map |

Change them later with **Configure** on the integration. Add the integration more than once to watch several areas.

<details>
<summary>YAML (legacy, still supported)</summary>

```yaml
# configuration.yaml
geo_location:
  - platform: emsc_quakes
    radius: 250 # km, optional
    days: 30 # optional
    # latitude: 44.5   # optional, defaults to your home location
    # longitude: 25.5
```

</details>

## Alerts

```yaml
automation:
  - alias: Earthquake alert
    triggers:
      - trigger: event
        event_type: emsc_quakes_new
    actions:
      # use notify.mobile_app_<your_phone> for a push notification
      - action: persistent_notification.create
        data:
          title: "Earthquake {{ trigger.event.data.name }}"
          message: >-
            M{{ trigger.event.data.magnitude }} {{ trigger.event.data.region }},
            depth {{ trigger.event.data.depth_km }} km,
            {{ trigger.event.data.distance_km }} km away at {{ trigger.event.data.time }}.
            {{ trigger.event.data.url }}
```

Event data: `name`, `magnitude`, `magnitude_type`, `depth_km`, `region`, `time`, `latitude`, `longitude`,
`distance_km`, `external_id`, `url`.

Quakes already in the window at startup load silently; quakes that happen while Home Assistant is off are not alerted.

## Map card

```yaml
type: map
title: Earthquakes
geo_location_sources:
  - emsc_quakes
default_zoom: 6
```

## Data

Data © [EMSC](https://www.emsc-csem.org/), via the FDSN event web service at seismicportal.eu.
