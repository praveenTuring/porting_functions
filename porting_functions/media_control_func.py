import json
import media_control

def port_media_control_db(source_json_str,db_suffix) -> None:
      # Load default DB
    with open("/content/DBs/MediaControlDefaultDB.json") as f:
        defaultdb = json.load(f)

    # Parse source JSON
    source_db = json.loads(source_json_str, strict=False)
    defaultdb['active_media_player'] = source_db.get('active_media_player')
    defaultdb['media_players'] = source_db.get('media_players', {})
    _output_path = f"/content/DBs/ported_db_{db_suffix}_media_control.json"
    with open(_output_path, "w") as f:
        json.dump(defaultdb, f, indent=2)
    media_control.SimulationEngine.db.load_state(_output_path)
