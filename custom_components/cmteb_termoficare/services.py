"""Services for CMTEB Termoficare."""
import logging
import requests
from homeassistant.core import ServiceCall

_LOGGER = logging.getLogger(__name__)

async def async_test_connection(hass, call: ServiceCall):
    """Test connection to CMTEB website."""
    from .const import URL_CMTEB
    
    try:
        # Încearcă mai întâi HTTP
        test_url = URL_CMTEB.replace('https://', 'http://')
        response = requests.get(test_url, timeout=10)
        
        if response.status_code == 200:
            _LOGGER.info("✅ Conexiunea la CMTEB funcționează cu HTTP!")
            return {"status": "success", "protocol": "HTTP"}
        else:
            _LOGGER.error(f"❌ Eroare HTTP: {response.status_code}")
            return {"status": "error", "code": response.status_code}
            
    except requests.exceptions.SSLError:
        _LOGGER.error("❌ Eroare SSL - site-ul poate necesita HTTPS")
        return {"status": "error", "message": "SSL Error"}
        
    except requests.exceptions.ConnectionError as e:
        _LOGGER.error(f"❌ Eroare de conexiune: {e}")
        return {"status": "error", "message": str(e)}
        
    except Exception as e:
        _LOGGER.error(f"❌ Eroare neașteptată: {e}")
        return {"status": "error", "message": str(e)}

async def async_setup_services(hass):
    """Set up services for CMTEB."""
    from .const import DOMAIN
    
    hass.services.async_register(
        DOMAIN, "test_connection", async_test_connection
    )
