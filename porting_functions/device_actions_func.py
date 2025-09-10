import json
from datetime import datetime, timezone
import device_actions

def port_device_actions_db(source_json_str: str,db_suffix) -> None:


    with open("/content/DBs/DeviceActionsDefaultDB.json", "r") as f:
        template_db = json.load(f)

    source_db = json.loads(source_json_str, strict=False)

    def normalize_media_list(src_list):
        normalized = []
        for item in src_list:
            name = item.get("name") if isinstance(item, dict) else str(item)
            normalized.append({
                "name": name,
                "created_at": datetime.now(timezone.utc).isoformat()
            })
        return normalized

    ported_db = {}

    for key, template_val in template_db.items():
        if key not in source_db:
            ported_db[key] = [] if isinstance(template_val, list) else {} if isinstance(template_val, dict) else None
            continue

        if key == "phone_state":
            ported_db[key] = {}
            src_phone_state = source_db.get(key, {})

            for ps_key, ps_template_val in template_val.items():
                if ps_key not in src_phone_state:
                    ported_db[key][ps_key] = [] if isinstance(ps_template_val, list) else {} if isinstance(ps_template_val, dict) else None
                    continue

                if ps_key == "installed_apps":
                    ported_apps = []
                    app_template = ps_template_val[0] if ps_template_val else {}

                    for src_app in src_phone_state.get(ps_key, []):
                        new_app = {}
                        for field in app_template.keys():
                            new_app[field] = src_app.get(field, False if field in ["is_default", "is_system_app"] else None)
                        ported_apps.append(new_app)

                    ported_db[key][ps_key] = ported_apps

                elif ps_key in ["photos", "videos", "screenshots"]:
                    ported_db[key][ps_key] = normalize_media_list(src_phone_state.get(ps_key, []))

                elif isinstance(ps_template_val, dict):
                    new_dict = {}
                    for field in ps_template_val.keys():
                        new_dict[field] = src_phone_state[ps_key].get(field, None)
                    ported_db[key][ps_key] = new_dict

                else:
                    ported_db[key][ps_key] = src_phone_state[ps_key]

        else:
            ported_db[key] = source_db[key]

    # Save ported DB
    _output_path = f'/content/DBs/DeviceActionsPorted_{db_suffix}_DB.json'
    with open(_output_path, "w") as f:
        json.dump(ported_db, f, indent=2)

    device_actions.SimulationEngine.db.load_state(_output_path)
