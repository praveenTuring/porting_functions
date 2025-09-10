import json
from datetime import datetime, timedelta, timezone
import generic_media

def port_generic_media_db(source_json_str: str,db_suffix) -> None:


    # Known provider URLs
    PROVIDER_URLS = {
        "Apple Music": "https://music.apple.com",
        "Spotify": "https://spotify.com",
        "Deezer": "https://www.deezer.com",
        "Amazon Music": "https://music.amazon.com",
        "SoundCloud": "https://soundcloud.com"
    }

    def string_to_iso_datetime(s: str) -> str:
        num = sum((i+1) * ord(c) for i, c in enumerate(s))
        base = datetime(2000, 1, 1, tzinfo=timezone.utc)
        dt = base + timedelta(seconds=num % (60*60*24*365*30))
        return dt.isoformat()

    with open("/content/DBs/GenericMediaDefaultDB.json", "r") as f:
        template_db = json.load(f)

    source_db = json.loads(source_json_str, strict=False)

    ported_db = {}

    for key, template_val in template_db.items():
        if key not in source_db:
            ported_db[key] = [] if isinstance(template_val, list) else {} if isinstance(template_val, dict) else None
            continue

        if key == "providers":
            ported_db[key] = []
            provider_template = template_val[0] if template_val else {}

            for src_provider in source_db.get(key, []):
                new_provider = {}
                name = src_provider.get("name", "")
                for field in provider_template.keys():
                    if field == "base_url":
                        new_provider[field] = PROVIDER_URLS.get(name, f"https://{name.replace(' ', '').lower()}.com")
                    else:
                        new_provider[field] = src_provider.get(field, None)
                ported_db[key].append(new_provider)

        elif isinstance(template_val, list) and template_val and isinstance(template_val[0], dict):
            ported_list = []
            template_item = template_val[0]

            if key == "tracks":
                for idx, src_item in enumerate(source_db[key], start=1):
                    new_item = {}
                    for field in template_item.keys():
                        if field in src_item:
                            new_item[field] = src_item[field]
                        else:
                            if field == "rank":
                                new_item[field] = idx
                            elif field == "release_timestamp":
                                title = src_item.get("title", f"track_{idx}")
                                new_item[field] = string_to_iso_datetime(title)
                            elif field == "is_liked":
                                new_item[field] = False
                            else:
                                new_item[field] = None
                    ported_list.append(new_item)

            elif key == "podcasts":
                for src_item in source_db[key]:
                    new_item = {}
                    for field in template_item.keys():
                        if field == "episodes":
                            new_item["episodes"] = []
                            episode_template = template_item["episodes"][0] if template_item.get("episodes") else {}
                            for ep in src_item.get("episodes", []):
                                new_ep = {f: ep.get(f, None) for f in episode_template.keys()}
                                new_item["episodes"].append(new_ep)
                        else:
                            new_item[field] = src_item.get(field, None)
                    ported_list.append(new_item)

            else:
                for src_item in source_db[key]:
                    new_item = {f: src_item.get(f, None) for f in template_item.keys()}
                    ported_list.append(new_item)

            ported_db[key] = ported_list

        else:
            ported_db[key] = source_db[key]

    # --- Generate Artists from Tracks & Albums ---
    def generate_artists(ported_db):
        artist_dict = {}  # (artist_name, provider) -> id
        artists = []
        counter = 1

        # from tracks
        for track in ported_db.get("tracks", []):
            name = track.get("artist_name")
            provider = track.get("provider", "unknown")
            if name and (name, provider) not in artist_dict:
                artist_id = f"artist_{counter}"
                counter += 1
                artist_dict[(name, provider)] = artist_id
                artists.append({
                    "id": artist_id,
                    "name": name,
                    "provider": provider,
                    "content_type": "ARTIST"
                })

        # from albums
        for album in ported_db.get("albums", []):
            name = album.get("artist_name")
            provider = album.get("provider", "unknown")
            if name and (name, provider) not in artist_dict:
                artist_id = f"artist_{counter}"
                counter += 1
                artist_dict[(name, provider)] = artist_id
                artists.append({
                    "id": artist_id,
                    "name": name,
                    "provider": provider,
                    "content_type": "ARTIST"
                })

        ported_db["artists"] = artists

    generate_artists(ported_db)

    # Save final DB
    _output_path = f'/content/DBs/GenericMediaPorted_{db_suffix}_DB.json'
    with open(_output_path, "w") as f:
        json.dump(ported_db, f, indent=2)

    generic_media.SimulationEngine.db.load_state(_output_path)
