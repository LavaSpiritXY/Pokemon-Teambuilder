"""Whole-team competitive analysis for the Pokémon Champions teambuilder.

The analyzer is intentionally independent of Streamlit so it can be tested in CI
and reused by future recommendation, threat-testing, and meta-trend features.
It consumes already-resolved Pokémon dictionaries and does not perform network IO.
"""
from __future__ import annotations

from collections import Counter
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Set, Tuple

from champions.constants import TYPE_CHART_DATA
from champions.meta_utils import detect_archetypes
from champions.move_data import get_hardcoded_move_type


TYPE_NAMES = tuple(TYPE_CHART_DATA.keys())

_PRIORITY_MOVES = {
    "fake out", "quick attack", "extreme speed", "e-speed", "aqua jet",
    "bullet punch", "mach punch", "vacuum wave", "ice shard", "sucker punch",
    "shadow sneak", "accelerock", "jet punch", "grassy glide", "first impression",
    "feint", "follow me", "rage powder",
}

_SPEED_CONTROL = {
    "tailwind": "Tailwind",
    "trick room": "Trick Room",
    "icy wind": "Icy Wind",
    "electroweb": "Electroweb",
    "mud shot": "Mud Shot",
    "string shot": "String Shot",
    "quash": "Quash",
    "bulldoze": "Bulldoze",
}

_WEATHER = {
    "rain dance": "Rain",
    "sunny day": "Sun",
    "sandstorm": "Sand",
    "snowscape": "Snow",
}

_WEATHER_ABILITIES = {
    "drizzle": "Rain",
    "primordial sea": "Rain",
    "drought": "Sun",
    "desolate land": "Sun",
    "sand stream": "Sand",
    "snow warning": "Snow",
}

_TERRAIN = {
    "electric terrain": "Electric Terrain",
    "grassy terrain": "Grassy Terrain",
    "misty terrain": "Misty Terrain",
    "psychic terrain": "Psychic Terrain",
}

_TERRAIN_ABILITIES = {
    "electric surge": "Electric Terrain",
    "grassy surge": "Grassy Terrain",
    "misty surge": "Misty Terrain",
    "psychic surge": "Psychic Terrain",
}

_DISRUPTION = {
    "fake out", "taunt", "encore", "snarl", "icy wind", "electroweb", "thunder wave",
    "nuzzle", "will-o-wisp", "parting shot", "helping hand", "follow me", "rage powder",
    "ally switch", "protect", "wide guard", "quick guard", "feint", "haze", "clear smog",
    "trick room", "tailwind", "encore", "disable", "torment",
}

_SUPPORT = {
    "helping hand", "follow me", "rage powder", "reflect", "light screen", "aurora veil",
    "safeguard", "heal pulse", "life dew", "pollen puff", "wide guard", "quick guard",
    "tailwind", "trick room", "protect",
}

_SETUP = {
    "swords dance", "nasty plot", "calm mind", "dragon dance", "quiver dance", "shell smash",
    "bulk up", "coil", "iron defense", "agility", "tidy up", "growth", "belly drum",
}



def _norm(value: Any) -> str:
    return str(value or "").strip().lower()


def _display_move_name(value: str) -> str:
    return " ".join(part.capitalize() for part in value.split())


def _move_names(mon: Mapping[str, Any]) -> List[str]:
    raw = mon.get("moves") or []
    if isinstance(raw, Mapping):
        raw = list(raw.keys())
    return [_norm(m) for m in raw if _norm(m)]


def _abilities(mon: Mapping[str, Any]) -> Set[str]:
    raw = mon.get("abilities") or []
    if isinstance(raw, Mapping):
        raw = list(raw.keys())
    return {_norm(a) for a in raw if _norm(a)}


def _types(mon: Mapping[str, Any]) -> List[str]:
    return [str(t).strip().title() for t in (mon.get("types") or []) if str(t).strip()]


def _species_key(mon: Mapping[str, Any]) -> str:
    return _norm(mon.get("name"))


def _defensive_multiplier(attacking_type: str, mon: Mapping[str, Any]) -> float:
    """Return the team's effective defensive multiplier for one member.

    Account for ability-based immunities that are relevant to team coverage.
    """
    defending_types = _types(mon)
    if attacking_type == "Ground" and "levitate" in _abilities(mon):
        return 0.0
    mult = 1.0
    for defending_type in defending_types:
        mult *= TYPE_CHART_DATA.get(attacking_type, {}).get(defending_type, 1.0)
    return mult


def _move_type(move: str) -> str | None:
    return get_hardcoded_move_type(move) or None


def _clamp_score(value: float) -> float:
    return round(max(0.0, min(100.0, value)), 1)


def _weighted_balance(parts: Iterable[Tuple[float, float]]) -> float:
    total_weight = sum(weight for _, weight in parts)
    return 0.0 if total_weight <= 0 else sum(value * weight for value, weight in parts) / total_weight


class TeamAnalyzer:
    """Analyze an entire team from resolved Pokémon data."""

    def __init__(self, team: Sequence[Mapping[str, Any]]):
        self.team = [dict(mon) for mon in team if _norm(mon.get("name"))]

    def analyze(self) -> Dict[str, Any]:
        defensive = self._defensive_coverage()
        offensive = self._offensive_coverage()
        functions = self._functional_coverage()
        redundancy = self._redundancy()
        archetypes = self._archetype_profile()

        overall = _weighted_balance(
            (
                (defensive["score"], 0.30),
                (offensive["score"], 0.22),
                (functions["score"], 0.28),
                (redundancy["score"], 0.12),
                (archetypes["score"], 0.08),
            )
        )

        return {
            "team_size": len(self.team),
            "overall_score": _clamp_score(overall),
            "grade": self._grade(overall),
            "defensive": defensive,
            "offensive": offensive,
            "functions": functions,
            "redundancy": redundancy,
            "archetypes": archetypes,
            "summary": self._summary(defensive, offensive, functions, redundancy, archetypes),
        }

    def _defensive_coverage(self) -> Dict[str, Any]:
        answers: Dict[str, int] = Counter()
        weaknesses: Counter[str] = Counter()
        resists: Counter[str] = Counter()
        immunities: Counter[str] = Counter()
        severe_gaps: List[Tuple[str, float]] = []

        for attack_type in TYPE_NAMES:
            multipliers = [_defensive_multiplier(attack_type, mon) for mon in self.team]
            answers[attack_type] = sum(mult < 1.0 for mult in multipliers)
            if multipliers and all(mult > 1.0 for mult in multipliers):
                severe_gaps.append((attack_type, max(multipliers)))
            for mon, mult in zip(self.team, multipliers):
                if mult > 1.0:
                    weaknesses[attack_type] += 1
                elif mult < 1.0:
                    resists[attack_type] += 1
                if mult == 0.0:
                    immunities[attack_type] += 1

        covered = sum(bool(answers[t]) for t in TYPE_NAMES)
        weak_points = sum(weaknesses.values())
        resist_points = sum(resists.values())
        immunity_points = sum(immunities.values())
        base = (covered / len(TYPE_NAMES)) * 65.0 if TYPE_NAMES else 0.0
        support_bonus = min(25.0, resist_points * 0.9 + immunity_points * 1.8)
        penalty = min(30.0, len(severe_gaps) * 7.5 + max(0, weak_points - resist_points) * 0.35)
        score = _clamp_score(base + support_bonus - penalty)

        return {
            "score": score,
            "covered_types": [t for t in TYPE_NAMES if answers[t]],
            "uncovered_types": [t for t in TYPE_NAMES if not answers[t]],
            "best_answers": [t for t in TYPE_NAMES if answers[t] >= 2],
            "severe_gaps": [t for t, _ in sorted(severe_gaps, key=lambda item: (-item[1], item[0]))],
            "weakness_counts": dict(weaknesses),
            "resistance_counts": dict(resists),
            "immunity_counts": dict(immunities),
        }

    def _offensive_coverage(self) -> Dict[str, Any]:
        move_type_counts: Counter[str] = Counter()
        meaningful_coverage: Dict[str, Set[str]] = {t: set() for t in TYPE_NAMES}
        super_effective_counts: Counter[str] = Counter()
        best_multipliers: Dict[str, float] = {t: 1.0 for t in TYPE_NAMES}

        for mon in self.team:
            mon_types = set(_types(mon))
            for move in _move_names(mon):
                move_type = _move_type(move)
                if not move_type:
                    continue
                move_type_counts[move_type] += 1
                for defending_type in TYPE_NAMES:
                    mult = TYPE_CHART_DATA.get(move_type, {}).get(defending_type, 1.0)
                    if mult > best_multipliers[defending_type]:
                        best_multipliers[defending_type] = mult
                    if move_type in mon_types and mult >= 2.0:
                        meaningful_coverage[defending_type].add(move_type)
                        super_effective_counts[defending_type] += 1

        covered = sum(best_multipliers[t] >= 2.0 for t in TYPE_NAMES)
        quad = sum(best_multipliers[t] >= 4.0 for t in TYPE_NAMES)
        stab_types = sum(1 for t in move_type_counts if any(t in set(_types(mon)) for mon in self.team))
        score = _clamp_score(
            (covered / len(TYPE_NAMES) * 65.0 if TYPE_NAMES else 0.0)
            + min(20.0, stab_types * 3.0)
            + min(15.0, quad * 2.5)
        )

        return {
            "score": score,
            "covered_types": [t for t in TYPE_NAMES if best_multipliers[t] >= 2.0],
            "uncovered_types": [t for t in TYPE_NAMES if best_multipliers[t] < 2.0],
            "quad_coverage": [t for t in TYPE_NAMES if best_multipliers[t] >= 4.0],
            "move_type_counts": dict(move_type_counts),
            "best_multipliers": best_multipliers,
            "stab_type_count": stab_types,
            "meaningful_coverage": {k: sorted(v) for k, v in meaningful_coverage.items() if v},
        }

    def _functional_coverage(self) -> Dict[str, Any]:
        moves = {move for mon in self.team for move in _move_names(mon)}
        abilities = {ability for mon in self.team for ability in _abilities(mon)}
        speed_control = sorted({label for move, label in _SPEED_CONTROL.items() if move in moves})
        priority = sorted(move for move in moves if move in _PRIORITY_MOVES)
        weather = sorted({label for move, label in _WEATHER.items() if move in moves} | {label for ability, label in _WEATHER_ABILITIES.items() if ability in abilities})
        terrain = sorted({label for move, label in _TERRAIN.items() if move in moves} | {label for ability, label in _TERRAIN_ABILITIES.items() if ability in abilities})

        weather_sources = []
        seen_weather_sources = set()
        for move in moves:
            if move in _WEATHER:
                key = ("move", move)
                if key not in seen_weather_sources:
                    seen_weather_sources.add(key)
                    weather_sources.append({"label": _display_move_name(move), "type": _move_type(move) or "Normal"})
        weather_ability_types = {
            "drizzle": "Water", "primordial sea": "Water",
            "drought": "Fire", "desolate land": "Fire",
            "sand stream": "Rock", "snow warning": "Ice",
        }
        for ability in abilities:
            if ability in _WEATHER_ABILITIES:
                key = ("ability", ability)
                if key not in seen_weather_sources:
                    seen_weather_sources.add(key)
                    weather_sources.append({"label": _display_move_name(ability), "type": weather_ability_types.get(ability, "Normal")})

        terrain_sources = []
        seen_terrain_sources = set()
        for move in moves:
            if move in _TERRAIN:
                key = ("move", move)
                if key not in seen_terrain_sources:
                    seen_terrain_sources.add(key)
                    terrain_type = _TERRAIN[move].replace(" Terrain", "")
                    terrain_sources.append({"label": _display_move_name(move), "type": terrain_type})
        for ability in abilities:
            if ability in _TERRAIN_ABILITIES:
                key = ("ability", ability)
                if key not in seen_terrain_sources:
                    seen_terrain_sources.add(key)
                    terrain_type = _TERRAIN_ABILITIES[ability].replace(" Terrain", "")
                    terrain_sources.append({"label": _display_move_name(ability), "type": terrain_type})

        disruption = sorted(_display_move_name(move) for move in moves if move in _DISRUPTION)
        support = sorted(_display_move_name(move) for move in moves if move in _SUPPORT)
        setup = sorted(move for move in moves if move in _SETUP)

        physical = 0
        special = 0
        for mon in self.team:
            raw_stats = mon.get("stats") or {}
            if float(raw_stats.get("attack", 0) or 0) >= float(raw_stats.get("special-attack", 0) or 0):
                physical += 1
            else:
                special += 1

        scores = {
            "speed_control": min(100.0, 55.0 if speed_control else 0.0 + len(speed_control) * 20.0),
            "priority": min(100.0, 35.0 + len(priority) * 15.0) if priority else 15.0,
            "weather_terrain": min(100.0, 45.0 + len(weather) * 25.0 + len(terrain) * 20.0) if (weather or terrain) else 35.0,
            "disruption": min(100.0, 20.0 + len(disruption) * 10.0),
            "support": min(100.0, 20.0 + len(support) * 10.0),
            "role_diversity": 60.0 if physical and special else 35.0,
        }
        if len(speed_control) >= 2:
            scores["speed_control"] = 100.0
        elif len(speed_control) == 1:
            scores["speed_control"] = 75.0

        score = _weighted_balance(
            ((scores["speed_control"], 0.28), (scores["priority"], 0.12), (scores["weather_terrain"], 0.10),
             (scores["disruption"], 0.20), (scores["support"], 0.15), (scores["role_diversity"], 0.15))
        )

        return {
            "score": _clamp_score(score),
            "speed_control": speed_control,
            "priority_moves": priority,
            "weather": weather,
            "weather_sources": weather_sources,
            "terrain": terrain,
            "terrain_sources": terrain_sources,
            "disruption": disruption,
            "support": support,
            "setup": setup,
            "physical_members": physical,
            "special_members": special,
            "signals": scores,
        }

    def _redundancy(self) -> Dict[str, Any]:
        type_counts = Counter(t for mon in self.team for t in _types(mon))
        move_types = Counter(_move_type(move) for mon in self.team for move in _move_names(mon) if _move_type(move))
        duplicate_types = {t: c for t, c in type_counts.items() if c >= 3}
        duplicate_move_types = {t: c for t, c in move_types.items() if c >= 4}

        unique_types = len(type_counts)
        type_variety = min(100.0, unique_types / 8.0 * 100.0)
        penalty = min(35.0, len(duplicate_types) * 12.0 + len(duplicate_move_types) * 4.0)
        score = _clamp_score(type_variety - penalty + min(20.0, len(self.team) * 2.0))

        return {
            "score": score,
            "type_counts": dict(type_counts),
            "duplicate_types": duplicate_types,
            "duplicate_move_types": duplicate_move_types,
        }

    def _archetype_profile(self) -> Dict[str, Any]:
        counts: Counter[str] = Counter()
        by_member: Dict[str, List[str]] = {}
        for mon in self.team:
            matches = [item.get("name") for item in detect_archetypes(dict(mon)) if item.get("name")]
            by_member[str(mon.get("name"))] = matches
            counts.update(matches)
        unique = len(counts)
        score = _clamp_score(min(100.0, 45.0 + unique * 12.0 + sum(1 for c in counts.values() if c >= 2) * 7.0))
        return {"score": score, "counts": dict(counts), "by_member": by_member}

    def _summary(self, defensive: Mapping[str, Any], offensive: Mapping[str, Any], functions: Mapping[str, Any], redundancy: Mapping[str, Any], archetypes: Mapping[str, Any]) -> Dict[str, List[str]]:
        strengths: List[str] = []
        concerns: List[str] = []
        notes: List[str] = []

        if defensive["score"] >= 75:
            strengths.append("Broad defensive coverage")
        elif defensive["score"] < 50:
            concerns.append("Defensive coverage has significant gaps")
        if defensive["severe_gaps"]:
            concerns.append("No team member comfortably answers: " + ", ".join(defensive["severe_gaps"][:3]))

        if offensive["score"] >= 75:
            strengths.append("Strong offensive type coverage")
        elif offensive["score"] < 50:
            concerns.append("Offensive coverage is narrow")
        if offensive["quad_coverage"]:
            notes.append("Reliable 4× offensive pressure into: " + ", ".join(offensive["quad_coverage"][:4]))

        if functions["speed_control"]:
            strengths.append("Speed-control plan: " + ", ".join(functions["speed_control"]))
        else:
            concerns.append("No obvious speed-control tool found")
        if functions["priority_moves"]:
            notes.append("Priority available: " + ", ".join(functions["priority_moves"][:4]))
        if functions["weather"] or functions["terrain"]:
            strengths.append("Field control: " + ", ".join(functions["weather"] + functions["terrain"]))
        if functions["disruption"]:
            strengths.append("Disruption options present")
        if functions["physical_members"] == 0 or functions["special_members"] == 0:
            concerns.append("Damage profile is heavily one-sided")

        if redundancy["duplicate_types"]:
            concerns.append("High defensive typing redundancy: " + ", ".join(sorted(redundancy["duplicate_types"])) )
        if archetypes["counts"]:
            notes.append("Detected archetypes: " + ", ".join(sorted(archetypes["counts"])))

        return {"strengths": strengths[:5], "concerns": concerns[:5], "notes": notes[:5]}

    @staticmethod
    def _grade(score: float) -> str:
        if score >= 90:
            return "S"
        if score >= 80:
            return "A"
        if score >= 70:
            return "B"
        if score >= 60:
            return "C"
        if score >= 50:
            return "D"
        return "E"


def build_team_analyzer_input(active_slots: Sequence[Tuple[int, Mapping[str, Any]]], pokemon_details: Mapping[str, Mapping[str, Any]]) -> List[Dict[str, Any]]:
    """Convert Streamlit slot state + resolved details into analyzer input."""
    team: List[Dict[str, Any]] = []
    for _, slot in active_slots:
        name = str(slot.get("name") or "").strip()
        if not name:
            continue
        details = dict(pokemon_details.get(name) or {})
        team.append({
            "name": name,
            "types": list(details.get("types") or slot.get("types") or []),
            "stats": dict(details.get("stats") or slot.get("stats") or {}),
            "moves": list(slot.get("moves") or []),
            "abilities": list(details.get("abilities") or [slot.get("ability")] if slot.get("ability") else []),
            "item": slot.get("item", ""),
        })
    return team
