if user_input is not None:
    errors = {}
    if not user_input.get("adresa"):
        errors["adresa"] = "adresa_required"
    if not user_input.get("punct_termic"):
        errors["punct_termic"] = "punct_termic_required"

    if not errors:
        unique_id = f"cmteb_{user_input['adresa'].lower().replace(' ', '_')}"
        await self.async_set_unique_id(unique_id)
        self._abort_if_unique_id_configured()
        return self.async_create_entry(
            title=f"CMTEB {user_input['adresa']}",
            data=user_input,
        )

return self.async_show_form(
    step_id="user",
    data_schema=data_schema,
    errors=errors,
)
