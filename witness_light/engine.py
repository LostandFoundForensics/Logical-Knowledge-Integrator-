"""
Witness Light — engine.py
Phase 2 draft generator.
Operates on artifact reference metadata only — never on evidence content.
Emits only the five allowed sentence classes.
"""
from __future__ import annotations

from typing import List

from models import (
    ArtifactRef,
    Draft,
    DraftParagraph,
    Intent,
    Purpose,
    SentenceClass,
    now_iso,
)
from policy import enforce_paragraph_policy, require_disclaimer

CONF_MAP = {"High": "High", "Medium": "Medium", "Low": "Low"}


def _truthloom_confidence(artifact: ArtifactRef) -> str:
    if artifact.truthloom_header is None:
        return "Inconclusive"
    env = artifact.truthloom_header.confidence_envelope.strip().capitalize()
    return CONF_MAP.get(env, "Inconclusive")


def generate_phase2_draft(
    case_id: str,
    purpose: Purpose,
    intent: Intent,
    artifacts: List[ArtifactRef],
) -> Draft:
    """
    Phase 2 generator:
    - Uses only artifact reference metadata (no content)
    - Emits Observed / Context / Limitation / Unknown / Consistent With only
    - Inherits Truthloom confidence but never elevates it
    - Fail-closed on any banned phrasing via policy enforcement
    """
    paragraphs: List[DraftParagraph] = []

    for a in artifacts:
        conf = _truthloom_confidence(a)
        dsids = [a.truthloom_header.dataset_id] if a.truthloom_header else []

        # ── Observed ──────────────────────────────────────────────────────────
        paragraphs.append(
            DraftParagraph(
                sentence_class=SentenceClass.OBSERVED,
                text=(
                    f"Artifact {a.artifact_id} is present as a reference generated "
                    f"by {a.source_tool} at {a.extraction_time_iso}. "
                    f"Hash recorded: {a.hash_value}."
                ),
                artifact_ids=[a.artifact_id],
                truthloom_dataset_ids=dsids,
                confidence=conf,
            )
        )

        # ── Limitation ────────────────────────────────────────────────────────
        lims = list(a.known_limitations or [])
        if a.truthloom_header and a.truthloom_header.known_failure_modes:
            lims += [
                f"Known failure mode: {m}"
                for m in a.truthloom_header.known_failure_modes
            ]

        if lims:
            paragraphs.append(
                DraftParagraph(
                    sentence_class=SentenceClass.LIMITATION,
                    text=(
                        "Limitations noted for this artifact: "
                        + "; ".join(lims)
                        + "."
                    ),
                    artifact_ids=[a.artifact_id],
                    truthloom_dataset_ids=dsids,
                    confidence="High",
                )
            )
        else:
            paragraphs.append(
                DraftParagraph(
                    sentence_class=SentenceClass.LIMITATION,
                    text=(
                        "No specific limitations were provided with this artifact "
                        "reference; absence of listed limitations does not imply "
                        "completeness."
                    ),
                    artifact_ids=[a.artifact_id],
                    truthloom_dataset_ids=dsids,
                    confidence="Medium",
                )
            )

        # ── Unknown ───────────────────────────────────────────────────────────
        paragraphs.append(
            DraftParagraph(
                sentence_class=SentenceClass.UNKNOWN,
                text=(
                    "This reference alone does not establish what the underlying "
                    "evidence contains, only that a referenced artifact exists and "
                    "was recorded at extraction time."
                ),
                artifact_ids=[a.artifact_id],
                truthloom_dataset_ids=dsids,
                confidence="High",
            )
        )

    # ── Context (one block covering all artifacts) ────────────────────────────
    if artifacts:
        paragraphs.append(
            DraftParagraph(
                sentence_class=SentenceClass.CONTEXT,
                text=(
                    "Artifact references may originate from different acquisition "
                    "methods and scopes. The absence of a record in a given artifact "
                    "set may reflect extraction scope limits, encryption, app retention "
                    "behavior, or OS logging constraints."
                ),
                artifact_ids=[a.artifact_id for a in artifacts],
                truthloom_dataset_ids=[
                    a.truthloom_header.dataset_id
                    for a in artifacts
                    if a.truthloom_header
                ],
                confidence="Medium",
            )
        )

    # ── Consistent With (only for Truthloom-validated artifacts) ─────────────
    for a in artifacts:
        if a.truthloom_header:
            paragraphs.append(
                DraftParagraph(
                    sentence_class=SentenceClass.CONSISTENT_WITH,
                    text=(
                        f"The artifact type '{a.truthloom_header.artifact_type}' is "
                        f"consistent with Truthloom validation dataset "
                        f"{a.truthloom_header.dataset_id} for OS "
                        f"{a.truthloom_header.os_version_tested} and app "
                        f"{a.truthloom_header.app_version_tested}, within the "
                        f"documented validation envelope."
                    ),
                    artifact_ids=[a.artifact_id],
                    truthloom_dataset_ids=[a.truthloom_header.dataset_id],
                    confidence=_truthloom_confidence(a),
                )
            )

    # ── Policy enforcement (fail closed) ─────────────────────────────────────
    paragraphs = enforce_paragraph_policy(paragraphs)

    return Draft(
        case_id=case_id,
        purpose=purpose,
        intent=intent,
        created_time_iso=now_iso(),
        disclaimer=require_disclaimer(purpose.value),
        paragraphs=paragraphs,
    )
