import json
import google_home

def port_google_home_db(source_json_str: str,db_suffix) -> None:


    with open("/content/DBs/GoogleHomeDefaultDB.json") as f:
        template_db = json.load(f)

    source_db = json.loads(source_json_str, strict=False)

    structure_keys = list(source_db.get("structures", {}).keys())
    if not structure_keys:
        raise ValueError("No structures found in source JSON")
    struct_key = structure_keys[0]

    source_structure = source_db["structures"][struct_key]

    ported_db = {
        "structures": {
            struct_key: {
                "name": source_structure.get("name", struct_key),
                "rooms": {}
            }
        }
    }

    for room_name, room_data in source_structure.get("rooms", {}).items():
        ported_db["structures"][struct_key]["rooms"][room_name] = {
            "name": room_name,
            "devices": {}
        }

        for dev_type, dev_list in room_data["devices"].items():
            ported_db["structures"][struct_key]["rooms"][room_name]["devices"][dev_type] = []

            for device in dev_list:
                dev_template = (
                    template_db["structures"].get(struct_key, {})
                    .get("rooms", {})
                    .get(room_name, {})
                    .get("devices", {})
                    .get(dev_type, [{}])[0]
                )

                new_device = dict(device)

                new_device["device_state"] = []
                for state in device.get("device_state", []):
                    if state["name"] == "off":
                        continue
                    new_device["device_state"].append(state)

                for field, default_val in dev_template.items():
                    if field not in new_device:
                        new_device[field] = default_val

                ported_db["structures"][struct_key]["rooms"][room_name]["devices"][dev_type].append(new_device)
    _output_path = f"/content/DBs/GoogleHomePorted_{db_suffix}_DB.json"
    with open(_output_path, "w") as f:
        json.dump(ported_db, f, indent=2)

    google_home.SimulationEngine.db.load_state(_output_path)
