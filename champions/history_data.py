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


@lru_cache(maxsize=8)
def _load_champions_history_cached(
    path: str,
    modified_ns: int,
    file_size: int,
) -> Dict[str, Any]:
    """Load history using the file revision as part of the cache key.

    The sync workflow replaces ``champions_meta_history.json``. Using the
    modification timestamp and size in the cache key means a long-running
    Streamlit process automatically sees the new history without requiring a
    restart or a manual cache clear.
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


def _history_revision(path: Path) -> tuple[int, int]:
    """Return a cheap filesystem revision token for the generated history."""
    try:
        stat = path.stat()
        return stat.st_mtime_ns, stat.st_size
    except OSError:
        return 0, 0


def load_champions_history(path: Optional[str] = None) -> Dict[str, Any]:
    """Load aggregated history and automatically invalidate after file changes."""
    history_path = Path(path) if path is not None else DEFAULT_HISTORY_PATH
    modified_ns, file_size = _history_revision(history_path)
    return _load_champions_history_cached(
        str(history_path),
        modified_ns,
        file_size,
    )


def history_revision(path: Optional[str] = None) -> str:
    """Return a stable revision token for cache keys in higher-level analytics."""
    history_path = Path(path) if path is not None else DEFAULT_HISTORY_PATH
    modified_ns, file_size = _history_revision(history_path)
    return f"{modified_ns}:{file_size}"


def get_history_pokemon_record(
    pokemon_name: Any,
    *,
    regulation: Optional[str] = None,
    history_path: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Return one aggregated Pokémon record, optionally filtered by regulation."""
    key = _canonical_key(pokemon_name)
    if not key:
        return None

    record = (load_champions_history(history_path).get("pokemon") or {}).get(key)
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
    *,
    history_path: Optional[str] = None,
) -> Optional[int]:
    """Return tournament team appearances in one regulation."""
    if not regulation:
        return None

    record = get_history_pokemon_record(pokemon_name, history_path=history_path)
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
    history_path: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Return clean overall, recent, and regulation-aware history metrics."""
    record = get_history_pokemon_record(
        pokemon_name,
        regulation=regulation,
        history_path=history_path,
    )
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

    recent_usage_weight = max(0.0, float(record.get("recent_usage_weight", 0.0) or 0.0))
    recent_win_rate = _safe_rate(record.get("recent_win_rate"))
    recent_top_cut_rate = _safe_rate(record.get("recent_top_cut_rate"))

    current_key = requested_regulation or active_regulation
    current_appearances = get_history_regulation_appearances(
        pokemon_name,
        current_key,
        history_path=history_path,
    )

    regulations = record.get("regulations") or {}
    regulation_metrics = record.get("regulation_metrics") or {}
    current_metrics = regulation_metrics.get(current_key, {}) if current_key else {}
    if not isinstance(current_metrics, dict):
        current_metrics = {}

    current_win_rate = _safe_rate(current_metrics.get("win_rate"))
    current_top_cut_rate = _safe_rate(current_metrics.get("top_cut_rate"))
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
            "win_rate": current_win_rate,
            "top_cut_rate": current_top_cut_rate,
            "win_rate_available": current_win_rate is not None,
            "top_cut_rate_available": current_top_cut_rate is not None,
        },
    }


def get_history_partners(
    pokemon_name: Any,
    *,
    top_n: int = 10,
    history_path: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Return tournament partners in their aggregated ranking order."""
    key = _canonical_key(pokemon_name)
    if not key or top_n <= 0:
        return []

    partners = (load_champions_history(history_path).get("partners") or {}).get(key)
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
    "history_revision",
    "get_history_pokemon_record",
    "get_history_regulation_appearances",
    "get_history_metrics",
    "get_history_partners",
    "build_legacy_meta_db",
]
