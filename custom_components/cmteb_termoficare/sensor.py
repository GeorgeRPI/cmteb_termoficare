"""Sensor platform for CMTEB Termoficare."""
import logging
from datetime import timedelta
import requests
from bs4 import BeautifulSoup
import time
import re
from typing import List, Tuple

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, URL_CMTEB

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(minutes=30)

# Dicționar cu prescurtări și variante comune
ADRESA_VARIATIONS = {
    'str': ['str', 'str.', 'Str', 'Str.', 'strada', 'Strada', 'STRADA'],
    'bd': ['bd', 'bd.', 'Bd', 'Bd.', 'bld', 'bld.', 'Bld', 'Bld.', 'bulevard', 'Bulevard', 'BULEVARD'],
    'sos': ['sos', 'sos.', 'Sos', 'Sos.', 'şos', 'şos.', 'Şos', 'Şos.', 'sosea', 'Sosea', 'şosea', 'Şosea', 'SOSEA'],
    'calea': ['calea', 'Calea', 'CALAEA'],
    'drum': ['drm', 'drm.', 'Drm', 'Drm.', 'drum', 'Drum', 'DRUM'],
    'p-ta': ['p-ta', 'p-ta.', 'P-ta', 'P-ta.', 'piața', 'Piața', 'piata', 'Piata', 'PIAȚA'],
    'aleea': ['aleea', 'Aleea', 'ALEEA'],
    'intrare': ['intrare', 'Intrare', 'INTRARE'],
    'platforma': ['platforma', 'Platforma', 'PLATFORMA']
}

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the CMTEB sensors from a config entry."""
    address = config_entry.data.get("adresa")
    punct_termic = config_entry.data.get("punct_termic", "")
    
    # Generează un nume unic pentru senzori bazat pe adresă și punct termic
    address_slug = _create_address_slug(address, punct_termic)

    sensors = [
        CmtebSensor(config_entry, "agent_afectat", "Agent Termic Afectat", address_slug),
        CmtebSensor(config_entry, "cauza_interventie", "Cauză Intervenție", address_slug),
        CmtebSensor(config_entry, "data_estimata_reparatie", "Dată Estimată Reparație", address_slug)
    ]
    async_add_entities(sensors, update_before_add=True)

def _create_address_slug(address, punct_termic=""):
    """Creează un slug unic pentru adresă și punct termic."""
    # Curăță adresa pentru a crea un nume de entitate valid
    slug = address.lower().strip()
    
    # Adaugă punctul termic dacă există
    if punct_termic:
        slug += "_" + punct_termic.lower().strip()
    
    # Înlocuiește spații și caractere speciale
    slug = re.sub(r'[^\w\s]', '', slug)  # Remove special characters
    slug = re.sub(r'\s+', '_', slug)     # Replace spaces with underscores
    
    # Limitează lungimea (max 32 de caractere pentru entity_id)
    slug = slug[:32]
    
    # Asigură-te că începe cu o literă
    if not slug[0].isalpha():
        slug = 'adresa_' + slug
    
    return slug

def _normalize_address(address: str) -> str:
    """Normalizează o adresă prin înlocuirea prescurtărilor."""
    if not address:
        return ""
    
    # Convert to lowercase for case-insensitive matching
    normalized = address.lower().strip()
    
    # Înlocuiește variantele cu forma standard
    for standard_form, variations in ADRESA_VARIATIONS.items():
        for variation in variations:
            # Caută varianta ca cuvânt întreg (cu spații în jur)
            pattern = r'\b' + re.escape(variation.lower()) + r'\b'
            if re.search(pattern, normalized):
                normalized = re.sub(pattern, standard_form, normalized)
                break
    
    return normalized.strip()

def _extract_street_name(address: str) -> str:
    """Extrage doar numele străzii din adresă (fără tipul străzii)."""
    if not address:
        return ""
    
    address_lower = address.lower()
    
    # Listă cu toate variantele posibile pentru tipurile de străzi
    street_types = []
    for variations in ADRESA_VARIATIONS.values():
        street_types.extend([v.lower() for v in variations])
    
    # Sortează după lungime (cele mai lungi primele) pentru a evita potriviri greșite
    street_types.sort(key=len, reverse=True)
    
    # Încearcă să elimine tipul străzii
    for street_type in street_types:
        # Verifică dacă tipul străzii există în adresă
        pattern = r'\b' + re.escape(street_type) + r'\b'
        if re.search(pattern, address_lower):
            # Elimină tipul străzii și orice puncte/spații în plus
            cleaned = re.sub(pattern, '', address_lower)
            cleaned = re.sub(r'[\.\s]+', ' ', cleaned).strip()
            return cleaned
    
    # Dacă nu găsește tip de stradă, returnează adresa completă
    return address_lower

def _find_exact_match(user_address: str, user_punct_termic: str, site_location: str) -> bool:
    """
    Caută potrivire exactă între adresa+punct_termic utilizator și locația de pe site.
    
    Logica de căutare:
    1. Verifică dacă punctul termic exact există în locația site-ului
    2. Verifică dacă adresa exactă există în locația site-ului  
    3. Fallback la căutarea parțială doar pentru adresă
    """
    if not site_location:
        return False
    
    site_location_lower = site_location.lower()
    user_address_lower = user_address.lower() if user_address else ""
    user_punct_lower = user_punct_termic.lower() if user_punct_termic else ""
    
    _LOGGER.debug(f"Căutare precisă - Adresă: '{user_address}', Punct: '{user_punct_termic}', Site: '{site_location}'")
    
    # Cazul 1: Avem atât adresă cât și punct termic specific
    if user_address and user_punct_termic:
        # Verifică dacă ambele sunt prezente în locația site-ului
        address_in_site = user_address_lower in site_location_lower
        punct_in_site = user_punct_lower in site_location_lower
        
        if address_in_site and punct_in_site:
            _LOGGER.info(f"✅ Potrivire exactă găsită: '{user_address}' + '{user_punct_termic}' în '{site_location}'")
            return True
        
        # Dacă punctul termic este exact în locație, consideră potrivire
        if punct_in_site and any(word in site_location_lower for word in user_punct_lower.split()):
            _LOGGER.info(f"✅ Potrivire după punct termic: '{user_punct_termic}' în '{site_location}'")
            return True
    
    # Cazul 2: Doar adresă fără punct termic specific
    elif user_address and not user_punct_termic:
        # Verifică dacă adresa este în locația site-ului
        if user_address_lower in site_location_lower:
            _LOGGER.info(f"✅ Potrivire după adresă: '{user_address}' în '{site_location}'")
            return True
        
        # Verifică cu normalizare
        user_norm = _normalize_address(user_address)
        site_norm = _normalize_address(site_location)
        if user_norm and site_norm and user_norm in site_norm:
            _LOGGER.info(f"✅ Potrivire normalizată: '{user_address}' în '{site_location}'")
            return True
    
    # Cazul 3: Doar punct termic fără adresă specifică
    elif user_punct_termic and not user_address:
        if user_punct_lower in site_location_lower:
            _LOGGER.info(f"✅ Potrivire doar punct termic: '{user_punct_termic}' în '{site_location}'")
            return True
    
    _LOGGER.debug(f"❌ Nu s-a găsit potrivire precisă pentru '{user_address}' + '{user_punct_termic}' în '{site_location}'")
    return False

class CmtebSensor(SensorEntity):
    """Representation of a CMTEB Sensor."""

    def __init__(self, config_entry, sensor_type, friendly_name, address_slug):
        """Initialize the sensor."""
        self._config_entry = config_entry
        self._type = sensor_type
        self._friendly_name = friendly_name
        self._address_slug = address_slug
        self._state = "Necunoscut"
        self._attrs = {}
        self._address = config_entry.data.get("adresa")
        self._punct_termic = config_entry.data.get("punct_termic", "")
        self._available = True

    @property
    def name(self):
        """Return the name of the sensor."""
        return f"cmteb_{self._type}_{self._address_slug}"

    @property
    def friendly_name(self):
        """Return the friendly name of the sensor."""
        base_name = f"CMTEB {self._friendly_name}"
        if self._punct_termic:
            return f"{base_name} - {self._address} ({self._punct_termic})"
        return f"{base_name} - {self._address}"

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
        """Fetch data from CMTEB website with precise matching."""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'ro-RO,ro;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
            }

            # Folosim session pentru a gestiona redirect-urile automat
            session = requests.Session()
            session.headers.update(headers)
            
            response = session.get(
                URL_CMTEB, 
                timeout=30,
                allow_redirects=True
            )
            
            if response.status_code != 200:
                self._state = f"Eroare HTTP {response.status_code}"
                self._available = False
                self._attrs = {
                    "Eroare": f"Cod HTTP: {response.status_code}",
                    "Adresa": self._address,
                    "Punct_Termic": self._punct_termic,
                    "Ultima_Încercare": time.strftime("%Y-%m-%d %H:%M:%S")
                }
                return False

            # Parse the HTML
            soup = BeautifulSoup(response.content, 'html.parser')
            tables = soup.find_all('table')

            if not tables:
                self._state = "Fără date"
                self._available = True
                self._attrs = {
                    "Adresa": self._address,
                    "Punct_Termic": self._punct_termic,
                    "Status": "Nu s-au găsit tabele pe pagină",
                    "Ultima_Actualizare": time.strftime("%Y-%m-%d %H:%M:%S")
                }
                return True

            # Caută datele pentru adresa + punct termic specific
            data_gasita = False
            
            for table in tables:
                rows = table.find_all('tr')[1:]  # Skip header row
                
                for row in rows:
                    cols = [ele.text.strip() for ele in row.find_all('td')]
                    
                    if len(cols) >= 5:
                        location_text = cols[1] if len(cols) > 1 else ""
                        
                        # Verifică potrivirea precisă cu adresa + punct termic
                        if _find_exact_match(self._address, self._punct_termic, location_text):
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
                                "Punct_Termic": self._punct_termic,
                                "Locatie_Gasita": location_text,
                                "Ultima_Actualizare": time.strftime("%Y-%m-%d %H:%M:%S"),
                                "Metoda_Potrivire": "precisa_adresa_punct"
                            }
                            self._available = True
                            data_gasita = True
                            _LOGGER.info(f"✅ Date găsite pentru '{self._address}' + '{self._punct_termic}' în locația '{location_text}'")
                            break
                
                if data_gasita:
                    break

            if not data_gasita:
                # Dacă nu s-au găsit date pentru combinația exactă
                self._state = "Fără întreruperi"
                self._available = True
                self._attrs = {
                    "Adresa": self._address,
                    "Punct_Termic": self._punct_termic,
                    "Ultima_Actualizare": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "Status": "Nu s-au găsit întreruperi pentru această combinație adresă+punct termic"
                }
                _LOGGER.info(f"ℹ️ Nu s-au găsit întreruperi pentru: '{self._address}' + '{self._punct_termic}'")
            
            return True

        except Exception as e:
            _LOGGER.error(f"❌ Eroare la preluarea datelor: {e}")
            self._state = "Eroare conexiune"
            self._available = False
            self._attrs = {
                "Eroare": str(e),
                "Adresa": self._address,
                "Punct_Termic": self._punct_termic,
                "Ultima_Încercare": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            return False

    async def async_update(self):
        """Update the sensor."""
        await self.hass.async_add_executor_job(self._fetch_data)
