"""
Pokémon Champions tournament data layer.

PHASE 1
-------
This module is intentionally isolated from app.py.

It does NOT fetch tournament data yet and it does NOT modify the existing
Strategizer.  It provides the stable data structures, normalization helpers,
and HTTP/caching primitives that the later tournament importer will use.

Keeping this separate is deliberate: if a tournament source changes, we want
to repair this module rather than introduce more tournament logic into the
main Streamlit application.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import re
from typing import Any, Dict, List, Optional, Tuple

import requests


# ============================================================================
# 1. CONFIGURATION
# ============================================================================

# The current Champions tournament data layer is kept separate from the
# application's existing CURRENT_REGULATION value.  We will populate this
# from verified event data in a later phase rather than hard-coding it here.
CHAMPIONS_DATA_VERSION = 1

# Network defaults.  These are deliberately conservative so a future data
# importer cannot accidentally hammer a public tournament-data service.
REQUEST_TIMEOUT_SECONDS = 20
REQUEST_HEADERS = {
    "User-Agent": "Pokemon-Teambuilder/ChampionsData (+https://github.com/LavaSpiritXY/Pokemon-Teambuilder)"
}


# ============================================================================
# 2. NORMALIZED DATA STRUCTURES
# ============================================================================

@dataclass
class ChampionsEvent:
    """A normalized Champions tournament/event record."""

    event_id: str
    name: str = ""
    date: Optional[str] = None
    location: str = ""
    regulation: str = ""
    event_type: str = ""
    player_count: int = 0
    source: str = ""
    source_url: str = ""
    official: bool = False


@dataclass
class ChampionsResult:
    """A normalized player result from one tournament."""

    event_id: str
    player_name: str
    placement: Optional[int] = None
    wins: int = 0
    losses: int = 0
    draws: int = 0
    top_cut: bool = False


@dataclass
class ChampionsTeam:
    """A normalized tournament team."""

    event_id: str
    player_name: str
    pokemon: List[str] = field(default_factory=list)


# ============================================================================
# 3. POKÉMON NAME NORMALIZATION
# ============================================================================

# Separators commonly introduced by tournament websites, spreadsheets, or
# URLs.  We preserve the actual form information while producing a stable key.
_NAME_SEPARATORS = re.compile(r"[\s_./]+")


def normalize_champions_name(name: Any) -> str:
    """Return a human-readable, stable Pokémon/form name.

    This is intentionally conservative in Phase 1.  It does NOT try to guess
    forms from an arbitrary string.  The detailed Champions form mapping will
    be added once the real tournament payload has been inspected.
    """

    if name is None:
        return ""

    value = str(name).strip()
    if not value:
        return ""

    value = value.replace("–", "-").replace("—", "-")
    value = _NAME_SEPARATORS.sub(" ", value)
    value = re.sub(r"\s+", " ", value).strip()

    return value


def champions_species_key(name: Any) -> str:
    """Return the canonical lookup key used by the Champions data layer.

    The key is intentionally deterministic.  Form-aware aliases will be
    added later and will all pass through this single function.
    """

    normalized = normalize_champions_name(name)
    if not normalized:
        return ""

    return normalized.casefold().replace(" ", "-")


# ============================================================================
# 4. SAFE HTTP PRIMITIVES
# ============================================================================

_SESSION: Optional[requests.Session] = None


def get_http_session() -> requests.Session:
    """Return one reusable HTTP session for future tournament requests."""

    global _SESSION

    if _SESSION is None:
        _SESSION = requests.Session()
        _SESSION.headers.update(REQUEST_HEADERS)

    return _SESSION


def fetch_json(url: str, *, timeout: int = REQUEST_TIMEOUT_SECONDS) -> Any:
    """Fetch JSON from a verified endpoint.

    This function is intentionally generic.  No Limitless/RK9 endpoint is
    hard-coded until the source format has been verified.

    Raises:
        ValueError: if the response is not valid JSON.
        requests.RequestException: for network/HTTP failures.
    """

    if not isinstance(url, str) or not url.strip():
        raise ValueError("A non-empty URL is required.")

    response = get_http_session().get(url.strip(), timeout=timeout)
    response.raise_for_status()

    try:
        return response.json()
    except ValueError as exc:
        raise ValueError(
            f"Expected JSON from tournament data source, got {response.headers.get('content-type', 'unknown')}"
        ) from exc


# ============================================================================
# 5. IN-MEMORY DATA CONTAINER
# ============================================================================

@dataclass
class ChampionsDataStore:
    """Container for normalized tournament data.

    This is deliberately an in-memory object for Phase 1.  Persistent caching
    will be added only after the source payload and update strategy are tested.
    """

    events: Dict[str, ChampionsEvent] = field(default_factory=dict)
    results: List[ChampionsResult] = field(default_factory=list)
    teams: List[ChampionsTeam] = field(default_factory=list)
    updated_at: Optional[str] = None

    def mark_updated(self) -> None:
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def clear(self) -> None:
        self.events.clear()
        self.results.clear()
        self.teams.clear()
        self.updated_at = None


# One process-local store.  It is not connected to Streamlit yet.
CHAMPIONS_DATA_STORE = ChampionsDataStore()


# ============================================================================
# 6. FUTURE INTEGRATION POINTS
# ============================================================================


def get_cached_event(event_id: Any) -> Optional[ChampionsEvent]:
    """Return an already-normalized event, if present."""

    key = str(event_id).strip()
    if not key:
        return None
    return CHAMPIONS_DATA_STORE.events.get(key)


def store_event(event: ChampionsEvent) -> None:
    """Store one normalized event."""

    if not event.event_id:
        raise ValueError("ChampionsEvent.event_id cannot be empty.")

    CHAMPIONS_DATA_STORE.events[str(event.event_id)] = event
    CHAMPIONS_DATA_STORE.mark_updated()


def store_result(result: ChampionsResult) -> None:
    """Store one normalized tournament result."""

    if not result.event_id or not result.player_name:
        raise ValueError("ChampionsResult requires event_id and player_name.")

    CHAMPIONS_DATA_STORE.results.append(result)
    CHAMPIONS_DATA_STORE.mark_updated()


def store_team(team: ChampionsTeam) -> None:
    """Store one normalized tournament team."""

    if not team.event_id or not team.player_name:
        raise ValueError("ChampionsTeam requires event_id and player_name.")

    team.pokemon = [
        normalize_champions_name(name)
        for name in team.pokemon
        if normalize_champions_name(name)
    ]

    CHAMPIONS_DATA_STORE.teams.append(team)
    CHAMPIONS_DATA_STORE.mark_updated()


__all__ = [
    "CHAMPIONS_DATA_VERSION",
    "REQUEST_TIMEOUT_SECONDS",
    "ChampionsEvent",
    "ChampionsResult",
    "ChampionsTeam",
    "ChampionsDataStore",
    "CHAMPIONS_DATA_STORE",
    "normalize_champions_name",
    "champions_species_key",
    "get_http_session",
    "fetch_json",
    "get_cached_event",
    "store_event",
    "store_result",
    "store_team",
]
