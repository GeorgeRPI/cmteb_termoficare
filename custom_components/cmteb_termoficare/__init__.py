"""Platforma cmteb_termoficare."""
import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

DOMAIN = "cmteb_termoficare"

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Configurează cmteb_termoficare din config entry."""
    hass.data.setdefault(DOMAIN, {})
    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Elimină o config entry."""
    await hass.config_entries.async_forward_entry_unload(entry, "sensor")
    return True
