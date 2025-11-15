import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback

class CmtebConfigFlow(config_entries.ConfigFlow, domain="cmteb"):
    """Handle a config flow for CMTEB."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            return self.async_create_entry(
                title=user_input["nume_punct"],
                data=user_input
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("nume_punct"): str,
                vol.Required("id_punct"): str
            }),
            errors=errors
        )
