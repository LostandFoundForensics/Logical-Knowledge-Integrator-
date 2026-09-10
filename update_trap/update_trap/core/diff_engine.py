"""
Update Trap — core/diff_engine.py
Computes the diff between two snapshots at three levels:
  1. File presence/absence/hash changes (Phase 1)
  2. SQLite table/column changes (Phase 1)
  3. Structured (JSON/plist/XML) key changes (Phase 2)
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from update_trap.core.models import Snapshot, SQLiteSchema, SQLiteTable, SQLiteColumn
from update_trap.core.logbook import LogBook


@dataclass
class PathChange:
    kind: str  # "added" | "removed" | "modified"
    rel_path: str
    old_sha256: str | None = None
    new_sha256: str | None = None


@dataclass
class SchemaChange:
    db_rel_path: str
    table: str
    change: str  # "table_added" | "table_removed" | "column_added" | "column_removed" | "column_changed"
    details: dict


@dataclass
class StructuredChange:
    rel_path: str
    kind: str                 # "json" | "plist" | "xml"
    change: str                # "added" | "removed" | "keys_added" | "keys_removed"
    details: dict


@dataclass
class DiffReport:
    baseline_label: str
    new_label: str
    path_changes: List[PathChange] = field(default_factory=list)
    schema_changes: List[SchemaChange] = field(default_factory=list)
    structured_changes: List[StructuredChange] = field(default_factory=list)

    def human_summary(self) -> str:
        lines = []
        lines.append(f"Baseline: {self.baseline_label}")
        lines.append(f"New: {self.new_label}")
        lines.append("")
        lines.append(f"Path changes: {len(self.path_changes)}")
        lines.append(f"SQLite schema changes: {len(self.schema_changes)}")
        lines.append(f"Structured-key changes: {len(self.structured_changes)}")
        if self.schema_changes:
            lines.append("")
            lines.append("Top schema changes (first 10):")
            for sc in self.schema_changes[:10]:
                lines.append(f"- {sc.db_rel_path} :: {sc.table} :: {sc.change}")
        if self.structured_changes:
            lines.append("")
            lines.append("Top structured-key changes (first 10):")
            for ch in self.structured_changes[:10]:
                lines.append(f"- {ch.rel_path} :: {ch.kind} :: {ch.change}")
        return "\n".join(lines)


class DiffEngine:
    def __init__(self, logbook: LogBook) -> None:
        self.logbook = logbook

    def diff(self, base: Snapshot, new: Snapshot) -> DiffReport:
        report = DiffReport(baseline_label=base.label, new_label=new.label)

        self.logbook.note("DiffEngine: computing file/path changes.")
        report.path_changes.extend(self._diff_files(base, new))

        self.logbook.note("DiffEngine: computing SQLite schema changes.")
        report.schema_changes.extend(self._diff_sqlite(base, new))

        self.logbook.note("DiffEngine: computing structured-key changes.")
        report.structured_changes.extend(self._diff_structured(base, new))

        self.logbook.note("DiffEngine: diff complete.")
        return report

    # ── File-level diff (Phase 1) ─────────────────────────────────────────────

    def _diff_files(self, base: Snapshot, new: Snapshot) -> List[PathChange]:
        out: List[PathChange] = []
        base_paths = set(base.files.keys())
        new_paths = set(new.files.keys())

        for p in sorted(new_paths - base_paths):
            out.append(PathChange(kind="added", rel_path=p, new_sha256=new.files[p].sha256))

        for p in sorted(base_paths - new_paths):
            out.append(PathChange(kind="removed", rel_path=p, old_sha256=base.files[p].sha256))

        for p in sorted(base_paths & new_paths):
            if base.files[p].sha256 != new.files[p].sha256:
                out.append(
                    PathChange(
                        kind="modified",
                        rel_path=p,
                        old_sha256=base.files[p].sha256,
                        new_sha256=new.files[p].sha256,
                    )
                )
        return out

    # ── SQLite schema diff (Phase 1) ───────────────────────────────────────────

    def _diff_sqlite(self, base: Snapshot, new: Snapshot) -> List[SchemaChange]:
        out: List[SchemaChange] = []
        base_dbs = set(base.sqlite_dbs.keys())
        new_dbs = set(new.sqlite_dbs.keys())

        for db in sorted(new_dbs - base_dbs):
            out.append(SchemaChange(db_rel_path=db, table="(db)", change="db_added", details={}))
        for db in sorted(base_dbs - new_dbs):
            out.append(SchemaChange(db_rel_path=db, table="(db)", change="db_removed", details={}))

        for db in sorted(base_dbs & new_dbs):
            out.extend(self._diff_one_schema(db, base.sqlite_dbs[db], new.sqlite_dbs[db]))

        return out

    def _diff_one_schema(self, db_rel: str, a: SQLiteSchema, b: SQLiteSchema) -> List[SchemaChange]:
        out: List[SchemaChange] = []
        a_tables = set(a.tables.keys())
        b_tables = set(b.tables.keys())

        for t in sorted(b_tables - a_tables):
            out.append(SchemaChange(db_rel_path=db_rel, table=t, change="table_added", details={}))

        for t in sorted(a_tables - b_tables):
            out.append(SchemaChange(db_rel_path=db_rel, table=t, change="table_removed", details={}))

        for t in sorted(a_tables & b_tables):
            out.extend(self._diff_table(db_rel, a.tables[t], b.tables[t]))

        return out

    def _diff_table(self, db_rel: str, a: SQLiteTable, b: SQLiteTable) -> List[SchemaChange]:
        out: List[SchemaChange] = []
        a_cols = {c.name: c for c in a.columns}
        b_cols = {c.name: c for c in b.columns}

        for c in sorted(b_cols.keys() - a_cols.keys()):
            out.append(
                SchemaChange(
                    db_rel_path=db_rel,
                    table=a.name,
                    change="column_added",
                    details={"column": c, "new": _col_to_dict(b_cols[c])},
                )
            )
        for c in sorted(a_cols.keys() - b_cols.keys()):
            out.append(
                SchemaChange(
                    db_rel_path=db_rel,
                    table=a.name,
                    change="column_removed",
                    details={"column": c, "old": _col_to_dict(a_cols[c])},
                )
            )

        for c in sorted(a_cols.keys() & b_cols.keys()):
            if not _cols_equivalent(a_cols[c], b_cols[c]):
                out.append(
                    SchemaChange(
                        db_rel_path=db_rel,
                        table=a.name,
                        change="column_changed",
                        details={"column": c, "old": _col_to_dict(a_cols[c]), "new": _col_to_dict(b_cols[c])},
                    )
                )
        return out

    # ── Structured-key diff (Phase 2) ───────────────────────────────────────────

    def _diff_structured(self, base: Snapshot, new: Snapshot) -> List[StructuredChange]:
        out: List[StructuredChange] = []
        a = base.structured_files
        b = new.structured_files
        a_paths = set(a.keys())
        b_paths = set(b.keys())

        for p in sorted(b_paths - a_paths):
            out.append(StructuredChange(
                rel_path=p, kind=b[p].kind, change="added",
                details={"keys_count": len(b[p].keys)},
            ))

        for p in sorted(a_paths - b_paths):
            out.append(StructuredChange(
                rel_path=p, kind=a[p].kind, change="removed",
                details={"keys_count": len(a[p].keys)},
            ))

        for p in sorted(a_paths & b_paths):
            # If the structural kind itself changed (e.g. json -> plist),
            # treat it as a removal followed by an addition rather than
            # trying to diff incompatible key sets.
            if a[p].kind != b[p].kind:
                out.append(StructuredChange(
                    rel_path=p, kind=a[p].kind, change="removed",
                    details={"reason": "kind changed"},
                ))
                out.append(StructuredChange(
                    rel_path=p, kind=b[p].kind, change="added",
                    details={"reason": "kind changed"},
                ))
                continue

            a_keys = set(a[p].keys)
            b_keys = set(b[p].keys)
            added = sorted(b_keys - a_keys)
            removed = sorted(a_keys - b_keys)

            if added:
                out.append(StructuredChange(
                    rel_path=p, kind=a[p].kind, change="keys_added",
                    details={"count": len(added), "sample": added[:25]},
                ))
            if removed:
                out.append(StructuredChange(
                    rel_path=p, kind=a[p].kind, change="keys_removed",
                    details={"count": len(removed), "sample": removed[:25]},
                ))

        return out


def _cols_equivalent(x: SQLiteColumn, y: SQLiteColumn) -> bool:
    return (
        (x.col_type or "").lower() == (y.col_type or "").lower()
        and bool(x.notnull) == bool(y.notnull)
        and (x.default or None) == (y.default or None)
        and bool(x.pk) == bool(y.pk)
    )


def _col_to_dict(c: SQLiteColumn) -> dict:
    return {"name": c.name, "type": c.col_type, "notnull": c.notnull, "default": c.default, "pk": c.pk}
