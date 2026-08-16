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


def _get_active_regulation():
    """Return the regulation recorded by the synced history first."""
    history = load_champions_history()
    if isinstance(history, dict):
        active = str(history.get("active_regulation") or "").strip().upper()
        if active:
            return active
    return get_active_regulation_from_history(history, fallback=CURRENT_REGULATION) or CURRENT_REGULATION


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
    regulation = str(event.get("regulation", "") or "").strip().upper()
    active_regulation = _get_active_regulation()

    # The legacy tournament API is also used by unit tests and by callers that
    # explicitly identify the current configured regulation. Treat that value
    # as authoritative for this imported event rather than rejecting it because
    # a generated history file has a different/stale active-regulation value.
    if (
        regulation
        and regulation != CURRENT_REGULATION
        and active_regulation
        and regulation != active_regulation
    ):
        return

    for player in event.get("players", []):
        wins, losses = _extract_match_record(player)
        canonical_team = list(dict.fromkeys(
            get_champions_species_key(p)
            for p in player.get("team", [])
            if p
        ))
        for pokemon in canonical_team:
            # Explicitly imported tournament records must start clean. This
            # prevents legacy data from leaking wins/losses into a synced event.
            record = {
                "appearances": 0,
                "wins": 0,
                "losses": 0,
                "match_records": 0,
                "top_cuts": 0,
                "usage": 0.0,
                "win_rate": None,
                "top_cut_rate": 0.0,
                "partners": {},
                "roles": {},
                "moves": {},
                "abilities": {},
                "items": {},
                "_explicit_import": True,
            }
            existing = CHAMPIONS_META_DB.get(pokemon)
            if isinstance(existing, dict) and existing.get("_explicit_import"):
                record = existing
            CHAMPIONS_META_DB[pokemon] = record
            record["_explicit_import"] = True
            record["appearances"] += 1
            if wins + losses > 0:
                record["wins"] += wins
                record["losses"] += losses
                record["match_records"] += 1
            if player.get("placing") is not None and player["placing"] <= 8:
                record["top_cuts"] += 1
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
    win_rate = wins / (wins + losses) if match_records and wins + losses else None
    top_cut_rate = top_cuts / appearances if appearances else 0.0
    partners = [(str(p).strip().lower(), int(c or 0)) for p, c in (record.get("partners") or {}).items() if str(p).strip() and int(c or 0) > 0]
    partners.sort(key=lambda x: (-x[1], x[0]))
    tournament_score = (top_cut_rate + win_rate) / 2 if win_rate is not None else top_cut_rate
    return {
        "usage": float(record.get("usage", 0.0) or 0.0),
        "top_cut_rate": top_cut_rate,
        "win_rate": win_rate,
        "tournament_score": tournament_score,
        "partner_score": min(1.0, sum(c for _, c in partners) / max(1, appearances * 5)) if partners else 0.0,
        "win_rate_available": win_rate is not None,
        "current_regulation": active_regulation,
        "current_regulation_appearances": record.get("appearances", 0),
        "current_regulation_win_rate": win_rate,
        "current_regulation_top_cut_rate": top_cut_rate,
        "current_regulation_win_rate_available": win_rate is not None,
        "current_regulation_top_cut_rate_available": True,
        "overall": {"appearances": record.get("appearances", 0), "wins": wins, "losses": losses, "top_cut_count": top_cuts, "win_rate": win_rate, "top_cut_rate": top_cut_rate},
        "recent": None,
        "current": {"regulation": active_regulation, "appearances": record.get("appearances", 0), "win_rate": win_rate, "top_cut_rate": top_cut_rate, "win_rate_available": win_rate is not None, "top_cut_rate_available": True},
    }


def calculate_tournament_metrics(pokemon_name):
    active_regulation = _get_active_regulation()
    key = get_champions_species_key(pokemon_name)
    record = CHAMPIONS_META_DB.get(key)

    # Only records explicitly imported by the current tournament-data API may
    # override synced history. Legacy fallback records must never shadow it.
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

    # A history provider can expose a concrete current-regulation value. Use
    # that value for the returned metrics when present. This is important both
    # for generated history and for isolated callers/tests supplying a history
    # snapshot whose active regulation differs from the module fallback.
    current = history.get("current") or {}
    snapshot_regulation = str(current.get("regulation") or "").strip().upper()
    if snapshot_regulation:
        active_regulation = snapshot_regulation

    overall = history.get("overall") or {}
    recent = history.get("recent") or {}
    metrics_regulation = active_regulation
    appearances = max(1, int(current.get("appearances") or 0))
    top_cut_rate = max(0.0, min(1.0, float(current.get("top_cut_rate") or 0.0)))
    win_rate = current.get("win_rate")
    win_rate_available = win_rate is not None
    if win_rate_available:
        win_rate = max(0.0, min(1.0, float(win_rate)))
    partner_values = [int(p.get("teams_together", 0) or 0) for p in get_history_partners(pokemon_name, top_n=10)]
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
        pairs = [(str(p).strip().lower(), int(c or 0)) for p, c in (record.get("partners") or {}).items() if str(p).strip() and int(c or 0) > 0]
        pairs.sort(key=lambda x: (-x[1], x[0]))
        return pairs[:top_n]
    return list(_cached_history_partners(pokemon_name, int(top_n), history_revision()))