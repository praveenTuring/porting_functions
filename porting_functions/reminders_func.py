import json 
import generic_reminders

def port_generic_reminder_db(source_json_str,db_suffix) -> None:
    # Load the default DB's
    generic_reminders.SimulationEngine.db.load_state("/content/DBs/GenericRemindersDefaultDB.json")

    with open("/content/DBs/GenericRemindersDefaultDB.json") as f:
        default_db = json.load(f)
    source_db = json.loads(source_json_str, strict=False)
    source_keys = source_db.keys()
    default_keys = default_db.keys()
    if 'reminders' in source_keys:
        generic_reminders.SimulationEngine.db.DB['reminders'] = source_db.get ("reminders",[])
    if 'operations' in source_keys:
        generic_reminders.SimulationEngine.db.DB['operations'] = source_db.get ("operations",[])
    if 'counters' in source_keys:
        generic_reminders.SimulationEngine.db.DB['counters'] = source_db.get ("counters",[])
    if 'actions' in source_db.keys():
        generic_reminders.SimulationEngine.db.DB['actions'] = source_db.get ("actions",[])
    # Remove any key from default that doesn't exist in source
    for key in list(default_keys):  # make a list copy first
        if key not in source_keys:
            generic_reminders.SimulationEngine.db.DB[key].clear()
    # Save and reload
    out_path = f"/content/DBs/GenericReminders_ported_{db_suffix}_DB.json"
    generic_reminders.SimulationEngine.db.save_state(out_path)
    generic_reminders.SimulationEngine.db.load_state(out_path)
