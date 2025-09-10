import re
import uuid
import json
from datetime import datetime
import phone


def port_phone_db(phone_db_str: str, contacts_db_str: str,db_suffix) -> None:

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

    # Load inputs
    received_json = json.loads(phone_db_str)
    contacts_db = json.loads(contacts_db_str)

    final_json = {
        "contacts": {},
        "businesses": {},
        "special_contacts": {},
        "call_history": {},
        "prepared_calls": {},
        "recipient_choices": {},
        "not_found_records": {}
    }

    # --- Step 1: Convert contacts
    phone_to_contact = {}
    for key, contact in contacts_db.items():
        normalized_numbers = []
        for phone_entry in contact.get("phoneNumbers", []):
            norm_value = normalize_phone(phone_entry.get("value", ""))
            if norm_value:
                normalized_numbers.append({
                    "value": norm_value,
                    "type": phone_entry.get("type", ""),
                    "primary": phone_entry.get("primary", False)
                })
                phone_to_contact[norm_value] = contact

        first_phone = normalized_numbers[0]["value"] if normalized_numbers else ""
        givenName = contact.get("names", [{}])[0].get("givenName", "")
        familyName = contact.get("names", [{}])[0].get("familyName", "")

        if first_phone:
            resource_uuid = uuid.uuid5(CONTACTS_NAMESPACE, first_phone)
        else:
            resource_uuid = uuid.uuid5(CONTACTS_NAMESPACE, givenName + familyName)

        resource_name = f"people/{resource_uuid}"

        entry = {
            "resourceName": resource_name,
            "etag": str(uuid.uuid5(CONTACTS_NAMESPACE, resource_name)),
            "names": contact.get("names", []),
            "emailAddresses": contact.get("emailAddresses", []),
            "phoneNumbers": normalized_numbers,
            "organizations": contact.get("organizations", []),
            "notes": contact.get("notes", ""),
            "phone": {
                "contact_id": resource_name.split("/")[-1],
                "contact_name": f"{givenName} {familyName}".strip(),
                "recipient_type": "CONTACT",
                "contact_photo_url": None,
                "contact_endpoints": [
                    {
                        "endpoint_type": "PHONE_NUMBER",
                        "endpoint_value": num["value"],
                        "endpoint_label": num.get("type", "")
                    }
                    for num in normalized_numbers
                ]
            }
        }

        final_json["contacts"][resource_name] = entry

    # --- Step 2: Convert call_history
    for call_id, call in received_json.get("call_history", {}).items():
        # Convert timestamp string -> float epoch
        try:
            dt = datetime.strptime(call["timestamp"], "%Y-%m-%dT%H-%M-%S")
            epoch_time = dt.timestamp()
        except Exception:
            epoch_time = None

        phone_number = normalize_phone(call["phone_number"])
        recipient_contact = phone_to_contact.get(phone_number)
        if recipient_contact:
            recipient_name = f"{recipient_contact['names'][0].get('givenName','')} {recipient_contact['names'][0].get('familyName','')}".strip()
            recipient_photo_url = None
        else:
            recipient_name = call.get("recipient_name", "")
            recipient_photo_url = None

        final_json["call_history"][call_id] = {
            "call_id": call["call_id"],
            "timestamp": epoch_time,
            "phone_number": phone_number,
            "recipient_name": recipient_name,
            "recipient_photo_url": recipient_photo_url,
            "on_speakerphone": call.get("on_speakerphone", False),
            "status": call.get("status", "unknown")
        }

    # Write the ported DB
    _output_path = f"/content/DBs/PhonePorted_{db_suffix}_DB.json"
    with open(_output_path, "w") as f:
        json.dump(final_json, f, indent=2)

    phone.SimulationEngine.db.load_state(_output_path)
