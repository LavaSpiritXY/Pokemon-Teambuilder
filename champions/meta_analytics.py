from typing import Dict, List

import streamlit as strlit

from champions.meta_utils import detect_archetypes
from champions.meta_viability import calculate_meta_viability
from champions.pokemon_data import fetch_pokemon_details
from champions.roles import infer_slot_role
from champions.roster_data import display_name_for_species_key, fetch_champions_pokedex_entries
from champions.species_keys import canonical_species_key
from champions.smogon_data import get_smogon_stats_for
from champions.tournament_data import calculate_tournament_metrics, get_tournament_partners
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
    # Keep the analytics module independent of app.py's TYPE_CHART_DATA global.
    # The canonical Champions type set is stable and deliberately local here.
    return [
        "normal", "fire", "water", "electric", "grass", "ice",
        "fighting", "poison", "ground", "flying", "psychic", "bug",
        "rock", "ghost", "dragon", "dark", "steel", "fairy",
    ]


def _candidate_names(target_name: str) -> List[str]:
    names = []
    for species_key in fetch_champions_pokedex_entries():
        display_name = display_name_for_species_key(species_key)
        if not display_name:
            continue
        if display_name.lower() == target_name.lower():
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

@strlit.cache_data(ttl=3600, show_spinner=False)
def get_cached_meta_candidate(name: str) -> Dict | None:
    try:
        c_data = fetch_pokemon_details(name)

        if not c_data.get("types"):
            return None

        tournament = calculate_tournament_metrics(name)

        if tournament["usage"] > 0:
            tournament_viability = (
                tournament["tournament_score"] * 100
            )
        else:
            smogon = get_smogon_stats_for(name)

            tournament_viability = (
                smogon.get("meta_usage_tier", 0.15) * 60
            )

        return {
            "types": c_data.get("types", []),
            "stats": c_data.get("stats", {}),
            "abilities": c_data.get("abilities", []),
            "moves": c_data.get("moves", []),
            "viability_index": int(
                max(
                    0,
                    min(
                        100,
                        tournament_viability
                    )
                )
            ),
        }

    except Exception:
        return None

@strlit.cache_data(ttl=3600, show_spinner=False)
def compute_meta_analytics(mon_name: str) -> Dict:
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
    for candidate_name in _candidate_names(mon_name):
        try:
            candidate_data = fetch_pokemon_details(candidate_name)
            if not candidate_data:
                continue
            score = _candidate_score(mon_data, candidate_data, tournament_partners, candidate_name)
            if score > 0:
                candidate_types = candidate_data.get("types", [])
                teammate_scores.append((score, candidate_name, candidate_types[0] if candidate_types else "Unknown"))
        except Exception:
            continue

    teammate_scores.sort(key=lambda item: item[0], reverse=True)
    teammates = [(name, pokemon_type) for _, name, pokemon_type in teammate_scores[:3]]

    return {
        "tier": tier,
        "viability": f"{viability_value} / 100",
        "speed_tier": _speed_tier(speed),
        "momentum_rating": _momentum_profile(moves),
        "hazard_utility": _utility_profile(moves),
        "offensive_profile": _offensive_profile(attack, special_attack),
        "role": infer_slot_role({"name": mon_name, "moves": moves}, fetch_pokemon_details),
        "teammates": teammates,
        "counters": [],
    }
