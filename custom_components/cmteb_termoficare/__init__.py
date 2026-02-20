"""The cmteb_termoficare integration."""
import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up cmteb_termoficare from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    if "services" not in hass.data[DOMAIN]:
        from .services import async_setup_services
        await async_setup_services(hass)
        hass.data[DOMAIN]["services"] = True

    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    await hass.config_entries.async_forward_entry_unload(entry, "sensor")
    return True
