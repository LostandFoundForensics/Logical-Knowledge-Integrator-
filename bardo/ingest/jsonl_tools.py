"""
Universal JSONL ingest for LoKi tool exports into Bardo.

Never opens original evidence — only case export JSONL/JSON files.

Supported shapes:
  - android_excavator / idriller / memory_snare / recall_engine:
      {artifact_type, record, provenance?, quality?}
  - pattern_harvester:
      {pattern_type, value, source_path, byte_offset, confidence}
  - integrity_breaker:
      {rule_id, title, severity, source_path, matched, confidence}
  - nimbus_bridge:
      {provider, artifact_type, summary, record, source_path}
  - truthrelic inventory:
      {relative_path, size_bytes, mtime_epoch, sha256, ...}
  - generic observation-like lines
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from bardo.core.models import Observation
from bardo.core.store import CaseStore

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,24}")
PHONE_RE = re.compile(r"\+?[0-9][0-9\s.\-()]{6,20}[0-9]")


def _obs_id(tool: str, artifact_type: str, payload: Dict[str, Any], path: str) -> str:
    raw = f"{tool}|{artifact_type}|{path}|{json.dumps(payload, sort_keys=True, default=str)}"
    return hashlib.sha256(raw.encode("utf-8", errors="replace")).hexdigest()[:24]


def _ts_ms(rec: Dict[str, Any]) -> Optional[int]:
    for key in (
        "date_unix_ms",
        "last_visit_unix_ms",
        "visit_unix_ms",
        "start_unix_ms",
        "when_ms",
        "timestamp_unix_ms",
        "date",
        "time",
        "mtime_epoch",
    ):
        v = rec.get(key)
        if v is None:
            continue
        try:
            if isinstance(v, str) and "T" in v:
                continue
            n = float(v)
            n_i = int(n)
            if key == "mtime_epoch" or (n_i > 1_000_000_000 and n_i < 10_000_000_000):
                return n_i * 1000
            if n_i >= 10_000_000_000:
                return n_i
            if n_i > 0:
                return n_i * 1000
        except Exception:
            continue
    return None


def _entities_from_text(*parts: Any) -> List[str]:
    text = " ".join(str(p) for p in parts if p)
    found: List[str] = []
    for m in EMAIL_RE.finditer(text):
        found.append(m.group(0))
    for m in PHONE_RE.finditer(text):
        val = re.sub(r"[\s.\-()]", "", m.group(0))
        if len(val) >= 7:
            found.append(m.group(0).strip())
    return list(dict.fromkeys(found))


def _entities_from_record(rec: Dict[str, Any]) -> List[str]:
    out: List[str] = []
    for key in (
        "address", "number", "value", "email", "phone", "name", "url", "ssid", "title",
    ):
        v = rec.get(key)
        if v and isinstance(v, (str, int, float)):
            out.append(str(v).strip())
    out.extend(_entities_from_text(rec.get("body"), rec.get("text"), rec.get("summary")))
    return list(dict.fromkeys(x for x in out if x and len(x) >= 3))


def _summary_from_record(artifact_type: str, rec: Dict[str, Any]) -> str:
    for key in (
        "body", "text", "url", "title", "display_name", "number", "address",
        "name", "ssid", "summary", "value",
    ):
        if rec.get(key):
            return str(rec[key])[:200]
    if rec.get("first") or rec.get("last"):
        return f"{rec.get('first') or ''} {rec.get('last') or ''}".strip()[:200]
    return artifact_type


def normalize_row(obj: Dict[str, Any], *, default_tool: str) -> Optional[Observation]:
    if not isinstance(obj, dict):
        return None

    if "pattern_type" in obj and "value" in obj:
        tool = default_tool or "pattern_harvester"
        ptype = str(obj.get("pattern_type") or "pattern")
        value = str(obj.get("value") or "")
        path_s = str(obj.get("source_path") or "")
        rec = {"value": value, "pattern_type": ptype, "byte_offset": obj.get("byte_offset")}
        return Observation(
            obs_id=_obs_id(tool, f"pattern.{ptype}", rec, path_s),
            source_tool=tool,
            artifact_type=f"pattern.{ptype}",
            summary=value[:200],
            entities=_entities_from_text(value),
            payload=rec,
            provenance_path=path_s,
            confidence=float(obj.get("confidence") or 0.7),
            flags=["pattern_match"],
        )

    if "rule_id" in obj and ("title" in obj or "matched" in obj):
        tool = default_tool or "integrity_breaker"
        rid = str(obj.get("rule_id") or "rule")
        title = str(obj.get("title") or rid)
        path_s = str(obj.get("source_path") or "")
        rec = {
            "rule_id": rid,
            "matched": obj.get("matched"),
            "severity": obj.get("severity"),
            "snippet": obj.get("snippet"),
        }
        return Observation(
            obs_id=_obs_id(tool, f"ioc.{rid}", rec, path_s),
            source_tool=tool,
            artifact_type=f"ioc.{rid}",
            summary=title[:200],
            entities=_entities_from_text(obj.get("matched"), obj.get("snippet")),
            payload=rec,
            provenance_path=path_s,
            confidence=float(obj.get("confidence") or 0.5),
            flags=[str(obj.get("severity") or "info")],
        )

    if obj.get("provider") and obj.get("artifact_type"):
        tool = default_tool or "nimbus_bridge"
        at = str(obj.get("artifact_type") or "cloud")
        rec = dict(obj.get("record") or {})
        summary = str(obj.get("summary") or _summary_from_record(at, rec))
        path_s = str(obj.get("source_path") or "")
        ts = _ts_ms(rec)
        label = str(rec.get("time") or "")
        return Observation(
            obs_id=_obs_id(tool, at, rec, path_s),
            source_tool=tool,
            artifact_type=at,
            summary=summary[:200],
            timestamp_unix_ms=ts,
            timestamp_label=label,
            entities=_entities_from_record(rec),
            payload=rec,
            provenance_path=path_s,
            confidence=float(obj.get("confidence") or 0.8),
            flags=[],
        )

    if "relative_path" in obj and "size_bytes" in obj:
        tool = default_tool or "truthrelic"
        rel = str(obj.get("relative_path") or "")
        rec = {
            "relative_path": rel,
            "size_bytes": obj.get("size_bytes"),
            "sha256": obj.get("sha256"),
            "mtime_epoch": obj.get("mtime_epoch"),
            "is_dir": obj.get("is_dir"),
        }
        return Observation(
            obs_id=_obs_id(tool, "fs.entry", rec, rel),
            source_tool=tool,
            artifact_type="fs.entry",
            summary=rel[:200],
            timestamp_unix_ms=_ts_ms(rec),
            payload=rec,
            provenance_path=rel,
            confidence=0.95,
            flags=["inventory"],
        )

    if "artifact_type" in obj:
        tool = default_tool or str(obj.get("source_tool") or "unknown")
        rec = dict(obj.get("record") or {})
        if not rec:
            skip = {
                "artifact_type", "summary", "source_path", "source_tool",
                "confidence", "flags", "domain", "file_id", "provenance", "quality",
            }
            rec = {k: v for k, v in obj.items() if k not in skip}
        at = str(obj.get("artifact_type") or "unknown")
        path_s = str(
            obj.get("source_path")
            or (obj.get("provenance") or {}).get("source_logical_path")
            or (obj.get("provenance") or {}).get("source_real_path")
            or ""
        )
        quality = obj.get("quality") or {}
        conf = obj.get("confidence")
        if conf is None:
            conf = quality.get("confidence") or 0.9
        flags = list(obj.get("flags") or quality.get("flags") or [])
        summary = str(obj.get("summary") or _summary_from_record(at, rec))
        ts = _ts_ms(rec)
        label = str(rec.get("date_iso") or rec.get("time") or "")
        ents = _entities_from_record(rec)
        if obj.get("entities"):
            ents = list(dict.fromkeys(list(obj["entities"]) + ents))
        return Observation(
            obs_id=_obs_id(tool, at, rec or {"summary": summary}, path_s),
            source_tool=tool,
            artifact_type=at,
            summary=summary[:200],
            timestamp_unix_ms=ts,
            timestamp_label=label,
            entities=ents,
            payload=rec,
            provenance_path=path_s,
            confidence=float(conf),
            flags=flags,
        )

    summary = str(obj.get("summary") or obj.get("text") or obj.get("title") or "")
    if not summary:
        return None
    tool = default_tool or str(obj.get("source_tool") or "generic")
    at = str(obj.get("artifact_type") or obj.get("type") or "generic")
    rec = dict(obj.get("record") or obj)
    path_s = str(obj.get("source_path") or obj.get("path") or "")
    ts = obj.get("timestamp_unix_ms") or _ts_ms(rec)
    try:
        ts_i = int(ts) if ts is not None else None
    except Exception:
        ts_i = None
    return Observation(
        obs_id=_obs_id(tool, at, {"summary": summary}, path_s),
        source_tool=tool,
        artifact_type=at,
        summary=summary[:200],
        timestamp_unix_ms=ts_i,
        entities=_entities_from_record(rec),
        payload=rec,
        provenance_path=path_s,
        confidence=float(obj.get("confidence") or 0.7),
        flags=[],
    )


def ingest_jsonl(path: Path, store: CaseStore, *, source_tool: str) -> Dict[str, int]:
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(path)
    added = 0
    skipped = 0
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                skipped += 1
                continue
            obs = normalize_row(obj, default_tool=source_tool)
            if obs is None:
                skipped += 1
                continue
            if source_tool and source_tool not in ("auto",):
                obs.source_tool = source_tool
            store.upsert_observation(obs)
            added += 1
    return {"added": added, "skipped": skipped, "tool": source_tool}


def ingest_excavator_jsonl(path: Path, store: CaseStore) -> Dict[str, int]:
    return ingest_jsonl(path, store, source_tool="android_excavator")


def ingest_idriller_jsonl(path: Path, store: CaseStore) -> Dict[str, int]:
    return ingest_jsonl(path, store, source_tool="idriller")


def ingest_memory_snare_jsonl(path: Path, store: CaseStore) -> Dict[str, int]:
    return ingest_jsonl(path, store, source_tool="memory_snare")


def ingest_recall_engine_jsonl(path: Path, store: CaseStore) -> Dict[str, int]:
    return ingest_jsonl(path, store, source_tool="recall_engine")


def ingest_pattern_harvester_jsonl(path: Path, store: CaseStore) -> Dict[str, int]:
    return ingest_jsonl(path, store, source_tool="pattern_harvester")


def ingest_integrity_breaker_jsonl(path: Path, store: CaseStore) -> Dict[str, int]:
    return ingest_jsonl(path, store, source_tool="integrity_breaker")


def ingest_nimbus_jsonl(path: Path, store: CaseStore) -> Dict[str, int]:
    return ingest_jsonl(path, store, source_tool="nimbus_bridge")


def ingest_truthrelic_jsonl(path: Path, store: CaseStore) -> Dict[str, int]:
    return ingest_jsonl(path, store, source_tool="truthrelic")


DISCOVERY_RULES: List[Tuple[str, str, str]] = [
    ("android_excavator", "artifacts.jsonl", "android_excavator"),
    ("memory_snare", "artifacts.jsonl", "memory_snare"),
    ("idriller", "artifacts.jsonl", "idriller"),
    ("recall_engine", "artifacts.jsonl", "recall_engine"),
    ("pattern_harvester", "findings.jsonl", "pattern_harvester"),
    ("integrity_breaker", "findings.jsonl", "integrity_breaker"),
    ("nimbus_bridge", "artifacts.jsonl", "nimbus_bridge"),
    ("truthrelic", "inventory.jsonl", "truthrelic"),
]


def discover_exports(root: Path) -> List[Tuple[Path, str]]:
    root = Path(root)
    found: List[Tuple[Path, str]] = []
    seen = set()
    for folder, fname, tool in DISCOVERY_RULES:
        for p in root.rglob(fname):
            try:
                rel = p.relative_to(root).as_posix().lower()
            except ValueError:
                rel = str(p).lower()
            if folder not in rel and tool not in rel:
                if p.parent.name.lower() not in (folder, tool):
                    continue
            key = str(p.resolve())
            if key in seen:
                continue
            try:
                if p.stat().st_size <= 0:
                    continue
            except OSError:
                continue
            seen.add(key)
            found.append((p, tool))
    return found


def ingest_directory(root: Path, store: CaseStore) -> Dict[str, Any]:
    results = []
    total = 0
    for path, tool in discover_exports(root):
        stats = ingest_jsonl(path, store, source_tool=tool)
        results.append({"path": str(path), **stats})
        total += stats.get("added", 0)
    return {"files": results, "total_added": total}
