"""Fast practical ranking for already-computed counter assessments.

This layer intentionally performs no network requests.  The core counter engine
has already computed matchup, survival, move quality, speed and tournament
signals, so we can rank those assessments using a practical blend without
adding latency to Pokémon or move lookups.

The core matchup score remains dominant.  Tournament evidence is supporting
evidence rather than a substitute for actually being able to pressure and
survive the target.
"""
from __future__ import annotations

from typing import Iterable, List


def _value(assessment, name: str, default: float = 0.0) -> float:
    try:
        return float(getattr(assessment, name, default) or default)
    except (TypeError, ValueError):
        return default


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def _practical_score(assessment) -> float:
    """Blend independent evidence into a practical 0-100 counter score."""
    core = _value(assessment, "score")
    matchup = _value(assessment, "matchup")
    survival = _value(assessment, "survival")
    move_quality = _value(assessment, "move_quality")
    speed = _value(assessment, "speed")
    tournament = _value(assessment, "tournament")
    confidence = _value(assessment, "confidence") * 100.0

    # Core matchup remains the largest signal.  Tournament data helps answer
    # "is this actually practical in the format?" but cannot create a counter
    # from a weak matchup by itself.
    score = (
        core * 0.55
        + matchup * 0.15
        + survival * 0.12
        + move_quality * 0.08
        + speed * 0.03
        + tournament * 0.04
        + confidence * 0.03
    )

    # A candidate with no verified pressure route should never receive a high
    # practical score just because its defensive or tournament numbers look good.
    if not list(getattr(assessment, "best_moves", []) or []):
        score *= 0.65

    # Very poor survival means the counter is usually theoretical rather than
    # repeatable, even when the type matchup looks attractive.
    if survival < 40.0:
        score *= 0.88

    return _clamp(score)


def apply_practical_counter_ranking(assessments: Iterable) -> List:
    """Attach practical scores and return assessments in practical order.

    No data fetching occurs here, keeping this layer effectively free compared
    with the batch Pokémon-data fetch that precedes it.
    """
    output = list(assessments or [])
    for assessment in output:
        core = _value(assessment, "score")
        practical = _practical_score(assessment)
        bonus = _clamp((practical - core) * 0.15, -3.0, 3.0)

        # Keep the original score meaningful while allowing practical evidence
        # to break close calls.  The separate practical_score attribute is the
        # full ranking signal and is also useful to the UI/debug output.
        assessment.practical_score = round(practical, 3)
        assessment.practical_bonus = round(bonus, 3)
        assessment.score = _clamp(core + bonus)

        reasons = list(getattr(assessment, "reasons", []) or [])
        reasons.append(f"Practical counter score: {practical:.1f}/100")
        assessment.reasons = list(dict.fromkeys(reasons))

    output.sort(
        key=lambda item: (
            _value(item, "practical_score"),
            _value(item, "score"),
            _value(item, "confidence"),
            _value(item, "matchup"),
        ),
        reverse=True,
    )
    return output
