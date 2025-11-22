"""Config flow for CMTEB Termoficare."""
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN

class CmtebConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for CMTEB Termoficare."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            # Validate the input
            if not user_input.get("adresa"):
                errors["base"] = "adresa_required"
            else:
                # Create unique ID
                unique_id = f"cmteb_{user_input['adresa'].lower().replace(' ', '_')}"
                
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=f"CMTEB {user_input['adresa']}",
                    data=user_input
                )

        # Define the form schema
        data_schema = vol.Schema({
            vol.Required("adresa"): cv.string,
            vol.Optional("punct_termic"): cv.string,
        })

        return self.async_show_form(
            step_id="user", 
            data_schema=data_schema, 
            errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return CmtebOptionsFlow(config_entry)

class CmtebOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for CMTEB Termoficare."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required(
                    "adresa",
                    default=self.config_entry.options.get("adresa", self.config_entry.data.get("adresa", ""))
                ): cv.string,
                vol.Optional(
                    "punct_termic", 
                    default=self.config_entry.options.get("punct_termic", self.config_entry.data.get("punct_termic", ""))
                ): cv.string,
            })
        )
