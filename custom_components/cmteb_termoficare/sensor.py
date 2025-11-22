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
SCAN_INTERVAL = timedelta(minutes=10)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Configurează senzorii CMTEB din config entry."""
    nume_locatie = config_entry.data.get("nume_locatie")
    adresa = config_entry.data.get("adresa")

    sensors = [
        CmtebSensor(config_entry, "agent_afectat", "Agent Termic Afectat"),
        CmtebSensor(config_entry, "cauza_interventie", "Cauză Intervenție"),
        CmtebSensor(config_entry, "data_estimata_reparatie", "Dată Estimată Reparație")
    ]
    async_add_entities(sensors, update_before_add=True)

class CmtebSensor(SensorEntity):
    """Reprezintă un Senzor CMTEB."""

    def __init__(self, config_entry, sensor_type, nume_afisat):
        self._config_entry = config_entry
        self._type = sensor_type
        self._nume_afisat = nume_afisat
        self._state = None
        self._attrs = {}
        self._adresa = config_entry.data.get("adresa")
        self._nume_locatie = config_entry.data.get("nume_locatie")

    @property
    def name(self):
        return f"cmteb_{self._type}"

    @property
    def friendly_name(self):
        return f"CMTEB {self._nume_afisat}"

    @property
    def state(self):
        return self._state

    @property
    def extra_state_attributes(self):
        return self._attrs

    @property
    def unique_id(self):
        return f"{self._config_entry.entry_id}_{self._type}"

    def update(self):
        """Actualizează datele senzorului."""
        try:
            response = requests.get(URL_CMTEB, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Caută toate tabelele pe pagină
            tabele = soup.find_all('table')
            
            for tabel in tabele:
                randuri = tabel.find_all('tr')[1:]  # Sărim header-ul
                
                for rand in randuri:
                    coloane = [col.text.strip() for col in rand.find_all('td')]
                    
                    if len(coloane) >= 5 and self._adresa in coloane[1]:
                        # Am găsit locația în tabel
                        agent_afectat = coloane[2]
                        cauza = coloane[3]
                        data_estimata = coloane[4]

                        if self._type == "agent_afectat":
                            self._state = agent_afectat
                        elif self._type == "cauza_interventie":
                            self._state = cauza
                        elif self._type == "data_estimata_reparatie":
                            self._state = data_estimata
                        
                        self._attrs = {
                            "Locație": self._nume_locatie,
                            "Adresă căutată": self._adresa,
                            "Adresă găsită": coloane[1]
                        }
                        return
            
            # Dacă nu găsim locația
            self._state = "Fără întreruperi"
            self._attrs = {
                "Locație": self._nume_locatie,
                "Adresă": self._adresa,
                "Status": "Nu s-au găsit întreruperi pentru această adresă"
            }

        except Exception as e:
            logging.error(f"Eroare la actualizare CMTEB: {e}")
            self._state = "Eroare conectare"
            self._attrs = {"Eroare": str(e)}
