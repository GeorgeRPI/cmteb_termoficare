import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up CMTEB from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    
    # Setup sensor platform
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True
