"""Sensor platform for CMTEB Termoficare."""
import logging
from datetime import timedelta
import requests
from bs4 import BeautifulSoup
import time
import random

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, URL_CMTEB

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(minutes=60)  # Redus la 1 oră pentru a nu suprasolicita

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
    async_add_entities(sensors, update_before_add=False)  # Schimbat în False

class CmtebSensor(SensorEntity):
    """Representation of a CMTEB Sensor."""

    def __init__(self, config_entry, sensor_type, friendly_name):
        """Initialize the sensor."""
        self._config_entry = config_entry
        self._type = sensor_type
        self._friendly_name = friendly_name
        self._state = "Necunoscut"
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
        """Return random headers to mimic different browsers."""
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0'
        ]
        
        return {
            'User-Agent': random.choice(user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ro-RO,ro;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0'
        }

    def _try_connect(self, use_https=True):
        """Try to connect with retry logic."""
        url = URL_CMTEB
        if not use_https:
            url = url.replace('https://', 'http://')
            
        for attempt in range(3):
            try:
                headers = self._get_headers()
                _LOGGER.debug(f"Încercare {attempt + 1} pentru {url}")
                
                response = requests.get(
                    url, 
                    headers=headers, 
                    timeout=20,
                    verify=False if not use_https else True
                )
                response.raise_for_status()
                return response
                
            except requests.exceptions.SSLError:
                _LOGGER.warning(f"Eroare SSL la încercarea {attempt + 1}, încerc fără HTTPS")
                if use_https:
                    return self._try_connect(use_https=False)
                else:
                    raise
                    
            except requests.exceptions.ConnectionError as e:
                if attempt == 2:  # Ultima încercare
                    raise e
                time.sleep(2)  # Așteaptă 2 secunde între încercări
                continue
                
            except Exception as e:
                if attempt == 2:
                    raise e
                time.sleep(2)
                continue
                
        return None

    def _fetch_data(self):
        """Fetch data from CMTEB website."""
        try:
            response = self._try_connect()
            
            if not response or not response.content:
                self._state = "Eroare conexiune"
                self._available = False
                self._attrs = {
                    "Eroare": "Răspuns gol de la server",
                    "Adresa": self._address,
                    "Ultima Încercare": time.strftime("%Y-%m-%d %H:%M:%S")
                }
                return False

            # Use built-in HTML parser
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Verifică dacă pagina conține datele așteptate
            tables = soup.find_all('table')
            if not tables:
                _LOGGER.warning("Nu s-au găsit tabele pe pagină")
                self._state = "Fără date"
                self._available = True
                self._attrs = {
                    "Adresa": self._address,
                    "Status": "Pagina nu conține tabele",
                    "Ultima Actualizare": time.strftime("%Y-%m-%d %H:%M:%S")
                }
                return True

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
            _LOGGER.warning(f"Eroare de conexiune la CMTEB: {str(e)}")
            self._state = "Eroare conexiune"
            self._available = False
            self._attrs = {
                "Eroare": str(e),
                "Adresa": self._address,
                "Ultima Încercare": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            return False
            
        except Exception as e:
            _LOGGER.error(f"Eroare neașteptată: {str(e)}")
            self._state = "Eroare neașteptată"
            self._available = False
            self._attrs = {
                "Eroare": str(e),
                "Adresa": self._address, 
                "Ultima Încercare": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            return False

    async def async_update(self):
        """Update the sensor."""
        # Adaugă un delay random între 0-10 secunde pentru a nu suprasolicita
        import asyncio
        await asyncio.sleep(random.randint(0, 10))
        await self.hass.async_add_executor_job(self._fetch_data)
