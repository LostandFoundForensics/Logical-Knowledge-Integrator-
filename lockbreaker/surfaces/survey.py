"""
Phase 0 — Access Surface Survey.

Always run first. Always safe. Produces a plain-language map of lawful entry points.
"""
from __future__ import annotations

from typing import Any, Dict, List

from lockbreaker.surfaces.detectors import ALL_DETECTORS, SurfaceResult


def survey_access_surfaces(ctx: Dict[str, Any] | None = None) -> List[SurfaceResult]:
    ctx = ctx or {}
    results: List[SurfaceResult] = []
    for detector in ALL_DETECTORS:
        try:
            results.append(detector(ctx))
        except Exception as e:
            results.append(
                SurfaceResult(
                    surface_id="detector_error",
                    label="Detector error",
                    status="not_available",
                    why=f"{getattr(detector, '__name__', detector)}: {e}",
                    risk_level="low",
                )
            )
    return results


def summarize_survey(results: List[SurfaceResult]) -> Dict[str, Any]:
    available = [r for r in results if r.status == "available"]
    partial = [r for r in results if r.status == "partially_available"]
    missing = [r for r in results if r.status == "not_available"]
    return {
        "available": [r.surface_id for r in available],
        "partially_available": [r.surface_id for r in partial],
        "not_available": [r.surface_id for r in missing],
        "available_count": len(available),
        "surfaces": [r.to_dict() for r in results],
    }
