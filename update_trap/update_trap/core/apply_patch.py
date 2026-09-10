"""
Update Trap — core/apply_patch.py
Applies an APPROVED patch (never a suggested one) to a parser's config.
Config-only — never touches parser code, never auto-applies a suggestion
that hasn't been through human review.

Fix applied: the original `cfg["tables"][table]["columns"][old] = new`
raised a raw KeyError if the table named in the approved patch wasn't
present in cfg["tables"] — e.g. if the parser config on disk was stale,
malformed, or the table was renamed/removed since the patch was
generated. Now raises a clear, named ValueError instead, and the same
guard is applied to cfg["paths"] in case a config is missing that key
entirely.
"""
from __future__ import annotations
import json
import copy
from typing import Any, Dict


def apply_approved_patch(config_path: str, approved_patch_path: str) -> Dict[str, Any]:
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    with open(approved_patch_path, "r", encoding="utf-8") as f:
        patch = json.load(f)

    original = copy.deepcopy(cfg)
    changes = patch.get("changes", {})

    # ── Path overrides ────────────────────────────────────────────────────────
    if "paths" not in cfg:
        cfg["paths"] = []
    for p in changes.get("path_overrides", []):
        if p not in cfg["paths"]:
            cfg["paths"].append(p)

    # ── Column maps ───────────────────────────────────────────────────────────
    # FIX: guard against a missing table instead of raising a raw KeyError.
    for db_table, maps in changes.get("column_map", {}).items():
        if "::" not in db_table:
            raise ValueError(
                f"Malformed db_table key in approved patch: '{db_table}' "
                f"(expected format 'db_glob::table_name')"
            )
        _, table = db_table.split("::", 1)

        if "tables" not in cfg or table not in cfg["tables"]:
            raise ValueError(
                f"Approved patch {patch.get('patch_id', '(unknown)')} references "
                f"table '{table}' (from '{db_table}'), but that table is not "
                f"present in the parser config at {config_path}. "
                f"The config may be stale or the table may have been renamed "
                f"or removed since this patch was generated — re-verify before "
                f"re-attempting."
            )

        if "columns" not in cfg["tables"][table]:
            cfg["tables"][table]["columns"] = {}

        for old, new in maps.items():
            cfg["tables"][table]["columns"][old] = new

    return {
        "before": original,
        "after": cfg,
    }
