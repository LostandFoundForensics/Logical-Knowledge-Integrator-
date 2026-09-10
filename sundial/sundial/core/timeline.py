"""
Sundial — Timeline Query Engine

This is where the reading happens. Key rules enforced here:

1. Observed and inferred events come from DIFFERENT tables. The default query
   returns observed only. Inference must be explicitly requested.

2. Timezone precedence is EXPLICIT and surfaced to the reader. The spec allowed
   scope.time_basis and per-event timezone_basis to contradict; this engine
   states the rule: the event's own timezone_basis always wins for display,
   and the chosen display basis is reported alongside every result so the
   reader can see it. No silent reinterpretation.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from sundial.core.bundle import CaseBundle


@dataclass
class TimelineFilter:
    categories: Optional[List[str]] = None      # None = all
    start: Optional[str] = None                  # ISO8601 inclusive
    end: Optional[str] = None                    # ISO8601 inclusive
    include_inferred: bool = False               # observed-only by default
    search: Optional[str] = None                 # matches summary text
    limit: int = 2000


@dataclass
class TimelineRow:
    event_id: str
    category: Optional[str]
    timestamp_start: str
    timestamp_end: Optional[str]
    timestamp_quality: Optional[str]
    timezone_basis: Optional[str]
    summary_plain: Optional[str]
    summary_technical: Optional[str]
    observability: str
    confidence: Optional[float]
    source_count: Optional[int]
    thread_key: Optional[str]
    is_inferred: bool = False
    confidence_level: Optional[str] = None
    confidence_reasons: List[str] = field(default_factory=list)


@dataclass
class TimelineResult:
    rows: List[TimelineRow]
    observed_count: int
    inferred_count: int
    display_timezone_rule: str
    notes: List[str] = field(default_factory=list)


# The single, stated timezone precedence rule shown to every reader.
TZ_PRECEDENCE_RULE = (
    "Each event is displayed in the timezone it was stored in (its own "
    "timezone_basis). Where an event has no basis, it is shown as recorded "
    "and labeled UNKNOWN. Sundial does not silently convert times."
)


class TimelineEngine:
    def __init__(self, bundle: CaseBundle):
        self.bundle = bundle

    def query(self, flt: TimelineFilter) -> TimelineResult:
        if self.bundle.conn is None:
            return TimelineResult(
                rows=[], observed_count=0, inferred_count=0,
                display_timezone_rule=TZ_PRECEDENCE_RULE,
                notes=["No database loaded — there is no timeline to show."],
            )

        observed = self._query_observed(flt)
        inferred: List[TimelineRow] = []
        if flt.include_inferred and self.bundle.has_table("inferred_events"):
            inferred = self._query_inferred(flt)

        combined = observed + inferred
        # Stable ordering: time, then observed before inferred at the same instant
        combined.sort(key=lambda r: (r.timestamp_start or "", r.is_inferred))

        notes: List[str] = []
        if flt.include_inferred and not inferred:
            notes.append("Inferred events were requested but none are present.")
        if not flt.include_inferred:
            notes.append("Showing observed events only. Inference is turned off.")

        return TimelineResult(
            rows=combined,
            observed_count=len(observed),
            inferred_count=len(inferred),
            display_timezone_rule=TZ_PRECEDENCE_RULE,
            notes=notes,
        )

    # ── Observed ──────────────────────────────────────────────────────────────
    def _query_observed(self, flt: TimelineFilter) -> List[TimelineRow]:
        sql = ["SELECT * FROM events WHERE 1=1"]
        params: List[Any] = []

        if flt.categories:
            placeholders = ",".join("?" for _ in flt.categories)
            sql.append(f"AND category IN ({placeholders})")
            params.extend(flt.categories)
        if flt.start:
            sql.append("AND timestamp_start >= ?")
            params.append(flt.start)
        if flt.end:
            sql.append("AND timestamp_start <= ?")
            params.append(flt.end)
        if flt.search:
            sql.append("AND (summary_plain LIKE ? OR summary_technical LIKE ?)")
            like = f"%{flt.search}%"
            params.extend([like, like])

        sql.append("ORDER BY timestamp_start ASC LIMIT ?")
        params.append(int(flt.limit))

        cur = self.bundle.conn.execute(" ".join(sql), params)
        rows: List[TimelineRow] = []
        for r in cur.fetchall():
            rows.append(TimelineRow(
                event_id=r["event_id"],
                category=r["category"],
                timestamp_start=r["timestamp_start"],
                timestamp_end=r["timestamp_end"],
                timestamp_quality=r["timestamp_quality"],
                timezone_basis=r["timezone_basis"] or "UNKNOWN",
                summary_plain=r["summary_plain"],
                summary_technical=r["summary_technical"],
                observability=r["observability"] or "OBSERVED",
                confidence=r["confidence"],
                source_count=r["source_count"],
                thread_key=r["thread_key"] if "thread_key" in r.keys() else None,
                is_inferred=False,
            ))
        return rows

    # ── Inferred (separate table, opt-in only) ────────────────────────────────
    def _query_inferred(self, flt: TimelineFilter) -> List[TimelineRow]:
        sql = ["SELECT * FROM inferred_events WHERE hidden = 0"]
        params: List[Any] = []

        if flt.start:
            sql.append("AND timestamp_estimated >= ?")
            params.append(flt.start)
        if flt.end:
            sql.append("AND timestamp_estimated <= ?")
            params.append(flt.end)
        if flt.search:
            sql.append("AND summary_plain LIKE ?")
            params.append(f"%{flt.search}%")

        sql.append("ORDER BY timestamp_estimated ASC LIMIT ?")
        params.append(int(flt.limit))

        cur = self.bundle.conn.execute(" ".join(sql), params)
        rows: List[TimelineRow] = []
        for r in cur.fetchall():
            reasons = []
            try:
                reasons = json.loads(r["confidence_reasons"] or "[]")
            except Exception:
                reasons = []
            rows.append(TimelineRow(
                event_id=r["event_id"],
                category="INFERRED",
                timestamp_start=r["timestamp_estimated"],
                timestamp_end=r["timestamp_range_end"],
                timestamp_quality="RANGE",
                timezone_basis="UNKNOWN",
                summary_plain=r["summary_plain"],
                summary_technical=None,
                observability="INFERRED",
                confidence=r["confidence"],
                source_count=None,
                thread_key=None,
                is_inferred=True,
                confidence_level=r["confidence_level"],
                confidence_reasons=reasons,
            ))
        return rows

    # ── Single event detail (for the raw / proof view) ────────────────────────
    def event_detail(self, event_id: str) -> Optional[Dict[str, Any]]:
        if self.bundle.conn is None:
            return None
        cur = self.bundle.conn.execute(
            "SELECT * FROM events WHERE event_id = ?", (event_id,)
        )
        ev = cur.fetchone()
        if ev is None:
            # Might be an inferred event
            return self._inferred_detail(event_id)

        detail: Dict[str, Any] = {k: ev[k] for k in ev.keys()}
        detail["is_inferred"] = False
        detail["sources"] = self._sources_for(event_id)
        detail["hash_refs"] = self._hash_refs_for(event_id)
        detail["conflicts"] = self._conflicts_for(event_id)
        detail["links"] = self._links_for(event_id)
        return detail

    def _inferred_detail(self, event_id: str) -> Optional[Dict[str, Any]]:
        if not self.bundle.has_table("inferred_events"):
            return None
        cur = self.bundle.conn.execute(
            "SELECT * FROM inferred_events WHERE event_id = ?", (event_id,)
        )
        ev = cur.fetchone()
        if ev is None:
            return None
        detail = {k: ev[k] for k in ev.keys()}
        detail["is_inferred"] = True
        for jf in ("confidence_reasons", "supporting_event_ids"):
            try:
                detail[jf] = json.loads(detail.get(jf) or "[]")
            except Exception:
                detail[jf] = []
        return detail

    def _sources_for(self, event_id: str) -> List[Dict[str, Any]]:
        if not self.bundle.has_table("event_sources"):
            return []
        cur = self.bundle.conn.execute(
            "SELECT * FROM event_sources WHERE event_id = ?", (event_id,)
        )
        return [dict(r) for r in cur.fetchall()]

    def _hash_refs_for(self, event_id: str) -> List[Dict[str, Any]]:
        if not self.bundle.has_table("event_hash_refs"):
            return []
        cur = self.bundle.conn.execute(
            "SELECT * FROM event_hash_refs WHERE event_id = ?", (event_id,)
        )
        return [dict(r) for r in cur.fetchall()]

    def _conflicts_for(self, event_id: str) -> List[Dict[str, Any]]:
        if not self.bundle.has_table("event_conflicts"):
            return []
        cur = self.bundle.conn.execute(
            "SELECT * FROM event_conflicts WHERE event_id = ?", (event_id,)
        )
        return [dict(r) for r in cur.fetchall()]

    def _links_for(self, event_id: str) -> List[Dict[str, Any]]:
        if not self.bundle.has_table("event_links"):
            return []
        cur = self.bundle.conn.execute(
            "SELECT * FROM event_links WHERE event_id_a = ? OR event_id_b = ?",
            (event_id, event_id),
        )
        return [dict(r) for r in cur.fetchall()]

    # ── Gaps ──────────────────────────────────────────────────────────────────
    def gaps(self) -> List[Dict[str, Any]]:
        if self.bundle.conn is None or not self.bundle.has_table("timeline_gaps"):
            return []
        cur = self.bundle.conn.execute(
            "SELECT * FROM timeline_gaps ORDER BY gap_start ASC"
        )
        out = []
        for r in cur.fetchall():
            d = dict(r)
            try:
                d["explanations"] = json.loads(d.get("explanations") or "[]")
            except Exception:
                d["explanations"] = []
            out.append(d)
        return out

    # ── Category counts for the overview ──────────────────────────────────────
    def category_counts(self) -> Dict[str, int]:
        if self.bundle.conn is None:
            return {}
        cur = self.bundle.conn.execute(
            "SELECT category, COUNT(*) AS c FROM events GROUP BY category"
        )
        return {(r["category"] or "UNCATEGORIZED"): r["c"] for r in cur.fetchall()}
