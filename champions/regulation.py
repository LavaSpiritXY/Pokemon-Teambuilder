"""Helpers for selecting the active Pokémon Champions regulation.

The sync pipeline may discover both currently running and future regulation
announcements. These helpers deliberately separate *detected* regulations
from the regulation that is active as of a given date.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Tuple


_REGULATION_PREFIX = "M-"


def _normalise_regulation(value: Any) -> Optional[str]:
    text = str(value or "").strip().upper()
    if not text:
        return None
    if text.startswith(_REGULATION_PREFIX) and len(text) > 2:
        return text
    return None


def _parse_event_date(value: Any) -> Optional[date]:
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).date() if value.tzinfo else value.date()
    if isinstance(value, date):
        return value
    text = str(value or "").strip()
    if not text:
        return None

    candidate = text.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(candidate).date()
    except ValueError:
        pass

    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def select_active_champions_regulation(
    tournaments: Iterable[Dict[str, Any]],
    *,
    as_of: Optional[date] = None,
) -> Optional[str]:
    """Return the regulation belonging to the latest completed event.

    Future-dated events are ignored, so discovering a future regulation does
    not switch the application early. Rows without a usable date are ignored
    because they cannot safely establish which regulation is currently active.
    """
    reference_date = as_of or datetime.now(timezone.utc).date()
    best_date: Optional[date] = None
    best_regulation: Optional[str] = None

    for tournament in tournaments:
        if not isinstance(tournament, dict):
            continue

        regulation = _normalise_regulation(
            tournament.get("regulation") or tournament.get("format")
        )
        if not regulation:
            continue

        event_date = _parse_event_date(
            tournament.get("date")
            or tournament.get("start_date")
            or tournament.get("startDate")
        )
        if event_date is None or event_date > reference_date:
            continue

        completed = tournament.get("completed")
        if completed is False:
            continue

        if best_date is None or event_date >= best_date:
            best_date = event_date
            best_regulation = regulation

    return best_regulation


def get_active_regulation_from_history(
    history: Dict[str, Any],
    *,
    fallback: Optional[str] = None,
) -> Optional[str]:
    """Read the active regulation recorded by the automatic sync."""
    if not isinstance(history, dict):
        return _normalise_regulation(fallback)

    active = _normalise_regulation(history.get("active_regulation"))
    if active:
        return active

    return _normalise_regulation(fallback)


def update_history_regulation_metadata(
    path: Path,
    *,
    active_regulation: Optional[str],
    detected_regulations: Iterable[str] = (),
) -> Tuple[bool, Dict[str, Any]]:
    """Persist sync-derived regulation metadata without rebuilding history."""
    if not path.exists() or not path.stat().st_size:
        return False, {}

    try:
        history = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False, {}

    if not isinstance(history, dict):
        return False, {}

    active = _normalise_regulation(active_regulation)
    detected = sorted(
        {
            regulation
            for regulation in (
                _normalise_regulation(value) for value in detected_regulations
            )
            if regulation
        }
    )

    changed = (
        history.get("active_regulation") != active
        or history.get("detected_regulations") != detected
    )

    if not changed:
        return False, history

    history["active_regulation"] = active
    history["detected_regulations"] = detected
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(history, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporary.replace(path)

    # history_data.py caches the aggregate for runtime performance. The sync
    # job has just changed the on-disk payload, so invalidate that cache or a
    # running process can continue serving the pre-sync regulation metadata.
    try:
        from champions.history_data import load_champions_history
        load_champions_history.cache_clear()
    except ImportError:
        pass

    return True, history


__all__ = [
    "get_active_regulation_from_history",
    "select_active_champions_regulation",
    "update_history_regulation_metadata",
]
