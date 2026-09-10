from __future__ import annotations
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any, Dict, List, Optional, Set, Tuple

from ..bardo_core.schema import (
    Entity, Artifact, Relationship,
    EntityType, RelationshipType,
    EntityRef, ArtifactRef, TimeRange,
)
from ..bardo_core.confidence import aggregate_artifact_confidence
from ..bardo_artifact_store.storage_sqlite import BardoStore


# ── Conflict resolution doctrine ──────────────────────────────────────────────

@dataclass
class ConflictResolutionPolicy:
    """
    Court-explainable rules for resolving tool disagreements.
    Every decision is documented and traceable.
    """
    # Maximum timestamp spread (seconds) before flagging as conflict
    timestamp_conflict_threshold_sec: int = 120

    # Source priority for timestamp resolution (higher = more trusted)
    source_priority: Dict[str, int] = field(default_factory=lambda: {
        "FILESYSTEM": 4,
        "APP_LOG":    3,
        "SYSTEM_LOG": 3,
        "CLOUD_LOG":  5,   # Cloud logs are often most reliable
        "INFERRED":   1,
    })

    # Tool priority for conflict resolution
    tool_priority: Dict[str, int] = field(default_factory=lambda: {
        "cellebrite": 4,
        "magnet":     3,
        "oxygen":     3,
        "idriller":   5,   # Our own tools — highest trust
        "android_excavator": 5,
        "recall_engine": 5,
        "autopsy":    2,
    })

    def resolve_timestamp_conflict(
        self,
        assertions: List[Dict[str, Any]],
    ) -> Tuple[Optional[str], str]:
        """
        Returns (best_timestamp_iso, rationale).
        Rationale is court-explainable text.
        """
        if not assertions:
            return None, "No timestamps available."

        # Prefer highest-priority source
        best = max(
            assertions,
            key=lambda a: self.source_priority.get(a.get("source", "INFERRED"), 0)
        )
        rationale = (
            f"Timestamp selected from {best.get('source', 'unknown')} source "
            f"(priority={self.source_priority.get(best.get('source','INFERRED'), 0)}). "
            f"Conflict policy: highest-trusted source wins. "
            f"{len(assertions)} source(s) compared."
        )
        return best.get("timestamp"), rationale


DEFAULT_POLICY = ConflictResolutionPolicy()


# ── Entity resolution ─────────────────────────────────────────────────────────

@dataclass
class ResolutionMatch:
    entity_a_id: str
    entity_b_id: str
    match_basis: str
    confidence: float


class EntityResolver:
    """
    Identifies when two entity records refer to the same real-world entity
    and merges them with documented basis.
    """

    def __init__(self, store: BardoStore):
        self.store = store

    def resolve_all(self) -> List[ResolutionMatch]:
        """
        Runs all resolution strategies across the entity store.
        Returns matches for analyst review — does NOT auto-merge.
        Auto-merge is an analyst action, logged in provenance.
        """
        matches: List[ResolutionMatch] = []
        matches.extend(self._resolve_by_phone_number())
        matches.extend(self._resolve_by_email())
        matches.extend(self._resolve_by_device_identifier())
        return matches

    def _resolve_by_phone_number(self) -> List[ResolutionMatch]:
        """Entities sharing a normalized phone number are likely the same."""
        people = self.store.find_entities_by_type(EntityType.PERSON)
        matches = []
        seen: Dict[str, str] = {}

        for entity in people:
            phone = _normalize_phone(entity.attributes.get("phone", ""))
            if not phone:
                continue
            if phone in seen:
                matches.append(ResolutionMatch(
                    entity_a_id=seen[phone],
                    entity_b_id=entity.entity_id,
                    match_basis=f"Shared normalized phone number: {phone}",
                    confidence=0.92,
                ))
            else:
                seen[phone] = entity.entity_id

        return matches

    def _resolve_by_email(self) -> List[ResolutionMatch]:
        people = self.store.find_entities_by_type(EntityType.PERSON)
        matches = []
        seen: Dict[str, str] = {}

        for entity in people:
            email = (entity.attributes.get("email", "") or "").lower().strip()
            if not email or "@" not in email:
                continue
            if email in seen:
                matches.append(ResolutionMatch(
                    entity_a_id=seen[email],
                    entity_b_id=entity.entity_id,
                    match_basis=f"Shared email address: {email}",
                    confidence=0.95,
                ))
            else:
                seen[email] = entity.entity_id

        return matches

    def _resolve_by_device_identifier(self) -> List[ResolutionMatch]:
        devices = self.store.find_entities_by_type(EntityType.DEVICE)
        matches = []
        seen: Dict[str, str] = {}

        for device in devices:
            for id_field in ("imei", "udid", "serial", "mac_address"):
                val = (device.attributes.get(id_field, "") or "").upper().strip()
                if val:
                    key = f"{id_field}:{val}"
                    if key in seen:
                        matches.append(ResolutionMatch(
                            entity_a_id=seen[key],
                            entity_b_id=device.entity_id,
                            match_basis=f"Shared {id_field}: {val}",
                            confidence=0.98,
                        ))
                    else:
                        seen[key] = device.entity_id
                    break

        return matches


# ── Temporal linking ──────────────────────────────────────────────────────────

@dataclass
class TemporalLink:
    artifact_a_id: str
    artifact_b_id: str
    gap_seconds: float
    link_type: str
    confidence: float
    rationale: str


class TemporalLinker:
    """
    Links artifacts that occurred close in time — suggesting causal
    or contextual relationships worth investigating.
    """

    def __init__(
        self,
        store: BardoStore,
        proximity_window_sec: int = 300,  # 5 minutes
    ):
        self.store = store
        self.window = proximity_window_sec

    def find_proximate_events(
        self,
        center_artifact_id: str,
    ) -> List[TemporalLink]:
        """
        Finds artifacts that occurred within the proximity window
        of the given artifact.
        """
        anchor = self.store.get_artifact(center_artifact_id)
        if not anchor or not anchor.get("best_time"):
            return []

        from datetime import datetime
        anchor_time = datetime.fromisoformat(anchor["best_time"])
        start = anchor_time - timedelta(seconds=self.window)
        end = anchor_time + timedelta(seconds=self.window)

        nearby = self.store.query_artifacts_in_time_range(start, end)
        links = []

        for art in nearby:
            if art["artifact_id"] == center_artifact_id:
                continue
            if not art.get("best_time"):
                continue

            other_time = datetime.fromisoformat(art["best_time"])
            gap = abs((other_time - anchor_time).total_seconds())

            links.append(TemporalLink(
                artifact_a_id=center_artifact_id,
                artifact_b_id=art["artifact_id"],
                gap_seconds=gap,
                link_type="temporal_proximity",
                confidence=max(0.40, 1.0 - (gap / (self.window * 2))),
                rationale=(
                    f"Events within {gap:.0f} seconds of each other. "
                    f"Proximity window: {self.window}s. "
                    "Correlation is observational — causation not implied."
                ),
            ))

        return sorted(links, key=lambda l: l.gap_seconds)


# ── Tool conflict detection ───────────────────────────────────────────────────

@dataclass
class ToolConflict:
    artifact_type: str
    field: str
    tool_a: str
    value_a: Any
    tool_b: str
    value_b: Any
    severity: str   # LOW | MEDIUM | HIGH
    resolution: str
    policy_applied: str


class ToolConflictDetector:
    """
    Detects when two tools report different values for the same artifact field.
    Applies the ConflictResolutionPolicy and documents every decision.
    """

    def __init__(self, policy: ConflictResolutionPolicy = DEFAULT_POLICY):
        self.policy = policy

    def detect(
        self,
        artifact_a: Dict[str, Any],
        artifact_b: Dict[str, Any],
        field: str,
    ) -> Optional[ToolConflict]:
        """Compare a specific field between two artifact dicts from different tools."""
        val_a = artifact_a.get(field)
        val_b = artifact_b.get(field)

        if val_a == val_b:
            return None  # No conflict

        tool_a = artifact_a.get("source_tool", "unknown_a")
        tool_b = artifact_b.get("source_tool", "unknown_b")

        # Determine severity
        if field in ("timestamp", "best_time"):
            # Timestamp conflicts — apply resolution policy
            try:
                from datetime import datetime
                dt_a = datetime.fromisoformat(str(val_a)) if val_a else None
                dt_b = datetime.fromisoformat(str(val_b)) if val_b else None
                if dt_a and dt_b:
                    spread = abs((dt_a - dt_b).total_seconds())
                    severity = (
                        "HIGH" if spread > 3600
                        else "MEDIUM" if spread > 120
                        else "LOW"
                    )
                else:
                    severity = "MEDIUM"
            except Exception:
                severity = "MEDIUM"

            # Apply resolution
            prio_a = self.policy.tool_priority.get(tool_a.lower(), 2)
            prio_b = self.policy.tool_priority.get(tool_b.lower(), 2)
            if prio_a >= prio_b:
                resolution = f"Using {tool_a} value: {val_a}"
                policy = f"{tool_a} priority={prio_a} >= {tool_b} priority={prio_b}"
            else:
                resolution = f"Using {tool_b} value: {val_b}"
                policy = f"{tool_b} priority={prio_b} > {tool_a} priority={prio_a}"
        else:
            severity = "LOW"
            resolution = f"Both values retained; analyst review required."
            policy = "No automatic resolution for non-temporal field conflicts."

        return ToolConflict(
            artifact_type=artifact_a.get("artifact_type", "UNKNOWN"),
            field=field,
            tool_a=tool_a,
            value_a=val_a,
            tool_b=tool_b,
            value_b=val_b,
            severity=severity,
            resolution=resolution,
            policy_applied=policy,
        )


# ── Utilities ─────────────────────────────────────────────────────────────────

def _normalize_phone(phone: str) -> str:
    """Strip formatting, keep digits and leading +."""
    import re
    if not phone:
        return ""
    digits = re.sub(r"[^\d+]", "", phone)
    # Normalize US numbers
    if digits.startswith("1") and len(digits) == 11:
        digits = "+" + digits
    elif len(digits) == 10:
        digits = "+1" + digits
    return digits
