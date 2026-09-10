from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from ..bardo_timeline.timeline_builder import Timeline, TimelineEntry


@dataclass
class NarrativeClause:
    """
    A single sentence-level claim in the narrative.
    Every clause cites its supporting artifact IDs.
    This is what makes the narrative court-defensible.
    """
    text: str
    artifact_ids: List[str]
    confidence: float
    inference_level: str  # OBSERVED | DERIVED | INFERRED

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "artifact_ids": self.artifact_ids,
            "confidence": self.confidence,
            "inference_level": self.inference_level,
        }


@dataclass
class NarrativeSection:
    heading: str
    clauses: List[NarrativeClause] = field(default_factory=list)
    time_window: Optional[str] = None

    def plain_text(self) -> str:
        return "\n".join(f"- {c.text}" for c in self.clauses)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "heading": self.heading,
            "time_window": self.time_window,
            "clauses": [c.to_dict() for c in self.clauses],
        }


@dataclass
class CaseNarrative:
    case_id: str
    generated_at: str
    sections: List[NarrativeSection] = field(default_factory=list)
    limitations: List[str] = field(default_factory=list)

    def full_text(self) -> str:
        parts = [f"CASE NARRATIVE — {self.case_id}", ""]
        for section in self.sections:
            parts.append(f"## {section.heading}")
            if section.time_window:
                parts.append(f"Period: {section.time_window}")
            parts.append(section.plain_text())
            parts.append("")
        if self.limitations:
            parts.append("## Limitations")
            for lim in self.limitations:
                parts.append(f"- {lim}")
        return "\n".join(parts)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "case_id": self.case_id,
            "generated_at": self.generated_at,
            "sections": [s.to_dict() for s in self.sections],
            "limitations": self.limitations,
        }


class Narrator:
    """
    Generates plain-language narratives from a Bardo timeline.

    Design principles:
    - Every claim cites artifact IDs (traceable)
    - Inference level is always declared (OBSERVED / DERIVED / INFERRED)
    - Forbidden phrasing is blocked (proves, clearly shows, without doubt)
    - The narrator never draws conclusions — it describes observations
    """

    FORBIDDEN_PHRASES = [
        "proves", "clearly shows", "without a doubt",
        "definitively", "certainly", "undeniably",
    ]

    def __init__(self):
        self._entity_labels: Dict[str, str] = {}

    def register_entity_label(self, entity_id: str, label: str) -> None:
        self._entity_labels[entity_id] = label

    def _label(self, entity_id: str) -> str:
        return self._entity_labels.get(entity_id, entity_id[:8])

    def narrate_daily_summary(
        self, timeline: Timeline, target_date: datetime
    ) -> NarrativeSection:
        """What happened on a specific day?"""
        day_start = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)

        day_entries = [
            e for e in timeline.entries
            if day_start <= e.timestamp < day_end
        ]

        heading = f"Activity on {target_date.strftime('%B %d, %Y')}"
        clauses: List[NarrativeClause] = []

        if not day_entries:
            clauses.append(NarrativeClause(
                text="No recorded activity was observed on this date.",
                artifact_ids=[],
                confidence=1.0,
                inference_level="OBSERVED",
            ))
        else:
            # Group by artifact type
            by_type: Dict[str, List[TimelineEntry]] = {}
            for entry in day_entries:
                by_type.setdefault(entry.artifact_type, []).append(entry)

            for atype, entries in sorted(by_type.items()):
                count = len(entries)
                first = entries[0].timestamp.strftime("%H:%M")
                last = entries[-1].timestamp.strftime("%H:%M")
                avg_conf = sum(e.confidence for e in entries) / count

                text = self._describe_type_group(atype, count, first, last, entries)
                clauses.append(NarrativeClause(
                    text=text,
                    artifact_ids=[e.artifact_id for e in entries],
                    confidence=round(avg_conf, 2),
                    inference_level="OBSERVED",
                ))

        return NarrativeSection(
            heading=heading,
            clauses=clauses,
            time_window=f"{day_start.date()} 00:00 – 23:59",
        )

    def narrate_communication_story(
        self, timeline: Timeline, entity_label: Optional[str] = None
    ) -> NarrativeSection:
        """Who did this person communicate with and when?"""
        comm_types = {"MESSAGE", "CALL"}
        comm_entries = [
            e for e in timeline.entries
            if e.artifact_type in comm_types
        ]

        heading = "Communication Activity"
        if entity_label:
            heading = f"Communications Involving {entity_label}"

        clauses: List[NarrativeClause] = []

        if not comm_entries:
            clauses.append(NarrativeClause(
                text="No communication artifacts were observed in this evidence set.",
                artifact_ids=[],
                confidence=1.0,
                inference_level="OBSERVED",
            ))
            return NarrativeSection(heading=heading, clauses=clauses)

        messages = [e for e in comm_entries if e.artifact_type == "MESSAGE"]
        calls = [e for e in comm_entries if e.artifact_type == "CALL"]

        if messages:
            clauses.append(NarrativeClause(
                text=(
                    f"The evidence contains {len(messages)} message artifact(s). "
                    f"The earliest observed message was recorded at "
                    f"{messages[0].timestamp.strftime('%Y-%m-%d %H:%M')} and the "
                    f"latest at {messages[-1].timestamp.strftime('%Y-%m-%d %H:%M')}."
                ),
                artifact_ids=[e.artifact_id for e in messages[:100]],
                confidence=round(
                    sum(e.confidence for e in messages) / len(messages), 2
                ),
                inference_level="OBSERVED",
            ))

        if calls:
            clauses.append(NarrativeClause(
                text=(
                    f"The evidence contains {len(calls)} call record(s). "
                    f"Call records span from "
                    f"{calls[0].timestamp.strftime('%Y-%m-%d %H:%M')} to "
                    f"{calls[-1].timestamp.strftime('%Y-%m-%d %H:%M')}."
                ),
                artifact_ids=[e.artifact_id for e in calls[:100]],
                confidence=round(
                    sum(e.confidence for e in calls) / len(calls), 2
                ),
                inference_level="OBSERVED",
            ))

        return NarrativeSection(heading=heading, clauses=clauses)

    def narrate_incident_window(
        self, timeline: Timeline, start: datetime, end: datetime, label: str = ""
    ) -> NarrativeSection:
        """What happened during a specific time window?"""
        window_entries = timeline.filter_by_range(start, end).entries
        heading = label or f"Activity {start.strftime('%Y-%m-%d %H:%M')} – {end.strftime('%H:%M')}"
        clauses: List[NarrativeClause] = []

        if not window_entries:
            clauses.append(NarrativeClause(
                text="No artifacts were recorded during this time window.",
                artifact_ids=[],
                confidence=1.0,
                inference_level="OBSERVED",
            ))
        else:
            clauses.append(NarrativeClause(
                text=(
                    f"{len(window_entries)} artifact(s) were observed during this period. "
                    f"These span {len(set(e.artifact_type for e in window_entries))} "
                    f"artifact type(s)."
                ),
                artifact_ids=[e.artifact_id for e in window_entries],
                confidence=round(
                    sum(e.confidence for e in window_entries) / len(window_entries), 2
                ),
                inference_level="OBSERVED",
            ))
            for entry in window_entries[:10]:  # show first 10 details
                clauses.append(NarrativeClause(
                    text=(
                        f"At {entry.timestamp.strftime('%H:%M:%S')}: "
                        f"{entry.summary or entry.artifact_type}"
                    ),
                    artifact_ids=[entry.artifact_id],
                    confidence=entry.confidence,
                    inference_level="OBSERVED",
                ))

        return NarrativeSection(
            heading=heading,
            clauses=clauses,
            time_window=f"{start.isoformat()} – {end.isoformat()}",
        )

    def build_narrative(
        self,
        timeline: Timeline,
        daily_dates: Optional[List[datetime]] = None,
    ) -> CaseNarrative:
        """Full case narrative combining all story types."""
        from datetime import timezone
        now = datetime.now(timezone.utc).isoformat()

        sections = []

        # Overview
        if timeline.entries:
            first = timeline.entries[0].timestamp
            last = timeline.entries[-1].timestamp
            overview = NarrativeSection(
                heading="Evidence Overview",
                clauses=[NarrativeClause(
                    text=(
                        f"This case contains {len(timeline.entries)} observed artifact(s) "
                        f"spanning from {first.strftime('%Y-%m-%d')} to "
                        f"{last.strftime('%Y-%m-%d')}. "
                        f"All artifacts are labeled by type and confidence level. "
                        f"Observations are reported as found — no conclusions are drawn."
                    ),
                    artifact_ids=[],
                    confidence=1.0,
                    inference_level="OBSERVED",
                )],
            )
            sections.append(overview)

        # Communications
        sections.append(self.narrate_communication_story(timeline))

        # Daily summaries if requested
        if daily_dates:
            for date in daily_dates:
                sections.append(self.narrate_daily_summary(timeline, date))

        limitations = [
            "This narrative describes only artifacts present in the provided evidence.",
            "Absence of an artifact does not confirm that no such event occurred.",
            "Timestamps are reported as recorded — clock skew or manipulation is not detectable from artifacts alone.",
            "All claims are labeled OBSERVED, DERIVED, or INFERRED. Only OBSERVED claims are directly supported by artifact data.",
        ]

        return CaseNarrative(
            case_id=timeline.case_id,
            generated_at=now,
            sections=sections,
            limitations=limitations,
        )

    def _describe_type_group(
        self,
        atype: str,
        count: int,
        first_time: str,
        last_time: str,
        entries: List[TimelineEntry],
    ) -> str:
        descriptions = {
            "MESSAGE":        f"{count} message artifact(s) observed between {first_time} and {last_time}.",
            "CALL":           f"{count} call record(s) observed between {first_time} and {last_time}.",
            "WEB_ACTIVITY":   f"{count} web activity artifact(s) observed between {first_time} and {last_time}.",
            "APP_ACTIVITY":   f"{count} application activity artifact(s) observed between {first_time} and {last_time}.",
            "LOCATION_POINT": f"{count} location artifact(s) recorded between {first_time} and {last_time}.",
            "SYSTEM_EVENT":   f"{count} system event(s) recorded between {first_time} and {last_time}.",
            "FILE_METADATA":  f"{count} file metadata artifact(s) observed between {first_time} and {last_time}.",
            "AUTH_EVENT":     f"{count} authentication event(s) observed between {first_time} and {last_time}.",
            "MEDIA":          f"{count} media artifact(s) observed between {first_time} and {last_time}.",
        }
        return descriptions.get(
            atype,
            f"{count} {atype.lower().replace('_', ' ')} artifact(s) observed between {first_time} and {last_time}."
        )

    def lint_narrative(self, narrative: CaseNarrative) -> List[str]:
        """
        Checks for forbidden phrasing in the narrative.
        Same principle as Chop Shop's claim_lint.
        """
        violations = []
        for section in narrative.sections:
            for clause in section.clauses:
                for phrase in self.FORBIDDEN_PHRASES:
                    if phrase.lower() in clause.text.lower():
                        violations.append(
                            f"Forbidden phrase '{phrase}' found in clause: '{clause.text[:80]}'"
                        )
        return violations
