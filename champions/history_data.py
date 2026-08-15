"""Read-only access to the aggregated Pokémon Champions tournament history.

The sync job writes ``champions_meta_history.json``. This module exposes a
small, regulation-aware API for the application so consumers do not need to
know the generated JSON schema or manually combine overall/recent metrics.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional


DEFAULT_HISTORY_PATH = Path("champions_meta_history.json")


def _canonical_key(name: Any) -> str:
    return str(name or "").strip().lower()


def _safe_non_negative_int(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def _safe_rate(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return None


@lru_cache(maxsize=1)
def load_champions_history(path: Optional[str] = None) -> Dict[str, Any]:
    """Load the aggregated Champions history once per Python process."""
    history_path = Path(path) if path is not None else DEFAULT_HISTORY_PATH
    if not history_path.exists():
        return {}

    try:
        with history_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return {}

    return payload if isinstance(payload, dict) else {}


def get_history_pokemon_record(
    pokemon_name: Any,
    *,
    regulation: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Return one aggregated Pokémon record, optionally filtered by regulation.

    The aggregate stores regulation-level appearance counts, while win/top-cut
    metrics are stored overall and for the recent window. We never fabricate
    regulation-specific rates that are not present in the source data.
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


def get_history_regulation_appearances(
    pokemon_name: Any,
    regulation: Optional[str],
) -> Optional[int]:
    """Return tournament team appearances in one regulation."""
    if not regulation:
        return None

    record = get_history_pokemon_record(pokemon_name)
    if not record:
        return None

    regulations = record.get("regulations") or {}
    key = str(regulation).strip().upper()
    if key not in regulations:
        return None

    return _safe_non_negative_int(regulations.get(key))


def get_history_metrics(
    pokemon_name: Any,
    *,
    regulation: Optional[str] = None,
    current_regulation: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Return clean overall, recent, and regulation-aware history metrics.

    ``overall`` contains full-history counts and rates.
    ``recent`` contains the generated recent-window signals.
    ``current`` contains regulation presence/appearances and leaves rates as
    ``None`` unless regulation-specific rate data exists in the aggregate.
    """
    record = get_history_pokemon_record(pokemon_name, regulation=regulation)
    if not record:
        return None

    requested_regulation = str(regulation).strip().upper() if regulation else None
    active_regulation = (
        str(current_regulation).strip().upper()
        if current_regulation else None
    )

    overall_appearances = _safe_non_negative_int(record.get("appearances"))
    overall_wins = _safe_non_negative_int(record.get("wins"))
    overall_losses = _safe_non_negative_int(record.get("losses"))
    overall_top_cuts = _safe_non_negative_int(record.get("top_cut_count"))

    overall_win_rate = _safe_rate(record.get("win_rate"))
    if overall_win_rate is None and overall_wins + overall_losses:
        overall_win_rate = overall_wins / (overall_wins + overall_losses)

    overall_top_cut_rate = _safe_rate(record.get("top_cut_rate"))
    if overall_top_cut_rate is None and overall_appearances:
        overall_top_cut_rate = overall_top_cuts / overall_appearances

    recent_usage_weight = max(
        0.0,
        float(record.get("recent_usage_weight", 0.0) or 0.0),
    )
    recent_win_rate = _safe_rate(record.get("recent_win_rate"))
    recent_top_cut_rate = _safe_rate(record.get("recent_top_cut_rate"))

    current_key = requested_regulation or active_regulation
    current_appearances = get_history_regulation_appearances(
        pokemon_name,
        current_key,
    )

    regulations = record.get("regulations") or {}
    regulation_available = bool(current_key and current_key in regulations)

    return {
        "pokemon": _canonical_key(pokemon_name),
        "display_name": record.get("display_name", pokemon_name),
        "requested_regulation": requested_regulation,
        "current_regulation": active_regulation,
        "regulation_available": regulation_available,
        "regulations": {
            str(key).strip().upper(): _safe_non_negative_int(value)
            for key, value in regulations.items()
        },
        "overall": {
            "appearances": overall_appearances,
            "wins": overall_wins,
            "losses": overall_losses,
            "top_cut_count": overall_top_cuts,
            "win_rate": overall_win_rate,
            "top_cut_rate": overall_top_cut_rate,
        },
        "recent": {
            "usage_weight": recent_usage_weight,
            "win_rate": recent_win_rate,
            "top_cut_rate": recent_top_cut_rate,
        },
        "current": {
            "regulation": current_key,
            "appearances": current_appearances,
            "win_rate": _safe_rate(
                (record.get("regulation_metrics") or {})
                .get(current_key, {})
                .get("win_rate")
            ) if current_key else None,
            "top_cut_rate": _safe_rate(
                (record.get("regulation_metrics") or {})
                .get(current_key, {})
                .get("top_cut_rate")
            ) if current_key else None,
            "win_rate_available": bool(
                current_key
                and _safe_rate(
                    (record.get("regulation_metrics") or {})
                    .get(current_key, {})
                    .get("win_rate")
                ) is not None
            ),
            "top_cut_rate_available": bool(
                current_key
                and _safe_rate(
                    (record.get("regulation_metrics") or {})
                    .get(current_key, {})
                    .get("top_cut_rate")
                ) is not None
            ),
        },
    }


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
    """Translate history into the legacy CHAMPIONS_META_DB shape."""
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
                frequency = _safe_non_negative_int(partner.get("teams_together"))
                if frequency:
                    partners[partner_key] = frequency

        appearances = _safe_non_negative_int(source.get("appearances"))
        wins = _safe_non_negative_int(source.get("wins"))
        losses = _safe_non_negative_int(source.get("losses"))
        top_cuts = _safe_non_negative_int(source.get("top_cut_count"))

        database[_canonical_key(key)] = {
            "appearances": appearances,
            "wins": wins,
            "losses": losses,
            "match_records": 1 if wins + losses else 0,
            "top_cuts": top_cuts,
            "usage": float(source.get("recent_usage_weight", 0.0) or 0.0),
            "win_rate": _safe_rate(source.get("win_rate")),
            "top_cut_rate": _safe_rate(source.get("top_cut_rate")) or 0.0,
            "partners": partners,
            "roles": {},
            "moves": {},
            "abilities": {},
            "items": {},
            "display_name": source.get("display_name", key),
            "historical_recent_win_rate": _safe_rate(source.get("recent_win_rate")),
            "historical_recent_top_cut_rate": _safe_rate(source.get("recent_top_cut_rate")),
            "historical_regulations": {
                str(reg_key).strip().upper(): _safe_non_negative_int(value)
                for reg_key, value in (source.get("regulations") or {}).items()
            },
        }

    return database


__all__ = [
    "DEFAULT_HISTORY_PATH",
    "load_champions_history",
    "get_history_pokemon_record",
    "get_history_regulation_appearances",
    "get_history_metrics",
    "get_history_partners",
    "build_legacy_meta_db",
]
