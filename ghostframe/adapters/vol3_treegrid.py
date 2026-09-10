"""
Convert a Volatility 3 TreeGrid into plain list-of-dicts rows.

Original Ghostframe code — does not copy Volatility source.
We only consume the public TreeGrid / TreeNode API.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


def _cell_to_plain(value: Any) -> Any:
    """Turn Volatility render types into JSON-friendly Python values."""
    if value is None:
        return None
    # Volatility uses sentinel types for missing values
    name = type(value).__name__
    if name in (
        "UnreadableValue",
        "NotApplicableValue",
        "NotAvailableValue",
        "UnparsableValue",
    ):
        return None
    if hasattr(value, "strftime"):
        try:
            return value.strftime("%Y-%m-%dT%H:%M:%S")
        except Exception:
            return str(value)
    if isinstance(value, (bytes, bytearray)):
        try:
            return value.hex()
        except Exception:
            return repr(value)
    if isinstance(value, (int, float, bool, str)):
        return value
    # Hex / format hint wrappers often stringify usefully
    try:
        return str(value)
    except Exception:
        return repr(value)


def treegrid_to_rows(treegrid: Any, *, max_rows: int = 100_000) -> List[Dict[str, Any]]:
    """
    Walk a TreeGrid and return a list of dicts keyed by column name.

    Safe upper bound on rows so a runaway plugin cannot exhaust memory.
    """
    if treegrid is None:
        return []

    columns = []
    try:
        columns = [c.name for c in treegrid.columns]
    except Exception:
        return []

    rows: List[Dict[str, Any]] = []

    def visitor(node: Any, _acc: Any) -> Any:
        if len(rows) >= max_rows:
            return _acc
        try:
            values = list(node.values)
        except Exception:
            return _acc
        row: Dict[str, Any] = {}
        for i, col in enumerate(columns):
            if i < len(values):
                row[col] = _cell_to_plain(values[i])
            else:
                row[col] = None
        rows.append(row)
        return _acc

    try:
        treegrid.populate(visitor, None)
    except Exception:
        # Partial results still useful
        pass
    return rows
