import re
import uuid
import json
import contacts

def port_db_contacts(port_contact_db,db_suffix) -> None:
    def normalize_phone(phone: str) -> str:
        if not phone:
            return ""

        original = str(phone).strip()

        has_plus = original.startswith("+")
        if original.startswith("00"):
            original = original[2:]
        elif original.startswith("011"):
            original = original[3:]

        digits = re.sub(r"\D", "", original)
        if not digits:
            return ""

        if has_plus:
            return f"+{digits}"
        return digits

    CONTACTS_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_DNS, "contacts")

    port_contact_db = json.loads(port_contact_db)
    contacts.SimulationEngine.db.DB["myContacts"] = {}

    for key, contact in port_contact_db.items():
        normalized_phone_numbers = []
        for phone_entry in contact.get("phoneNumbers", []):
            value = phone_entry.get("value", "")
            normalized_value = normalize_phone(value)
            if normalized_value:
                normalized_phone_numbers.append(
                    {
                        "value": normalized_value,
                        "type": phone_entry.get("type", ""),
                        "primary": phone_entry.get("primary", None),
                    }
                )

        first_phone = (
            normalized_phone_numbers[0]["value"] if normalized_phone_numbers else ""
        )
        email = contact.get("emailAddresses", [{}])[0].get("value", "")
        givenName = contact.get("names", [{}])[0].get("givenName", "")

        if first_phone:
            resource_uuid = uuid.uuid5(CONTACTS_NAMESPACE, first_phone)
        elif email:
            resource_uuid = uuid.uuid5(CONTACTS_NAMESPACE, email)
        else:
            resource_uuid = uuid.uuid5(CONTACTS_NAMESPACE, givenName)

        resource_name = f"people/{resource_uuid}"

        entry = {
            "resourceName": resource_name,
            "etag": str(uuid.uuid5(CONTACTS_NAMESPACE, resource_name)),
            "names": contact.get("names", []),
            "emailAddresses": contact.get("emailAddresses", []),
            "phoneNumbers": normalized_phone_numbers,
            "organizations": contact.get("organizations", []),
            "directory": contact.get("directory", []),
            "notes": contact.get("notes", ""),
        }

        contacts.SimulationEngine.db.DB["myContacts"][resource_name] = entry

    contacts.SimulationEngine.db.DB["otherContacts"] = port_contact_db.get(
        "otherContacts", {}
    )
    contacts.SimulationEngine.db.DB["directory"] = port_contact_db.get("directory", {})

    contacts.SimulationEngine.db.save_state(f"/content/DBs/ported_db_{db_suffix}_contacts.json")
    contacts.SimulationEngine.db.load_state(f"/content/DBs/ported_db_{db_suffix}_contacts.json")
