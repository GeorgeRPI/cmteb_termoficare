"""Custom integration for CMTEB termoficare Bucuresti."""
import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

DOMAIN = "cmteb"

async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the CMTEB component."""
    hass.data.setdefault(DOMAIN, {})
    _LOGGER.info("CMTEB component setup initiated")
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up CMTEB from a config entry."""
    _LOGGER.info(f"Setting up CMTEB entry: {entry.data}")
    
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = entry.data
    
    # Forward to sensor platform
    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])
    
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.info("Unloading CMTEB entry")
    
    unload_ok = await hass.config_entries.async_unload_platforms(entry, ["sensor"])
    
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    
    return unload_ok
