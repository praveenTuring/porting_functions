from datetime import datetime
import json
import clock 

def port_clock_db(source_json_str,db_suffix) -> None:
    """\n    Normalizes any vendor db dict so it matches the default db schema.\n    Schema is extracted dynamically from the provided default_db.\n    """

    with open("/content/DBs/ClockDefaultDB.json") as f:
      default_db = json.load(f)

    def build_template(structure):
        """\n        Recursively builds a template from the default DB's structure.\n        It strips actual example values but keeps type-compatible defaults.\n        """
        if isinstance(structure, dict):
            return {k: build_template(v) for k, v in structure.items()}
        elif isinstance(structure, list):
            if structure and isinstance(structure[0], dict):
                # Template for list of dicts → just one dict template
                return [build_template(structure[0])]
            else:
                # List of primitives
                return []
        else:
            # Convert example values to "empty" defaults based on type
            if isinstance(structure, str):
                return ""
            elif isinstance(structure, bool):
                return False
            elif isinstance(structure, (int, float)):
                return 0 if isinstance(structure, int) else 0.0
            else:
                return None

    def deep_merge(template, data):
        """\n        Recursively merges template and vendor data.\n        Vendor data overrides defaults, but missing keys get defaults.\n        """
        if isinstance(template, dict) and isinstance(data, dict):
            merged = {}
            for key in template:
                merged[key] = deep_merge(template[key], data.get(key, template[key]))
            return merged
        elif isinstance(template, list) and isinstance(data, list):
            if template and isinstance(template[0], dict):
                # Merge each dict in the list if applicable
                return [deep_merge(template[0], item) for item in data]
            else:
                return data
        else:
            return data if data is not None else template

    # Step 1: Build dynamic template from default DB
    schema_template = build_template(default_db)

    # Step 2: Merge defaults with vendor data
    normalized = deep_merge(schema_template, source_json_str)

    normalized_loaded = json.loads(normalized)
    for timer_id,timer in normalized_loaded.get("timers",{}).items():
        if timer.get("created_at"):
            timer["start_time"] = timer.get("start_time",timer.get("created_at"))
        else:
            timer["start_time"] = datetime.now().isoformat()



    out_path = f"/content/DBs/ClockPorted_{db_suffix}_DB.json"
    with open(out_path, "w") as f:
        json.dump(normalized_loaded, f, indent=2)
    clock.SimulationEngine.db.load_state(out_path)
