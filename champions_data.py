"""
Pokémon Champions tournament data layer.

PHASE 2
-------
This module is intentionally isolated from app.py.

Phase 2 establishes the verified Limitless VGC source connection and keeps
raw event-page fetching separate from parsing/analytics.  It does NOT yet
populate CHAMPIONS_META_DB or alter the existing Streamlit application.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import re
from typing import Any, Dict, List, Optional

import requests


# ============================================================================
# 1. CONFIGURATION
# ============================================================================

CHAMPIONS_DATA_VERSION = 2
REQUEST_TIMEOUT_SECONDS = 20

LIMITLESS_BASE_URL = "https://limitlessvgc.com"
LIMITLESS_TOURNAMENTS_URL = f"{LIMITLESS_BASE_URL}/tournaments"

REQUEST_HEADERS = {
    "User-Agent": (
        "Pokemon-Teambuilder/ChampionsData "
        "(+https://github.com/LavaSpiritXY/Pokemon-Teambuilder)"
    )
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

_NAME_SEPARATORS = re.compile(r"[\s_./]+")


def normalize_champions_name(name: Any) -> str:
    """Return a human-readable, stable Pokémon/form name."""

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
    """Return the canonical lookup key used by the Champions data layer."""

    normalized = normalize_champions_name(name)
    if not normalized:
        return ""

    return normalized.casefold().replace(" ", "-")


# ============================================================================
# 4. SAFE HTTP PRIMITIVES
# ============================================================================

_SESSION: Optional[requests.Session] = None


def get_http_session() -> requests.Session:
    """Return one reusable HTTP session for tournament requests."""

    global _SESSION

    if _SESSION is None:
        _SESSION = requests.Session()
        _SESSION.headers.update(REQUEST_HEADERS)

    return _SESSION


def fetch_text(url: str, *, timeout: int = REQUEST_TIMEOUT_SECONDS) -> str:
    """Fetch a text/HTML page from a verified source URL."""

    if not isinstance(url, str) or not url.strip():
        raise ValueError("A non-empty URL is required.")

    response = get_http_session().get(url.strip(), timeout=timeout)
    response.raise_for_status()
    return response.text


def fetch_json(url: str, *, timeout: int = REQUEST_TIMEOUT_SECONDS) -> Any:
    """Fetch JSON from a verified endpoint.

    No unverified Limitless JSON endpoint is assumed here.  The current
    source pages are public HTML pages, so HTML fetching is the primary Phase
    2 primitive.  JSON support remains available for a later verified source.
    """

    if not isinstance(url, str) or not url.strip():
        raise ValueError("A non-empty URL is required.")

    response = get_http_session().get(url.strip(), timeout=timeout)
    response.raise_for_status()

    try:
        return response.json()
    except ValueError as exc:
        raise ValueError(
            "Expected JSON from tournament data source, got "
            f"{response.headers.get('content-type', 'unknown')}"
        ) from exc


# ============================================================================
# 5. VERIFIED LIMITLESS URL BUILDERS
# ============================================================================


def build_limitless_tournament_url(event_id: Any, section: str = "") -> str:
    """Build a Limitless tournament URL without accepting arbitrary URLs."""

    event_key = str(event_id).strip()
    if not event_key:
        raise ValueError("event_id cannot be empty.")

    allowed_sections = {"", "teams", "statistics", "standings"}
    if section not in allowed_sections:
        raise ValueError(
            f"Unsupported tournament section: {section!r}. "
            f"Expected one of {sorted(allowed_sections)!r}."
        )

    url = f"{LIMITLESS_BASE_URL}/tournaments/{event_key}"
    if section:
        url += f"/{section}"

    return url


def fetch_limitless_tournament_page(
    event_id: Any,
    section: str = "",
    *,
    timeout: int = REQUEST_TIMEOUT_SECONDS,
) -> str:
    """Fetch one verified Limitless tournament page as raw HTML.

    Sections currently verified against the public Limitless site:
      - ``""``: results page
      - ``"teams"``: tournament team lists
      - ``"statistics"``: tournament Pokémon statistics
      - ``"standings"``: detailed standings/usage information where present

    Parsing is deliberately NOT performed here.  Keeping raw retrieval
    separate lets us inspect and test the source format before creating
    permanent parsers.
    """

    url = build_limitless_tournament_url(event_id, section)
    return fetch_text(url, timeout=timeout)


# ============================================================================
# 6. IN-MEMORY DATA CONTAINER
# ============================================================================

@dataclass
class ChampionsDataStore:
    """Container for normalized tournament data."""

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


CHAMPIONS_DATA_STORE = ChampionsDataStore()


# ============================================================================
# 7. DATA STORE HELPERS
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
    "LIMITLESS_BASE_URL",
    "LIMITLESS_TOURNAMENTS_URL",
    "ChampionsEvent",
    "ChampionsResult",
    "ChampionsTeam",
    "ChampionsDataStore",
    "CHAMPIONS_DATA_STORE",
    "normalize_champions_name",
    "champions_species_key",
    "get_http_session",
    "fetch_text",
    "fetch_json",
    "build_limitless_tournament_url",
    "fetch_limitless_tournament_page",
    "get_cached_event",
    "store_event",
    "store_result",
    "store_team",
]
