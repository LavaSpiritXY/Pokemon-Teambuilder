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
_EXPLICIT_IMPORT_NAMES = {}


def _normalise_regulation(value):
    return str(value or "").strip().upper()


def _get_active_regulation(history=None):
    if history is None:
        history = load_champions_history()
    if isinstance(history, dict):
        active = _normalise_regulation(history.get("active_regulation"))
        if active:
            return active
    derived = get_active_regulation_from_history(history, fallback=CURRENT_REGULATION)
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

    # Explicit imports are an isolated, in-memory test/application snapshot.
    # If the public DB has been cleared, discard every alias from the previous
    # snapshot.  More importantly, always replace the live record below rather
    # than merging it with an older record, so a placement-only import can
    # never inherit a previous match record.
    if not CHAMPIONS_META_DB:
        _EXPLICIT_IMPORT_NAMES.clear()

    history_snapshot = load_champions_history()
    active_regulation = _get_active_regulation(history_snapshot)
    configured_regulation = _normalise_regulation(CURRENT_REGULATION)
    allowed_regulations = {r for r in (active_regulation, configured_regulation) if r}
    if regulation and allowed_regulations and regulation not in allowed_regulations:
        return

    for player in event.get("players", []):
        wins, losses = _extract_match_record(player)
        raw_team = [p for p in player.get("team", []) if p]
        canonical_team = list(dict.fromkeys(get_champions_species_key(p) for p in raw_team))
        for raw_name, pokemon in zip(raw_team, canonical_team):
            pokemon_key = str(pokemon).strip().lower()
            record = {
                "pokemon_name": pokemon_key,
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
            # Replace, never accumulate, explicit-import records. This keeps
            # placement-only imports authoritative even after previous tests or
            # UI interactions imported a match record for the same species.
            CHAMPIONS_META_DB[pokemon_key] = record
            _EXPLICIT_IMPORT_NAMES[str(raw_name).strip().lower()] = record
            _EXPLICIT_IMPORT_NAMES[pokemon_key] = record
            for partner in canonical_team:
                partner_key = str(partner).strip().lower()
                if partner_key and partner_key != pokemon_key:
                    record["partners"][partner_key] = record["partners"].get(partner_key, 0) + 1


def _legacy_metrics(record, active_regulation=None):
    active_regulation = active_regulation or _get_active_regulation()
    appearances = max(1, int(record.get("appearances", 0) or 0))
    wins = max(0, int(record.get("wins", 0) or 0))
    losses = max(0, int(record.get("losses", 0) or 0))
    match_records = max(0, int(record.get("match_records", 0) or 0))
    top_cuts = max(0, int(record.get("top_cuts", 0) or 0))
    win_rate = None if match_records <= 0 or wins + losses <= 0 else wins / (wins + losses)
    top_cut_rate = top_cuts / appearances if appearances else 0.0
    partners = [(str(p).strip().lower(), int(c or 0)) for p, c in (record.get("partners") or {}).items() if str(p).strip() and int(c or 0) > 0]
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
        "overall": {"appearances": record.get("appearances", 0), "wins": wins, "losses": losses, "top_cut_count": top_cuts, "win_rate": win_rate, "top_cut_rate": top_cut_rate},
        "recent": None,
        "current": {"regulation": record_regulation, "appearances": record.get("appearances", 0), "win_rate": win_rate, "top_cut_rate": top_cut_rate, "win_rate_available": win_rate is not None, "top_cut_rate_available": True},
    }


def _find_explicit_import(pokemon_name):
    wanted = str(pokemon_name or "").strip().lower()
    if not wanted:
        return None

    record = _EXPLICIT_IMPORT_NAMES.get(wanted)
    if isinstance(record, dict) and record.get("_explicit_import"):
        if any(record is live_record for live_record in CHAMPIONS_META_DB.values()):
            return record

    try:
        canonical = str(get_champions_species_key(pokemon_name)).strip().lower()
    except Exception:
        canonical = ""

    if canonical:
        record = CHAMPIONS_META_DB.get(canonical)
        if isinstance(record, dict) and record.get("_explicit_import"):
            return record

    for record in CHAMPIONS_META_DB.values():
        if not isinstance(record, dict) or not record.get("_explicit_import"):
            continue
        names = {
            str(record.get("display_name", "")).strip().lower(),
            str(record.get("pokemon_name", "")).strip().lower(),
        }
        if wanted in names or wanted == canonical:
            return record
    return None


def calculate_tournament_metrics(pokemon_name):
    history_snapshot = load_champions_history()
    active_regulation = _get_active_regulation(history_snapshot)

    # An explicitly imported tournament record is authoritative. Resolve it
    # from the live DB first; this prevents stale alias entries from supplying
    # a previous test's match record.
    explicit_record = _find_explicit_import(pokemon_name)
    if isinstance(explicit_record, dict):
        return _legacy_metrics(explicit_record, active_regulation)

    history = get_history_metrics(
        pokemon_name,
        current_regulation=active_regulation,
    )

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
            "current_regulation_win_rate": None,
            "current_regulation_top_cut_rate": None,
            "current_regulation_win_rate_available": False,
            "current_regulation_top_cut_rate_available": False,
            "overall": {"appearances": 0, "wins": 0, "losses": 0, "top_cut_count": 0, "win_rate": None, "top_cut_rate": 0.0},
            "recent": None,
            "current": {"regulation": active_regulation, "appearances": 0, "win_rate": None, "top_cut_rate": None, "win_rate_available": False, "top_cut_rate_available": False},
        }

    return history


def get_tournament_partners(pokemon_name):
    explicit = _find_explicit_import(pokemon_name)
    if explicit:
        partners = [(str(p).strip().lower(), int(c or 0)) for p, c in (explicit.get("partners") or {}).items() if str(p).strip() and int(c or 0) > 0]
        partners.sort(key=lambda x: (-x[1], x[0]))
        return partners
    return get_history_partners(pokemon_name, current_regulation=_get_active_regulation())


def get_tournament_data_revision():
    return history_revision()
