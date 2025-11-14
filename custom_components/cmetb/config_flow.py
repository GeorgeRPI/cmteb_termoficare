"""Config flow for CMTEB integration."""
import voluptuous as vol
from homeassistant import config_entries
from .const import DOMAIN, CONF_SECTOR, CONF_NUME_PUNCT

class CmtebConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for CMTEB."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            # Validare simplă
            if not user_input[CONF_NUME_PUNCT].strip():
                errors[CONF_NUME_PUNCT] = "nume_required"
            else:
                # Crează intrarea
                title = f"{user_input[CONF_SECTOR]} - {user_input[CONF_NUME_PUNCT]}"
                return self.async_create_entry(title=title, data=user_input)

        # Schema simplă
        data_schema = vol.Schema({
            vol.Required(CONF_SECTOR, default="sector_1"): vol.In({
                "sector_1": "Sector 1",
                "sector_2": "Sector 2",
                "sector_3": "Sector 3", 
                "sector_4": "Sector 4",
                "sector_5": "Sector 5",
                "sector_6": "Sector 6"
            }),
            vol.Required(CONF_NUME_PUNCT): str
        })

        return self.async_show_form(
            step_id="user", 
            data_schema=data_schema, 
            errors=errors
        )
