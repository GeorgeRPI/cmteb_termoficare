"""Services for CMTEB Termoficare."""
import logging
import requests
from homeassistant.core import ServiceCall

_LOGGER = logging.getLogger(__name__)

async def async_test_connection(hass, call: ServiceCall):
    """Test connection to CMTEB website."""
    from .const import URL_CMTEB
    
    try:
        response = requests.get(URL_CMTEB, timeout=10)
        if response.status_code == 200:
            _LOGGER.info("✅ Conexiunea la CMTEB funcționează!")
            return True
        else:
            _LOGGER.error(f"❌ Eroare HTTP: {response.status_code}")
            return False
    except Exception as e:
        _LOGGER.error(f"❌ Eroare conexiune: {e}")
        return False

async def async_setup_services(hass):
    """Set up services for CMTEB."""
    hass.services.async_register(
        DOMAIN, "test_connection", async_test_connection
    )
