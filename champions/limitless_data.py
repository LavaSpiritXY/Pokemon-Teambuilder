"""
Pokémon Champions tournament data layer.

PHASE 4
-------
This module retrieves and normalizes completed Limitless tournament data.

It remains isolated from app.py.  It does NOT populate CHAMPIONS_META_DB and
it does NOT alter the Streamlit application yet.
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

CHAMPIONS_DATA_VERSION = 4
REQUEST_TIMEOUT_SECONDS = 20

LIMITLESS_BASE_URL = "https://play.limitlesstcg.com"
LIMITLESS_API_BASE_URL = f"{LIMITLESS_BASE_URL}/api"
LIMITLESS_TOURNAMENTS_URL = f"{LIMITLESS_BASE_URL}/tournaments"

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
    completed: bool = False


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
# 6. LIMITLESS API ACCESS
# ============================================================================


def list_limitless_tournaments(
    *,
    page: int = 1,
    limit: int = 50,
    regulation: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Return recent VGC tournaments, optionally restricted to a regulation."""

    if page < 1:
        raise ValueError("page must be >= 1")
    if limit < 1 or limit > 100:
        raise ValueError("limit must be between 1 and 100")
    if regulation is not None and regulation not in CHAMPIONS_REGULATIONS:
        raise ValueError(f"Unsupported Champions regulation: {regulation!r}.")

    url = build_limitless_api_url(
        "tournaments",
        game="VGC",
        page=page,
        limit=limit,
    )

    payload = fetch_json(url)
    if not isinstance(payload, list):
        raise ValueError("Limitless /tournaments returned a non-list payload.")

    results = [item for item in payload if isinstance(item, dict)]

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

    payload = fetch_json(
        build_limitless_api_url(f"tournaments/{event_key}/details")
    )

    if not isinstance(payload, dict):
        raise ValueError("Limitless tournament details returned a non-object payload.")

    return payload


def get_limitless_tournament_standings(event_id: Any) -> List[Dict[str, Any]]:
    """Return all player standings/results for one tournament."""

    event_key = str(event_id).strip()
    if not event_key:
        raise ValueError("event_id cannot be empty.")

    payload = fetch_json(
        build_limitless_api_url(f"tournaments/{event_key}/standings")
    )

    if not isinstance(payload, list):
        raise ValueError("Limitless standings returned a non-list payload.")

    return [item for item in payload if isinstance(item, dict)]


def get_limitless_tournament_pairings(event_id: Any) -> List[Dict[str, Any]]:
    """Return match pairings/results for one tournament."""

    event_key = str(event_id).strip()
    if not event_key:
        raise ValueError("event_id cannot be empty.")

    payload = fetch_json(
        build_limitless_api_url(f"tournaments/{event_key}/pairings")
    )

    if not isinstance(payload, list):
        raise ValueError("Limitless pairings returned a non-list payload.")

    return [item for item in payload if isinstance(item, dict)]


# ============================================================================
# 7. RESULT / TEAM EXTRACTION
# ============================================================================


def _extract_pokemon_names(decklist: Any) -> List[str]:
    """Extract Pokémon names from a Limitless deck/team payload.

    Champions teamlist payloads may evolve, so this function accepts several
    common container shapes without assuming that every field is Pokémon.
    Card/deck objects that do not clearly identify a Pokémon are ignored.
    """

    if decklist is None:
        return []

    candidates: List[Any] = []

    if isinstance(decklist, list):
        candidates = decklist
    elif isinstance(decklist, dict):
        for key in ("pokemon", "pokémon", "team", "members", "cards"):
            value = decklist.get(key)
            if isinstance(value, list):
                candidates.extend(value)

    names: List[str] = []
    for item in candidates:
        if isinstance(item, str):
            name = normalize_champions_name(item)
            if name:
                names.append(name)
            continue

        if not isinstance(item, dict):
            continue

        # Prefer explicit Pokémon/name fields.  Do not blindly interpret
        # arbitrary card names as Pokémon until the exact Champions payload is
        # confirmed by the source.
        for key in ("pokemon", "pokémon", "name"):
            value = item.get(key)
            if isinstance(value, str) and value.strip():
                names.append(normalize_champions_name(value))
                break

    # Stable de-duplication while preserving source order.
    output: List[str] = []
    seen = set()
    for name in names:
        key = champions_species_key(name)
        if key and key not in seen:
            seen.add(key)
            output.append(name)

    return output


def infer_top_cut_placement(placement: Optional[int], player_count: int) -> bool:
    """Conservative top-cut inference for completed tournament standings.

    The Limitless standings endpoint exposes final placement, while the
    details endpoint exposes tournament phases.  For this first extraction
    layer we use the common competitive convention of a top-8 cutoff when the
    event has at least 8 players.  A later phase-aware parser will replace this
    with the exact configured elimination size from tournament phases.
    """

    if placement is None or placement < 1:
        return False

    if player_count < 8:
        return placement <= max(1, player_count // 2)

    return placement <= 8


def normalize_limitless_event(payload: Dict[str, Any]) -> ChampionsEvent:
    """Convert a Limitless tournament payload into our event model."""

    event_id = str(payload.get("id", "")).strip()
    if not event_id:
        raise ValueError("Tournament payload has no id.")

    regulation = str(payload.get("format", "")).strip()
    phases = payload.get("phases") or []
    completed = bool(payload.get("ended"))
    if isinstance(phases, list) and phases:
        # Presence of tournament phases alone does not prove completion, so
        # completion is finalized by the standings fetch in load_event_data.
        completed = completed or False

    return ChampionsEvent(
        event_id=event_id,
        name=str(payload.get("name", "")).strip(),
        date=payload.get("date"),
        regulation=regulation,
        player_count=int(payload.get("players") or 0),
        source="Limitless",
        source_url=build_limitless_tournament_url(event_id),
        official=False,
        completed=completed,
    )


def normalize_limitless_result(
    event_id: Any,
    payload: Dict[str, Any],
    *,
    player_count: int = 0,
) -> ChampionsResult:
    """Convert one Limitless standings record into our result model."""

    record = payload.get("record") or {}
    if not isinstance(record, dict):
        record = {}

    player_name = str(
        payload.get("name") or payload.get("player") or ""
    ).strip()

    placement = payload.get("placing")
    try:
        placement = int(placement) if placement is not None else None
    except (TypeError, ValueError):
        placement = None

    return ChampionsResult(
        event_id=str(event_id),
        player_name=player_name,
        player_id=str(payload.get("player") or ""),
        placement=placement,
        wins=int(record.get("wins") or 0),
        losses=int(record.get("losses") or 0),
        draws=int(record.get("ties") or 0),
        top_cut=infer_top_cut_placement(placement, player_count),
        dropped_round=payload.get("drop"),
        decklist=payload.get("decklist"),
    )


def normalize_limitless_team(
    event_id: Any,
    result: ChampionsResult,
) -> ChampionsTeam:
    """Convert a normalized result's decklist into a team record."""

    return ChampionsTeam(
        event_id=event_id,
        player_name=result.player_name,
        pokemon=_extract_pokemon_names(result.decklist),
        raw_decklist=result.decklist,
    )


def load_limitless_event_data(event_id: Any) -> Dict[str, Any]:
    """Fetch and normalize one completed Champions tournament.

    This is the first end-to-end function in the data layer.  It fetches the
    details and standings, validates the regulation, and returns normalized
    event/results/teams without touching app.py or CHAMPIONS_META_DB.
    """

    event_key = str(event_id).strip()
    if not event_key:
        raise ValueError("event_id cannot be empty.")

    details = get_limitless_tournament_details(event_key)

    raw_format = str(details.get("format", "")).strip()
    tournament_name = str(details.get("name", "")).strip()

    regulation = raw_format

    # Limitless sometimes labels Champions tournaments as CUSTOM.
    # In those cases, recover the actual Champions regulation from
    # the tournament name.
    if raw_format.upper() == "CUSTOM":
        import re

        regulation_match = re.search(
            r"\bReg(?:ulation)?[\s_-]*([A-Z0-9]+(?:-[A-Z0-9]+)?)\b",
            tournament_name,
            flags=re.IGNORECASE,
        )

        if regulation_match:
            candidate = regulation_match.group(1).upper()

            # Normalise separators.
            candidate = candidate.replace("_", "-")
            candidate = re.sub(r"\s+", "-", candidate)

            if candidate in CHAMPIONS_REGULATIONS:
                regulation = candidate

    if regulation not in CHAMPIONS_REGULATIONS:
        raise ValueError(
            f"Tournament {event_key} uses unsupported format {raw_format!r}; "
            "it was not imported into Champions data."
        )

    standings = get_limitless_tournament_standings(event_key)

    # Use the recovered Champions regulation rather than Limitless'
    # raw "CUSTOM" format when constructing the normalized event.
    event_payload = dict(details)
    event_payload["format"] = regulation

    event = normalize_limitless_event(event_payload)
    event.completed = len(standings) > 0

    results = [
        normalize_limitless_result(
            event_key,
            row,
            player_count=event.player_count,
        )
        for row in standings
        if (row.get("name") or row.get("player"))
    ]

    teams = [normalize_limitless_team(event_key, result) for result in results]

    return {
        "event": event,
        "results": results,
        "teams": teams,
    }


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


def store_event_data(data: Dict[str, Any]) -> None:
    """Store the output of load_limitless_event_data()."""

    event = data["event"]
    results = data["results"]
    teams = data["teams"]

    store_event(event)
    for result in results:
        store_result(result)
    for team in teams:
        store_team(team)


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
    "normalize_limitless_team",
    "load_limitless_event_data",
    "infer_top_cut_placement",
    "get_cached_event",
    "store_event",
    "store_result",
    "store_team",
    "store_event_data",
]
