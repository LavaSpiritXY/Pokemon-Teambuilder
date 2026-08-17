from functools import lru_cache

from champions.constants import CURRENT_REGULATION
from champions.history_data import (
    build_legacy_meta_db,
    get_history_metrics,
    get_history_partners,
    history_revision,
    load_champions_history,
)
from champions.move_data import get_champions_species_key
from champions.regulation import get_active_regulation_from_history
from champions.roster_data import display_name_for_species_key

CHAMPIONS_META_DB = build_legacy_meta_db()
_EXPLICIT_IMPORT_KEYS = set()
_EXPLICIT_IMPORT_NAMES = {}


def _normalise_regulation(value):
    return str(value or "").strip().upper()


def _get_active_regulation(history=None):
    """Resolve the active regulation from one history snapshot."""
    if history is None:
        history = load_champions_history()

    if isinstance(history, dict):
        active = _normalise_regulation(history.get("active_regulation"))
        if active:
            return active

    derived = get_active_regulation_from_history(
        history,
        fallback=CURRENT_REGULATION,
    )
    return _normalise_regulation(derived) or _normalise_regulation(CURRENT_REGULATION)


def _extract_match_record(player):
    record = player.get("record") if isinstance(player.get("record"), dict) else {}
    wins = player.get("wins", record.get("wins"))
    losses = player.get("losses", record.get("losses"))
    try:
        wins = max(0, int(wins)) if wins is not None else 0
    except (TypeError, ValueError):
        wins = 0
    try:
        losses = max(0, int(losses)) if losses is not None else 0
    except (TypeError, ValueError):
        losses = 0
    return wins, losses


def import_champions_tournament(event):
    regulation = _normalise_regulation(event.get("regulation"))
    active_regulation = _get_active_regulation()
    configured_regulation = _normalise_regulation(CURRENT_REGULATION)

    allowed_regulations = {
        value for value in (active_regulation, configured_regulation) if value
    }
    if regulation and allowed_regulations and regulation not in allowed_regulations:
        return

    # The in-memory DB is deliberately cleared by the tournament-data tests
    # between cases. Keep the exact display-name index in sync with that DB so
    # an old explicit-import marker can never leak into a later test.
    if not CHAMPIONS_META_DB:
        _EXPLICIT_IMPORT_KEYS.clear()
        _EXPLICIT_IMPORT_NAMES.clear()

    for player in event.get("players", []):
        wins, losses = _extract_match_record(player)
        raw_team = [p for p in player.get("team", []) if p]
        canonical_team = list(dict.fromkeys(
            get_champions_species_key(p)
            for p in raw_team
        ))
        for raw_name, pokemon in zip(raw_team, canonical_team):
            record = {
                "pokemon_name": str(pokemon).strip().lower(),
                "display_name": str(raw_name).strip(),
                "appearances": 1,
                "wins": wins if wins + losses > 0 else 0,
                "losses": losses if wins + losses > 0 else 0,
                "match_records": 1 if wins + losses > 0 else 0,
                "top_cuts": 1 if player.get("placing") is not None and player["placing"] <= 8 else 0,
                "usage": 0.0,
                "win_rate": None,
                "top_cut_rate": 0.0,
                "partners": {},
                "roles": {},
                "moves": {},
                "abilities": {},
                "items": {},
                "_explicit_import": True,
                "_import_regulation": regulation or active_regulation or configured_regulation,
            }
            CHAMPIONS_META_DB[pokemon] = record
            _EXPLICIT_IMPORT_KEYS.add(pokemon)
            _EXPLICIT_IMPORT_NAMES[str(raw_name).strip().lower()] = record

            for partner in canonical_team:
                if partner != pokemon:
                    record["partners"][partner] = record["partners"].get(partner, 0) + 1


def _legacy_metrics(record, active_regulation=None):
    active_regulation = active_regulation or _get_active_regulation()
    appearances = max(1, int(record.get("appearances", 0) or 0))
    wins = max(0, int(record.get("wins", 0) or 0))
    losses = max(0, int(record.get("losses", 0) or 0))
    match_records = max(0, int(record.get("match_records", 0) or 0))
    top_cuts = max(0, int(record.get("top_cuts", 0) or 0))

    if match_records <= 0 or wins + losses <= 0:
        win_rate = None
    else:
        win_rate = wins / (wins + losses)

    top_cut_rate = top_cuts / appearances if appearances else 0.0
    partners = [
        (str(p).strip().lower(), int(c or 0))
        for p, c in (record.get("partners") or {}).items()
        if str(p).strip() and int(c or 0) > 0
    ]
    partners.sort(key=lambda x: (-x[1], x[0]))
    tournament_score = (top_cut_rate + win_rate) / 2 if win_rate is not None else top_cut_rate
    record_regulation = _normalise_regulation(record.get("_import_regulation") or active_regulation)
    return {
        "usage": float(record.get("usage", 0.0) or 0.0),
        "top_cut_rate": top_cut_rate,
        "win_rate": win_rate,
        "tournament_score": tournament_score,
        "partner_score": min(1.0, sum(c for _, c in partners) / max(1, appearances * 5)) if partners else 0.0,
        "win_rate_available": win_rate is not None,
        "current_regulation": record_regulation,
        "current_regulation_appearances": record.get("appearances", 0),
        "current_regulation_win_rate": win_rate,
        "current_regulation_top_cut_rate": top_cut_rate,
        "current_regulation_win_rate_available": win_rate is not None,
        "current_regulation_top_cut_rate_available": True,
        "overall": {
            "appearances": record.get("appearances", 0),
            "wins": wins,
            "losses": losses,
            "top_cut_count": top_cuts,
            "win_rate": win_rate,
            "top_cut_rate": top_cut_rate,
        },
        "recent": None,
        "current": {
            "regulation": record_regulation,
            "appearances": record.get("appearances", 0),
            "win_rate": win_rate,
            "top_cut_rate": top_cut_rate,
            "win_rate_available": win_rate is not None,
            "top_cut_rate_available": True,
        },
    }


def calculate_tournament_metrics(pokemon_name):
    history_snapshot = load_champions_history()
    active_regulation = _get_active_regulation(history_snapshot)
    wanted = str(pokemon_name or "").strip().lower()

    # Exact display-name match is checked FIRST. This is intentionally ahead
    # of both the species-key lookup and history lookup. A placement-only
    # explicit import is a real current-regulation observation, but it does
    # not contain match results; therefore its win rate must remain unknown.
    record = _EXPLICIT_IMPORT_NAMES.get(wanted)

    if not (isinstance(record, dict) and record.get("_explicit_import")):
        key = get_champions_species_key(pokemon_name)
        record = CHAMPIONS_META_DB.get(key)

    if not (isinstance(record, dict) and record.get("_explicit_import")):
        for candidate in CHAMPIONS_META_DB.values():
            if not isinstance(candidate, dict) or not candidate.get("_explicit_import"):
                continue
            display_name = str(candidate.get("display_name", "")).strip().lower()
            pokemon_key = str(candidate.get("pokemon_name", "")).strip().lower()
            if wanted in {display_name, pokemon_key}:
                record = candidate
                break

    if isinstance(record, dict) and record.get("_explicit_import"):
        return _legacy_metrics(record, active_regulation)

    history = get_history_metrics(pokemon_name, current_regulation=active_regulation)
    if not history:
        return {
            "usage": 0.0,
            "top_cut_rate": 0.0,
            "win_rate": None,
            "tournament_score": 0.0,
            "partner_score": 0.0,
            "win_rate_available": False,
            "current_regulation": active_regulation,
            "current_regulation_appearances": None,
            "overall": None,
            "recent": None,
            "current": None,
        }

    overall = history.get("overall") or {}
    recent = history.get("recent") or {}
    current = history.get("current") or {}

    snapshot_regulation = _normalise_regulation(current.get("regulation"))
    metrics_regulation = snapshot_regulation or active_regulation

    top_cut_rate = max(0.0, min(1.0, float(current.get("top_cut_rate") or 0.0)))
    win_rate = current.get("win_rate")
    win_rate_available = win_rate is not None
    if win_rate_available:
        win_rate = max(0.0, min(1.0, float(win_rate)))
    partner_values = [
        int(p.get("teams_together", 0) or 0)
        for p in get_history_partners(pokemon_name, top_n=10)
    ]
    appearances = max(1, int(current.get("appearances") or 0))
    partner_score = min(1.0, sum(v for v in partner_values if v > 0) / max(1, appearances * 5))
    recent_usage_score = min(1.0, max(0.0, float(recent.get("usage_weight", 0.0) or 0.0)) / 200.0)
    components = [(recent_usage_score, 0.20), (top_cut_rate, 0.35), (partner_score, 0.10)]
    if win_rate_available:
        components.append((win_rate, 0.35))
    total_weight = sum(w for _, w in components)
    tournament_score = sum(v * w for v, w in components) / total_weight if total_weight else 0.0
    return {
        "usage": recent_usage_score,
        "top_cut_rate": top_cut_rate,
        "win_rate": win_rate,
        "tournament_score": tournament_score,
        "partner_score": partner_score,
        "win_rate_available": win_rate_available,
        "current_regulation": metrics_regulation,
        "current_regulation_appearances": current.get("appearances"),
        "current_regulation_win_rate": current.get("win_rate"),
        "current_regulation_top_cut_rate": current.get("top_cut_rate"),
        "current_regulation_win_rate_available": current.get("win_rate_available", False),
        "current_regulation_top_cut_rate_available": current.get("top_cut_rate_available", False),
        "overall": overall,
        "recent": recent,
        "current": current,
    }


@lru_cache(maxsize=512)
def _cached_history_partners(pokemon_name, top_n, revision_token):
    results = []
    for partner in get_history_partners(pokemon_name, top_n=top_n):
        key = str(partner.get("pokemon", "")).strip().lower()
        if not key:
            continue
        display_name = display_name_for_species_key(key)
        if not display_name or display_name.lower().startswith("mega "):
            continue
        results.append((key, int(partner.get("teams_together", 0) or 0)))
        if len(results) >= top_n:
            break
    return tuple(results)


def get_tournament_partners(pokemon_name, top_n=10):
    key = get_champions_species_key(pokemon_name)
    record = CHAMPIONS_META_DB.get(key)
    if record is not None and record.get("_explicit_import"):
        pairs = [
            (str(p).strip().lower(), int(c or 0))
            for p, c in (record.get("partners") or {}).items()
            if str(p).strip() and int(c or 0) > 0
        ]
        pairs.sort(key=lambda x: (-x[1], x[0]))
        return pairs[:top_n]
    return list(_cached_history_partners(pokemon_name, int(top_n), history_revision()))
