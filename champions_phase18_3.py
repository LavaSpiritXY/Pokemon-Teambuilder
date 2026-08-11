"""Phase 18.3: polished Champions profile integration helpers.

Keeps rendering isolated while combining the Phase 18.2 analytics payload with
consistent display metadata. This module does not mutate the existing viability
engine or tournament metadata store.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from champions_phase18_2 import build_phase18_2_profile


def build_phase18_3_profile(
    pokemon_name: str,
    base_score: float,
    meta: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Return the display-ready Champions profile payload."""
    payload = build_phase18_2_profile(pokemon_name, base_score, meta)
    tournament = payload.get("tournament") or {}
    viability = payload.get("viability") or {}

    # Human-facing labels are derived here rather than altering source data.
    score = float(viability.get("adjusted_score", base_score) or base_score)
    if score >= 85:
        tier = "S"
    elif score >= 75:
        tier = "A"
    elif score >= 65:
        tier = "B"
    elif score >= 50:
        tier = "C"
    elif score >= 35:
        tier = "D"
    else:
        tier = "E"

    payload["display"] = {
        "name": pokemon_name,
        "viability_score": round(max(0.0, min(100.0, score)), 1),
        "viability_tier": tier,
        "tournament_available": bool(tournament.get("available")),
        "confidence": float(viability.get("confidence", 0.0) or 0.0),
    }
    return payload
