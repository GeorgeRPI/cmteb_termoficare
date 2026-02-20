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
            _LOGGER.info("Conexiunea la CMTEB funcționează!")
            return {"status": "success", "protocol": "HTTPS"}
        else:
            _LOGGER.error("Eroare HTTP: %s", response.status_code)
            return {"status": "error", "code": response.status_code}

    except requests.exceptions.SSLError:
        _LOGGER.error("Eroare SSL - site-ul poate necesita HTTPS")
        return {"status": "error", "message": "SSL Error"}

    except requests.exceptions.ConnectionError as e:
        _LOGGER.error("Eroare de conexiune: %s", e)
        return {"status": "error", "message": str(e)}

    except Exception as e:
        _LOGGER.error("Eroare neașteptată: %s", e)
        return {"status": "error", "message": str(e)}


async def async_setup_services(hass):
    """Set up services for CMTEB."""
    from .const import DOMAIN

    hass.services.async_register(DOMAIN, "test_connection", async_test_connection)
