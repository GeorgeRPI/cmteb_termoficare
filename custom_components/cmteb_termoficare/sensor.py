"""Sensor platform for CMTEB Termoficare."""
import logging
from datetime import timedelta, datetime
import re

import aiohttp
from bs4 import BeautifulSoup

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from.const import DOMAIN, URL_CMTEB

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(minutes=30)

ADRESA_VARIATIONS = {
    "str": ["str", "str.", "Str", "Str.", "strada", "Strada", "STRADA"],
    "bd": ["bd", "bd.", "Bd", "Bd.", "bld", "bld.", "Bld", "Bld.", "bulevard", "Bulevard", "BULEVARD"],
    "sos": ["sos", "sos.", "Sos", "Sos.", "şos", "şos.", "Şos", "Şos.", "sosea", "Sosea", "şosea", "Şosea", "SOSEA"],
    "calea": ["calea", "Calea", "CALAEA"],
    "drum": ["drm", "drm.", "Drm", "Drm.", "drum", "Drum", "DRUM"],
    "p-ta": ["p-ta", "p-ta.", "P-ta", "P-ta.", "piața", "Piața", "piata", "Piata", "PIAȚA"],
    "aleea": ["aleea", "Aleea", "ALEEA"],
    "intrare": ["intrare", "Intrare", "INTRARE"],
    "platforma": ["platforma", "Platforma", "PLATFORMA"],
}

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the CMTEB sensors from a config entry."""
    address = config_entry.options.get("adresa") or config_entry.data.get("adresa", "")
    punct_termic = config_entry.options.get("punct_termic") or config_entry.data.get("punct_termic", "")

    address_slug = _create_address_slug(address, punct_termic)

    sensors = [
        CmtebSensor(config_entry, "agent_afectat", "Agent Termic Afectat", address_slug),
        CmtebSensor(config_entry, "cauza_interventie", "Cauză Intervenție", address_slug),
        CmtebSensor(config_entry, "data_estimata_reparatie", "Dată Estimată Reparație", address_slug),
    ]
    async_add_entities(sensors, update_before_add=True)

def _create_address_slug(address, punct_termic=""):
    """Creează un slug unic pentru adresă și punct termic."""
    address = address or ""
    punct_termic = punct_termic or ""
    slug = address.lower().strip()

    if punct_termic:
        slug += "_" + punct_termic.lower().strip()

    slug = re.sub(r"[^\w\s]", "", slug)
    slug = re.sub(r"\s+", "_", slug).strip("_")

    if not slug:
        return "adresa_necunoscuta"

    slug = slug[:32]

    if not slug[0].isalpha():
        slug = "adresa_" + slug

    return slug

def _normalize_address(address: str) -> str:
    """Normalizează o adresă prin înlocuirea prescurtărilor."""
    if not address:
        return ""

    normalized = address.lower().strip()

    for standard_form, variations in ADRESA_VARIATIONS.items():
        for variation in variations:
            pattern = r"\b" + re.escape(variation.lower()) + r"\b"
            if re.search(pattern, normalized):
                normalized = re.sub(pattern, standard_form, normalized)
                break

    return normalized.strip()

def _find_exact_match(user_address: str, user_punct_termic: str, site_location: str) -> bool:
    """Caută potrivire exactă între adresa+punct_termic și locația de pe site."""
    if not site_location:
        return False

    site_location_lower = site_location.lower()
    user_address_lower = (user_address or "").lower()
    user_punct_lower = (user_punct_termic or "").lower()

    _LOGGER.debug("Căutare: Adresă='%s', Punct='%s', Site='%s'", user_address, user_punct_termic, site_location)

    if user_address and user_punct_termic:
        address_in_site = user_address_lower in site_location_lower
        punct_in_site = user_punct_lower in site_location_lower

        if address_in_site and punct_in_site:
            _LOGGER.info("Potrivire exactă: '%s' + '%s' în '%s'", user_address, user_punct_termic, site_location)
            return True

        if punct_in_site and any(word in site_location_lower for word in user_punct_lower.split()):
            _LOGGER.info("Potrivire punct termic: '%s' în '%s'", user_punct_termic, site_location)
            return True

    elif user_address and not user_punct_termic:
        if user_address_lower in site_location_lower:
            _LOGGER.info("Potrivire adresă: '%s' în '%s'", user_address, site_location)
            return True

        user_norm = _normalize_address(user_address)
        site_norm = _normalize_address(site_location)
        if user_norm and site_norm and user_norm in site_norm:
            _LOGGER.info("Potrivire normalizată: '%s' în '%s'", user_address, site_location)
            return True

    elif user_punct_termic and not user_address:
        if user_punct_lower in site_location_lower:
            _LOGGER.info("Potrivire doar punct: '%s' în '%s'", user_punct_termic, site_location)
            return True

    _LOGGER.debug("Fără potrivire pentru '%s' + '%s' în '%s'", user_address, user_punct_termic, site_location)
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
        self._address = config_entry.options.get("adresa") or config_entry.data.get("adresa", "")
        self._punct_termic = config_entry.options.get("punct_termic") or config_entry.data.get("punct_termic", "")
        self._available = True

    @property
    def name(self):
        return f"cmteb_{self._type}_{self._address_slug}"

    @property
    def friendly_name(self):
        base_name = f"CMTEB {self._friendly_name}"
        if self._punct_termic:
            return f"{base_name} - {self._address} ({self._punct_termic})"
        return f"{base_name} - {self._address}"

    @property
    def state(self):
        return self._state

    @property
    def available(self):
        return self._available

    @property
    def extra_state_attributes(self):
        return self._attrs

    @property
    def unique_id(self):
        return f"{self._config_entry.entry_id}_{self._type}"

    async def _async_fetch_data(self):
        """Fetch data from CMTEB website - ASYNC."""
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "ro-RO,ro;q=0.9,en;q=0.8",
            }

            session = async_get_clientsession(self.hass)
            async with session.get(URL_CMTEB, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as response:

                if response.status!= 200:
                    self._state = f"Eroare HTTP {response.status}"
                    self._available = False
                    self._attrs = {
                        "Eroare": f"Cod HTTP: {response.status}",
                        "Adresa": self._address,
                        "Punct_Termic": self._punct_termic,
                        "Ultima_Încercare": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    }
                    return False

                html = await response.text()

            soup = BeautifulSoup(html, "html.parser")
            tables = soup.find_all("table")

            if not tables:
                self._state = "Fără date"
                self._available = True
                self._attrs = {
                    "Adresa": self._address,
                    "Punct_Termic": self._punct_termic,
                    "Status": "Nu s-au găsit tabele pe pagină",
                    "Ultima_Actualizare": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }
                return True

            data_gasita = False

            for table in tables:
                rows = table.find_all("tr")[1:]

                for row in rows:
                    cols = [ele.text.strip() for ele in row.find_all("td")]

                    if len(cols) >= 5:
                        location_text = cols[1] if len(cols) > 1 else ""

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
                                "Ultima_Actualizare": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "Metoda_Potrivire": "precisa_adresa_punct",
                            }
                            self._available = True
                            data_gasita = True
                            _LOGGER.info("Date găsite pentru '%s' + '%s' în '%s'", self._address, self._punct_termic, location_text)
                            break

                if data_gasita:
                    break

            if not data_gasita:
                self._state = "Fără întreruperi"
                self._available = True
                self._attrs = {
                    "Adresa": self._address,
                    "Punct_Termic": self._punct_termic,
                    "Ultima_Actualizare": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Status": "Nu s-au găsit întreruperi pentru această combinație adresă+punct termic",
                }
                _LOGGER.info("Fără întreruperi pentru: '%s' + '%s'", self._address, self._punct_termic)

            return True

        except Exception as e:
            _LOGGER.error("Eroare la preluarea datelor: %s", e)
            self._state = "Eroare conexiune"
            self._available = False
            self._attrs = {
                "Eroare": str(e),
                "Adresa": self._address,
                "Punct_Termic": self._punct_termic,
                "Ultima_Încercare": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
            return False

    async def async_update(self):
        """Update the sensor."""
        await self._async_fetch_data()
