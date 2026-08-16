"""Evidence-weighted Pokémon Champions counter engine."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from threading import Lock
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import requests
import streamlit as strlit

from champions.meta_utils import detect_archetypes
from champions.move_data import fetch_move_type, get_champions_species_key
from champions.species_keys import canonical_species_key
from champions.tournament_data import calculate_tournament_metrics, get_tournament_partners
from champions.type_chart import get_type_relationships


_DAMAGE_CLASSES = {"physical", "special"}
_PRIORITY_MOVES = {
    "sucker punch", "mach punch", "vacuum wave", "bullet punch", "ice shard",
    "extreme speed", "fake out", "first impression", "aqua jet", "shadow sneak",
    "jet punch", "grassy glide", "quick attack", "accelerock", "espeed",
}
_UTILITY_MOVES = {
    "protect", "detect", "taunt", "encore", "will-o-wisp", "thunder wave",
    "haze", "clear smog", "knock off", "trick", "roar", "whirlwind",
    "parting shot", "u-turn", "volt switch", "flip turn", "tailwind",
}

_MOVE_METADATA_MEMORY: Dict[str, Dict[str, Any]] = {}
_MOVE_METADATA_LOCK = Lock()


def _move_slug(move_name: str) -> str:
    return str(move_name or "").strip().lower().replace(" ", "-").replace("'", "").replace(".", "")


def _fetch_move_metadata_uncached(move_name: str) -> Dict[str, Any]:
    slug = _move_slug(move_name)
    if not slug:
        return {}
    try:
        res = requests.get(f"https://pokeapi.co/api/v2/move/{slug}", timeout=3)
        if res.status_code != 200:
            return {}
        data = res.json()
        return {
            "type": str(data.get("type", {}).get("name", "normal")).title(),
            "power": int(data.get("power") or 0),
            "accuracy": data.get("accuracy"),
            "priority": int(data.get("priority") or 0),
            "damage_class": str(data.get("damage_class", {}).get("name", "status")).lower(),
            "effect_chance": data.get("effect_chance"),
        }
    except Exception:
        return {}


@strlit.cache_data(ttl=86400, show_spinner=False)
def _fetch_move_metadata_cached(move_name: str) -> Dict[str, Any]:
    return _fetch_move_metadata_uncached(move_name)


def _fetch_move_metadata(move_name: str) -> Dict[str, Any]:
    """Cached move metadata with an in-process cache for CLI/server speed."""
    key = _move_slug(move_name)
    if not key:
        return {}
    with _MOVE_METADATA_LOCK:
        cached = _MOVE_METADATA_MEMORY.get(key)
    if cached is not None:
        return cached
    data = _fetch_move_metadata_cached(move_name)
    with _MOVE_METADATA_LOCK:
        _MOVE_METADATA_MEMORY[key] = data
    return data


def _prefetch_move_metadata(move_names: Iterable[str], max_workers: int = 16) -> None:
    """Fetch unique move metadata concurrently before ranking counters."""
    unique: Dict[str, str] = {}
    for move in move_names or []:
        key = _move_slug(move)
        if not key:
            continue
        with _MOVE_METADATA_LOCK:
            if key in _MOVE_METADATA_MEMORY:
                continue
        unique[key] = str(move).strip()

    if not unique:
        return

    workers = max(1, min(int(max_workers or 1), len(unique), 16))
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(_fetch_move_metadata_uncached, name): (key, name)
            for key, name in unique.items()
        }
        for future in as_completed(futures):
            key, _name = futures[future]
            try:
                data = future.result()
            except Exception:
                data = {}
            with _MOVE_METADATA_LOCK:
                _MOVE_METADATA_MEMORY[key] = data


def _move_metadata(move_name: str) -> Dict[str, Any]:
    data = _fetch_move_metadata(move_name)
    if data:
        return data
    move_type = fetch_move_type(move_name)
    low = str(move_name).strip().lower()
    return {
        "type": move_type,
        "power": 0,
        "accuracy": None,
        "priority": 1 if low in _PRIORITY_MOVES else 0,
        "damage_class": "status",
        "effect_chance": None,
    }


def _normalise_usage(value: Any) -> float:
    try:
        number = float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0
    if number > 1.0:
        number /= 100.0
    return max(0.0, min(1.0, number))


def _observed_moves(candidate_data: Mapping[str, Any]) -> Dict[str, float]:
    raw = candidate_data.get("tournament_moves") or candidate_data.get("move_usage") or {}
    if isinstance(raw, Mapping) and isinstance(raw.get("moves"), Mapping):
        raw = raw["moves"]
    if not isinstance(raw, Mapping):
        return {}
    result: Dict[str, float] = {}
    for move, frequency in raw.items():
        try:
            value = float(frequency)
        except (TypeError, ValueError):
            continue
        if value > 1.0:
            value /= 100.0
        result[str(move).strip().lower()] = max(0.0, min(1.0, value))
    return result


def _effectiveness(attacking_type: str, defending_types: Sequence[str]) -> float:
    relations = get_type_relationships(attacking_type) or {}
    double = {str(x.get("name", "")).title() for x in relations.get("double_damage_to", [])}
    half = {str(x.get("name", "")).title() for x in relations.get("half_damage_to", [])}
    immune = {str(x.get("name", "")).title() for x in relations.get("no_damage_to", [])}
    multiplier = 1.0
    for defending in defending_types:
        name = str(defending).title()
        if name in immune:
            multiplier *= 0.0
        elif name in double:
            multiplier *= 2.0
        elif name in half:
            multiplier *= 0.5
    return multiplier


def _best_attack_multiplier(candidate: Mapping[str, Any], target_types: Sequence[str]) -> float:
    return max((_effectiveness(str(t), target_types) for t in candidate.get("types", [])), default=1.0)


def _best_target_stab(target: Mapping[str, Any], candidate_types: Sequence[str]) -> float:
    return max((_effectiveness(str(t), candidate_types) for t in target.get("types", [])), default=1.0)


def _is_stab(move_type: str, candidate_types: Sequence[str]) -> bool:
    return str(move_type).title() in {str(t).title() for t in candidate_types}


def _learnset_moves(data: Mapping[str, Any]) -> List[str]:
    return list(dict.fromkeys(str(m).strip() for m in data.get("moves", []) if str(m).strip()))


def _pressure_moves(candidate_name: str, candidate: Mapping[str, Any], target_types: Sequence[str]) -> Tuple[List[Dict[str, Any]], List[str], List[str]]:
    moves = _learnset_moves(candidate)
    observed = _observed_moves(candidate)
    if observed:
        legal_by_lower = {m.lower(): m for m in moves}
        selected = [legal_by_lower[k] for k, freq in observed.items() if freq >= 0.05 and k in legal_by_lower]
        if selected:
            moves = selected

    candidate_types = [str(t).title() for t in candidate.get("types", [])]
    attack = float(candidate.get("stats", {}).get("attack", 0) or 0)
    special_attack = float(candidate.get("stats", {}).get("special-attack", 0) or 0)
    rows: List[Dict[str, Any]] = []
    warnings: List[str] = []
    for move in moves:
        meta = _move_metadata(move)
        damage_class = meta.get("damage_class", "status")
        power = int(meta.get("power") or 0)
        move_type = str(meta.get("type") or fetch_move_type(move)).title()
        effectiveness = _effectiveness(move_type, target_types)
        frequency = observed.get(move.lower(), 0.0)
        if damage_class not in _DAMAGE_CLASSES or power <= 0:
            continue
        stat = attack if damage_class == "physical" else special_attack
        stat_factor = max(0.35, min(1.35, stat / 120.0))
        power_factor = max(0.25, min(1.35, power / 100.0))
        stab_factor = 1.5 if _is_stab(move_type, candidate_types) else 1.0
        frequency_factor = 0.80 + (frequency * 0.45 if observed else 0.0)
        pressure = effectiveness * stat_factor * power_factor * stab_factor * frequency_factor
        rows.append({
            "move": move, "type": move_type, "power": power, "category": damage_class,
            "effectiveness": effectiveness, "priority": int(meta.get("priority") or 0),
            "frequency": frequency, "pressure": pressure, "stab": _is_stab(move_type, candidate_types),
        })

    rows.sort(key=lambda row: (row["pressure"], row["effectiveness"], row["power"]), reverse=True)
    reasons: List[str] = []
    if not rows:
        warnings.append("No verified damaging Champions move produced a usable matchup route")
    else:
        best = rows[0]
        if observed and best["frequency"] > 0:
            reasons.append(f"Tournament-used pressure move: {best['move']} ({best['frequency'] * 100:.0f}% observed)")
        else:
            reasons.append(f"Verified Champions pressure move: {best['move']}")
        if best["effectiveness"] >= 4:
            reasons.append(f"{best['effectiveness']:g}× super-effective pressure is available through {best['move']}")
        elif best["effectiveness"] >= 2:
            reasons.append(f"Super-effective pressure is available through {best['move']}")
    return rows, reasons, warnings


def _utility_and_priority(candidate: Mapping[str, Any], target_types: Sequence[str]) -> Tuple[float, float, List[str]]:
    utility = 0.0
    priority = 0.0
    reasons: List[str] = []
    for move in _learnset_moves(candidate):
        meta = _move_metadata(move)
        low = move.lower()
        if low in _UTILITY_MOVES:
            utility += 1.0
        if int(meta.get("priority") or 0) > 0 or low in _PRIORITY_MOVES:
            priority += 1.0
    utility_score = min(100.0, utility * 20.0)
    priority_score = min(100.0, priority * 30.0)
    if utility:
        reasons.append("Has matchup utility that can disrupt, reposition, or deny setup")
    if priority:
        reasons.append("Has real priority options in its verified learnset")
    return utility_score, priority_score, reasons


_ABILITY_IMMUNITIES = {
    "levitate": {"Ground"}, "flash fire": {"Fire"}, "water absorb": {"Water"},
    "storm drain": {"Water"}, "dry skin": {"Water"}, "volt absorb": {"Electric"},
    "lightning rod": {"Electric"}, "motor drive": {"Electric"}, "sap sipper": {"Grass"},
    "soundproof": {"Normal", "Bug", "Psychic", "Steel", "Water", "Electric", "Ice", "Dragon", "Dark", "Fairy", "Rock", "Ground", "Flying", "Poison", "Ghost", "Fighting", "Fire"},
}


def _ability_defensive_bonus(candidate: Mapping[str, Any], target_types: Sequence[str]) -> Tuple[float, List[str]]:
    abilities = {str(a).strip().lower() for a in candidate.get("abilities", [])}
    bonus = 0.0
    reasons: List[str] = []
    for ability in abilities:
        absorbed = _ABILITY_IMMUNITIES.get(ability, set())
        for attack_type in target_types:
            if attack_type.title() in absorbed:
                bonus += 10.0
                reasons.append(f"{ability.title()} can create an immunity to {attack_type.title()} pressure")
    if "unaware" in abilities:
        bonus += 5.0
        reasons.append("Unaware can blunt setup-based counterplay")
    return min(20.0, bonus), reasons


def _target_damaging_stabs(target: Mapping[str, Any], candidate_types: Sequence[str]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    target_types = [str(t).title() for t in target.get("types", [])]
    stats = target.get("stats", {})
    attack = float(stats.get("attack", 0) or 0)
    special_attack = float(stats.get("special-attack", 0) or 0)
    observed = _observed_moves(target)
    for move in _learnset_moves(target):
        meta = _move_metadata(move)
        category = meta.get("damage_class", "status")
        power = int(meta.get("power") or 0)
        move_type = str(meta.get("type") or fetch_move_type(move)).title()
        if category not in _DAMAGE_CLASSES or power <= 0 or move_type not in target_types:
            continue
        effectiveness = _effectiveness(move_type, candidate_types)
        stat = attack if category == "physical" else special_attack
        freq = observed.get(move.lower(), 0.0)
        threat = max(0.2, power / 100.0) * max(0.3, stat / 120.0) * effectiveness
        if freq:
            threat *= 0.8 + freq * 0.4
        rows.append({"move": move, "type": move_type, "power": power, "category": category, "effectiveness": effectiveness, "threat": threat})
    rows.sort(key=lambda row: row["threat"], reverse=True)
    return rows[:6]


def _defensive_score(target: Mapping[str, Any], candidate: Mapping[str, Any]) -> Tuple[float, List[str], List[str]]:
    candidate_types = [str(t).title() for t in candidate.get("types", [])]
    target_types = [str(t).title() for t in target.get("types", [])]
    candidate_stats = candidate.get("stats", {})
    bulk = sum(float(candidate_stats.get(k, 0) or 0) for k in ("hp", "defense", "special-defense"))
    strongest = _target_damaging_stabs(target, candidate_types)
    if strongest:
        threat = strongest[0]["effectiveness"]
        if threat == 0: base = 100.0
        elif threat <= 0.25: base = 96.0
        elif threat <= 0.5: base = 86.0
        elif threat <= 1.0: base = 66.0
        elif threat <= 2.0: base = 34.0
        else: base = 12.0
    else:
        best_stab = _best_target_stab(target, candidate_types)
        base = {0.0: 100.0, 0.25: 96.0, 0.5: 86.0, 1.0: 66.0, 2.0: 34.0}.get(best_stab, 12.0)
    bulk_bonus = max(-8.0, min(12.0, (bulk - 285.0) / 16.0))
    ability_bonus, ability_reasons = _ability_defensive_bonus(candidate, target_types)
    score = max(0.0, min(100.0, base + bulk_bonus + ability_bonus))
    reasons = list(ability_reasons)
    warnings: List[str] = []
    if strongest:
        best = strongest[0]
        if best["effectiveness"] <= 0.5:
            reasons.append(f"Best observed/legal target STAB is only {best['effectiveness']:g}× into this candidate")
        elif best["effectiveness"] >= 2:
            warnings.append(f"Target has a {best['effectiveness']:g}× STAB route through {best['move']}")
    else:
        warnings.append("Target move data was insufficient for a move-level defensive check")
    return score, reasons, warnings


def _tournament_score(name: str) -> Tuple[float, float, Dict[str, Any]]:
    try: metrics = calculate_tournament_metrics(name) or {}
    except Exception: metrics = {}
    usage = _normalise_usage(metrics.get("usage"))
    win_value = metrics.get("current_regulation_win_rate")
    if win_value is None: win_value = metrics.get("win_rate")
    win = _normalise_usage(win_value)
    top_cut = _normalise_usage(metrics.get("current_regulation_top_cut_rate", metrics.get("top_cut_rate")))
    tournament = _normalise_usage(metrics.get("tournament_score"))
    win_component = max(0.0, min(1.0, 0.5 + (win - 0.5) * 2.5))
    top_component = min(1.0, top_cut * 4.0)
    usage_component = min(1.0, usage)
    score = 100.0 * (tournament * 0.50 + win_component * 0.18 + top_component * 0.20 + usage_component * 0.12)
    confidence = min(1.0, usage_component * 0.45 + top_component * 0.30 + min(1.0, abs(win - 0.5) * 4.0) * 0.25)
    return max(0.0, min(100.0, score)), confidence, metrics


def _team_context_score(target_name: str, candidate_name: str, target_metrics: Mapping[str, Any], target_partner_counts: Mapping[str, int]) -> Tuple[float, List[str]]:
    candidate_key = canonical_species_key(candidate_name)
    pair_count = int(target_partner_counts.get(candidate_key, 0) or 0)
    target_appearances = max(1, int(target_metrics.get("current_regulation_appearances") or target_metrics.get("overall", {}).get("appearances", 1) or 1))
    pair_rate = min(1.0, pair_count / target_appearances)
    score = min(45.0, pair_rate * 100.0) * 0.35
    reasons: List[str] = []
    if pair_count: reasons.append(f"Recorded tournament co-occurrence with the target: {pair_count} teams")
    return score, reasons


@dataclass
class CounterAssessment:
    name: str
    category: str
    score: float
    confidence: float
    offensive: float
    defensive: float
    speed: float
    move_quality: float
    tournament: float
    team_context: float
    matchup: float = 0.0
    survival: float = 0.0
    best_moves: List[str] = field(default_factory=list)
    move_evidence: List[Dict[str, Any]] = field(default_factory=list)
    reasons: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


def assess_counter(target_name: str, target_data: Mapping[str, Any], candidate_name: str, candidate_data: Mapping[str, Any], *, target_partner_counts: Optional[Mapping[str, int]] = None) -> CounterAssessment:
    target_types = [str(t).title() for t in target_data.get("types", [])]
    candidate_types = [str(t).title() for t in candidate_data.get("types", [])]
    if not target_types or not candidate_types:
        return CounterAssessment(candidate_name, "Invalid", -100.0, 0.0, 0, 0, 0, 0, 0, 0)
    move_rows, move_reasons, move_warnings = _pressure_moves(candidate_name, candidate_data, target_types)
    utility_score, priority_score, utility_reasons = _utility_and_priority(candidate_data, target_types)
    best_attack = _best_attack_multiplier(candidate_data, target_types)
    if move_rows:
        best_pressure = move_rows[0]["pressure"]
        best_effectiveness = move_rows[0]["effectiveness"]
        stab_pressure = max((row["effectiveness"] for row in move_rows if row["stab"]), default=0.0)
        move_quality = min(100.0, best_pressure * 36.0 + min(30.0, stab_pressure * 10.0))
    else:
        best_effectiveness = 0.0
        move_quality = 0.0
    if best_effectiveness >= 4.0: type_offense = 100.0
    elif best_effectiveness >= 2.0: type_offense = 78.0
    elif best_attack >= 2.0: type_offense = 45.0
    else: type_offense = 15.0
    offensive = type_offense * 0.50 + move_quality * 0.35 + priority_score * 0.05 + utility_score * 0.10
    defensive, defensive_reasons, defensive_warnings = _defensive_score(target_data, candidate_data)
    target_speed = float(target_data.get("stats", {}).get("speed", 0) or 0)
    candidate_speed = float(candidate_data.get("stats", {}).get("speed", 0) or 0)
    max_priority = max((int(row.get("priority") or 0) for row in move_rows), default=0)
    if candidate_speed >= target_speed + 35: speed = 100.0
    elif candidate_speed >= target_speed + 15: speed = 88.0
    elif candidate_speed >= target_speed: speed = 72.0
    elif max_priority > 0: speed = 62.0
    elif candidate_speed + 20 >= target_speed: speed = 42.0
    else: speed = 20.0
    tournament, tournament_confidence, candidate_metrics = _tournament_score(candidate_name)
    target_metrics = calculate_tournament_metrics(target_name) or {}
    partner_counts = target_partner_counts or {}
    team_context, team_reasons = _team_context_score(target_name, candidate_name, target_metrics, partner_counts)
    target_archetypes = {a.get("name") for a in detect_archetypes(target_data)}
    candidate_archetypes = {a.get("name") for a in detect_archetypes(candidate_data)}
    overlap = len(target_archetypes & candidate_archetypes)
    team_context = min(55.0, team_context + overlap * 5.0)
    target_attack_multiplier = _best_target_stab(target_data, candidate_types)
    return_risk = max(0.0, target_attack_multiplier - 1.0)
    matchup = offensive * 0.42 + defensive * 0.28 + speed * 0.14 + move_quality * 0.16
    survival = defensive * 0.60 + speed * 0.15 + (100.0 - min(100.0, return_risk * 40.0)) * 0.25
    warnings = list(move_warnings) + list(defensive_warnings)
    reasons = list(move_reasons) + list(utility_reasons) + list(defensive_reasons) + list(team_reasons)
    if best_attack >= 4.0 and best_effectiveness < 2.0: warnings.append("Typing looks excellent, but no verified damaging move currently proves the matchup")
    if target_attack_multiplier >= 2.0 and speed < 70.0 and defensive < 55.0: warnings.append("Target can likely win the return interaction before this candidate establishes pressure")
    if candidate_speed >= target_speed: reasons.append("Base Speed gives this candidate a realistic first-action window")
    if priority_score: reasons.append("Priority can preserve the pressure window against faster targets")
    if tournament >= 60: reasons.append("Strong current tournament evidence supports practical use")
    elif tournament < 18: warnings.append("Limited tournament evidence")
    evidence = matchup * 0.40 + survival * 0.22 + tournament * 0.22 + team_context * 0.08 + utility_score * 0.04 + priority_score * 0.04
    confidence = max(0.08, min(1.0, 0.30 + tournament_confidence * 0.35 + (0.20 if move_rows else 0.0) + (0.10 if best_effectiveness >= 2.0 else 0.0) + (0.05 if target_attack_multiplier <= 1.0 else 0.0)))
    score = evidence * (0.70 + 0.30 * confidence)
    hard_route = best_effectiveness >= 2.0 and move_quality >= 48.0
    safe_route = defensive >= 58.0 or speed >= 88.0
    if hard_route and safe_route: category = "Hard Counter" if defensive >= 65.0 or speed >= 88.0 else "Soft Counter"
    elif hard_route or (speed >= 88.0 and move_quality >= 55.0 and defensive >= 42.0): category = "Soft Counter"
    elif matchup >= 62.0 and team_context >= 18.0: category = "Strategic Counter"
    else: category = "Matchup Check"
    if category == "Hard Counter" and tournament < 20 and confidence < 0.45:
        category = "Soft Counter"
        warnings.append("Strong intrinsic matchup, but tournament evidence is too thin for Hard Counter confidence")
    if best_effectiveness < 2.0 and move_quality < 55.0:
        category = "Matchup Check"; score *= 0.72; warnings.append("No strong verified super-effective damage route")
    if target_attack_multiplier >= 2.0 and defensive < 45.0 and speed < 88.0:
        category = "Matchup Check"; score *= 0.70; warnings.append("Fails the survivability / tempo gate against the target")
    if best_effectiveness >= 2.0: reasons.append(f"Verified {best_effectiveness:g}× offensive type pressure into the target")
    if target_attack_multiplier <= 0.5: reasons.append(f"Target's strongest STAB typing is only {target_attack_multiplier:g}× into this candidate")
    return CounterAssessment(candidate_name, category, max(-100.0, min(100.0, score)), confidence, offensive, defensive, speed, move_quality, tournament, team_context, matchup, survival, [row["move"] for row in move_rows[:3]], move_rows[:5], list(dict.fromkeys(reasons)), list(dict.fromkeys(warnings)))


def rank_counters(target_name: str, target_data: Mapping[str, Any], candidates: Iterable[Tuple[str, Mapping[str, Any]]], *, limit: int = 3) -> List[CounterAssessment]:
    """Rank practical counters with quality gates and profile diversity."""
    candidate_list = list(candidates)
    partner_counts = dict(get_tournament_partners(target_name, top_n=50))

    # The expensive part of the old engine was hidden inside every candidate:
    # each learnset move made its own sequential PokéAPI request. A 60-candidate
    # shortlist could therefore create thousands of serial requests. Resolve all
    # unique move metadata once, concurrently, before the scoring pass.
    all_moves = set(_learnset_moves(target_data))
    for _name, data in candidate_list:
        all_moves.update(_learnset_moves(data))
    _prefetch_move_metadata(all_moves, max_workers=16)

    assessments: List[CounterAssessment] = []
    for name, data in candidate_list:
        try:
            assessment = assess_counter(target_name, target_data, name, data, target_partner_counts=partner_counts)
        except Exception:
            continue
        if assessment.score >= 45.0 and assessment.category != "Matchup Check":
            assessments.append(assessment)

    assessments.sort(key=lambda item: (item.score, item.confidence, item.matchup, item.tournament), reverse=True)
    selected: List[CounterAssessment] = []
    selected_profiles: List[Tuple[set, set]] = []
    for assessment in assessments:
        if len(selected) >= max(0, int(limit)):
            break
        data = next((d for n, d in candidate_list if n == assessment.name), {})
        types = {str(t).title() for t in data.get("types", [])}
        move_types = {str(row.get("type", "")).title() for row in assessment.move_evidence if row.get("effectiveness", 0) >= 2}
        duplicate_profile = False
        for existing_types, existing_move_types in selected_profiles:
            type_overlap = len(types & existing_types) / max(1, len(types | existing_types))
            move_overlap = len(move_types & existing_move_types) / max(1, len(move_types | existing_move_types)) if (move_types or existing_move_types) else 0.0
            if type_overlap >= 0.75 and move_overlap >= 0.75 and assessment.score < selected[-1].score + 3.0:
                duplicate_profile = True
                break
        if duplicate_profile:
            continue
        selected.append(assessment)
        selected_profiles.append((types, move_types))
    if len(selected) < int(limit):
        for assessment in assessments:
            if assessment not in selected:
                selected.append(assessment)
            if len(selected) >= int(limit):
                break
    return selected[: max(0, int(limit))]
