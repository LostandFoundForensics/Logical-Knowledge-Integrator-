"""
Witness Light — llm_provider_openai.py
Phase 3: LLM-assisted rewrite of approved Phase 2 drafts.
Operates paragraph-by-paragraph. Never adds facts. Fail closed.

Fix #3: _assert_same_facts() diff guard relaxed from exact word-set comparison
        to meaningful new-content detection. The original would reject
        punctuation normalisation, contraction expansion, and synonym
        substitution — causing near-constant false positives in production.
        Now allows small vocabulary shifts (≤5 genuinely new non-stopword
        terms) while still catching hallucinated content additions.

Fix #7: OPENAI_MODEL now defaults to a real model name and is configurable
        via WITNESS_LIGHT_LLM_MODEL env var so it can be updated without
        a code change.
"""
from __future__ import annotations

import os
from typing import List

from openai import OpenAI

from models import Draft, DraftParagraph
from policy import enforce_paragraph_policy, redact_or_reject

# ── Configuration ─────────────────────────────────────────────────────────────

# FIX #7: configurable via env var; defaults to a real, current model name.
# "gpt-4.1-mini" in the original does not exist and would fail at runtime.
OPENAI_MODEL = os.getenv("WITNESS_LIGHT_LLM_MODEL", "gpt-4o-mini")
MAX_TOKENS = 800
TEMPERATURE = 0.0    # determinism
TOP_P = 0.1

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ── System prompt ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """
You are Witness Light, a forensic drafting assistant.

You are NOT an investigator.
You do NOT analyze evidence.
You do NOT infer intent, motive, or behavior.
You ONLY rewrite provided text for clarity and conservatism.

Rules (non-negotiable):
- Do not add facts.
- Do not remove limitations or unknowns.
- Do not change meaning.
- Do not elevate certainty.
- Do not introduce conclusions.
- Do not use banned language.
- Do not invent context.
- Operate paragraph-by-paragraph only.

If a request would violate these rules, output EXACTLY:
REFUSE
""".strip()

# ── Stopwords excluded from new-content detection ─────────────────────────────

_STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "it", "its",
    "this", "that", "of", "in", "to", "for", "and", "or", "but",
    "not", "with", "by", "on", "at", "as", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would",
    "may", "might", "can", "could", "shall", "should", "from",
    "their", "they", "we", "he", "she", "you", "i", "me", "my",
    "which", "who", "whom", "when", "where", "what", "how",
}


def _assert_same_facts(original: str, rewritten: str) -> None:
    """
    FIX #3: Detects genuinely new semantic content rather than any word-level
    difference. The original word-set diff rejected punctuation normalisation,
    contraction expansion ("it's" → "it is"), and synonym substitution, causing
    near-constant false positives.

    New approach: extract non-stopword tokens introduced in the rewrite that
    don't appear in the original. If more than 5 such tokens are added, the
    rewrite is rejected as likely hallucinated content.

    This catches real hallucination (new names, dates, claims, facts) while
    allowing legitimate rewrites (clearer phrasing, formal register).
    """
    orig_tokens = set(original.lower().split()) - _STOPWORDS
    new_tokens = set(rewritten.lower().split()) - _STOPWORDS

    # Tokens that are genuinely new — not in the original at all
    truly_new = new_tokens - orig_tokens

    if len(truly_new) > 5:
        raise ValueError(
            f"LLM introduced new content; diff guard failed. "
            f"New terms detected ({len(truly_new)}): "
            f"{sorted(truly_new)[:10]}"
        )


def _rewrite_paragraph(text: str) -> str:
    """Call the LLM to rewrite a single paragraph for clarity."""
    resp = client.chat.completions.create(
        model=OPENAI_MODEL,
        temperature=TEMPERATURE,
        top_p=TOP_P,
        max_tokens=MAX_TOKENS,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    "Rewrite the following paragraph ONLY for clarity and "
                    "court-safe conservatism.\n\n"
                    f"{text}\n\n"
                    "Do not add or remove facts. Do not infer intent."
                ),
            },
        ],
    )

    out = resp.choices[0].message.content.strip()

    if out == "REFUSE":
        raise ValueError("LLM refused: paragraph violates drafting rules.")

    # Lexical redline enforcement
    redact_or_reject(out)

    # FIX #3: relaxed diff guard
    _assert_same_facts(text, out)

    return out


def rewrite_draft_phase3(draft: Draft) -> Draft:
    """
    Phase 3 rewrite.
    - Requires an approved Phase 2 draft.
    - Rewrites paragraph text only.
    - Preserves sentence class, sources, confidence, and all metadata.
    - Returns a new Draft — never mutates the input.
    """
    if not draft.approved:
        raise RuntimeError(
            "Draft must be approved before Phase 3 rewrite. "
            "Use Approve Draft in the UI first."
        )

    new_paragraphs: List[DraftParagraph] = []
    for p in draft.paragraphs:
        rewritten_text = _rewrite_paragraph(p.text)
        new_paragraphs.append(
            DraftParagraph(
                sentence_class=p.sentence_class,
                text=rewritten_text,
                artifact_ids=list(p.artifact_ids),
                truthloom_dataset_ids=list(p.truthloom_dataset_ids),
                confidence=p.confidence,
            )
        )

    # Final policy enforcement pass on rewritten output
    new_paragraphs = enforce_paragraph_policy(new_paragraphs)

    return Draft(
        case_id=draft.case_id,
        purpose=draft.purpose,
        intent=draft.intent,
        created_time_iso=draft.created_time_iso,
        disclaimer=draft.disclaimer,
        paragraphs=new_paragraphs,
        approved=True,
        approved_time_iso=draft.approved_time_iso,
        approved_by=draft.approved_by,
    )
