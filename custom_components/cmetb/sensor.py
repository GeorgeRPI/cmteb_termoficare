"""Sensor platform for CMTEB integration."""
import logging
from homeassistant.components.sensor import SensorEntity
from .const import DOMAIN, CONF_SECTOR, CONF_NUME_PUNCT

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the sensor platform."""
    data = config_entry.data
    sensor = CmtebSensor(data)
    async_add_entities([sensor])

class CmtebSensor(SensorEntity):
    """Representation of a CMTEB Sensor."""

    def __init__(self, config):
        """Initialize the sensor."""
        self._config = config
        self._state = None
        self._attributes = {}

    @property
    def name(self):
        """Return the name of the sensor."""
        return f"Termoficare {self._config[CONF_SECTOR]} - {self._config[CONF_NUME_PUNCT]}"

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state if self._state else "Necunoscut"

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return self._attributes

    def update(self):
        """Fetch new state data for the sensor."""
        # Date de test pentru moment
        self._state = "Functionare normala"
        self._attributes = {
            "sector": self._config[CONF_SECTOR],
            "nume_punct": self._config[CONF_NUME_PUNCT],
            "afectat": "Nimic",
            "culoare": "verde"
        }
