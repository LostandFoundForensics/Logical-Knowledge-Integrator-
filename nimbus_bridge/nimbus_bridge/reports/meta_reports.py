from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict


def write_meta_reports(*, case_root: Path, import_id: str, parse_result: Dict[str, Any]) -> Dict[str, str]:
    out_dir = case_root / "exports" / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)

    parse_json = out_dir / f"meta_parse_{import_id}.json"
    mapping_json = out_dir / f"meta_mapping_{import_id}.json"
    gaps_json = out_dir / f"meta_gaps_{import_id}.json"

    parse_json.write_text(json.dumps(parse_result, indent=2, ensure_ascii=False, default=str), encoding="utf-8")

    mapping = {
        "provider": "meta_dyi",
        "notes": [
            "Nimbus Bridge imports user-provided exports only; no account access occurred.",
            "Epoch milliseconds may be converted to UTC when explicitly present (observed transformation).",
            "No inference is performed (no delivery, no read receipts, no intent).",
        ],
        "mappings": {
            "messages": {
                "sender_name/raw": "artifact_message.from_raw",
                "timestamp_ms/raw": "artifact_message.date_raw",
                "timestamp_ms->utc": "artifact_message.timestamp_parsed_utc (when enabled and ms is int)",
                "content/raw": "artifact_message.body_text",
                "thread/title": "artifact_message.subject_raw or thread_hint",
            },
            "security": {
                "timestamp/raw": "artifact_event.dtstart_raw",
                "location/raw": "artifact_event.location_raw",
            },
            "contacts": {
                "name/raw": "artifact_contact.display_name",
                "record/raw": "artifact_contact.raw_fields",
            },
            "media": {"file evidence": "artifact_file (catalog only; no content interpretation)"},
        },
    }
    mapping_json.write_text(json.dumps(mapping, indent=2, ensure_ascii=False), encoding="utf-8")

    gaps = {
        "provider": "meta_dyi",
        "import_id": import_id,
        "gaps": parse_result.get("gaps", []),
        "fixed_non_claims": [
            "This export does not establish delivery, deletion, authorship, or account control beyond provided records.",
            "Message order reflects export structure and may not reflect send/receive order.",
            "Reactions/metadata do not prove viewing.",
        ],
    }
    gaps_json.write_text(json.dumps(gaps, indent=2, ensure_ascii=False), encoding="utf-8")

    return {
        "meta_parse_json": str(parse_json),
        "meta_mapping_json": str(mapping_json),
        "meta_gaps_json": str(gaps_json),
    }
