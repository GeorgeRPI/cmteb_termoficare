"""The cmteb_termoficare integration."""
import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .services import async_setup_services

_LOGGER = logging.getLogger(__name__)

DOMAIN = "cmteb_termoficare"

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up cmteb_termoficare from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    
    # Setup services
    await async_setup_services(hass)
    
    # Forward the setup to the sensor platform
    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    await hass.config_entries.async_forward_entry_unload(entry, "sensor")
    return True
