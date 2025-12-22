"""Sensor platform for CMTEB Termoficare."""
import logging
from datetime import timedelta, datetime
import requests
from bs4 import BeautifulSoup
import time
import re
import json
from typing import List, Tuple, Dict, Any
import calendar
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.storage import Store

from .const import DOMAIN, URL_CMTEB

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(minutes=30)
STORAGE_VERSION = 1
STORAGE_KEY = f"{DOMAIN}.storage"

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

class HistoryManager:
    """Manager pentru istoricul lunar."""
    
    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry):
        """Initialize history manager."""
        self.hass = hass
        self.config_entry = config_entry
        self.address = config_entry.data.get("adresa")
        self.punct_termic = config_entry.data.get("punct_termic", "")
        self.store = Store(hass, STORAGE_VERSION, f"{STORAGE_KEY}_{config_entry.entry_id}")
        self.data = {}
        
    async def async_load(self):
        """Încarcă datele din storage."""
        self.data = await self.store.async_load() or {}
        
    async def async_save(self):
        """Salvează datele în storage."""
        await self.store.async_save(self.data)
        
    def get_current_month_key(self):
        """Returnează cheia pentru luna curentă."""
        now = datetime.now()
        return f"{now.year}-{now.month:02d}"
        
    def get_days_in_month(self):
        """Returnează numărul de zile din luna curentă."""
        now = datetime.now()
        return calendar.monthrange(now.year, now.month)[1]
        
    def update_history(self, state: str):
        """Actualizează istoricul pentru ziua curentă."""
        if not state:
            return
            
        month_key = self.get_current_month_key()
        current_day = datetime.now().day
        
        # Initializează structura pentru luna curentă
        if month_key not in self.data:
            self.data[month_key] = {
                "month": datetime.now().strftime("%B %Y"),
                "month_number": datetime.now().month,
                "year": datetime.now().year,
                "days_in_month": self.get_days_in_month(),
                "daily_states": {},
                "statistics": {
                    "incalzire_oprit": 0,
                    "apa_calda_oprit": 0,
                    "functional": 0,
                    "deficienta": 0,
                    "acc_inc_oprit": 0,
                    "zile_inregistrate": 0
                }
            }
        
        # Actualizează starea pentru ziua curentă
        if str(current_day) not in self.data[month_key]["daily_states"]:
            self.data[month_key]["daily_states"][str(current_day)] = []
            
        # Adaugă starea curentă pentru ziua de azi (fără duplicate)
        daily_states = self.data[month_key]["daily_states"][str(current_day)]
        if state not in daily_states:
            daily_states.append(state)
            
        # Recalculează statisticile pentru întreaga lună
        self._recalculate_monthly_stats(month_key)
        
    def _recalculate_monthly_stats(self, month_key: str):
        """Recalculează statisticile pentru o lună."""
        month_data = self.data[month_key]
        stats = month_data["statistics"]
        
        # Resetare statistici
        for key in stats:
            stats[key] = 0
            
        # Calcul statistici bazat pe stările zilnice
        zile_inregistrate = 0
        
        for day, states in month_data["daily_states"].items():
            if not states:
                continue
                
            zile_inregistrate += 1
            
            # Pentru fiecare zi, verifică ce stări au fost înregistrate
            has_incalzire = False
            has_apa_calda = False
            has_deficienta = False
            has_functional = False
            
            for state in states:
                state_lower = state.lower()
                if "încălzire" in state_lower or "incalzire" in state_lower:
                    has_incalzire = True
                    stats["incalzire_oprit"] += 1
                elif "apă caldă" in state_lower or "apa calda" in state_lower or "acc" in state_lower:
                    has_apa_calda = True
                    stats["apa_calda_oprit"] += 1
                elif "deficienta" in state_lower or "deficiență" in state_lower:
                    has_deficienta = True
                    stats["deficienta"] += 1
                elif "fără întreruperi" in state_lower or "fara intreruperi" in state_lower or "functional" in state_lower:
                    has_functional = True
                    stats["functional"] += 1
            
            # Dacă ambele sunt oprite în aceeași zi
            if has_incalzire and has_apa_calda:
                stats["acc_inc_oprit"] += 1
                
        stats["zile_inregistrate"] = zile_inregistrate
                    
    def get_monthly_statistics(self) -> Dict[str, Any]:
        """Returnează statisticile pentru luna curentă."""
        month_key = self.get_current_month_key()
        if month_key not in self.data:
            now = datetime.now()
            month_name = ["Ianuarie", "Februarie", "Martie", "Aprilie", "Mai", "Iunie",
                         "Iulie", "August", "Septembrie", "Octombrie", "Noiembrie", "Decembrie"][now.month - 1]
            
            return {
                "month": f"{month_name} {now.year}",
                "month_number": now.month,
                "year": now.year,
                "zile_in_luna": self.get_days_in_month(),
                "zile_incalzire_oprit": 0,
                "zile_apa_calda_oprit": 0,
                "zile_functional": 0,
                "zile_deficienta": 0,
                "zile_acc_inc_oprit": 0,
                "zile_trecute": datetime.now().day,
                "zile_ramase": self.get_days_in_month() - datetime.now().day,
                "procent_functional": 0,
                "procent_oprit": 0,
                "procent_deficienta": 0
            }
            
        month_data = self.data[month_key]
        stats = month_data["statistics"]
        
        # Calculăm zilele trecute din lună
        current_day = datetime.now().day
        zile_trecute = min(current_day, month_data["days_in_month"])
        zile_ramase = max(0, month_data["days_in_month"] - current_day)
        
        # Calculăm procentele
        total_zile_posibile = zile_trecute
        if total_zile_posibile > 0:
            procent_functional = round((stats["functional"] / total_zile_posibile) * 100, 1)
            total_oprit = stats["incalzire_oprit"] + stats["apa_calda_oprit"]
            procent_oprit = round((total_oprit / total_zile_posibile) * 100, 1)
            procent_deficienta = round((stats["deficienta"] / total_zile_posibile) * 100, 1)
        else:
            procent_functional = 0
            procent_oprit = 0
            procent_deficienta = 0
        
        return {
            "month": month_data["month"],
            "month_number": month_data.get("month_number", datetime.now().month),
            "year": month_data.get("year", datetime.now().year),
            "zile_in_luna": month_data["days_in_month"],
            "zile_incalzire_oprit": stats["incalzire_oprit"],
            "zile_apa_calda_oprit": stats["apa_calda_oprit"],
            "zile_functional": stats["functional"],
            "zile_deficienta": stats["deficienta"],
            "zile_acc_inc_oprit": stats["acc_inc_oprit"],
            "zile_trecute": zile_trecute,
            "zile_ramase": zile_ramase,
            "zile_inregistrate": stats.get("zile_inregistrate", 0),
            "procent_functional": procent_functional,
            "procent_oprit": procent_oprit,
            "procent_deficienta": procent_deficienta
        }

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the CMTEB sensors from a config entry."""
    address = config_entry.data.get("adresa")
    punct_termic = config_entry.data.get("punct_termic", "")
    
    # Generează un nume unic pentru senzori
    address_slug = _create_address_slug(address, punct_termic)
    
    # Crează history manager
    history_manager = HistoryManager(hass, config_entry)
    await history_manager.async_load()

    # Crează senzorii
    sensors = [
        CmtebSensor(config_entry, "agent_afectat", "Agent Termic Afectat", address_slug, history_manager),
        CmtebSensor(config_entry, "cauza_interventie", "Cauză Intervenție", address_slug, history_manager),
        CmtebSensor(config_entry, "data_estimata_reparatie", "Dată Estimată Reparație", address_slug, history_manager),
        CmtebSensorIstoric(config_entry, "istoric_lunar", "Istoric Lunar", address_slug, history_manager)
    ]
    async_add_entities(sensors, update_before_add=True)

def _create_address_slug(address, punct_termic=""):
    """Creează un slug unic pentru adresă și punct termic."""
    if not address:
        return "unknown"
        
    slug = address.lower().strip()
    
    if punct_termic:
        slug += "_" + punct_termic.lower().strip()
    
    slug = re.sub(r'[^\w\s]', '', slug)
    slug = re.sub(r'\s+', '_', slug)
    slug = slug[:32]
    
    if not slug[0].isalpha():
        slug = 'adresa_' + slug
    
    return slug

def _normalize_address(address: str) -> str:
    """Normalizează o adresă prin înlocuirea prescurtărilor."""
    if not address:
        return ""
    
    normalized = address.lower().strip()
    
    for standard_form, variations in ADRESA_VARIATIONS.items():
        for variation in variations:
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
    
    street_types = []
    for variations in ADRESA_VARIATIONS.values():
        street_types.extend([v.lower() for v in variations])
    
    street_types.sort(key=len, reverse=True)
    
    for street_type in street_types:
        pattern = r'\b' + re.escape(street_type) + r'\b'
        if re.search(pattern, address_lower):
            cleaned = re.sub(pattern, '', address_lower)
            cleaned = re.sub(r'[\.\s]+', ' ', cleaned).strip()
            return cleaned
    
    return address_lower

def _find_exact_match(user_address: str, user_punct_termic: str, site_location: str) -> bool:
    """Caută potrivire exactă între adresa+punct_termic utilizator și locația de pe site."""
    if not site_location:
        return False
    
    site_location_lower = site_location.lower()
    user_address_lower = user_address.lower() if user_address else ""
    user_punct_lower = user_punct_termic.lower() if user_punct_termic else ""
    
    # Cazul 1: Avem atât adresă cât și punct termic specific
    if user_address and user_punct_termic:
        address_in_site = user_address_lower in site_location_lower
        punct_in_site = user_punct_lower in site_location_lower
        
        if address_in_site and punct_in_site:
            return True
        
        if punct_in_site and any(word in site_location_lower for word in user_punct_lower.split()):
            return True
    
    # Cazul 2: Doar adresă fără punct termic specific
    elif user_address and not user_punct_termic:
        if user_address_lower in site_location_lower:
            return True
        
        user_norm = _normalize_address(user_address)
        site_norm = _normalize_address(site_location)
        if user_norm and site_norm and user_norm in site_norm:
            return True
    
    # Cazul 3: Doar punct termic fără adresă specifică
    elif user_punct_termic and not user_address:
        if user_punct_lower in site_location_lower:
            return True
    
    return False

class CmtebSensor(SensorEntity):
    """Representation of a CMTEB Sensor."""

    def __init__(self, config_entry, sensor_type, friendly_name, address_slug, history_manager=None):
        """Initialize the sensor."""
        self._config_entry = config_entry
        self._type = sensor_type
        self._friendly_name = friendly_name
        self._address_slug = address_slug
        self._history_manager = history_manager
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
        if self._punct_termic:
            return f"CMTEB {self._friendly_name} - {self._address} ({self._punct_termic})"
        return f"CMTEB {self._friendly_name} - {self._address}"

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
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            }

            session = requests.Session()
            session.headers.update(headers)
            
            response = session.get(URL_CMTEB, timeout=30, allow_redirects=True)
            
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

            soup = BeautifulSoup(response.content, 'html.parser')
            tables = soup.find_all('table')

            if not tables:
                self._state = "Fără date"
                self._available = True
                self._attrs = {
                    "Adresa": self._address,
                    "Punct_Termic": self._punct_termic,
                    "Status": "Nu s-au găsit tabele",
                    "Ultima_Actualizare": time.strftime("%Y-%m-%d %H:%M:%S")
                }
                return True

            data_gasita = False
            for table in tables:
                rows = table.find_all('tr')[1:]
                
                for row in rows:
                    cols = [ele.text.strip() for ele in row.find_all('td')]
                    
                    if len(cols) >= 5:
                        location_text = cols[1] if len(cols) > 1 else ""
                        
                        if _find_exact_match(self._address, self._punct_termic, location_text):
                            agent_afectat = cols[2] if len(cols) > 2 else "N/A"
                            cauza = cols[3] if len(cols) > 3 else "N/A"
                            data_estimata = cols[4] if len(cols) > 4 else "N/A"

                            if self._type == "agent_afectat":
                                self._state = agent_afectat
                                # Actualizează istoricul pentru agentul afectat
                                if self._history_manager:
                                    self._history_manager.update_history(agent_afectat)
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
                            break
                
                if data_gasita:
                    break

            if not data_gasita:
                self._state = "Fără întreruperi"
                self._available = True
                if self._history_manager and self._type == "agent_afectat":
                    self._history_manager.update_history("Fără întreruperi")
                    
                self._attrs = {
                    "Adresa": self._address,
                    "Punct_Termic": self._punct_termic,
                    "Ultima_Actualizare": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "Status": "Nu s-au găsit întreruperi"
                }
            
            return True

        except Exception as e:
            _LOGGER.error(f"Eroare la preluarea datelor: {e}")
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

class CmtebSensorIstoric(SensorEntity):
    """Senzor pentru istoricul lunar."""
    
    def __init__(self, config_entry, sensor_type, friendly_name, address_slug, history_manager):
        """Initialize the history sensor."""
        self._config_entry = config_entry
        self._type = sensor_type
        self._friendly_name = friendly_name
        self._address_slug = address_slug
        self._history_manager = history_manager
        self._state = "Luna Curentă"
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
        if self._punct_termic:
            return f"CMTEB {self._friendly_name} - {self._address} ({self._punct_termic})"
        return f"CMTEB {self._friendly_name} - {self._address}"

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

    def _update_attributes(self):
        """Actualizează atributele senzorului."""
        stats = self._history_manager.get_monthly_statistics()
        
        # Setează starea principală
        self._state = stats["month"]
        
        # Setează atributele detaliate
        self._attrs = {
            "Luna": stats["month"],
            "An": stats["year"],
            "Numar luna": stats["month_number"],
            "Zile in luna": stats["zile_in_luna"],
            "Zile trecute": stats["zile_trecute"],
            "Zile ramase": stats["zile_ramase"],
            "Zile inregistrate": stats["zile_inregistrate"],
            
            # Statistici ACC (Apă Caldă)
            "ACC oprit (zile)": stats["zile_apa_calda_oprit"],
            "ACC procent oprit": f"{stats['procent_oprit']}%" if stats['zile_apa_calda_oprit'] > 0 else "0%",
            
            # Statistici INC (Încălzire)
            "INC oprit (zile)": stats["zile_incalzire_oprit"],
            "INC procent oprit": f"{stats['procent_oprit']}%" if stats['zile_incalzire_oprit'] > 0 else "0%",
            
            # Statistici generale
            "Zile functional": stats["zile_functional"],
            "Procent functional": f"{stats['procent_functional']}%",
            
            "Zile deficienta": stats["zile_deficienta"],
            "Procent deficienta": f"{stats['procent_deficienta']}%",
            
            "Zile ACC+INC oprit": stats["zile_acc_inc_oprit"],
            "Procent ACC+INC oprit": f"{stats['procent_oprit']}%" if stats['zile_acc_inc_oprit'] > 0 else "0%",
            
            # Sumar
            "Total zile cu probleme": stats["zile_incalzire_oprit"] + stats["zile_apa_calda_oprit"] + stats["zile_deficienta"],
            "Zile fara probleme": stats["zile_functional"],
            
            "Adresa": self._address,
            "Punct Termic": self._punct_termic,
            "Ultima actualizare": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Adaugă și statistici pe săptămâni dacă sunt disponibile
        current_day = datetime.now().day
        if current_day >= 7:
            self._attrs["Saptamana 1 (zile 1-7)"] = "Disponibil"
        if current_day >= 14:
            self._attrs["Saptamana 2 (zile 8-14)"] = "Disponibil"
        if current_day >= 21:
            self._attrs["Saptamana 3 (zile 15-21)"] = "Disponibil"
        if current_day >= 28:
            self._attrs["Saptamana 4 (zile 22-28)"] = "Disponibil"

    async def async_update(self):
        """Update the sensor."""
        self._update_attributes()
        self._available = True
        
        # Salvează istoricul la fiecare actualizare
        await self._history_manager.async_save()

    async def async_added_to_hass(self):
        """Run when entity about to be added to hass."""
        await super().async_added_to_hass()
        self._update_attributes()
