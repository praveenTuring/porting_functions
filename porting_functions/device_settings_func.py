# Load default DB
import json
import device_setting

def port_device_setting_db(source_json_str,db_suffix) -> None:

    with open("/content/DBs/DeviceSettingDefaultDB.json") as f:
        defaultdb = json.load(f)

    # Parse source JSON
    source_db = json.loads(source_json_str, strict=False)
    defaultdb['device_settings'] = source_db.get('device_settings',{})
    defaultdb['installed_apps'] = source_db.get('installed_apps', {})
    defaultdb['device_insights'] = source_db.get('device_insights', {})



        # Save output DB
    _output_path = f"/content/DBs/ported_db_{db_suffix}_device_settings.json"
    with open(_output_path, "w") as f:
        json.dump(defaultdb, f, indent=2)
    device_setting.SimulationEngine.db.load_state(_output_path)


