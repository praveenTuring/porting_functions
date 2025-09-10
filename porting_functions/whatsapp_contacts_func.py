import whatsapp
import contacts

def port_db_whatsapp_and_contacts(port_contact_db, port_whatsapp_db,db_suffix) -> None:
    import re
    from datetime import datetime, timezone
    import uuid
    import json

    WHATSAPP_CONTACTS_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_DNS, "whatsapp_contacts")

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

    def normalize_date_formats(date_str):
        if not date_str:
            return date_str
        try:
            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except ValueError:
            dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
        return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # ================================
    # WHATSAPP DATA CONVERSION
    # ================================
    def convert_whatsapp_contacts(contacts_data, current_user_jid):
        """Convert old WhatsApp contacts format to new v0.1.0 format."""
        converted_contacts = {}

        for jid, contact in contacts_data.items():
            jid_full = f"{jid}@s.whatsapp.net"

            # Parse name components
            names = []
            if contact.get("name_in_address_book"):
                parts = contact["name_in_address_book"].split()
                given = parts[0]
                family = " ".join(parts[1:]) if len(parts) > 1 else ""
                # try to get the family from profile_name
                if not family and contact.get("profile_name"):
                    parts = contact["profile_name"].split()
                    family = " ".join(parts[1:]) if len(parts) > 1 else ""
                names.append({"givenName": given, "familyName": family})

            # Parse phone numbers
            phone_numbers = []
            if contact.get("phone_number"):
                normalized_number = normalize_phone(contact["phone_number"])
                if normalized_number:
                    phone_numbers.append(
                        {
                            "value": normalized_number,
                            "type": "mobile",
                            "primary": True,
                        }
                    )

            # Create new contact entry
            contact_entry = {
                "resourceName": f"people/{jid_full}",
                "etag": f"etag_{jid}",
                "names": names,
                "emailAddresses": [],
                "phoneNumbers": phone_numbers,
                "organizations": [],
                "whatsapp": {
                    "jid": jid_full,
                    "name_in_address_book": contact.get("name_in_address_book", "")
                    or "",
                    "profile_name": contact.get("profile_name", "") or "",
                    "phone_number": normalize_phone(contact.get("phone_number", ""))
                    or "",
                    "is_whatsapp_user": contact.get("is_whatsapp_user", False),
                },
            }

            converted_contacts[f"people/{jid_full}"] = contact_entry

        return converted_contacts

    def parse_jid(inp):
        return f"{inp}@s.whatsapp.net" if "@" not in inp else inp

    def parse_group_metadata(group_metadata):
        if not group_metadata:
            return None

        return {
            "group_description": group_metadata.get("group_description", ""),
            "creation_timestamp": normalize_date_formats(
                group_metadata.get("creation_timestamp", "")
            ),
            "owner_jid": parse_jid(group_metadata.get("owner_jid", "")),
            "participants_count": len(group_metadata.get("participants", []) or []),
            "participants": [
                {
                    "jid": parse_jid(participant.get("jid", "")),
                    "name_in_address_book": participant.get("name_in_address_book", ""),
                    "profile_name": participant.get("profile_name", ""),
                    "is_admin": participant.get("is_admin", False),
                }
                for participant in (group_metadata.get("participants") or [])
                if isinstance(participant, dict)
            ],
        }

    def convert_whatsapp_chats(chats_data, current_user_jid):
        """Convert old WhatsApp chats format to new v0.1.0 format."""
        converted_chats = {}

        for chat_id, chat in chats_data.items():
            suffix = "@g.us" if chat.get("is_group", False) else "@s.whatsapp.net"
            if "@" in chat_id:
                jid_full = chat_id.split("@", 1)[0] + suffix
            else:
                jid_full = chat_id + suffix

            # Convert messages
            messages = []
            for msg in chat["messages"]:
                converted_msg = {
                    "message_id": msg["message_id"],
                    "chat_jid": jid_full,
                    "sender_jid": f"{msg['sender_jid']}@s.whatsapp.net",
                    "sender_name": msg["sender_name"],
                    "timestamp": normalize_date_formats(msg["timestamp"]),
                    "text_content": msg["text_content"],
                    "is_outgoing": msg["sender_name"] == "Me",
                }

                # Handle quoted messages if present
                if "quoted_message_info" in msg:
                    converted_msg["quoted_message_info"] = {
                        "quoted_message_id": msg["quoted_message_info"][
                            "quoted_message_id"
                        ],
                        "quoted_sender_jid": f"{msg['quoted_message_info']['quoted_sender_jid']}@s.whatsapp.net",
                        "quoted_text_preview": msg["quoted_message_info"][
                            "quoted_text_preview"
                        ],
                    }

                messages.append(converted_msg)

            # Calculate last active timestamp
            last_active_timestamp = None
            if messages:
                try:
                    last_ts = max(
                        datetime.fromisoformat(m["timestamp"]) for m in chat["messages"]
                    )
                    last_active_timestamp = last_ts.isoformat()
                except Exception:
                    pass

            # Create new chat entry
            new_chat = {
                "chat_jid": jid_full,
                "name": chat.get("name", "") or "",
                "is_group": chat.get("is_group", False),
                "last_active_timestamp": normalize_date_formats(last_active_timestamp),
                "unread_count": 0,
                "is_archived": chat.get("is_archived", False),
                "is_pinned": chat.get("is_pinned", False),
                "is_muted_until": chat.get("is_muted_until", ""),
                "group_metadata": parse_group_metadata(chat.get("group_metadata", {})),
                "messages": messages,
            }

            converted_chats[jid_full] = new_chat

        return converted_chats

    def parse_whatsapp_data(whatsapp_data):
        """Main function to parse old WhatsApp data to new format."""
        current_user_jid = parse_jid(
            whatsapp_data.get("current_user_jid", list(whatsapp_data.keys())[0])
        )

        contacts = convert_whatsapp_contacts(
            whatsapp_data.get("contacts", {}), current_user_jid
        )
        chats = convert_whatsapp_chats(whatsapp_data.get("chats", {}), current_user_jid)

        return current_user_jid, contacts, chats

    # ================================
    # CONTACTS DATA CONVERSION
    # ================================
    get_full_name = lambda x: (
        (
            x.get("names", [{}])[0].get("givenName", "")
            + " "
            + x.get("names", [{}])[0].get("familyName", "")
        ).strip()
        if x.get("names")
        else ""
    )

    def merge_whatsapp_contacts(whatsapp_contacts, contacts):
        """Merge WhatsApp contacts into existing contacts without losing data."""

        for resource_name, wa_contact in whatsapp_contacts.items():
            wa_phone = normalize_phone(wa_contact["whatsapp"].get("phone_number"))
            wa_phone_str = (
                wa_phone.lstrip("1") if wa_phone.startswith("1") else wa_phone
            )
            wa_phone_str = (
                wa_phone.lstrip("+") if wa_phone.startswith("+") else wa_phone
            )
            wa_contact_name = get_full_name(wa_contact)
            wa_profile_name = wa_contact["whatsapp"]["name_in_address_book"]
            wa_address_name = wa_contact["whatsapp"]["profile_name"]
            contact_resources = [
                (x["whatsapp"]["jid"], x["resourceName"], get_full_name(x))
                for x in contacts.values()
            ]
            matching_contacts = list(
                (
                    (x[1], x[0])
                    for x in contact_resources
                    if wa_phone_str in x[0]
                    or wa_contact_name in x[2]
                    or wa_profile_name in x[2]
                    or wa_address_name in x[2]
                )
            )

            if len(matching_contacts) > 1:
                # if the matching contacts are greater than 1
                # we have to pick the right contact based on number contact may be same for a user but not the number
                contact_exist = next(
                    (x[0] for x in matching_contacts if wa_phone_str in x[1]), None
                )
                if not contact_exist:
                    contact_exist = next(
                        (
                            x[1]
                            for x in contact_resources
                            if wa_phone_str in x[0]
                            or wa_contact_name in x[2]
                            or wa_profile_name in x[2]
                            or wa_address_name in x[2]
                        ),
                        None,
                    )
            else:
                contact_exist = next(
                    (
                        x[1]
                        for x in contact_resources
                        if wa_phone_str in x[0]
                        or wa_contact_name in x[2]
                        or wa_profile_name in x[2]
                        or wa_address_name in x[2]
                    ),
                    None,
                )
            # check if there are more than one contact matching

            # print(contact_exist,wa_contact_name,wa_profile_name,contact_resources)
            if contact_exist or resource_name in contacts:
                contact = contacts[contact_exist or resource_name]

                contact.setdefault("phoneNumbers", [])
                if wa_phone and all(
                    normalize_phone(p.get("value")) != wa_phone
                    for p in contact["phoneNumbers"]
                ):
                    contact["phoneNumbers"].append(
                        {
                            "value": wa_phone,  # normalized value
                            "type": "whatsapp",
                            "primary": True,
                        }
                    )
                contact["whatsapp"] = wa_contact["whatsapp"]
                contact["whatsapp"]["is_whatsapp_user"] = True

            else:
                wa_contact["whatsapp"]["is_whatsapp_user"] = True
                contacts[resource_name] = wa_contact
        return contacts

    def parse_contacts_data(contacts_data, whatsapp_contacts):
        parsed_contacts = {}

        phone_to_wa_res = {
            normalize_phone(phone.get("value")): res
            for res, wa in whatsapp_contacts.items()
            for phone in wa.get("phoneNumbers", [])
        }

        for _, contact in contacts_data.items():
            names = contact.get("names", [])
            contact_name = (
                f"{names[0].get('givenName', '')} {names[0].get('familyName', '')}".strip()
                if names
                else ""
            )
            # there should be a phone number for contact
            org_phone_number = (
                contact["phoneNumbers"][0]["value"] if "phoneNumbers" in contact else ""
            )
            phone_number = normalize_phone(org_phone_number)

            # Normalize all phone numbers inside contact
            normalized_phone_numbers = []
            for p in contact.get("phoneNumbers", []):
                val = normalize_phone(p.get("value"))
                if val:
                    normalized_phone_numbers.append(
                        {
                            "value": val,
                            "type": p.get("type", ""),
                            "primary": p.get("primary", False),
                        }
                    )

            if not org_phone_number:
                # we create resource name based on contact resourceName
                resource_uuid = uuid.uuid5(
                    namespace=WHATSAPP_CONTACTS_NAMESPACE, name=contact["resourceName"]
                )
                resource_name = f"people/{resource_uuid}"
            elif phone_number in phone_to_wa_res:
                resource_name = phone_to_wa_res[phone_number]
            else:
                resource_uuid = uuid.uuid5(
                    namespace=WHATSAPP_CONTACTS_NAMESPACE, name=phone_number
                )
                resource_name = f"people/{resource_uuid}"

            parsed_contacts[resource_name] = {
                "resourceName": resource_name,
                "etag": str(
                    uuid.uuid5(
                        namespace=WHATSAPP_CONTACTS_NAMESPACE, name=resource_name
                    )
                ),
                "names": names,
                "emailAddresses": contact.get("emailAddresses", []),
                "phoneNumbers": normalized_phone_numbers,
                "organizations": contact.get("organizations", []),
                "addresses": contact.get("addresses", []) or [],
                "notes": contact.get("notes", ""),
                "phone": {
                    "contact_id": resource_name.split("/")[-1],
                    "contact_name": contact_name or "",
                    "contact_photo_url": None,
                    "contact_endpoints": [
                        {
                            "endpoint_type": "PHONE_NUMBER",
                            "endpoint_value": normalize_phone(p.get("value", "")),
                            "endpoint_label": p.get("type", ""),
                        }
                        for p in contact.get("phoneNumbers", [])
                    ],
                },
                "whatsapp": {
                    "jid": f"{phone_number}@s.whatsapp.net" if phone_number else "",
                    "name_in_address_book": contact_name or "",
                    "profile_name": contact_name or "",
                    "phone_number": phone_number or "",
                    "is_whatsapp_user": phone_number in phone_to_wa_res,
                },
            }

        return merge_whatsapp_contacts(whatsapp_contacts, parsed_contacts)

    # Parse JSON data
    whatsapp_data = json.loads(port_whatsapp_db)
    contact_data = json.loads(port_contact_db)
    # Convert WhatsApp data
    (
        current_user_jid,
        parsed_whatsapp_contacts,
        parsed_whatsapp_chats,
    ) = parse_whatsapp_data(whatsapp_data)

    # Convert contacts data
    parsed_contacts = parse_contacts_data(contact_data, parsed_whatsapp_contacts)

    # Update WhatsApp database
    whatsapp.SimulationEngine.db.DB["current_user_jid"] = current_user_jid
    whatsapp.SimulationEngine.db.DB["contacts"] = parsed_whatsapp_contacts
    whatsapp.SimulationEngine.db.DB["chats"] = parsed_whatsapp_chats

    # Update contacts database
    contacts.SimulationEngine.db.DB["myContacts"] = parsed_contacts
    contacts.SimulationEngine.db.DB["directory"] = contact_data.get("directory",{})
    contacts.SimulationEngine.db.DB["otherContacts"] = contact_data.get("otherContacts",{})

    # Save and reload databases
    contacts.SimulationEngine.db.save_state(
        f"/content/DBs/ported_db_{db_suffix}_contacts.json"
    )
    contacts.SimulationEngine.db.load_state(
        f"/content/DBs/ported_db_{db_suffix}_contacts.json"
    )
    whatsapp.SimulationEngine.db.save_state(
        f"/content/DBs/ported_db_{db_suffix}_whatsapp.json"
    )
    whatsapp.SimulationEngine.db.load_state(
        f"/content/DBs/ported_db_initial_{db_suffix}_whatsapp.json"
    )
