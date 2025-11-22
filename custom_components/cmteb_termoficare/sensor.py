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
SCAN_INTERVAL = timedelta(hours=2)

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
    async_add_entities(sensors, update_before_add=True)  # True pentru a testa imediat

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

    def _fetch_data(self):
        """Fetch data from CMTEB website."""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'ro-RO,ro;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
            }

            _LOGGER.info(f"Încerc să accesez: {URL_CMTEB}")
            
            # Folosim session pentru a gestiona redirect-urile automat
            session = requests.Session()
            session.headers.update(headers)
            
            response = session.get(
                URL_CMTEB, 
                timeout=30,
                allow_redirects=True  # Permite redirect-urile
            )
            
            _LOGGER.info(f"Răspuns primit: Status {response.status_code}, Redirect: {len(response.history)}")
            
            if response.status_code != 200:
                self._state = f"Eroare HTTP {response.status_code}"
                self._available = False
                self._attrs = {
                    "Eroare": f"Cod HTTP: {response.status_code}",
                    "Adresa": self._address,
                    "Ultima Încercare": time.strftime("%Y-%m-%d %H:%M:%S")
                }
                return False

            # Verifică dacă conținutul este HTML valid
            if not response.content:
                self._state = "Răspuns gol"
                self._available = False
                self._attrs = {
                    "Eroare": "Serverul a returnat conținut gol",
                    "Adresa": self._address,
                    "Ultima Încercare": time.strftime("%Y-%m-%d %H:%M:%S")
                }
                return False

            # Parse the HTML
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Verifică titlul paginii pentru confirmare
            title = soup.find('title')
            if title:
                _LOGGER.info(f"Titlul paginii: {title.text}")

            tables = soup.find_all('table')
            _LOGGER.info(f"Am găsit {len(tables)} tabele pe pagină")

            if not tables:
                self._state = "Fără tabele"
                self._available = True
                self._attrs = {
                    "Adresa": self._address,
                    "Status": "Nu s-au găsit tabele pe pagină",
                    "Ultima Actualizare": time.strftime("%Y-%m-%d %H:%M:%S")
                }
                return True

            # Caută datele pentru adresa specificată
            data_gasita = False
            for i, table in enumerate(tables):
                rows = table.find_all('tr')[1:]  # Skip header row
                _LOGGER.info(f"Tabel {i+1}: {len(rows)} rânduri")
                
                for j, row in enumerate(rows):
                    cols = [ele.text.strip() for ele in row.find_all('td')]
                    
                    if len(cols) >= 5 and self._address:
                        location_text = cols[1] if len(cols) > 1 else ""
                        _LOGGER.debug(f"Rând {j+1}: {location_text}")
                        
                        # Caută potrivire parțială în text
                        if self._address.lower() in location_text.lower():
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
                                "Ultima Actualizare": time.strftime("%Y-%m-%d %H:%M:%S"),
                                "Tabel": i + 1,
                                "Rand": j + 1
                            }
                            self._available = True
                            _LOGGER.info(f"✅ DATE GĂSITE pentru {self._address}: {self._state}")
                            data_gasita = True
                            break
                
                if data_gasita:
                    break

            if not data_gasita:
                # Dacă nu s-au găsit date
                self._state = "Fără întreruperi"
                self._available = True
                self._attrs = {
                    "Adresa": self._address,
                    "Punct Termic": self._punct_termic,
                    "Ultima Actualizare": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "Status": "Nu s-au găsit întreruperi pentru această adresă",
                    "Tabele Verificate": len(tables)
                }
                _LOGGER.info(f"ℹ️ Nu s-au găsit întreruperi pentru: {self._address}")
            
            return True

        except requests.exceptions.RequestException as e:
            _LOGGER.error(f"❌ Eroare de conexiune: {e}")
            self._state = "Eroare conexiune"
            self._available = False
            self._attrs = {
                "Eroare": str(e),
                "Adresa": self._address,
                "Ultima Încercare": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            return False
            
        except Exception as e:
            _LOGGER.error(f"❌ Eroare neașteptată: {e}")
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
        await self.hass.async_add_executor_job(self._fetch_data)
