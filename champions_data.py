"""
Pokémon Champions tournament data layer.

PHASE 3
-------
This module now connects to the documented Limitless Tournament API.

Important: this module is STILL isolated from app.py.  It does not populate
CHAMPIONS_META_DB and does not alter the Streamlit application yet.

The verified source for Pokémon Champions community tournament data is the
Limitless Tournament Platform API.  Its VGC tournaments use the VGC game ID,
while Champions regulations currently appear as Regulation M-A / M-B.
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

CHAMPIONS_DATA_VERSION = 3
REQUEST_TIMEOUT_SECONDS = 20

LIMITLESS_BASE_URL = "https://play.limitlesstcg.com"
LIMITLESS_API_BASE_URL = f"{LIMITLESS_BASE_URL}/api"
LIMITLESS_TOURNAMENTS_URL = f"{LIMITLESS_BASE_URL}/tournaments"

# Champions regulations are deliberately represented as a set.  We will
# continue adding future Champions regulation IDs here when verified rather
# than changing the application's main CURRENT_REGULATION by hand.
CHAMPIONS_REGULATIONS = {
    "M-A",
    "M-B",
}

REQUEST_HEADERS = {
    "User-Agent": (
        "Pokemon-Teambuilder/ChampionsData "
        "(+https://github.com/LavaSpiritXY/Pokemon-Teambuilder)"
    ),
    "Accept": "application/json",
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
    source: str = "Limitless"
    source_url: str = ""
    official: bool = False


@dataclass
class ChampionsResult:
    """A normalized player result from one tournament."""

    event_id: str
    player_name: str
    player_id: str = ""
    placement: Optional[int] = None
    wins: int = 0
    losses: int = 0
    draws: int = 0
    top_cut: bool = False
    dropped_round: Optional[int] = None
    decklist: Any = None


@dataclass
class ChampionsTeam:
    """A normalized tournament team."""

    event_id: str
    player_name: str
    pokemon: List[str] = field(default_factory=list)
    raw_decklist: Any = None


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


def fetch_json(url: str, *, timeout: int = REQUEST_TIMEOUT_SECONDS) -> Any:
    """Fetch JSON from a verified Limitless API URL."""

    if not isinstance(url, str) or not url.strip():
        raise ValueError("A non-empty URL is required.")

    response = get_http_session().get(url.strip(), timeout=timeout)
    response.raise_for_status()

    try:
        return response.json()
    except ValueError as exc:
        raise ValueError(
            "Expected JSON from Limitless, got "
            f"{response.headers.get('content-type', 'unknown')}"
        ) from exc


def fetch_text(url: str, *, timeout: int = REQUEST_TIMEOUT_SECONDS) -> str:
    """Fetch a text/HTML page when a public page is needed for diagnostics."""

    if not isinstance(url, str) or not url.strip():
        raise ValueError("A non-empty URL is required.")

    response = get_http_session().get(url.strip(), timeout=timeout)
    response.raise_for_status()
    return response.text


# ============================================================================
# 5. LIMITLESS API URL BUILDERS
# ============================================================================


def build_limitless_api_url(path: str, **params: Any) -> str:
    """Build a Limitless API URL using only the documented API base."""

    clean_path = str(path).strip().lstrip("/")
    if not clean_path:
        raise ValueError("API path cannot be empty.")

    url = f"{LIMITLESS_API_BASE_URL}/{clean_path}"

    encoded = []
    for key, value in params.items():
        if value is None or value == "":
            continue
        encoded.append(
            f"{key}={requests.utils.quote(str(value), safe='')}"
        )

    if encoded:
        url += "?" + "&".join(encoded)

    return url


def build_limitless_tournament_url(event_id: Any, section: str = "") -> str:
    """Build a public Limitless tournament URL."""

    event_key = str(event_id).strip()
    if not event_key:
        raise ValueError("event_id cannot be empty.")

    allowed_sections = {"", "details", "standings", "pairings", "metagame"}
    if section not in allowed_sections:
        raise ValueError(
            f"Unsupported tournament section: {section!r}. "
            f"Expected one of {sorted(allowed_sections)!r}."
        )

    url = f"{LIMITLESS_BASE_URL}/tournament/{event_key}"
    if section:
        url += f"/{section}"

    return url


# ============================================================================
# 6. VERIFIED LIMITLESS API ACCESS
# ============================================================================


def list_limitless_tournaments(
    *,
    page: int = 1,
    limit: int = 50,
    regulation: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Return recent VGC tournaments, optionally restricted to Champions regs.

    The API documents ``game=VGC`` and pagination via ``page``/``limit``.
    Regulation M-A/M-B are the currently verified Champions regulation IDs.

    We filter the returned records locally as an additional safety check so
    an unrelated VGC regulation can never silently enter the Champions data
    store.
    """

    if page < 1:
        raise ValueError("page must be >= 1")
    if limit < 1 or limit > 100:
        raise ValueError("limit must be between 1 and 100")
    if regulation is not None and regulation not in CHAMPIONS_REGULATIONS:
        raise ValueError(
            f"Unsupported Champions regulation: {regulation!r}."
        )

    url = build_limitless_api_url(
        "tournaments",
        game="VGC",
        page=page,
        limit=limit,
    )

    payload = fetch_json(url)
    if not isinstance(payload, list):
        raise ValueError("Limitless /tournaments returned a non-list payload.")

    results = []
    for tournament in payload:
        if not isinstance(tournament, dict):
            continue

        # The list endpoint supplies basic tournament information.  The
        # regulation is verified from /details below, not guessed from the
        # tournament name.
        results.append(tournament)

    if regulation is None:
        return results

    filtered = []
    for tournament in results:
        event_id = tournament.get("id")
        if not event_id:
            continue

        details = get_limitless_tournament_details(event_id)
        if details.get("format") == regulation:
            filtered.append({**tournament, **details})

    return filtered


def get_limitless_tournament_details(event_id: Any) -> Dict[str, Any]:
    """Return the documented details payload for one tournament."""

    event_key = str(event_id).strip()
    if not event_key:
        raise ValueError("event_id cannot be empty.")

    url = build_limitless_api_url(f"tournaments/{event_key}/details")
    payload = fetch_json(url)

    if not isinstance(payload, dict):
        raise ValueError("Limitless tournament details returned a non-object payload.")

    return payload


def get_limitless_tournament_standings(event_id: Any) -> List[Dict[str, Any]]:
    """Return all player standings/results for one tournament."""

    event_key = str(event_id).strip()
    if not event_key:
        raise ValueError("event_id cannot be empty.")

    url = build_limitless_api_url(f"tournaments/{event_key}/standings")
    payload = fetch_json(url)

    if not isinstance(payload, list):
        raise ValueError("Limitless standings returned a non-list payload.")

    return [item for item in payload if isinstance(item, dict)]


def get_limitless_tournament_pairings(event_id: Any) -> List[Dict[str, Any]]:
    """Return match pairings/results for one tournament."""

    event_key = str(event_id).strip()
    if not event_key:
        raise ValueError("event_id cannot be empty.")

    url = build_limitless_api_url(f"tournaments/{event_key}/pairings")
    payload = fetch_json(url)

    if not isinstance(payload, list):
        raise ValueError("Limitless pairings returned a non-list payload.")

    return [item for item in payload if isinstance(item, dict)]


# ============================================================================
# 7. NORMALIZATION OF LIMITLESS API RESULTS
# ============================================================================


def normalize_limitless_event(payload: Dict[str, Any]) -> ChampionsEvent:
    """Convert a Limitless tournament payload into our event model."""

    event_id = str(payload.get("id", "")).strip()
    if not event_id:
        raise ValueError("Tournament payload has no id.")

    regulation = str(payload.get("format", "")).strip()
    return ChampionsEvent(
        event_id=event_id,
        name=str(payload.get("name", "")).strip(),
        date=payload.get("date"),
        regulation=regulation,
        player_count=int(payload.get("players") or 0),
        source="Limitless",
        source_url=build_limitless_tournament_url(event_id),
        official=False,
    )


def normalize_limitless_result(
    event_id: Any,
    payload: Dict[str, Any],
) -> ChampionsResult:
    """Convert one Limitless standings record into our result model."""

    record = payload.get("record") or {}
    if not isinstance(record, dict):
        record = {}

    player_name = str(
        payload.get("name") or payload.get("player") or ""
    ).strip()

    return ChampionsResult(
        event_id=str(event_id),
        player_name=player_name,
        player_id=str(payload.get("player") or ""),
        placement=payload.get("placing"),
        wins=int(record.get("wins") or 0),
        losses=int(record.get("losses") or 0),
        draws=int(record.get("ties") or 0),
        top_cut=False,
        dropped_round=payload.get("drop"),
        decklist=payload.get("decklist"),
    )


# ============================================================================
# 8. IN-MEMORY DATA CONTAINER
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
# 9. DATA STORE HELPERS
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
    "CHAMPIONS_REGULATIONS",
    "LIMITLESS_BASE_URL",
    "LIMITLESS_API_BASE_URL",
    "LIMITLESS_TOURNAMENTS_URL",
    "ChampionsEvent",
    "ChampionsResult",
    "ChampionsTeam",
    "ChampionsDataStore",
    "CHAMPIONS_DATA_STORE",
    "normalize_champions_name",
    "champions_species_key",
    "get_http_session",
    "fetch_json",
    "fetch_text",
    "build_limitless_api_url",
    "build_limitless_tournament_url",
    "list_limitless_tournaments",
    "get_limitless_tournament_details",
    "get_limitless_tournament_standings",
    "get_limitless_tournament_pairings",
    "normalize_limitless_event",
    "normalize_limitless_result",
    "get_cached_event",
    "store_event",
    "store_result",
    "store_team",
]
