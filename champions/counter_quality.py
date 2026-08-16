"""Tournament-move quality layer for counter recommendations.

This sits above the core matchup engine so tournament move evidence can affect
ranking without changing the counter engine's public assessment API.

The rule is deliberately conservative:
- legal Champions learnset filtering remains owned by counter_engine;
- observed tournament moves receive a modest ranking advantage;
- a theoretical counter is never promoted solely because a move is popular;
- the original matchup score remains the dominant signal.
"""
from __future__ import annotations

from typing import Iterable, List


def _observed_move_strength(assessment) -> float:
    """Return the strongest observed tournament frequency in an assessment."""
    rows = getattr(assessment, "move_evidence", None) or []
    best = 0.0
    for row in rows:
        try:
            frequency = float(row.get("frequency", 0.0) or 0.0)
        except (TypeError, ValueError):
            continue
        if frequency > best:
            best = frequency
    return max(0.0, min(1.0, best))


def apply_tournament_move_quality(assessments: Iterable) -> List:
    """Apply a small, evidence-aware ranking adjustment to counter assessments.

    ``counter_engine`` already guarantees that observed moves are legal before
    they enter ``move_evidence``. This layer therefore does not perform a second
    learnset lookup or invent moves; it only rewards observed, matchup-relevant
    pressure that has real tournament frequency behind it.
    """
    output = list(assessments or [])
    for assessment in output:
        observed_strength = _observed_move_strength(assessment)
        if observed_strength <= 0.0:
            continue

        # Maximum adjustment is intentionally small relative to the core score.
        # A 100%-observed move gets +5; a 5%-observed move gets only +0.25.
        bonus = min(5.0, observed_strength * 5.0)
        assessment.score = min(100.0, float(getattr(assessment, "score", 0.0)) + bonus)

        confidence = float(getattr(assessment, "confidence", 0.0) or 0.0)
        assessment.confidence = min(1.0, confidence + min(0.05, observed_strength * 0.05))

        reasons = list(getattr(assessment, "reasons", []) or [])
        evidence_rows = getattr(assessment, "move_evidence", None) or []
        best_observed = max(
            evidence_rows,
            key=lambda row: float(row.get("frequency", 0.0) or 0.0),
            default=None,
        )
        if best_observed:
            move = str(best_observed.get("move") or "").strip()
            if move:
                reasons.append(
                    f"Tournament move evidence strengthens this route: {move} "
                    f"({observed_strength * 100:.0f}% observed)"
                )
        assessment.reasons = list(dict.fromkeys(reasons))

    output.sort(
        key=lambda item: (
            float(getattr(item, "score", -100.0) or -100.0),
            float(getattr(item, "confidence", 0.0) or 0.0),
            float(getattr(item, "matchup", 0.0) or 0.0),
            float(getattr(item, "tournament", 0.0) or 0.0),
        ),
        reverse=True,
    )
    return output
