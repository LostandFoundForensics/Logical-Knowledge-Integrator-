"""
Simple timeline for non-technical readers.

Loads Bardo timeline JSON (or a plain event list) and produces:
  - ordered rows
  - plain-language day groups
  - HTML / TXT exports

Observed-only by design for this path (no inferred events mixed in).
"""
from __future__ import annotations

import html
import json
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class SimpleEvent:
    event_id: str
    when_ms: Optional[int]
    when_label: str
    category: str
    summary: str
    tool: str
    entities: List[str] = field(default_factory=list)
    confidence: float = 0.9

    def day_key(self) -> str:
        if self.when_ms is None:
            return "Unknown date"
        try:
            dt = datetime.fromtimestamp(self.when_ms / 1000.0, tz=timezone.utc)
            return dt.strftime("%Y-%m-%d")
        except Exception:
            return "Unknown date"

    def time_label(self) -> str:
        if self.when_label:
            return self.when_label
        if self.when_ms is None:
            return "—"
        try:
            dt = datetime.fromtimestamp(self.when_ms / 1000.0, tz=timezone.utc)
            return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
        except Exception:
            return f"unix_ms={self.when_ms}"


def load_bardo_timeline(path: Path) -> List[SimpleEvent]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    raw = data["events"] if isinstance(data, dict) and "events" in data else data
    if not isinstance(raw, list):
        raise ValueError("Timeline JSON must be a list or {events: [...]}")
    out: List[SimpleEvent] = []
    for i, ev in enumerate(raw):
        if not isinstance(ev, dict):
            continue
        when_ms = ev.get("when_ms") or ev.get("timestamp_unix_ms")
        try:
            when_ms_i = int(when_ms) if when_ms is not None else None
        except Exception:
            when_ms_i = None
        out.append(
            SimpleEvent(
                event_id=str(ev.get("obs_id") or ev.get("event_id") or f"e{i}"),
                when_ms=when_ms_i,
                when_label=str(ev.get("when_label") or ev.get("date_iso") or ""),
                category=str(ev.get("type") or ev.get("category") or "event"),
                summary=str(ev.get("summary") or "")[:300],
                tool=str(ev.get("tool") or ""),
                entities=list(ev.get("entities") or []),
                confidence=float(ev.get("confidence") or 0.9),
            )
        )
    out.sort(key=lambda e: (e.when_ms is None, e.when_ms or 0))
    return out


def group_by_day(events: List[SimpleEvent]) -> Dict[str, List[SimpleEvent]]:
    groups: Dict[str, List[SimpleEvent]] = defaultdict(list)
    for e in events:
        groups[e.day_key()].append(e)
    return dict(sorted(groups.items(), key=lambda kv: kv[0]))


def to_plain_text(events: List[SimpleEvent], *, case_id: str = "") -> str:
    lines = [
        "Sundial timeline (observed events)",
        f"Case: {case_id or 'unspecified'}",
        "Times shown in UTC when converted from unix milliseconds.",
        "This view does not mix in inferred events.",
        "",
    ]
    for day, rows in group_by_day(events).items():
        lines.append(f"=== {day} ({len(rows)} events) ===")
        for e in rows:
            ent = f" | {', '.join(e.entities[:3])}" if e.entities else ""
            tool = f" [{e.tool}]" if e.tool else ""
            lines.append(f"  {e.time_label()}  ·  {e.category}{tool}")
            lines.append(f"    {e.summary}{ent}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def to_html(events: List[SimpleEvent], *, case_id: str = "", title: str = "Timeline") -> str:
    parts = [
        "<!DOCTYPE html><html><head><meta charset='utf-8'>",
        f"<title>{html.escape(title)}</title>",
        "<style>",
        "body{font-family:system-ui,sans-serif;max-width:900px;margin:2rem auto;padding:0 1rem;color:#111}",
        "h1{font-size:1.4rem} h2{font-size:1.1rem;margin-top:2rem;border-bottom:1px solid #ccc;padding-bottom:.3rem}",
        ".ev{margin:.8rem 0;padding:.6rem;border-left:3px solid #333;background:#fafafa}",
        ".meta{color:#555;font-size:.9rem} .sum{margin-top:.3rem}",
        ".note{color:#666;font-size:.85rem;margin-bottom:1.5rem}",
        "</style></head><body>",
        f"<h1>{html.escape(title)}</h1>",
        f"<p class='note'>Case: {html.escape(case_id or 'unspecified')}. "
        "Observed events only. Times in UTC when derived from unix ms. "
        "Not a finding of guilt or intent.</p>",
    ]
    for day, rows in group_by_day(events).items():
        parts.append(f"<h2>{html.escape(day)} <span class='meta'>({len(rows)})</span></h2>")
        for e in rows:
            ent = ""
            if e.entities:
                ent = " · " + html.escape(", ".join(e.entities[:5]))
            tool = f" · {html.escape(e.tool)}" if e.tool else ""
            parts.append("<div class='ev'>")
            parts.append(
                f"<div class='meta'>{html.escape(e.time_label())} · "
                f"{html.escape(e.category)}{tool}{ent}</div>"
            )
            parts.append(f"<div class='sum'>{html.escape(e.summary)}</div>")
            parts.append("</div>")
    parts.append("</body></html>")
    return "\n".join(parts)
