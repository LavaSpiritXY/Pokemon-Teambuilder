"""Phase 14: safe integration layer for Champions tournament metrics.

This module deliberately does not modify the existing Strategizer scoring.
It exposes a small, defensive API that app.py can consume in a later phase.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

try:
    from champions_meta import get_champions_meta
except ImportError:  # pragma: no cover
    get_champions_meta = None


def get_champions_profile(pokemon_name: str) -> Dict[str, Any]:
    """Return display-ready Champions statistics for one Pokémon.

    Missing data is represented safely instead of raising an exception, so
    importing this module cannot break the existing application.
    """
    empty: Dict[str, Any] = {
        "available": False,
        "pokemon": pokemon_name,
        "appearances": 0,
        "wins": 0,
        "losses": 0,
        "draws": 0,
        "win_rate": None,
        "top_cut_rate": None,
        "recent_win_rate": None,
        "partners": [],
        "regulations": {},
    }

    if not pokemon_name or get_champions_meta is None:
        return empty

    try:
        raw = get_champions_meta(pokemon_name)
    except Exception:
        return empty

    if not raw:
        return empty

    profile = dict(empty)
    profile.update(raw)
    profile["available"] = True
    profile["pokemon"] = pokemon_name
    profile["partners"] = list(profile.get("partners") or [])
    profile["regulations"] = dict(profile.get("regulations") or {})
    return profile


def champions_profile_summary(pokemon_name: str) -> Optional[str]:
    """Create a concise UI-safe summary, or None when data is unavailable."""
    profile = get_champions_profile(pokemon_name)
    if not profile["available"]:
        return None

    appearances = int(profile.get("appearances") or 0)
    win_rate = profile.get("win_rate")
    top_cut_rate = profile.get("top_cut_rate")

    parts = [f"{appearances} tournament team appearances"]
    if win_rate is not None:
        parts.append(f"{float(win_rate) * 100:.1f}% win rate")
    if top_cut_rate is not None:
        parts.append(f"{float(top_cut_rate) * 100:.1f}% top-cut rate")
    return " · ".join(parts)
