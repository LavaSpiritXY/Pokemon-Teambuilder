"""Phase 18.2: form-aware Champions analytics and evidence-ranked checks.

This layer keeps the existing Strategizer score isolated. It combines the
existing metadata result with the read-only Champions tournament evidence and
normalises display/form names through champions_meta's resolver.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from champions_integration import get_champions_profile
from champions_meta import _candidate_keys
from champions_viability import apply_champions_adjustment


def resolve_tournament_identity(pokemon_name: str) -> Dict[str, Any]:
    """Return the exact/fallback tournament identity used for a display name."""
    candidates = _candidate_keys(pokemon_name)
    profile = get_champions_profile(pokemon_name)
    return {
        "display_name": pokemon_name,
        "candidates": candidates,
        "available": bool(profile.get("available")),
        "resolved_key": candidates[0] if candidates else "",
        "profile": profile,
    }


def build_tournament_viability(base_score: float, pokemon_name: str) -> Dict[str, Any]:
    """Expose score, evidence score and contribution without mutating base scoring."""
    result = apply_champions_adjustment(base_score, pokemon_name)
    result["tournament_contribution"] = float(result.get("adjustment", 0.0))
    result["evidence_confidence"] = float(result.get("confidence", 0.0))
    result["evidence_score"] = float(result.get("evidence_score", 0.0))
    return result


def _counter_score(candidate: Dict[str, Any]) -> float:
    """Rank a known meta check using evidence without pretending it is a matchup win rate."""
    appearances = max(0.0, float(candidate.get("appearances") or 0))
    win_rate = candidate.get("win_rate")
    try:
        win = max(0.0, min(1.0, float(win_rate))) if win_rate is not None else 0.5
    except (TypeError, ValueError):
        win = 0.5
    frequency = min(appearances / 500.0, 1.0)
    return (frequency * 0.55) + (win * 0.45)


def rank_meta_checks(pokemon_name: str, candidates: Iterable[Any], limit: int = 6) -> List[Dict[str, Any]]:
    """Rank existing app counter/check candidates with Champions evidence.

    The tournament dataset does not contain pairwise battle results, so this
    deliberately does not manufacture a fake counter win rate. Candidates are
    still matchup checks from the existing engine, while tournament usage and
    win rate determine which checks are most relevant to the current meta.
    """
    rows: List[Dict[str, Any]] = []
    seen = set()
    for entry in candidates or []:
        if isinstance(entry, (list, tuple)):
            name = entry[0] if entry else ""
        elif isinstance(entry, dict):
            name = entry.get("pokemon") or entry.get("name") or ""
        else:
            name = entry
        name = str(name or "").strip()
        if not name:
            continue
        key = " ".join(name.lower().split())
        if key in seen or key == " ".join(pokemon_name.lower().split()):
            continue
        seen.add(key)
        profile = get_champions_profile(name)
        row = {
            "pokemon": name,
            "available": bool(profile.get("available")),
            "appearances": int(profile.get("appearances") or 0),
            "win_rate": profile.get("win_rate"),
            "confidence": 0.0,
            "relevance_score": 0.0,
        }
        appearances = row["appearances"]
        row["confidence"] = min((appearances / 100.0) ** 0.5, 1.0) if appearances else 0.0
        row["relevance_score"] = _counter_score(row)
        rows.append(row)
    rows.sort(key=lambda r: (r["relevance_score"], r["appearances"]), reverse=True)
    return rows[: max(0, int(limit))]


def build_phase18_2_profile(
    pokemon_name: str,
    base_score: float,
    meta: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build one safe, display-ready analytics payload."""
    identity = resolve_tournament_identity(pokemon_name)
    profile = identity["profile"]
    viability = build_tournament_viability(base_score, pokemon_name)
    meta = dict(meta or {})
    checks = rank_meta_checks(pokemon_name, meta.get("counters") or [])
    return {
        "pokemon": pokemon_name,
        "identity": identity,
        "tournament": profile,
        "viability": viability,
        "speed_tier": meta.get("speed_tier", "N/A"),
        "offensive_profile": meta.get("offensive_profile", "N/A"),
        "momentum_rating": meta.get("momentum_rating", "N/A"),
        "hazard_utility": meta.get("hazard_utility", "N/A"),
        "counters": checks,
        "partners": list(profile.get("partners") or [])[:6],
    }
