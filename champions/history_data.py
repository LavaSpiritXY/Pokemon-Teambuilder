"""Read-only access to the aggregated Champions tournament history.

This module is deliberately independent from app.py.  The aggregation job
writes ``champions_meta_history.json`` and this module provides a small,
stable compatibility API for the existing tournament-data layer.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional


DEFAULT_HISTORY_PATH = Path("champions_meta_history.json")


@lru_cache(maxsize=1)
def load_champions_history(
    path: str = str(DEFAULT_HISTORY_PATH),
) -> Dict[str, Any]:
    """Load the aggregated Champions history once per Python process.

    Missing or malformed history is treated as unavailable rather than making
    the existing app fail to import.  The caller can therefore continue using
    the old empty-database behaviour until the generated history file exists.
    """

    history_path = Path(path)
    if not history_path.exists():
        return {}

    try:
        with history_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return {}

    return payload if isinstance(payload, dict) else {}


def _canonical_key(name: Any) -> str:
    return str(name or "").strip().lower()


def get_history_pokemon_record(
    pokemon_name: Any,
    *,
    regulation: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Return one aggregated Pokémon record from Champions history.

    The historical aggregation currently stores Pokémon metrics across all
    imported regulations.  A regulation filter is therefore only used as a
    presence check: it never fabricates regulation-specific win rates from
    data that was not stored at that granularity.
    """

    key = _canonical_key(pokemon_name)
    if not key:
        return None

    record = (load_champions_history().get("pokemon") or {}).get(key)
    if not isinstance(record, dict):
        return None

    if regulation:
        regulation_key = str(regulation).strip().upper()
        regulations = record.get("regulations") or {}
        if regulation_key and not regulations.get(regulation_key):
            return None

    return record


def get_history_partners(
    pokemon_name: Any,
    *,
    top_n: int = 10,
) -> List[Dict[str, Any]]:
    """Return tournament partners in their aggregated ranking order."""

    key = _canonical_key(pokemon_name)
    if not key or top_n <= 0:
        return []

    partners = (load_champions_history().get("partners") or {}).get(key)
    if not isinstance(partners, list):
        return []

    results: List[Dict[str, Any]] = []
    for partner in partners:
        if not isinstance(partner, dict):
            continue
        partner_key = _canonical_key(partner.get("pokemon"))
        if not partner_key:
            continue
        results.append(partner)
        if len(results) >= top_n:
            break

    return results


def build_legacy_meta_db(
    *,
    regulation: Optional[str] = None,
) -> Dict[str, Dict[str, Any]]:
    """Translate the new history format into the old CHAMPIONS_META_DB shape.

    This keeps the existing scoring functions working without requiring app.py
    changes.  Partner frequencies are copied from the aggregated partner
    records; they are intentionally not presented as regulation-specific.
    """

    history = load_champions_history()
    pokemon_records = history.get("pokemon") or {}
    partner_records = history.get("partners") or {}

    if not isinstance(pokemon_records, dict):
        return {}

    database: Dict[str, Dict[str, Any]] = {}

    for key, source in pokemon_records.items():
        if not isinstance(source, dict):
            continue

        if regulation:
            regulation_key = str(regulation).strip().upper()
            regulations = source.get("regulations") or {}
            if regulation_key and not regulations.get(regulation_key):
                continue

        partners: Dict[str, int] = {}
        partner_list = partner_records.get(key, [])
        if isinstance(partner_list, list):
            for partner in partner_list:
                if not isinstance(partner, dict):
                    continue
                partner_key = _canonical_key(partner.get("pokemon"))
                if not partner_key:
                    continue
                try:
                    frequency = max(0, int(partner.get("teams_together", 0) or 0))
                except (TypeError, ValueError):
                    frequency = 0
                if frequency:
                    partners[partner_key] = frequency

        appearances = max(0, int(source.get("appearances", 0) or 0))
        wins = max(0, int(source.get("wins", 0) or 0))
        losses = max(0, int(source.get("losses", 0) or 0))
        top_cuts = max(0, int(source.get("top_cut_count", 0) or 0))

        database[_canonical_key(key)] = {
            "appearances": appearances,
            "wins": wins,
            "losses": losses,
            "match_records": 1 if wins + losses else 0,
            "top_cuts": top_cuts,
            "usage": float(source.get("recent_usage_weight", 0.0) or 0.0),
            "win_rate": source.get("win_rate"),
            "top_cut_rate": float(source.get("top_cut_rate", 0.0) or 0.0),
            "partners": partners,
            "roles": {},
            "moves": {},
            "abilities": {},
            "items": {},
            "display_name": source.get("display_name", key),
            "historical_recent_win_rate": source.get("recent_win_rate"),
            "historical_recent_top_cut_rate": source.get("recent_top_cut_rate"),
            "historical_regulations": dict(source.get("regulations") or {}),
        }

    return database


__all__ = [
    "DEFAULT_HISTORY_PATH",
    "load_champions_history",
    "get_history_pokemon_record",
    "get_history_partners",
    "build_legacy_meta_db",
]
