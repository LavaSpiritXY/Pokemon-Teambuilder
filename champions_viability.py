"""Phase 16: Champions-aware viability and recommendation evidence.

This module sits between the existing Strategizer scoring engine and the
Champions tournament dataset.  It does not modify app.py or the existing
viability calculation yet.  It provides a deterministic, bounded tournament
adjustment that can be integrated safely in a later UI/scoring patch.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from champions_integration import get_champions_profile


MIN_APPEARANCES = 10
MAX_APPEARANCE_CONFIDENCE = 1.0
WIN_RATE_NEUTRAL = 0.50
TOP_CUT_NEUTRAL = 0.20
RECENT_WEIGHT = 0.35
OVERALL_WEIGHT = 0.65
MAX_TOURNAMENT_ADJUSTMENT = 18.0


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _confidence(appearances: int) -> float:
    if appearances <= 0:
        return 0.0
    return _clamp((appearances / 100.0) ** 0.5, 0.0, MAX_APPEARANCE_CONFIDENCE)


def get_champions_viability_evidence(pokemon_name: str) -> Dict[str, Any]:
    """Return bounded tournament evidence for one Pokémon.

    The evidence is intentionally separate from the existing app score.  A
    missing Pokémon, sparse sample, or malformed dataset never produces a
    positive or negative adjustment by accident.
    """
    profile = get_champions_profile(pokemon_name)
    if not profile.get("available"):
        return {
            "available": False,
            "pokemon": pokemon_name,
            "confidence": 0.0,
            "adjustment": 0.0,
            "evidence_score": 0.0,
            "partner_support": 0.0,
        }

    appearances = int(profile.get("appearances") or 0)
    win_rate = profile.get("win_rate")
    recent_win_rate = profile.get("recent_win_rate")
    top_cut_rate = profile.get("top_cut_rate")

    if win_rate is None or top_cut_rate is None or appearances < MIN_APPEARANCES:
        return {
            "available": True,
            "pokemon": pokemon_name,
            "confidence": _confidence(appearances),
            "adjustment": 0.0,
            "evidence_score": 0.0,
            "partner_support": 0.0,
        }

    win = _clamp(float(win_rate), 0.0, 1.0)
    recent = _clamp(float(recent_win_rate if recent_win_rate is not None else win), 0.0, 1.0)
    top_cut = _clamp(float(top_cut_rate), 0.0, 1.0)

    effective_win = (win * OVERALL_WEIGHT) + (recent * RECENT_WEIGHT)
    # Win rate is centred at 50%; top-cut rate is centred at 20%, matching the
    # historical dataset's broad tournament baseline rather than rewarding
    # raw usage by itself.
    win_signal = (effective_win - WIN_RATE_NEUTRAL) * 100.0
    top_cut_signal = (top_cut - TOP_CUT_NEUTRAL) * 100.0
    raw_signal = (win_signal * 0.70) + (top_cut_signal * 0.30)

    confidence = _confidence(appearances)
    adjustment = _clamp(raw_signal * 0.45 * confidence, -MAX_TOURNAMENT_ADJUSTMENT, MAX_TOURNAMENT_ADJUSTMENT)
    evidence_score = _clamp(50.0 + adjustment * (50.0 / MAX_TOURNAMENT_ADJUSTMENT), 0.0, 100.0)

    partners = profile.get("partners") or []
    partner_support = 0.0
    if partners:
        rates: List[float] = []
        for partner in partners[:5]:
            try:
                together = float(partner.get("teams_together") or 0)
                shared_rate = float(partner.get("shared_win_rate"))
            except (TypeError, ValueError):
                continue
            if together > 0:
                rates.append(_clamp(shared_rate, 0.0, 1.0))
        if rates:
            partner_support = _clamp(((sum(rates) / len(rates)) - 0.50) * 100.0, -50.0, 50.0)

    return {
        "available": True,
        "pokemon": pokemon_name,
        "appearances": appearances,
        "win_rate": win,
        "recent_win_rate": recent,
        "top_cut_rate": top_cut,
        "confidence": confidence,
        "adjustment": adjustment,
        "evidence_score": evidence_score,
        "partner_support": partner_support,
    }


def apply_champions_adjustment(base_score: float, pokemon_name: str) -> Dict[str, Any]:
    """Return a new score while leaving the caller's existing score untouched."""
    evidence = get_champions_viability_evidence(pokemon_name)
    base = _clamp(float(base_score), 0.0, 100.0)
    adjusted = _clamp(base + float(evidence.get("adjustment", 0.0)), 0.0, 100.0)
    return {
        **evidence,
        "base_score": base,
        "adjusted_score": adjusted,
    }


def rank_champions_partners(pokemon_name: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Return tournament partners ranked for recommendation display."""
    profile = get_champions_profile(pokemon_name)
    rows = []
    for partner in profile.get("partners") or []:
        try:
            together = int(partner.get("teams_together") or 0)
            shared_rate = float(partner.get("shared_win_rate"))
        except (TypeError, ValueError):
            continue
        if not partner.get("pokemon") or together <= 0:
            continue
        # Balance partnership frequency and successful shared results so a
        # one-off 100% pairing cannot outrank a genuinely established core.
        frequency = min(together / 100.0, 1.0)
        quality = _clamp((shared_rate - 0.45) / 0.15, 0.0, 1.0)
        recommendation_score = (frequency * 0.60) + (quality * 0.40)
        rows.append({
            **partner,
            "recommendation_score": recommendation_score,
        })
    rows.sort(key=lambda row: (row["recommendation_score"], row["teams_together"]), reverse=True)
    return rows[: max(0, int(limit))]
