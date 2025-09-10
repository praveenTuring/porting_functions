from datetime import datetime
import json
import gmail

def port_gmail_db(source_json_str,db_suffix) -> None:
    def convert_datetime_with_tz(date_str, tz_str):
        utc_dt = datetime.fromisoformat(date_str)
        return utc_dt.strftime("%Y-%m-%dT%H:%M:%SZ"), str(int(utc_dt.timestamp()))

    def transform_email_entry(entry):
        utc_date, epoch = convert_datetime_with_tz(entry['date'], entry['timeZone'])

        headers = [
            {"name": "From", "value": entry.get("sender", "")},
            {"name": "To", "value": ", ".join(entry.get("recipients", []))},
            {"name": "Subject", "value": entry.get("subject", "")},
            {"name": "Date", "value": utc_date}
        ]

        raw = f"Subject: {entry.get('subject', '')}\n\n{entry.get('body', '')}"

        return {
            "id": entry["id"],
            "threadId": entry.get("threadId", ""),
            "raw": raw,
            "sender": entry.get("sender", ""),
            "recipient": ", ".join(entry.get("recipients", [])),
            "subject": entry.get("subject", ""),
            "body": entry.get("body", ""),
            "date": utc_date,
            "internalDate": epoch,
            "isRead": entry.get("isRead", False),
            "labelIds": entry.get("labelIds", []),
            "payload": {
                "mimeType": "text/plain",
                "parts": [
                    {
                        "mimeType": "text/plain",
                        "body": {"data": entry.get("body", "")}
                    }
                ],
                "headers": headers
            }
        }

    def normalize_labels(label_list):
      labels_dict = {}
      system_labels = {
          "INBOX": {"id": "INBOX", "name": "Inbox", "type": "system",
                    "labelListVisibility": "labelShow", "messageListVisibility": "show"},
          "UNREAD": {"id": "UNREAD", "name": "Unread", "type": "system",
                    "labelListVisibility": "labelShow", "messageListVisibility": "show"},
          "IMPORTANT": {"id": "IMPORTANT", "name": "Important", "type": "system",
                        "labelListVisibility": "labelShow", "messageListVisibility": "show"},
          "SENT": {"id": "SENT", "name": "Sent", "type": "system",
                  "labelListVisibility": "labelHide", "messageListVisibility": "hide"},
          "DRAFT": {"id": "DRAFT", "name": "Draft", "type": "system",
                    "labelListVisibility": "labelHide", "messageListVisibility": "hide"},
          "TRASH": {"id": "TRASH", "name": "Trash", "type": "system",
                    "labelListVisibility": "labelHide", "messageListVisibility": "hide"},
          "SPAM": {"id": "SPAM", "name": "Spam", "type": "system",
                  "labelListVisibility": "labelHide", "messageListVisibility": "hide"}
      }

      # Add system labels first
      labels_dict.update(system_labels)

      # Add custom labels from input list
      for label_name in label_list:
          if label_name not in labels_dict:  # Avoid overwriting system ones
              labels_dict[label_name.upper().replace(" ", "_")] = {
                  "id": label_name.upper().replace(" ", "_"),
                  "name": label_name,
                  "type": "user",
                  'labelListVisibility': 'labelHide',
                  'messageListVisibility': 'hide'
              }
      return labels_dict


    with open("/content/DBs/GmailDefaultDB.json") as f:
        defaultdb = json.load(f)

    source_db = json.loads(source_json_str, strict=False)

    defaultdb['users'] = {'me': {}}
    me = defaultdb['users']['me']
    me['profile'] = source_db.get('profile', {})
    me['messages'] = {}
    me['drafts'] = {}
    me['threads'] = source_db.get('threads', {})
    me['labels'] = normalize_labels(source_db.get('labels', []))
    me['history'] = source_db.get('history', [])
    me['watch'] = source_db.get('watch', {})
    me['vacation'] = source_db.get("settings", {}).get("vacation", {"enableAutoReply": False, "responseBodyPlainText": ""})
    me['autoForwarding'] = source_db.get("settings", {}).get("autoForwarding", {"enabled": False})

    for msg_id, msg_data in source_db.get('messages', {}).items():
        me['messages'][msg_id] = transform_email_entry(msg_data)

    for draft_id, draft_data in source_db.get('drafts', {}).items():
        if "message" in draft_data:
            me['drafts'][draft_id] = {
                "id": draft_data["id"],
                "message": transform_email_entry(draft_data["message"])
            }
        else:
            me['drafts'][draft_id] = {
                "id": draft_data["id"],
                "message": transform_email_entry(draft_data)
            }

    defaultdb['attachments'] = source_db.get('attachments', {})

    email = me['profile'].get('emailAddress')
    me['settings'] = {
        "imap": source_db.get("settings", {}).get("imap", {"enabled": True, "server": "imap.gmail.com", "port": 993}),
        "pop": source_db.get("settings", {}).get("pop", {"enabled": False, "server": "pop.gmail.com", "port": 995}),
        "vacation": me['vacation'],
        "language": source_db.get("settings", {}).get("language", {"displayLanguage": "en-US"}),
        "autoForwarding": me['autoForwarding'],
        "sendAs": source_db.get("settings", {}).get("sendAs", {
            email: {
                "sendAsEmail": email,
                "displayName": email.split('@')[0].title(),
                "replyToAddress": email,
                "signature": "Regards,\n" + email.split('@')[0].title(),
                "verificationStatus": "accepted",
                "smimeInfo": {
                    "smime_mock_1": {
                        "id": "smime_mock_1",
                        "encryptedKey": "mock_encrypted_key",
                        "default": True
                    }
                }
            }
        })
    }

    defaultdb['counters'] = {
        "message": len(me['messages']),
        "thread": len(me['threads']),
        "draft": len(me['drafts']),
        "label": len(me['labels']),
        "history": len(me['history']),
        "attachment": len(defaultdb.get('attachments', {})),
        "smime": sum(len(info.get("smimeInfo", {})) for info in me['settings']['sendAs'].values())
    }

    with open(f"/content/DBs/ported_db_{db_suffix}_gmail.json", "w") as f:
        json.dump(defaultdb, f, indent=2)

    gmail.SimulationEngine.db.load_state(f"/content/DBs/ported_db_{db_suffix}_gmail.json")
