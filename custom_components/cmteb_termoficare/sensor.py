"""Sensor platform for CMTEB Termoficare."""
import logging
from datetime import timedelta
import requests
from bs4 import BeautifulSoup
import time

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, URL_CMTEB

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(minutes=30)  # Mărit intervalul pentru a nu suprasolicita

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
        self._available = True

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
    def available(self):
        """Return if the sensor is available."""
        return self._available

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return self._attrs

    @property
    def unique_id(self):
        """Return a unique ID."""
        return f"{self._config_entry.entry_id}_{self._type}"

    def _get_headers(self):
        """Return headers to mimic a real browser."""
        return {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ro-RO,ro;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }

    def _fetch_data(self):
        """Fetch data from CMTEB website."""
        try:
            headers = self._get_headers()
            
            # Adaugă timeout și retry logic
            response = requests.get(
                URL_CMTEB, 
                headers=headers, 
                timeout=15,
                verify=True  # Verifică certificatul SSL
            )
            response.raise_for_status()
            
            # Verifică dacă primim conținut HTML valid
            if not response.content:
                raise Exception("Răspuns gol de la server")
                
            # Use built-in HTML parser
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Verifică dacă pagina conține datele așteptate
            if not soup.find_all('table'):
                raise Exception("Nu s-au găsit tabele pe pagină")
                
            tables = soup.find_all('table')

            data_gasita = False
            for table in tables:
                rows = table.find_all('tr')[1:]  # Skip header row
                
                for row in rows:
                    cols = [ele.text.strip() for ele in row.find_all('td')]
                    
                    if len(cols) >= 5:
                        # Check if either address or punct_termic matches
                        location_text = cols[1] if len(cols) > 1 else ""
                        address_match = self._address and self._address.lower() in location_text.lower()
                        punct_match = self._punct_termic and self._punct_termic.lower() in location_text.lower()
                        
                        if address_match or punct_match:
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
                                "Locatie Gasita": location_text,
                                "Ultima Actualizare": time.strftime("%Y-%m-%d %H:%M:%S")
                            }
                            data_gasita = True
                            _LOGGER.info(f"Date găsite pentru {self._address}: {self._state}")
                            break
                
                if data_gasita:
                    break
            
            if not data_gasita:
                # No matching location found
                self._state = "Fără întreruperi"
                self._attrs = {
                    "Adresa": self._address,
                    "Punct Termic": self._punct_termic,
                    "Ultima Actualizare": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "Status": "Nu s-au găsit întreruperi pentru această adresă"
                }
                _LOGGER.info(f"Nu s-au găsit întreruperi pentru: {self._address}")
            
            self._available = True
            return True

        except requests.exceptions.RequestException as e:
            _LOGGER.error(f"Eroare de conexiune la CMTEB: {str(e)}")
            self._state = "Eroare conexiune"
            self._available = False
            self._attrs = {
                "Eroare": str(e),
                "Adresa": self._address,
                "Ultima Încercare": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            return False
            
        except Exception as e:
            _LOGGER.error(f"Eroare la extragerea datelor de la CMTEB: {str(e)}")
            self._state = "Eroare date"
            self._available = False
            self._attrs = {
                "Eroare": str(e),
                "Adresa": self._address, 
                "Ultima Încercare": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            return False

    async def async_update(self):
        """Update the sensor."""
        await self.hass.async_add_executor_job(self._fetch_data)
