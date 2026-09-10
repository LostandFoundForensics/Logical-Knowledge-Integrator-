"""
ChronoChain correlation — link events that happen near each other in time.

Caps prevent O(n²) blow-ups on dense timelines (e.g. file-metadata floods).
Links are observations of proximity, not conclusions.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

from chronochain.core.schema import TimelineEvent


@dataclass
class CorrelationConfig:
    time_proximity_window_ms: int = 10_000
    session_window_ms: int = 180_000
    max_links_per_event: int = 8
    max_neighbors_scanned: int = 200
    enable_inferred_bridge_events: bool = False


def build_links(
    events: List[TimelineEvent],
    cfg: CorrelationConfig | None = None,
) -> Tuple[List[Dict[str, Any]], List[TimelineEvent]]:
    cfg = cfg or CorrelationConfig()
    links: List[Dict[str, Any]] = []
    inferred: List[TimelineEvent] = []

    events_sorted = sorted(events, key=lambda e: (int(e.ts.epoch_ms), str(e.event_id)))
    link_counts: Dict[str, int] = {}

    def can_link(eid: str) -> bool:
        return link_counts.get(eid, 0) < cfg.max_links_per_event

    def add_link(a: TimelineEvent, b: TimelineEvent, link_type: str, strength: float, rationale: str) -> None:
        if a.event_id == b.event_id:
            return
        if not can_link(a.event_id) or not can_link(b.event_id):
            return
        links.append({
            "from_event_id": a.event_id,
            "to_event_id": b.event_id,
            "link_type": link_type,
            "strength": float(strength),
            "inferred": False,
            "rationale": rationale,
            "evidence_json": json.dumps(
                {
                    "delta_ms": abs(int(a.ts.epoch_ms) - int(b.ts.epoch_ms)),
                    "categories": [a.category, b.category],
                },
                ensure_ascii=False,
            ),
        })
        link_counts[a.event_id] = link_counts.get(a.event_id, 0) + 1
        link_counts[b.event_id] = link_counts.get(b.event_id, 0) + 1

    n = len(events_sorted)
    for i, a in enumerate(events_sorted):
        if not can_link(a.event_id):
            continue
        scanned = 0
        for j in range(i + 1, n):
            if scanned >= cfg.max_neighbors_scanned:
                break
            b = events_sorted[j]
            delta = int(b.ts.epoch_ms) - int(a.ts.epoch_ms)
            if delta > cfg.time_proximity_window_ms:
                break
            scanned += 1
            if not can_link(b.event_id):
                continue
            # Same actor → stronger link
            shared_actors = set(a.actors) & set(b.actors)
            if shared_actors:
                add_link(
                    a, b, "proximity_same_actor", 0.8,
                    f"Within {delta}ms; shared actor(s): {', '.join(sorted(shared_actors)[:3])}",
                )
            elif a.category == b.category:
                add_link(
                    a, b, "proximity_same_category", 0.5,
                    f"Within {delta}ms; same category {a.category}",
                )
            else:
                add_link(
                    a, b, "proximity", 0.3,
                    f"Within {delta}ms",
                )

    return links, inferred
