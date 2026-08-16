from typing import Dict, List

import streamlit as strlit

from champions.history_data import history_revision
from champions.meta_utils import detect_archetypes
from champions.meta_viability import calculate_meta_viability
from champions.pokemon_data import fetch_pokemon_details
from champions.roles import infer_slot_role
from champions.roster_data import display_name_for_species_key
from champions.species_keys import canonical_species_key
from champions.smogon_data import get_smogon_stats_for
from champions.tournament_data import calculate_tournament_metrics, get_tournament_partners, load_champions_history
from champions.type_chart import get_type_relationships


_EMPTY_PROFILE = {
    "tier": "Unknown",
    "viability": "0 / 100",
    "speed_tier": "Unknown",
    "momentum_rating": "None",
    "hazard_utility": "None",
    "offensive_profile": "Balanced",
    "role": "Balanced Pick",
    "teammates": [],
    "counters": [],
}


def _speed_tier(speed: float) -> str:
    if speed >= 130:
        return "Extremely Fast"
    if speed >= 110:
        return "Very Fast"
    if speed >= 90:
        return "Fast"
    if speed >= 70:
        return "Average"
    if speed >= 50:
        return "Slow"
    return "Very Slow"


def _offensive_profile(attack: float, special_attack: float) -> str:
    if attack >= special_attack + 20:
        return "Physical Attacker"
    if special_attack >= attack + 20:
        return "Special Attacker"
    return "Mixed / Flexible"


def _utility_profile(moves: List[str]) -> str:
    move_set = {str(move) for move in moves}
    tags = []
    if move_set & {"Stealth Rock", "Spikes", "Toxic Spikes"}:
        tags.append("Hazard Setter")
    if move_set & {"Rapid Spin", "Defog"}:
        tags.append("Hazard Removal")
    if move_set & {"Recover", "Roost", "Synthesis", "Soft-Boiled"}:
        tags.append("Reliable Recovery")
    return ", ".join(tags) if tags else "Direct Offensive / Defensive Focus"


def _momentum_profile(moves: List[str]) -> str:
    move_set = {str(move) for move in moves}
    if move_set & {"U-turn", "Volt Switch", "Flip Turn", "Parting Shot"}:
        return "High Momentum"
    if move_set & {"Tailwind", "Trick Room"}:
        return "Speed Control"
    return "Direct Pressure"


def _type_weaknesses(types: List[str]) -> List[str]:
    weaknesses = set()
    for attacking_type in get_all_type_names():
        relations = get_type_relationships(attacking_type) or {}
        double = {item["name"].title() for item in relations.get("double_damage_to", [])}
        half = {item["name"].title() for item in relations.get("half_damage_to", [])}
        immune = {item["name"].title() for item in relations.get("no_damage_to", [])}
        multiplier = 1.0
        for defending_type in types:
            name = str(defending_type).title()
            if name in immune:
                multiplier *= 0.0
            elif name in double:
                multiplier *= 2.0
            elif name in half:
                multiplier *= 0.5
        if multiplier >= 2.0:
            weaknesses.add(attacking_type.title())
    return sorted(weaknesses)


def get_all_type_names() -> List[str]:
    return [
        "normal", "fire", "water", "electric", "grass", "ice",
        "fighting", "poison", "ground", "flying", "psychic", "bug",
        "rock", "ghost", "dragon", "dark", "steel", "fairy",
    ]


def _candidate_names(target_name: str) -> List[str]:
    """Return tournament-relevant Champions candidates for meta analysis."""
    history = load_champions_history() or {}
    species_keys = history.get("pokemon", {}).keys()
    target_key = canonical_species_key(target_name)
    names = []
    for species_key in species_keys:
        display_name = display_name_for_species_key(species_key)
        if not display_name:
            continue
        if canonical_species_key(display_name) == target_key:
            continue
        if display_name.lower().startswith("mega "):
            continue
        names.append(display_name)
    return list(dict.fromkeys(names))


def _candidate_score(target_data: Dict, candidate_data: Dict, tournament_partners: Dict, candidate_name: str) -> float:
    score = 0.0
    candidate_key = canonical_species_key(candidate_name)
    score += min(40.0, tournament_partners.get(candidate_key, 0) * 8.0)
    target_archetypes = {a.get("name") for a in detect_archetypes(target_data)}
    candidate_archetypes = {a.get("name") for a in detect_archetypes(candidate_data)}
    score += len(target_archetypes & candidate_archetypes) * 4.0
    target_weaknesses = set(_type_weaknesses(target_data.get("types", [])))
    for candidate_type in candidate_data.get("types", []):
        relations = get_type_relationships(candidate_type) or {}
        resistances = {item["name"].title() for item in relations.get("half_damage_from", [])}
        immunities = {item["name"].title() for item in relations.get("no_damage_from", [])}
        score += sum(8.0 if weakness in immunities else 5.0 for weakness in target_weaknesses if weakness in immunities or weakness in resistances)
        coverage = {item["name"].title() for item in relations.get("double_damage_to", [])}
        score += sum(3.0 for weakness in target_weaknesses if weakness in coverage)
    target_stats = target_data.get("stats", {})
    candidate_stats = candidate_data.get("stats", {})
    target_physical = target_stats.get("attack", 100) >= target_stats.get("special-attack", 100)
    candidate_physical = candidate_stats.get("attack", 100) >= candidate_stats.get("special-attack", 100)
    if target_physical != candidate_physical:
        score += 2.0
    return score


def _effectiveness(attacking_type: str, defending_types: List[str]) -> float:
    """Return the true dual-type damage multiplier for one attacking type."""
    relations = get_type_relationships(attacking_type) or {}
    double = {item["name"].title() for item in relations.get("double_damage_to", [])}
    half = {item["name"].title() for item in relations.get("half_damage_to", [])}
    immune = {item["name"].title() for item in relations.get("no_damage_to", [])}
    multiplier = 1.0
    for defending_type in defending_types:
        name = str(defending_type).title()
        if name in immune:
            multiplier *= 0.0
        elif name in double:
            multiplier *= 2.0
        elif name in half:
            multiplier *= 0.5
    return multiplier


def _best_stab_matchup(candidate_types: List[str], target_types: List[str]) -> float:
    """Best STAB multiplier the candidate's typing can naturally provide."""
    return max((_effectiveness(t, target_types) for t in candidate_types), default=1.0)


def _target_stab_pressure(target_types: List[str], candidate_types: List[str]) -> float:
    """Worst relevant target-STAB multiplier into the candidate."""
    return max((_effectiveness(t, candidate_types) for t in target_types), default=1.0)


def _move_type_pressure(candidate_data: Dict, target_types: List[str]) -> Dict[str, float]:
    """Estimate real move-based pressure from the candidate's known learnset.

    We deliberately do not assume every learned move is a competitive set.
    Instead, STAB access, priority, setup, recovery, and disruption are treated
    as supporting evidence around the hard type-chart matchup.
    """
    candidate_types = [str(t).title() for t in candidate_data.get("types", [])]
    moves = {str(m).strip().lower() for m in candidate_data.get("moves", [])}
    stab_types = {str(t).title() for t in candidate_types}

    best_move_multiplier = _best_stab_matchup(candidate_types, target_types)
    relevant_named_moves = {
        "sucker punch", "mach punch", "vacuum wave", "bullet punch", "ice shard",
        "extreme speed", "fake out", "first impression", "aqua jet", "shadow sneak",
        "protect", "detect", "recover", "roost", "slack off", "drain punch",
        "parting shot", "taunt", "will-o-wisp", "thunder wave", "haze", "clear smog",
        "encore", "trick", "knock off", "u-turn", "volt switch", "flip turn",
        "swords dance", "nasty plot", "calm mind", "bulk up", "dragon dance",
    }
    priority = len(moves & {"sucker punch", "mach punch", "vacuum wave", "bullet punch", "ice shard", "extreme speed", "fake out", "first impression", "aqua jet", "shadow sneak"})
    disruption = len(moves & {"taunt", "will-o-wisp", "thunder wave", "haze", "clear smog", "encore", "trick", "knock off"})
    sustain = len(moves & {"recover", "roost", "slack off", "moonlight", "morning sun", "synthesis", "soft-boiled", "drain punch"})
    pivot = len(moves & {"u-turn", "volt switch", "flip turn", "parting shot"})
    setup = len(moves & {"swords dance", "nasty plot", "calm mind", "bulk up", "dragon dance"})

    # A learned STAB move matching a weakness is stronger evidence than merely
    # possessing the typing, while utility improves the chance of converting
    # the matchup into an actual in-game answer.
    stab_move_access = 1.0 if best_move_multiplier >= 2.0 and any(
        move_type in stab_types for move_type in []
    ) else 0.0

    return {
        "best_multiplier": best_move_multiplier,
        "priority": float(priority),
        "disruption": float(disruption),
        "sustain": float(sustain),
        "pivot": float(pivot),
        "setup": float(setup),
        "stab_move_access": stab_move_access,
    }


def _tournament_quality(candidate_name: str) -> Dict[str, float]:
    """Turn raw tournament history into bounded evidence for counter quality."""
    try:
        metrics = calculate_tournament_metrics(candidate_name) or {}
    except Exception:
        return {"score": 0.0, "usage": 0.0, "win": 0.5, "top_cut": 0.0}

    usage = max(0.0, min(1.0, float(metrics.get("usage", 0.0) or 0.0)))
    win = metrics.get("win_rate")
    if win is None:
        win = metrics.get("current_regulation_win_rate")
    win = 0.5 if win is None else max(0.0, min(1.0, float(win)))
    top_cut = max(0.0, min(1.0, float(metrics.get("top_cut_rate", 0.0) or 0.0)))
    tournament_score = max(0.0, min(1.0, float(metrics.get("tournament_score", 0.0) or 0.0)))
    return {
        "score": tournament_score,
        "usage": usage,
        "win": win,
        "top_cut": top_cut,
    }


def _counter_score(target_data: Dict, candidate_data: Dict, candidate_name: str) -> float:
    """Score a candidate as a practical competitive counter.

    This is intentionally multi-factor. A candidate only reaches the top when
    it combines matchup correctness with evidence that it can actually be
    used: offensive pressure, defensive safety, speed control, disruption,
    recovery, tournament performance, and role independence all contribute.
    Raw typing is therefore a gate/evidence source, not the entire answer.
    """
    target_types = [str(t).title() for t in target_data.get("types", [])]
    candidate_types = [str(t).title() for t in candidate_data.get("types", [])]
    if not target_types or not candidate_types:
        return -999.0

    score = 0.0
    best_offense = _best_stab_matchup(candidate_types, target_types)
    incoming_stab = _target_stab_pressure(target_types, candidate_types)
    move_pressure = _move_type_pressure(candidate_data, target_types)
    tournament = _tournament_quality(candidate_name)

    # 1. Offensive matchup quality. 4x is a decisive natural advantage, 2x is
    # strong, neutral is merely a soft check, and resisted/immune is a warning.
    if best_offense >= 4.0:
        score += 36.0
    elif best_offense >= 2.0:
        score += 27.0
    elif best_offense == 1.0:
        score += 8.0
    elif best_offense == 0.5:
        score -= 7.0
    else:
        score -= 14.0

    # 2. Defensive matchup. A true counter should usually be able to switch in
    # at least once, not merely revenge-kill after taking a hit.
    if incoming_stab == 0.0:
        score += 28.0
    elif incoming_stab <= 0.25:
        score += 25.0
    elif incoming_stab <= 0.5:
        score += 20.0
    elif incoming_stab <= 1.0:
        score += 8.0
    elif incoming_stab <= 2.0:
        score -= 10.0
    else:
        score -= 24.0

    # 3. Don't let one-dimensional typing dominate. A candidate with pressure
    # plus priority/disruption/sustain is considerably more actionable.
    score += min(8.0, move_pressure["priority"] * 2.0)
    score += min(8.0, move_pressure["disruption"] * 2.0)
    score += min(7.0, move_pressure["sustain"] * 2.5)
    score += min(5.0, move_pressure["pivot"] * 1.5)
    score += min(4.0, move_pressure["setup"] * 1.5)

    # 4. Speed/revenge-kill layer. A faster counter is useful even if its
    # defensive entry is imperfect; a very slow one needs bulk/recovery.
    target_stats = target_data.get("stats", {})
    candidate_stats = candidate_data.get("stats", {})
    target_speed = float(target_stats.get("speed", 0) or 0)
    candidate_speed = float(candidate_stats.get("speed", 0) or 0)
    candidate_bulk = (
        float(candidate_stats.get("hp", 0) or 0)
        + float(candidate_stats.get("defense", 0) or 0)
        + float(candidate_stats.get("special-defense", 0) or 0)
    )
    if candidate_speed >= target_speed + 30:
        score += 9.0
    elif candidate_speed >= target_speed + 10:
        score += 6.0
    elif candidate_speed >= target_speed:
        score += 3.0
    elif candidate_speed + 20 < target_speed:
        score -= 5.0
    if candidate_bulk >= 330:
        score += 6.0
    elif candidate_bulk >= 285:
        score += 3.0
    elif candidate_bulk < 225 and incoming_stab >= 2.0:
        score -= 6.0

    # 5. Tournament evidence. Usage is deliberately not used as a giant raw
    # multiplier. Win rate/top-cut/tournament score make proven options rise,
    # but a perfect matchup can still beat a popular neutral Pokémon.
    score += tournament["score"] * 14.0
    score += (tournament["win"] - 0.5) * 12.0
    score += min(5.0, tournament["top_cut"] * 20.0)
    score += min(3.0, tournament["usage"] * 3.0)

    # 6. Role/archetype compatibility. Reward candidates whose toolkit attacks
    # the target's actual play pattern rather than just its type.
    target_archetypes = {a.get("name") for a in detect_archetypes(target_data)}
    candidate_archetypes = {a.get("name") for a in detect_archetypes(candidate_data)}
    score += min(6.0, len(target_archetypes & candidate_archetypes) * 2.0)

    # 7. Physical/special asymmetry. If the target is heavily physical, bulky
    # physical answers get extra credit; if special, special bulk matters.
    target_attack = float(target_stats.get("attack", 0) or 0)
    target_spa = float(target_stats.get("special-attack", 0) or 0)
    candidate_def = float(candidate_stats.get("defense", 0) or 0)
    candidate_spd = float(candidate_stats.get("special-defense", 0) or 0)
    if target_attack >= target_spa + 25:
        score += min(5.0, max(0.0, (candidate_def - 90.0) / 12.0))
    elif target_spa >= target_attack + 25:
        score += min(5.0, max(0.0, (candidate_spd - 90.0) / 12.0))

    # 8. Penalise fake counters: candidates that are weak to the target's STAB
    # and also fail to outspeed are generally poor practical answers.
    if incoming_stab >= 2.0 and candidate_speed <= target_speed:
        score -= 8.0
    if best_offense < 2.0 and incoming_stab >= 2.0:
        score -= 12.0

    return score


def _counter_diversity_penalty(candidate_name: str, selected: List[Dict]) -> float:
    """Discourage returning three copies of the same answer class."""
    if not selected:
        return 0.0
    candidate = canonical_species_key(candidate_name)
    penalty = 0.0
    for item in selected:
        if item["key"] == candidate:
            penalty += 100.0
        if item["primary_type"] == item["candidate_type"]:
            penalty += 7.0
    return penalty


def _select_diverse_counters(scored: List[Dict], limit: int = 3) -> List[tuple]:
    """Select high-quality counters while preserving strategic diversity."""
    selected: List[Dict] = []
    remaining = list(scored)
    while remaining and len(selected) < limit:
        best = None
        best_adjusted = -999999.0
        for item in remaining:
            adjusted = item["score"] - _counter_diversity_penalty(item["name"], selected)
            # Small quality bonus for a different primary typing when the raw
            # scores are close, preventing three Fire-type answers by default.
            if selected and all(item["primary_type"] != s["primary_type"] for s in selected):
                adjusted += 4.0
            if adjusted > best_adjusted:
                best_adjusted = adjusted
                best = item
        if best is None:
            break
        best["adjusted_score"] = best_adjusted
        selected.append(best)
        remaining.remove(best)
    return [(item["name"], item["candidate_type"]) for item in selected]


@strlit.cache_data(ttl=3600, show_spinner=False)
def _get_cached_meta_candidate(name: str, history_revision_token: str) -> Dict | None:
    """Cache candidate analytics until the generated history changes."""
    try:
        c_data = fetch_pokemon_details(name)
        if not c_data.get("types"):
            return None
        tournament = calculate_tournament_metrics(name)
        if tournament["usage"] > 0:
            tournament_viability = tournament["tournament_score"] * 100
        else:
            smogon = get_smogon_stats_for(name)
            tournament_viability = smogon.get("meta_usage_tier", 0.15) * 60
        return {
            "types": c_data.get("types", []),
            "stats": c_data.get("stats", {}),
            "abilities": c_data.get("abilities", []),
            "moves": c_data.get("moves", []),
            "viability_index": int(max(0, min(100, tournament_viability))),
        }
    except Exception:
        return None


def get_cached_meta_candidate(name: str) -> Dict | None:
    """Return cached candidate data keyed to the current history revision."""
    return _get_cached_meta_candidate(name, history_revision())


@strlit.cache_data(ttl=3600, show_spinner=False)
def _compute_meta_analytics_cached(mon_name: str, history_revision_token: str) -> Dict:
    """Cached analytics whose key includes the generated history revision."""
    if not mon_name or mon_name == "-- Choose a Pokémon --":
        return dict(_EMPTY_PROFILE)

    mon_data = fetch_pokemon_details(mon_name)
    if not mon_data:
        return dict(_EMPTY_PROFILE)

    types = mon_data.get("types", ["Normal"])
    stats = mon_data.get("stats", {})
    moves = mon_data.get("moves", [])
    abilities = mon_data.get("abilities", [])
    attack = float(stats.get("attack", 100))
    special_attack = float(stats.get("special-attack", 100))
    speed = float(stats.get("speed", 100))
    bst = float(sum(stats.values())) if stats else 500.0
    offensive_stat = max(attack, special_attack)
    raw_strength = min(100.0, (bst / 720.0) * 50.0 + (offensive_stat / 160.0) * 30.0)

    tournament = calculate_tournament_metrics(mon_name)
    viability = calculate_meta_viability(
        {
            "name": mon_name,
            "types": types,
            "abilities": abilities,
            "moves": moves,
            "default_score": raw_strength,
        },
        tournament_metrics=tournament,
    )

    viability_value = int(viability["viability_index"])
    if viability_value >= 90:
        tier = "S+ / Tournament Defining"
    elif viability_value >= 80:
        tier = "S / Elite Meta"
    elif viability_value >= 70:
        tier = "A / High Viability"
    elif viability_value >= 60:
        tier = "B / Solid Meta Pick"
    elif viability_value >= 45:
        tier = "C / Niche Pick"
    else:
        tier = "D / Low Meta Presence"

    tournament_partners = dict(get_tournament_partners(mon_name, top_n=10))
    teammate_scores = []
    counter_scores: List[Dict] = []

    for candidate_name in _candidate_names(mon_name):
        try:
            candidate_data = fetch_pokemon_details(candidate_name)
            if not candidate_data:
                continue
            score = _candidate_score(mon_data, candidate_data, tournament_partners, candidate_name)
            if score > 0:
                candidate_types = candidate_data.get("types", [])
                teammate_scores.append((score, candidate_name, candidate_types[0] if candidate_types else "Unknown"))

            counter_score = _counter_score(mon_data, candidate_data, candidate_name)
            if counter_score > 28.0:
                candidate_types = [str(t).title() for t in candidate_data.get("types", [])]
                if candidate_types:
                    counter_scores.append({
                        "score": counter_score,
                        "name": candidate_name,
                        "candidate_type": candidate_types[0],
                        "primary_type": candidate_types[0],
                        "key": canonical_species_key(candidate_name),
                    })
        except Exception:
            continue

    teammate_scores.sort(key=lambda item: item[0], reverse=True)
    teammates = [(name, pokemon_type) for _, name, pokemon_type in teammate_scores[:3]]

    counter_scores.sort(key=lambda item: item["score"], reverse=True)
    counters = _select_diverse_counters(counter_scores, limit=3)

    return {
        "tier": tier,
        "viability": f"{viability_value} / 100",
        "speed_tier": _speed_tier(speed),
        "momentum_rating": _momentum_profile(moves),
        "hazard_utility": _utility_profile(moves),
        "offensive_profile": _offensive_profile(attack, special_attack),
        "role": infer_slot_role({"name": mon_name, "moves": moves}, fetch_pokemon_details),
        "teammates": teammates,
        "counters": counters,
    }


def compute_meta_analytics(mon_name: str) -> Dict:
    """Return analytics keyed to the current Champions history revision."""
    return _compute_meta_analytics_cached(mon_name, history_revision())


compute_meta_analytics.clear = _compute_meta_analytics_cached.clear
