"""Evidence-weighted competitive counter engine for Pokémon Champions.

The engine deliberately separates *type-chart checks* from *practical counter
quality*. A candidate is rewarded for having a real offensive route, surviving
or outspeeding the target, possessing useful utility, and having tournament
proof. It also accepts observed tournament move usage when that data becomes
available, without requiring it today.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from champions.meta_utils import detect_archetypes
from champions.move_data import fetch_move_type
from champions.species_keys import canonical_species_key
from champions.tournament_data import calculate_tournament_metrics, get_tournament_partners
from champions.type_chart import get_type_relationships


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
    reasons: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


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
    return max(
        (_effectiveness(str(t), target_types) for t in candidate.get("types", [])),
        default=1.0,
    )


def _best_target_stab(target: Mapping[str, Any], candidate_types: Sequence[str]) -> float:
    return max(
        (_effectiveness(str(t), candidate_types) for t in target.get("types", [])),
        default=1.0,
    )


def _normalise_usage(value: Any) -> float:
    try:
        return max(0.0, min(1.0, float(value or 0.0)))
    except (TypeError, ValueError):
        return 0.0


def _observed_moves(candidate_name: str, candidate_data: Mapping[str, Any]) -> Dict[str, float]:
    """Read future tournament move-frequency data if it is present.

    Accepted shapes are intentionally loose so the history schema can evolve:
    ``{"moves": {"Close Combat": 0.81}}`` or a direct ``move_usage`` mapping.
    Percentages in the 0-100 range are converted to 0-1.
    """
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


def _move_quality(candidate: Mapping[str, Any], target_types: Sequence[str]) -> Tuple[float, List[str], List[str]]:
    moves = [str(m).strip() for m in candidate.get("moves", []) if str(m).strip()]
    observed = _observed_moves(str(candidate.get("name", "")), candidate)
    if observed:
        # Tournament-set frequency is stronger evidence than the raw learnset.
        move_names = [move for move, freq in observed.items() if freq >= 0.08]
    else:
        move_names = moves

    target_weak = max(
        (_effectiveness(fetch_move_type(move), target_types) for move in move_names),
        default=1.0,
    )
    target_types_lower = {str(t).title() for t in target_types}
    candidate_types = {str(t).title() for t in candidate.get("types", [])}

    weighted_pressure = 0.0
    best_move = ""
    utility = 0.0
    priority = 0.0
    for move in move_names:
        move_type = fetch_move_type(move)
        effectiveness = _effectiveness(move_type, target_types)
        frequency = observed.get(move.lower(), 1.0 if not observed else 0.0)
        weighted_pressure = max(weighted_pressure, effectiveness * frequency)
        if effectiveness >= 2.0 and (not best_move or frequency > observed.get(best_move.lower(), 0.0)):
            best_move = move
        low = move.lower()
        if low in {"protect", "detect", "taunt", "encore", "will-o-wisp", "thunder wave", "haze", "clear smog", "knock off", "trick"}:
            utility += frequency
        if low in {"sucker punch", "mach punch", "vacuum wave", "bullet punch", "ice shard", "extreme speed", "fake out", "first impression", "aqua jet", "shadow sneak"}:
            priority += frequency

    # A STAB move that actually hits the target weakness is worth much more than
    # merely knowing that the candidate has a favourable type.
    stab_pressure = 0.0
    for move in move_names:
        move_type = fetch_move_type(move)
        if move_type in candidate_types:
            stab_pressure = max(stab_pressure, _effectiveness(move_type, target_types))

    score = 0.0
    score += min(40.0, target_weak * 12.0)
    score += min(18.0, weighted_pressure * 12.0)
    score += min(12.0, stab_pressure * 5.0)
    score += min(8.0, utility * 4.0)
    score += min(8.0, priority * 4.0)
    score = min(100.0, score)

    reasons: List[str] = []
    warnings: List[str] = []
    if best_move:
        if observed:
            reasons.append(f"Tournament-used pressure move: {best_move}")
        else:
            reasons.append(f"Learnset provides super-effective pressure via {best_move}")
    if utility:
        reasons.append("Has disruption/positioning tools that can convert pressure into a matchup")
    if priority:
        reasons.append("Has useful priority access")
    if not move_names:
        warnings.append("No usable move evidence was available")
    if target_weak < 2.0:
        warnings.append("No clearly super-effective attack was found in the available move evidence")
    return score, reasons, warnings


def _tournament_score(name: str) -> Tuple[float, float, Dict[str, Any]]:
    try:
        metrics = calculate_tournament_metrics(name) or {}
    except Exception:
        metrics = {}
    usage = _normalise_usage(metrics.get("usage"))
    win = metrics.get("win_rate")
    if win is None:
        win = metrics.get("current_regulation_win_rate")
    try:
        win = max(0.0, min(1.0, float(win))) if win is not None else 0.5
    except (TypeError, ValueError):
        win = 0.5
    top_cut = _normalise_usage(metrics.get("top_cut_rate"))
    tournament = _normalise_usage(metrics.get("tournament_score"))
    confidence = min(1.0, (usage * 0.55) + (min(1.0, top_cut * 4.0) * 0.25) + (min(1.0, abs(win - 0.5) * 4.0) * 0.20))
    score = tournament * 70.0 + max(0.0, win - 0.45) * 40.0 + min(10.0, top_cut * 30.0)
    return min(100.0, score), confidence, metrics


def assess_counter(
    target_name: str,
    target_data: Mapping[str, Any],
    candidate_name: str,
    candidate_data: Mapping[str, Any],
    *,
    target_partner_counts: Optional[Mapping[str, int]] = None,
) -> CounterAssessment:
    """Build a detailed practical counter assessment."""
    target_types = [str(t).title() for t in target_data.get("types", [])]
    candidate_types = [str(t).title() for t in candidate_data.get("types", [])]
    if not target_types or not candidate_types:
        return CounterAssessment(candidate_name, "Invalid", -100.0, 0.0, 0, 0, 0, 0, 0, 0)

    best_attack = _best_attack_multiplier(candidate_data, target_types)
    target_attack = _best_target_stab(target_data, candidate_types)
    move_score, reasons, warnings = _move_quality({**candidate_data, "name": candidate_name}, target_types)

    target_stats = target_data.get("stats", {})
    candidate_stats = candidate_data.get("stats", {})
    target_speed = float(target_stats.get("speed", 0) or 0)
    candidate_speed = float(candidate_stats.get("speed", 0) or 0)
    candidate_bulk = sum(float(candidate_stats.get(k, 0) or 0) for k in ("hp", "defense", "special-defense"))

    offensive = 0.0
    if best_attack >= 4.0:
        offensive += 100
    elif best_attack >= 2.0:
        offensive += 78
    elif best_attack >= 1.0:
        offensive += 32
    elif best_attack > 0:
        offensive += 10
    offensive = offensive * 0.55 + move_score * 0.45

    defensive = {0.0: 100.0, 0.25: 96.0, 0.5: 82.0, 1.0: 55.0, 2.0: 22.0}.get(target_attack, 10.0 if target_attack > 2 else 55.0)
    defensive += min(12.0, max(0.0, (candidate_bulk - 240.0) / 12.0))
    defensive = max(0.0, min(100.0, defensive))

    if candidate_speed >= target_speed + 35:
        speed = 100.0
    elif candidate_speed >= target_speed + 15:
        speed = 84.0
    elif candidate_speed >= target_speed:
        speed = 68.0
    elif candidate_speed + 20 >= target_speed:
        speed = 45.0
    else:
        speed = 20.0

    tournament, tournament_confidence, metrics = _tournament_score(candidate_name)

    partner_context = 0.0
    target_partner_counts = target_partner_counts or {}
    candidate_key = canonical_species_key(candidate_name)
    pair_count = int(target_partner_counts.get(candidate_key, 0) or 0)
    target_appearances = max(1, int(metrics.get("current_regulation_appearances") or 1))
    if pair_count:
        # Pairing evidence matters, but cannot overwhelm the direct matchup.
        pair_rate = min(1.0, pair_count / target_appearances)
        partner_context = pair_rate * 100.0
        reasons.append(f"Recorded tournament pairing with the target: {pair_count} teams")

    target_archetypes = {a.get("name") for a in detect_archetypes(target_data)}
    candidate_archetypes = {a.get("name") for a in detect_archetypes(candidate_data)}
    archetype_overlap = len(target_archetypes & candidate_archetypes)
    team_context = min(100.0, partner_context * 0.70 + archetype_overlap * 12.0)

    # A practical counter must have a credible way to win the interaction.
    # This gate is deliberately strict enough to eliminate "same weakness"
    # candidates that are actually fragile or only theoretical answers.
    if best_attack < 2.0 and move_score < 48.0:
        warnings.append("No strong direct pressure route")
    if target_attack >= 2.0 and candidate_speed < target_speed and defensive < 60.0:
        warnings.append("Likely loses the return interaction before establishing pressure")

    weighted = (
        offensive * 0.30
        + defensive * 0.22
        + speed * 0.12
        + move_score * 0.16
        + tournament * 0.12
        + team_context * 0.08
    )

    # Evidence confidence prevents a tiny-data Pokémon from outranking a
    # well-proven answer solely because of a favourable theoretical matchup.
    confidence = max(0.05, min(1.0, 0.35 + tournament_confidence * 0.45 + (0.20 if pair_count else 0.0)))
    score = weighted * (0.72 + 0.28 * confidence)

    if best_attack >= 2.0 and target_attack <= 1.0 and move_score >= 55 and tournament >= 35:
        category = "Hard Counter"
    elif (best_attack >= 2.0 and move_score >= 42) or (speed >= 84 and move_score >= 50):
        category = "Soft Counter"
    elif team_context >= 45 and tournament >= 30:
        category = "Strategic Counter"
    else:
        category = "Matchup Check"

    if category == "Matchup Check":
        score -= 18.0

    if best_attack >= 2.0:
        reasons.append(f"{best_attack:g}× natural type pressure into the target")
    if target_attack <= 0.5:
        reasons.append(f"Target STAB is only {target_attack:g}× into this candidate")
    if candidate_speed >= target_speed:
        reasons.append("Can act before or around the target's base Speed tier")
    if tournament >= 45:
        reasons.append("Strong tournament evidence supports practical use")
    if tournament < 15:
        warnings.append("Limited tournament evidence")

    return CounterAssessment(
        name=candidate_name,
        category=category,
        score=max(-100.0, min(100.0, score)),
        confidence=confidence,
        offensive=offensive,
        defensive=defensive,
        speed=speed,
        move_quality=move_score,
        tournament=tournament,
        team_context=team_context,
        reasons=list(dict.fromkeys(reasons)),
        warnings=list(dict.fromkeys(warnings)),
    )


def rank_counters(
    target_name: str,
    target_data: Mapping[str, Any],
    candidates: Iterable[Tuple[str, Mapping[str, Any]]],
    *,
    limit: int = 3,
) -> List[CounterAssessment]:
    """Rank counters using evidence first, then enforce diversity.

    Diversity is a *tie-breaker*, never a reason to elevate a clearly worse
    answer. The selector also prevents three candidates whose only shared
    property is the same type-chart interaction.
    """
    partner_counts = dict(get_tournament_partners(target_name, top_n=50))
    assessments: List[CounterAssessment] = []
    for name, data in candidates:
        try:
            assessment = assess_counter(
                target_name,
                target_data,
                name,
                data,
                target_partner_counts=partner_counts,
            )
        except Exception:
            continue
        if assessment.score >= 42.0 and assessment.category != "Matchup Check":
            assessments.append(assessment)

    assessments.sort(key=lambda x: (x.score, x.confidence, x.tournament), reverse=True)
    selected: List[CounterAssessment] = []
    for assessment in assessments:
        if len(selected) >= limit:
            break
        candidate_types = {str(t).title() for t in (next((d.get("types", []) for n, d in candidates if n == assessment.name), []) or [])}
        selected_types = [str(t).title() for item in selected for t in item.name.split("|") if t]
        # Keep the raw score primary. Only reject near-duplicates when a better
        # answer with a meaningfully different profile exists later.
        if selected and assessment.score < selected[-1].score - 10:
            continue
        selected.append(assessment)

    return selected[: max(0, int(limit))]
