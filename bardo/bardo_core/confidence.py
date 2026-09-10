from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional
from .schema import TimeAssertion, TimeSource


# Source weight table — how much to trust each timestamp source
SOURCE_WEIGHTS: dict[TimeSource, float] = {
    TimeSource.FILESYSTEM: 0.90,
    TimeSource.APP_LOG:    0.85,
    TimeSource.SYSTEM_LOG: 0.80,
    TimeSource.CLOUD_LOG:  0.88,
    TimeSource.INFERRED:   0.45,
}

# Conflict penalty — applied when sources disagree
CONFLICT_PENALTY = 0.25


@dataclass
class ConfidenceResult:
    score: float
    basis: str
    warnings: List[str]

    @property
    def label(self) -> str:
        if self.score >= 0.90: return "HIGH"
        if self.score >= 0.70: return "MEDIUM"
        if self.score >= 0.50: return "LOW"
        return "VERY_LOW"


def score_time_assertions(assertions: List[TimeAssertion]) -> ConfidenceResult:
    """
    Aggregates confidence across multiple TimeAssertions for the same event.
    Rewards agreement, penalizes conflict, weights by source reliability.
    """
    if not assertions:
        return ConfidenceResult(0.0, "No time assertions", ["No timestamps available"])

    if len(assertions) == 1:
        a = assertions[0]
        weight = SOURCE_WEIGHTS.get(a.source, 0.50)
        score = a.confidence * weight
        return ConfidenceResult(
            score=round(score, 3),
            basis=f"Single assertion from {a.source.value}",
            warnings=[],
        )

    warnings: List[str] = []

    # Check for conflict — do assertions agree within a tolerance?
    datetimes = [a.best_datetime for a in assertions if a.best_datetime]
    conflict = False
    if len(datetimes) >= 2:
        timestamps_sec = sorted(dt.timestamp() for dt in datetimes)
        spread_sec = timestamps_sec[-1] - timestamps_sec[0]
        if spread_sec > 120:  # more than 2 minutes apart = conflict
            conflict = True
            warnings.append(
                f"Timestamp conflict: {len(datetimes)} sources disagree by "
                f"{spread_sec:.0f} seconds. Corroborate before asserting timing."
            )

    # Weighted average of individual confidences
    total_weight = 0.0
    weighted_sum = 0.0
    for a in assertions:
        w = SOURCE_WEIGHTS.get(a.source, 0.50)
        weighted_sum += a.confidence * w
        total_weight += w

    base_score = weighted_sum / total_weight if total_weight > 0 else 0.0

    # Apply conflict penalty
    if conflict:
        base_score = max(0.0, base_score - CONFLICT_PENALTY)
        warnings.append(
            f"Confidence reduced by {CONFLICT_PENALTY} due to source conflict."
        )

    # Bonus for corroboration (multiple sources agree)
    if not conflict and len(assertions) >= 2:
        corroboration_bonus = min(0.10, 0.03 * (len(assertions) - 1))
        base_score = min(1.0, base_score + corroboration_bonus)

    sources = ", ".join(sorted(set(a.source.value for a in assertions)))
    return ConfidenceResult(
        score=round(base_score, 3),
        basis=f"Aggregated from {len(assertions)} assertion(s): {sources}",
        warnings=warnings,
    )


def aggregate_artifact_confidence(individual_scores: List[float]) -> float:
    """
    Combines confidence scores from multiple artifacts supporting a single event.
    Uses a diminishing returns model — each additional artifact adds less.
    """
    if not individual_scores:
        return 0.0
    if len(individual_scores) == 1:
        return individual_scores[0]

    # Sort descending — strongest evidence first
    scores = sorted(individual_scores, reverse=True)
    result = scores[0]
    for s in scores[1:]:
        # Each additional artifact contributes diminishingly
        result = result + (1 - result) * s * 0.5

    return round(min(1.0, result), 3)


def tool_agreement_score(scores_by_tool: dict[str, float]) -> ConfidenceResult:
    """
    Scores agreement between multiple tools that reported the same finding.
    Used by conflict detection to decide whether to trust or flag.
    """
    if not scores_by_tool:
        return ConfidenceResult(0.0, "No tool scores", ["No tools provided data"])

    tools = list(scores_by_tool.keys())
    scores = list(scores_by_tool.values())
    warnings = []

    if len(scores) == 1:
        return ConfidenceResult(
            scores[0],
            f"Single tool: {tools[0]}",
            ["Only one tool — corroboration not possible"],
        )

    spread = max(scores) - min(scores)
    avg = sum(scores) / len(scores)

    if spread > 0.30:
        warnings.append(
            f"Tools disagree significantly (spread={spread:.2f}). "
            "Manual review recommended before asserting this finding."
        )
        avg = max(0.0, avg - 0.20)

    return ConfidenceResult(
        score=round(avg, 3),
        basis=f"Agreement across {len(tools)} tools: {', '.join(tools)}",
        warnings=warnings,
    )
