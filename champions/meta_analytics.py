from typing import Dict, List

import streamlit as strlit

from champions.counter_engine import rank_counters
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
    "counter_details": [],
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


def _effectiveness(attacking_type: str, defending_types: List[str]) -> float:
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


def _type_weaknesses(types: List[str]) -> List[str]:
    weaknesses = set()
    for attacking_type in get_all_type_names():
        if _effectiveness(attacking_type, types) >= 2.0:
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
    species_keys = (history.get("pokemon") or {}).keys()
    target_key = canonical_species_key(target_name)
    names: List[str] = []
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
    """Teammate score: partnership evidence plus role/type compatibility."""
    score = 0.0
    key = canonical_species_key(candidate_name)
    score += min(40.0, float(tournament_partners.get(key, 0) or 0) * 8.0)

    target_archetypes = {a.get("name") for a in detect_archetypes(target_data)}
    candidate_archetypes = {a.get("name") for a in detect_archetypes(candidate_data)}
    score += len(target_archetypes & candidate_archetypes) * 4.0

    target_weaknesses = set(_type_weaknesses(target_data.get("types", [])))
    for candidate_type in candidate_data.get("types", []):
        relations = get_type_relationships(candidate_type) or {}
        resistances = {item["name"].title() for item in relations.get("half_damage_from", [])}
        immunities = {item["name"].title() for item in relations.get("no_damage_from", [])}
        score += sum(
            8.0 if weakness in immunities else 5.0
            for weakness in target_weaknesses
            if weakness in immunities or weakness in resistances
        )

    target_stats = target_data.get("stats", {})
    candidate_stats = candidate_data.get("stats", {})
    if (target_stats.get("attack", 100) >= target_stats.get("special-attack", 100)) != (
        candidate_stats.get("attack", 100) >= candidate_stats.get("special-attack", 100)
    ):
        score += 2.0
    return score


@strlit.cache_data(ttl=3600, show_spinner=False)
def _get_cached_meta_candidate(name: str, history_revision_token: str) -> Dict | None:
    try:
        data = fetch_pokemon_details(name)
        if not data.get("types"):
            return None
        tournament = calculate_tournament_metrics(name)
        if tournament.get("usage", 0) > 0:
            viability = tournament.get("tournament_score", 0.0) * 100.0
        else:
            smogon = get_smogon_stats_for(name)
            viability = smogon.get("meta_usage_tier", 0.15) * 60.0
        return {
            "types": data.get("types", []),
            "stats": data.get("stats", {}),
            "abilities": data.get("abilities", []),
            "moves": data.get("moves", []),
            "viability_index": int(max(0, min(100, viability))),
        }
    except Exception:
        return None


def get_cached_meta_candidate(name: str) -> Dict | None:
    return _get_cached_meta_candidate(name, history_revision())


def _tier_for_viability(value: int) -> str:
    if value >= 90:
        return "S+ / Tournament Defining"
    if value >= 80:
        return "S / Elite Meta"
    if value >= 70:
        return "A / High Viability"
    if value >= 60:
        return "B / Solid Meta Pick"
    if value >= 45:
        return "C / Niche Pick"
    return "D / Low Meta Presence"


def _counter_tournament_evidence(target_name: str, candidate_name: str) -> Dict[str, float]:
    """Return tournament evidence used to decide whether a counter is practical.

    Pairings are deliberately interpreted as *adoption evidence*, not as proof
    that the candidate won the matchup.  This keeps the engine from treating a
    popular teammate as an automatic counter while still suppressing purely
    theoretical Pokédex answers.
    """
    target_metrics = calculate_tournament_metrics(target_name) or {}
    candidate_metrics = calculate_tournament_metrics(candidate_name) or {}
    partners = dict(get_tournament_partners(target_name, top_n=500) or [])
    pair_count = float(partners.get(canonical_species_key(candidate_name), 0) or 0)
    target_appearances = float(
        target_metrics.get("current_regulation_appearances")
        or target_metrics.get("overall", {}).get("appearances", 0)
        or 0
    )
    candidate_appearances = float(
        candidate_metrics.get("current_regulation_appearances")
        or candidate_metrics.get("overall", {}).get("appearances", 0)
        or 0
    )
    pair_ratio = pair_count / target_appearances if target_appearances > 0 else 0.0
    candidate_usage = float(candidate_metrics.get("usage", 0) or 0)
    candidate_score = float(candidate_metrics.get("tournament_score", 0) or 0)
    candidate_win_rate = float(candidate_metrics.get("win_rate", 0) or 0)
    target_win_rate = float(target_metrics.get("win_rate", 0) or 0)
    return {
        "pair_count": pair_count,
        "pair_ratio": pair_ratio,
        "target_appearances": target_appearances,
        "candidate_appearances": candidate_appearances,
        "candidate_usage": candidate_usage,
        "candidate_tournament_score": candidate_score,
        "candidate_win_rate": candidate_win_rate,
        "target_win_rate": target_win_rate,
    }


def _counter_is_practical(
    target_name: str,
    assessment,
    candidate_name: str,
) -> tuple[bool, str, Dict[str, float]]:
    """Gate counter suggestions on evidence that survives real-world scrutiny.

    A theoretical matchup is no longer enough.  A candidate must have a real
    offensive route, enough matchup/survival quality, and at least one practical
    evidence channel: meaningful tournament adoption, observed tournament move
    evidence, or exceptionally strong matchup evidence.
    """
    evidence = _counter_tournament_evidence(target_name, candidate_name)
    matchup = float(getattr(assessment, "matchup", 0.0) or 0.0)
    survival = float(getattr(assessment, "survival", 0.0) or 0.0)
    move_quality = float(getattr(assessment, "move_quality", 0.0) or 0.0)
    offensive = float(getattr(assessment, "offensive", 0.0) or 0.0)
    best_moves = list(getattr(assessment, "best_moves", []) or [])
    move_evidence = list(getattr(assessment, "move_evidence", []) or [])
    observed_move = any(float(row.get("frequency", 0.0) or 0.0) >= 0.05 for row in move_evidence)

    # These are intentionally hard floors.  They prevent a good type-chart
    # interaction from surviving when the candidate cannot actually convert it.
    if not best_moves:
        return False, "No verified damaging pressure route", evidence
    if matchup < 70.0:
        return False, "Matchup quality below practical threshold", evidence
    if survival < 45.0:
        return False, "Candidate is too fragile against the target", evidence
    if move_quality < 55.0 or offensive < 55.0:
        return False, "Offensive route is not convincing enough", evidence

    # Relative team adoption is much more useful than an arbitrary raw count:
    # 300 pairings means very different things for a target seen 1,000 vs
    # 10,000 times.  A 3% pair ratio is a meaningful practical signal.
    if evidence["pair_ratio"] >= 0.03:
        return True, "Strong tournament adoption against the target", evidence

    # Once tournament move data is available, a genuinely observed pressure
    # move can substitute for broad team-pairing evidence.
    if observed_move and matchup >= 80.0 and survival >= 55.0:
        return True, "Observed tournament move evidence supports the matchup", evidence

    # Allow a small number of genuine specialist answers through without
    # requiring huge team adoption, but only when the direct matchup is elite
    # AND the candidate itself has substantial tournament presence.
    if (
        matchup >= 88.0
        and survival >= 65.0
        and move_quality >= 70.0
        and evidence["candidate_usage"] >= 0.02
    ):
        return True, "Elite matchup plus established tournament presence", evidence

    return False, "Insufficient practical tournament evidence", evidence


def _practical_counter_sort_key(assessment, evidence: Dict[str, float]) -> float:
    """Re-rank surviving counters toward repeatable, evidenced answers."""
    adoption = min(100.0, evidence["pair_ratio"] * 100.0 * 2.5)
    if evidence["pair_ratio"] >= 0.03:
        adoption = max(adoption, 70.0)
    return (
        float(getattr(assessment, "score", 0.0) or 0.0) * 0.62
        + float(getattr(assessment, "matchup", 0.0) or 0.0) * 0.13
        + float(getattr(assessment, "survival", 0.0) or 0.0) * 0.10
        + float(getattr(assessment, "move_quality", 0.0) or 0.0) * 0.05
        + adoption * 0.10
    )


@strlit.cache_data(ttl=3600, show_spinner=False)
def _compute_meta_analytics_cached(mon_name: str, history_revision_token: str) -> Dict:
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

    tournament_partners = dict(get_tournament_partners(mon_name, top_n=50))
    teammate_scores = []
    candidates = []

    # Collect candidate data once and reuse it for teammates and counters.
    for candidate_name in _candidate_names(mon_name):
        try:
            candidate_data = fetch_pokemon_details(candidate_name)
            if not candidate_data or not candidate_data.get("types"):
                continue

            teammate_score = _candidate_score(
                mon_data,
                candidate_data,
                tournament_partners,
                candidate_name,
            )
            if teammate_score > 0:
                teammate_scores.append((
                    teammate_score,
                    candidate_name,
                    candidate_data["types"][0],
                ))

            candidate_data = dict(candidate_data)
            candidate_data["name"] = candidate_name
            candidates.append((candidate_name, candidate_data))
        except Exception:
            continue

    teammate_scores.sort(key=lambda item: item[0], reverse=True)
    teammates = [
        (name, pokemon_type)
        for _, name, pokemon_type in teammate_scores[:3]
    ]

    # Ask the counter engine for a broad pool first.  The old limit=3 meant
    # weak theoretical answers could occupy all three slots before practical
    # evidence was considered.  The policy gate below therefore needs room to
    # reject them and promote stronger alternatives.
    assessments = rank_counters(
        mon_name,
        mon_data,
        candidates,
        limit=20,
    )

    practical_assessments = []
    rejected_counter_reasons = []
    for assessment in assessments:
        is_practical, reason, evidence = _counter_is_practical(
            mon_name,
            assessment,
            assessment.name,
        )
        if is_practical:
            practical_assessments.append((
                _practical_counter_sort_key(assessment, evidence),
                assessment,
                evidence,
            ))
        else:
            rejected_counter_reasons.append((assessment.name, reason))

    practical_assessments.sort(key=lambda item: item[0], reverse=True)
    selected_assessments = [item[1] for item in practical_assessments[:3]]
    evidence_lookup = {item[1].name: item[2] for item in practical_assessments}

    candidate_lookup = {name: data for name, data in candidates}
    counters = [
        (
            assessment.name,
            str((candidate_lookup.get(assessment.name, {}).get("types") or ["Unknown"])[0]),
        )
        for assessment in selected_assessments
    ]
    counter_details = []
    for assessment in selected_assessments:
        evidence = evidence_lookup.get(assessment.name, {})
        counter_details.append({
            "pokemon": assessment.name,
            "category": assessment.category,
            "score": round(assessment.score, 1),
            "practical_score": round(_practical_counter_sort_key(assessment, evidence), 1),
            "confidence": round(assessment.confidence * 100.0, 1),
            "offensive": round(assessment.offensive, 1),
            "defensive": round(assessment.defensive, 1),
            "speed": round(assessment.speed, 1),
            "move_quality": round(assessment.move_quality, 1),
            "tournament": round(assessment.tournament, 1),
            "team_context": round(assessment.team_context, 1),
            "matchup": round(assessment.matchup, 1),
            "survival": round(assessment.survival, 1),
            "pair_count": int(evidence.get("pair_count", 0)),
            "pair_ratio": round(evidence.get("pair_ratio", 0.0) * 100.0, 2),
            "candidate_usage": round(evidence.get("candidate_usage", 0.0) * 100.0, 2),
            "best_moves": assessment.best_moves,
            "move_evidence": assessment.move_evidence,
            "reasons": assessment.reasons + [
                f"Practicality gate passed: {evidence.get('pair_ratio', 0.0) * 100.0:.1f}% target pairing rate"
                if evidence.get("pair_ratio", 0.0) >= 0.03
                else "Practicality gate passed through specialist matchup evidence"
            ],
            "warnings": assessment.warnings,
        })

    return {
        "tier": _tier_for_viability(viability_value),
        "viability": f"{viability_value} / 100",
        "speed_tier": _speed_tier(speed),
        "momentum_rating": _momentum_profile(moves),
        "hazard_utility": _utility_profile(moves),
        "offensive_profile": _offensive_profile(attack, special_attack),
        "role": infer_slot_role({"name": mon_name, "moves": moves}, fetch_pokemon_details),
        "teammates": teammates,
        "counters": counters,
        "counter_details": counter_details,
    }


def compute_meta_analytics(mon_name: str) -> Dict:
    """Return analytics keyed to the current Champions history revision."""
    return _compute_meta_analytics_cached(mon_name, history_revision())


compute_meta_analytics.clear = _compute_meta_analytics_cached.clear
