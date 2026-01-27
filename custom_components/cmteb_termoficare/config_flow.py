"""Config flow for CMTEB Termoficare."""
import voluptuous as vol
from homeassistant import config_entries

from .const import DOMAIN


class CMTEBConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for CMTEB Termoficare."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        if user_input is not None:
            # Validare simplă
            if user_input["adresa"] and user_input["punct_termic"]:
                unique_id = f"cmteb_{user_input['adresa'].strip().lower().replace(' ', '_')}"
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()
                
                return self.async_create_entry(
                    title=f"CMTEB {user_input['adresa']}",
                    data=user_input,
                )
            else:
                return self.async_show_form(
                    step_id="user",
                    data_schema=vol.Schema({
                        vol.Required("adresa"): str,
                        vol.Required("punct_termic"): str,
                    }),
                    errors={"base": "all_fields_required"},
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("adresa"): str,
                vol.Required("punct_termic"): str,
            }),
        )
