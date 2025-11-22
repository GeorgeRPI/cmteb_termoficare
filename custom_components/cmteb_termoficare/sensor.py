"""Sensor platform for CMTEB Termoficare."""
import logging
from datetime import timedelta
import requests
from bs4 import BeautifulSoup

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, URL_CMTEB

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(minutes=15)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the CMTEB sensors from a config entry."""
    address = config_entry.data.get("adresa")
    punct_termic = config_entry.data.get("punct_termic", "")

    sensors = [
        CmtebSensor(config_entry, "agent_afectat", "Agent Termic Afectat"),
        CmtebSensor(config_entry, "cauza_interventie", "Cauză Intervenție"),
        CmtebSensor(config_entry, "data_estimata_reparatie", "Dată Estimată Reparație")
    ]
    async_add_entities(sensors, update_before_add=True)

class CmtebSensor(SensorEntity):
    """Representation of a CMTEB Sensor."""

    def __init__(self, config_entry, sensor_type, friendly_name):
        """Initialize the sensor."""
        self._config_entry = config_entry
        self._type = sensor_type
        self._friendly_name = friendly_name
        self._state = None
        self._attrs = {}
        self._address = config_entry.data.get("adresa")
        self._punct_termic = config_entry.data.get("punct_termic", "")

    @property
    def name(self):
        """Return the name of the sensor."""
        return f"cmteb_{self._type}"

    @property
    def friendly_name(self):
        """Return the friendly name of the sensor."""
        return f"CMTEB {self._friendly_name}"

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return self._attrs

    @property
    def unique_id(self):
        """Return a unique ID."""
        return f"{self._config_entry.entry_id}_{self._type}"

    def _fetch_data(self):
        """Fetch data from CMTEB website."""
        try:
            response = requests.get(URL_CMTEB, timeout=10)
            response.raise_for_status()
            
            # Use built-in HTML parser instead of lxml
            soup = BeautifulSoup(response.content, 'html.parser')
            tables = soup.find_all('table')

            for table in tables:
                rows = table.find_all('tr')[1:]  # Skip header row
                
                for row in rows:
                    cols = [ele.text.strip() for ele in row.find_all('td')]
                    
                    if len(cols) >= 5:
                        # Check if either address or punct_termic matches
                        location_text = cols[1] if len(cols) > 1 else ""
                        address_match = self._address and self._address.lower() in location_text.lower()
                        punct_match = self._punct_termic and self._punct_termic.lower() in location_text.lower()
                        
                        if address_match or punct_match or (self._address and self._address in location_text):
                            # Found matching location
                            agent_afectat = cols[2] if len(cols) > 2 else "N/A"
                            cauza = cols[3] if len(cols) > 3 else "N/A"
                            data_estimata = cols[4] if len(cols) > 4 else "N/A"

                            if self._type == "agent_afectat":
                                self._state = agent_afectat
                            elif self._type == "cauza_interventie":
                                self._state = cauza
                            elif self._type == "data_estimata_reparatie":
                                self._state = data_estimata
                            
                            self._attrs = {
                                "Adresa": self._address,
                                "Punct Termic": self._punct_termic,
                                "Locatie Gasita": location_text
                            }
                            _LOGGER.info(f"Date gasite pentru {self._address}: {self._state}")
                            return True
            
            # No matching location found
            _LOGGER.info(f"Nu s-au gasit intreruperi pentru: {self._address}")
            self._state = "Nu există întreruperi"
            self._attrs = {
                "Adresa": self._address,
                "Punct Termic": self._punct_termic
            }
            return False

        except Exception as e:
            _LOGGER.error(f"Eroare la extragerea datelor de la CMTEB: {str(e)}")
            self._state = "Eroare de conectare"
            self._attrs = {"Eroare": str(e)}
            return False

    async def async_update(self):
        """Update the sensor."""
        await self.hass.async_add_executor_job(self._fetch_data)
