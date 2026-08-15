"""Helpers for selecting the active Pokémon Champions regulation.

The sync pipeline may discover both currently running and future regulation
announcements.  These helpers deliberately separate *detected* regulations
from the regulation that is active as of a given date.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any, Dict, Iterable, Optional


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

    # Accept the ISO forms commonly returned by Limitless.
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
    not switch the application early.  When multiple completed events share a
    date, the later row wins deterministically.  Rows without a usable date
    are ignored because they cannot safely establish which regulation is
    currently active.
    """
    reference_date = as_of or datetime.now(timezone.utc).date()
    best_date: Optional[date] = None
    best_regulation: Optional[str] = None

    for tournament in tournaments:
        if not isinstance(tournament, dict):
            continue

        regulation = _normalise_regulation(
            tournament.get("regulation")
            or tournament.get("format")
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

        # If an explicit completion flag exists, respect it.  Do not reject
        # rows where the source simply omits that flag; the event date is the
        # useful completed-event signal in the discovery feed.
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
    """Read the active regulation recorded by the automatic sync.

    Older history files do not have this metadata, so the supplied fallback
    remains available during the migration.  We never guess an active
    regulation from the presence of a future regulation alone.
    """
    if not isinstance(history, dict):
        return _normalise_regulation(fallback)

    active = _normalise_regulation(history.get("active_regulation"))
    if active:
        return active

    return _normalise_regulation(fallback)


__all__ = [
    "get_active_regulation_from_history",
    "select_active_champions_regulation",
]
