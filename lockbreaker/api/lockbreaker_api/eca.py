from __future__ import annotations
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional


def suggest_context(evidence: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Analyzes evidence metadata and produces examiner-confirmable context suggestions.
    All suggestions require examiner confirmation before reaching AKE.
    No suggestion is acted on automatically.
    """
    suggestions: List[Dict[str, Any]] = []
    filename = (evidence.get("filename") or "").lower()
    storage_uri = (evidence.get("storage_uri") or "").lower()
    combined = f"{filename} {storage_uri}"

    # ── Owner name inference ──────────────────────────────────────────────────
    name_patterns = [
        r"(?:iphone|ipad|backup|device)[-_\s]+([a-z]{3,20})",
        r"([a-z]{3,20})(?:s?[-_\s]+iphone|s?[-_\s]+ipad|s?[-_\s]+backup)",
        r"([a-z]{3,20})[-_](?:phone|device|mobile)",
    ]
    for pat in name_patterns:
        m = re.search(pat, combined)
        if m:
            candidate = m.group(1).title()
            if candidate.lower() not in ("iphone", "ipad", "backup", "device", "mobile"):
                suggestions.append({
                    "suggestion_id": "CTX-NAME-01",
                    "category": "identity",
                    "label": "Possible Owner Name",
                    "suggested_value": candidate,
                    "confidence": 0.72,
                    "source": "filename",
                    "explanation": f"Extracted from filename/path: '{filename}'",
                    "default_action": "confirm",
                    "examiner_action": "pending",
                })
            break

    # ── Locale inference ──────────────────────────────────────────────────────
    tz = evidence.get("timezone", "")
    if tz:
        locale_map = {
            "America": "en-US",
            "US": "en-US",
            "Europe": "en-EU",
            "Asia": "zh-CN",
            "Australia": "en-AU",
        }
        for prefix, locale in locale_map.items():
            if tz.startswith(prefix) or prefix in tz:
                suggestions.append({
                    "suggestion_id": "CTX-LOCALE-01",
                    "category": "locale",
                    "label": "Likely Locale",
                    "suggested_value": locale,
                    "confidence": 0.68,
                    "source": "timezone",
                    "explanation": f"Timezone '{tz}' suggests locale '{locale}'",
                    "default_action": "confirm",
                    "examiner_action": "pending",
                })
                break

    # ── Lifecycle / date hints ────────────────────────────────────────────────
    created = evidence.get("created_at") or evidence.get("backup_date")
    if created:
        try:
            dt = datetime.fromisoformat(str(created).replace("Z", ""))
            # Holiday season — common password creation period
            if dt.month in (11, 12):
                suggestions.append({
                    "suggestion_id": "CTX-LIFECYCLE-HOLIDAY",
                    "category": "lifecycle",
                    "label": "Holiday Period",
                    "suggested_value": f"{dt.year}_holiday",
                    "confidence": 0.60,
                    "source": "backup_timestamp",
                    "explanation": f"Backup created in {dt.strftime('%B %Y')} — common password-change period",
                    "default_action": "confirm",
                    "examiner_action": "pending",
                })
            # New Year — another common reset period
            if dt.month == 1:
                suggestions.append({
                    "suggestion_id": "CTX-LIFECYCLE-NEWYEAR",
                    "category": "lifecycle",
                    "label": "New Year Period",
                    "suggested_value": f"{dt.year}_new_year",
                    "confidence": 0.55,
                    "source": "backup_timestamp",
                    "explanation": f"Backup created in January {dt.year}",
                    "default_action": "confirm",
                    "examiner_action": "pending",
                })
            # Year hint always useful
            suggestions.append({
                "suggestion_id": "CTX-YEAR-01",
                "category": "lifecycle",
                "label": "Backup Year",
                "suggested_value": str(dt.year),
                "confidence": 0.90,
                "source": "backup_timestamp",
                "explanation": f"Backup created {dt.strftime('%Y-%m-%d')}",
                "default_action": "confirm",
                "examiner_action": "pending",
            })
        except Exception:
            pass

    # ── Device platform ───────────────────────────────────────────────────────
    platform = evidence.get("device_platform", "").lower()
    if not platform:
        if "iphone" in combined or "ipad" in combined or "ios" in combined:
            platform = "ios"
        elif "android" in combined or "samsung" in combined or "pixel" in combined:
            platform = "android"

    if platform:
        suggestions.append({
            "suggestion_id": "CTX-PLATFORM-01",
            "category": "platform",
            "label": "Device Platform",
            "suggested_value": platform,
            "confidence": 0.85,
            "source": "filename_inference",
            "explanation": f"Platform inferred as '{platform}'",
            "default_action": "confirm",
            "examiner_action": "pending",
        })

    return suggestions


def apply_examiner_decisions(
    suggestions: List[Dict[str, Any]],
    decisions: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Merges examiner confirmations/edits/rejections into confirmed_context.
    Only confirmed/edited suggestions reach AKE.
    """
    decision_map = {d["suggestion_id"]: d for d in decisions}
    confirmed: Dict[str, Any] = {}

    for s in suggestions:
        sid = s["suggestion_id"]
        decision = decision_map.get(sid, {})
        action = decision.get("action", s.get("default_action", "pending"))

        if action in ("confirm", "edited"):
            value = decision.get("final_value", s["suggested_value"])
            category = s["category"]

            if category == "identity":
                confirmed["owner_name"] = value
            elif category == "locale":
                confirmed["locale"] = value
            elif category == "lifecycle":
                confirmed.setdefault("lifecycle_hints", []).append(value)
                if "year" in sid.lower() or "year" in s["label"].lower():
                    confirmed["year_hint"] = value
            elif category == "platform":
                confirmed["platform"] = value

    return confirmed
