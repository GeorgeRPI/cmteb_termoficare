import voluptuous as vol
from homeassistant import config_entries
from .const import DOMAIN, SECTORI_PUNCTE

class CmtebConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for CMTEB."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            # Salvează configurația
            punct_complet = f"{user_input['sector']} - {user_input['nume_punct']}"
            
            return self.async_create_entry(
                title=punct_complet,
                data=user_input
            )

        # Creează schema dinamic cu sectoare și puncte
        schema = vol.Schema({
            vol.Required("sector"): vol.In({
                "sector_1": "Sector 1",
                "sector_2": "Sector 2", 
                "sector_3": "Sector 3",
                "sector_4": "Sector 4",
                "sector_5": "Sector 5",
                "sector_6": "Sector 6"
            }),
            vol.Required("nume_punct"): str
        })

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "mesaj": "Selectează sectorul și introdu numele punctului termic"
            }
        )
