"""Sensor platform for CMTEB Termoficare."""
import logging
from datetime import timedelta, datetime
import requests
from bs4 import BeautifulSoup
import time
import re
from typing import List, Tuple, Dict, Any
import calendar
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

class MonthlyHistory:
    """Clasă simplă pentru urmărirea istoricului lunar."""
    
    def __init__(self):
        self.history = {}
        
    def update_state(self, month_key: str, state: str):
        """Actualizează starea pentru luna curentă."""
        if month_key not in self.history:
            now = datetime.now()
            month_name = ["Ianuarie", "Februarie", "Martie", "Aprilie", "Mai", "Iunie",
                         "Iulie", "August", "Septembrie", "Octombrie", "Noiembrie", "Decembrie"][now.month - 1]
            
            self.history[month_key] = {
                "month": f"{month_name} {now.year}",
                "month_number": now.month,
                "year": now.year,
                "days_in_month": calendar.monthrange(now.year, now.month)[1],
                "daily_states": {},
                "statistics": {
                    "incalzire_days": 0,
                    "apa_calda_days": 0,
                    "functional_days": 0,
                    "deficienta_days": 0,
                    "acc_inc_days": 0
                }
            }
        
        current_day = datetime.now().day
        day_key = str(current_day)
        
        if day_key not in self.history[month_key]["daily_states"]:
            self.history[month_key]["daily_states"][day_key] = []
            
        if state not in self.history[month_key]["daily_states"][day_key]:
            self.history[month_key]["daily_states"][day_key].append(state)
            self._recalculate_stats(month_key)
    
    def _recalculate_stats(self, month_key: str):
        """Recalculează statisticile pentru o lună."""
        if month_key not in self.history:
            return
            
        month_data = self.history[month_key]
        stats = month_data["statistics"]
        
        # Reset stats
        for key in stats:
            stats[key] = 0
            
        # Calculate stats
        for day, states in month_data["daily_states"].items():
            if not states:
                continue
                
            has_incalzire = False
            has_apa_calda = False
            has_deficienta = False
            has_functional = False
            
            for state in states:
                state_lower = state.lower()
                if "încălzire" in state_lower or "incalzire" in state_lower:
                    has_incalzire = True
                elif "apă caldă" in state_lower or "apa calda" in state_lower or "acc" in state_lower:
                    has_apa_calda = True
                elif "deficienta" in state_lower or "deficiență" in state_lower:
                    has_deficienta = True
                elif "fără întreruperi" in state_lower or "fara intreruperi" in state_lower:
                    has_functional = True
            
            if has_incalzire:
                stats["incalzire_days"] += 1
            if has_apa_calda:
                stats["apa_calda_days"] += 1
            if has_deficienta:
                stats["deficienta_days"] += 1
            if has_functional:
                stats["functional_days"] += 1
            if has_incalzire and has_apa_calda:
                stats["acc_inc_days"] += 1
    
    def get_current_month_stats(self):
        """Returnează statisticile pentru luna curentă."""
        now = datetime.now()
        month_key = f"{now.year}-{now.month:02d}"
        
        if month_key not in self.history:
            month_name = ["Ianuarie", "Februarie", "Martie", "Aprilie", "Mai", "Iunie",
                         "Iulie", "August", "Septembrie", "Octombrie", "Noiembrie", "Decembrie"][now.month - 1]
            
            days_in_month = calendar.monthrange(now.year, now.month)[1]
            
            return {
                "month": f"{month_name} {now.year}",
                "days_in_month": days_in_month,
                "current_day": now.day,
                "incalzire_days": 0,
                "apa_calda_days": 0,
                "functional_days": 0,
                "deficienta_days": 0,
                "acc_inc_days": 0,
                "days_recorded": 0
            }
        
        month_data = self.history[month_key]
        stats = month_data["statistics"]
        
        return {
            "month": month_data["month"],
            "days_in_month": month_data["days_in_month"],
            "current_day": now.day,
            "incalzire_days": stats["incalzire_days"],
            "apa_calda_days": stats["apa_calda_days"],
            "functional_days": stats["functional_days"],
            "deficienta_days": stats["deficienta_days"],
            "acc_inc_days": stats["acc_inc_days"],
            "days_recorded": len(month_data["daily_states"])
        }

# Inițializează istoricul global
MONTHLY_HISTORY = MonthlyHistory()

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

    # Crează senzorii
    sensors = [
        CmtebSensor(config_entry, "agent_afectat", "Agent Termic Afectat", address_slug),
        CmtebSensor(config_entry, "cauza_interventie", "Cauză Intervenție", address_slug),
        CmtebSensor(config_entry, "data_estimata_reparatie", "Dată Estimată Reparație", address_slug),
        CmtebSensorIstoric(config_entry, "istoric_lunar", "Istoric Lunar", address_slug)
    ]
    async_add_entities(sensors, update_before_add=True)

# ... (toate funcțiile helper rămân la fel: _create_address_slug, _normalize_address, etc.)

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
        """Fetch data from CMTEB website with precise matching."""
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
                    "Status": "Nu s-au găsit tabele pe pagină",
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
                                # Actualizează istoricul
                                now = datetime.now()
                                month_key = f"{now.year}-{now.month:02d}"
                                MONTHLY_HISTORY.update_state(month_key, agent_afectat)
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
                if self._type == "agent_afectat":
                    now = datetime.now()
                    month_key = f"{now.year}-{now.month:02d}"
                    MONTHLY_HISTORY.update_state(month_key, "Fără întreruperi")
                    
                self._attrs = {
                    "Adresa": self._address,
                    "Punct_Termic": self._punct_termic,
                    "Ultima_Actualizare": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "Status": "Nu s-au găsit întreruperi pentru această combinație adresă+punct termic"
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
    
    def __init__(self, config_entry, sensor_type, friendly_name, address_slug):
        """Initialize the history sensor."""
        self._config_entry = config_entry
        self._type = sensor_type
        self._friendly_name = friendly_name
        self._address_slug = address_slug
        self._state = "Calculare..."
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

    async def async_update(self):
        """Update the sensor."""
        try:
            stats = MONTHLY_HISTORY.get_current_month_stats()
            
            # Calculează procentele
            days_passed = stats["current_day"]
            if days_passed > 0:
                inc_percent = round((stats["incalzire_days"] / days_passed) * 100, 1)
                acc_percent = round((stats["apa_calda_days"] / days_passed) * 100, 1)
                func_percent = round((stats["functional_days"] / days_passed) * 100, 1)
                def_percent = round((stats["deficienta_days"] / days_passed) * 100, 1)
                acc_inc_percent = round((stats["acc_inc_days"] / days_passed) * 100, 1)
            else:
                inc_percent = acc_percent = func_percent = def_percent = acc_inc_percent = 0
            
            # Setează starea principală
            self._state = stats["month"]
            
            # Setează atributele
            self._attrs = {
                "Luna": stats["month"],
                "Zile in luna": stats["days_in_month"],
                "Zile trecute": days_passed,
                "Zile ramase": stats["days_in_month"] - days_passed,
                "Zile inregistrate": stats["days_recorded"],
                
                # Statistici INC (Încălzire)
                "INC oprit (zile)": stats["incalzire_days"],
                "INC procent oprit": f"{inc_percent}%",
                
                # Statistici ACC (Apă Caldă)
                "ACC oprit (zile)": stats["apa_calda_days"],
                "ACC procent oprit": f"{acc_percent}%",
                
                # Statistici generale
                "Zile functional": stats["functional_days"],
                "Procent functional": f"{func_percent}%",
                
                "Zile deficienta": stats["deficienta_days"],
                "Procent deficienta": f"{def_percent}%",
                
                "Zile ACC+INC oprit": stats["acc_inc_days"],
                "Procent ACC+INC oprit": f"{acc_inc_percent}%",
                
                # Informații suplimentare
                "Adresa": self._address,
                "Punct Termic": self._punct_termic,
                "Ultima actualizare": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            self._available = True
            
        except Exception as e:
            _LOGGER.error(f"Eroare la actualizarea istoricului: {e}")
            self._state = "Eroare"
            self._available = False
            self._attrs = {
                "Eroare": str(e),
                "Adresa": self._address,
                "Ultima incercare": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
