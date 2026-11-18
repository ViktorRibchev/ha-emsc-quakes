"""UI setup and options for EMSC Earthquakes."""
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, OptionsFlowWithReload
from homeassistant.const import CONF_LATITUDE, CONF_LOCATION, CONF_LONGITUDE, CONF_RADIUS
from homeassistant.helpers.selector import (
    LocationSelector,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
)

from .const import CONF_DAYS, DEFAULT_DAYS, DEFAULT_RADIUS, DOMAIN


def _schema(lat, lon, radius, days):
    return vol.Schema(
        {
            vol.Required(CONF_LOCATION, default={CONF_LATITUDE: lat, CONF_LONGITUDE: lon}): LocationSelector(),
            vol.Required(CONF_RADIUS, default=radius): NumberSelector(
                NumberSelectorConfig(min=10, max=2000, step=10, unit_of_measurement="km", mode=NumberSelectorMode.BOX)
            ),
            vol.Required(CONF_DAYS, default=days): NumberSelector(
                NumberSelectorConfig(min=1, max=365, unit_of_measurement="days", mode=NumberSelectorMode.BOX)
            ),
        }
    )


def _options(user_input):
    loc = user_input[CONF_LOCATION]
    return {
        CONF_LATITUDE: loc[CONF_LATITUDE],
        CONF_LONGITUDE: loc[CONF_LONGITUDE],
        CONF_RADIUS: user_input[CONF_RADIUS],
        CONF_DAYS: int(user_input[CONF_DAYS]),
    }


class EmscConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="EMSC Earthquakes", data={}, options=_options(user_input))
        return self.async_show_form(
            step_id="user",
            data_schema=_schema(self.hass.config.latitude, self.hass.config.longitude, DEFAULT_RADIUS, DEFAULT_DAYS),
        )

    @staticmethod
    def async_get_options_flow(config_entry):
        return EmscOptionsFlow()


class EmscOptionsFlow(OptionsFlowWithReload):
    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(data=_options(user_input))
        o = self.config_entry.options
        return self.async_show_form(
            step_id="init",
            data_schema=_schema(o[CONF_LATITUDE], o[CONF_LONGITUDE], o[CONF_RADIUS], o[CONF_DAYS]),
        )
