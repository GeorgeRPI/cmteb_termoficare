import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN

DATA_SCHEMA = vol.Schema({
    vol.Required("nume_locatie", description="Introdu numele locației tale"): cv.string,
    vol.Required("adresa", description="Adresa exactă cum apare pe CMTEB"): cv.string,
})

class CmtebConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Gestionează config flow pentru CMTEB Termoficare."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Pasul inițial pentru configurare."""
        errors = {}

        if user_input is not None:
            # Validează inputul
            if not user_input["adresa"]:
                errors["base"] = "adresa_obligatorie"
            else:
                # Creează ID unic
                unique_id = f"cmteb_{user_input['adresa'].lower().replace(' ', '_')}"
                
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=f"CMTEB {user_input['nume_locatie']}",
                    data=user_input
                )

        return self.async_show_form(
            step_id="user", 
            data_schema=DATA_SCHEMA, 
            errors=errors,
            description_placeholders={
                "instructions": "Introdu datele locației tale pentru a verifica întreruperile la termoficare."
            }
        )
