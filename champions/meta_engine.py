import math
from dataclasses import dataclass, field
from typing import Dict, List, Set

from champions.constants import TYPE_CHART_DATA


@dataclass
class MoveProfile:
    name: str
    category: str  # "Physical", "Special", "Status"
    type: str
    base_power: int
    accuracy: float
    usage_rate: float
    tags: Set[str] = field(default_factory=set)


@dataclass
class MonMetaProfile:
    name: str
    types: List[str]
    base_stats: Dict[str, int]
    common_moves: Dict[str, MoveProfile]
    common_abilities: Dict[str, float]
    common_items: Dict[str, float]
    meta_usage_tier: float
    top_partners: Dict[str, float]


class TeamEvaluator:
    TYPE_CHART: Dict[str, Dict[str, float]] = TYPE_CHART_DATA

    def __init__(self, meta_profiles: Dict[str, MonMetaProfile]):
        self.meta = meta_profiles

    def evaluate_candidate(self, candidate_name: str, current_team: List[str]) -> Dict[str, float]:
        candidate = self.meta.get(candidate_name)
        if not candidate:
            raise ValueError(f"Candidate {candidate_name} not found in meta profile.")

        team_profiles = [self.meta[name] for name in current_team if name in self.meta]

        defensive_score = self._calc_defensive_synergy(candidate, team_profiles)
        threat_coverage_score = self._calc_moveset_threat_coverage(candidate)
        archetype_synergy_score = self._calc_archetype_synergy(candidate, team_profiles)
        counter_index = self._calc_counter_index(candidate, team_profiles)

        raw_score = (
            (defensive_score * 0.30)
            + (threat_coverage_score * 0.25)
            + (archetype_synergy_score * 0.25)
            + (counter_index * 0.20)
        )

        sharpened_score = self._apply_variance_scaling(raw_score)

        return {
            "final_rating": round(sharpened_score, 2),
            "defensive_fit": round(defensive_score, 2),
            "meta_coverage": round(threat_coverage_score, 2),
            "synergy_index": round(archetype_synergy_score, 2),
            "counter_utility": round(counter_index, 2),
            "recommendation_class": self._classify_rating(sharpened_score),
        }

    def _calc_defensive_synergy(self, candidate: MonMetaProfile, team: List[MonMetaProfile]) -> float:
        if not team:
            return 50.0

        type_vulnerabilities: Dict[str, float] = {}

        for atk_type in self.TYPE_CHART.keys():
            vulnerability_sum = 0.0
            for member in team:
                mult = self._get_defensive_multiplier(atk_type, member.types)
                if mult > 1.0:
                    vulnerability_sum += mult - 1.0
                elif mult < 1.0:
                    vulnerability_sum -= 1.0 - mult
            type_vulnerabilities[atk_type] = vulnerability_sum

        synergy_points = 0.0
        for atk_type, team_vuln in type_vulnerabilities.items():
            cand_mult = self._get_defensive_multiplier(atk_type, candidate.types)

            if team_vuln > 0:
                if cand_mult == 0.0:
                    synergy_points += (team_vuln ** 1.5) * 25.0
                elif cand_mult < 1.0:
                    synergy_points += team_vuln * 12.0
                elif cand_mult > 1.0:
                    synergy_points -= (team_vuln * cand_mult) ** 2 * 8.0

        return self._normalize(synergy_points, min_val=-100, max_val=100)

    def _calc_moveset_threat_coverage(self, candidate: MonMetaProfile) -> float:
        coverage_score = 0.0

        for target_name, target_mon in self.meta.items():
            if target_name == candidate.name:
                continue

            meta_weight = target_mon.meta_usage_tier
            best_effective_power = 0.0

            for move in candidate.common_moves.values():
                if move.category == "Status":
                    continue

                eff = self._get_offensive_multiplier(move.type, target_mon.types)
                stab = 1.5 if move.type in candidate.types else 1.0
                effective_power = move.base_power * eff * stab * move.usage_rate
                best_effective_power = max(best_effective_power, effective_power)

            coverage_score += (best_effective_power / 100.0) * meta_weight

        return self._normalize(coverage_score, min_val=0, max_val=10)

    def _calc_archetype_synergy(self, candidate: MonMetaProfile, team: List[MonMetaProfile]) -> float:
        if not team:
            return 50.0

        synergy_score = 50.0
        candidate_tags = self._extract_mon_tags(candidate)

        for member in team:
            member_tags = self._extract_mon_tags(member)

            if member.name in candidate.top_partners:
                synergy_score += candidate.top_partners[member.name] * 20.0

            if "trick_room" in candidate_tags and member.base_stats.get("spe", 0) < 50:
                synergy_score += 15.0
            if "tailwind" in candidate_tags and 70 <= member.base_stats.get("spe", 0) <= 110:
                synergy_score += 10.0
            if "redirection" in candidate_tags and self._is_setup_sweeper(member):
                synergy_score += 15.0

        return max(0.0, min(100.0, synergy_score))

    def _calc_counter_index(self, candidate: MonMetaProfile, team: List[MonMetaProfile]) -> float:
        counter_score = 0.0

        for meta_mon in self.meta.values():
            threat_to_team = 0.0
            for team_member in team:
                if self._mon_beats_mon(meta_mon, team_member):
                    threat_to_team += 1.0

            if threat_to_team > 0 and self._mon_beats_mon(candidate, meta_mon):
                counter_score += threat_to_team * meta_mon.meta_usage_tier * 30.0

        return self._normalize(counter_score, min_val=0, max_val=50)

    def _apply_variance_scaling(self, score: float) -> float:
        centered = (score - 50.0) / 50.0
        sharpened = math.copysign(abs(centered) ** 1.35, centered)
        return max(0.0, min(100.0, (sharpened * 50.0) + 50.0))

    def _classify_rating(self, score: float) -> str:
        if score >= 82.0:
            return "Core Synergistic Pick"
        if score >= 65.0:
            return "Strong Meta Counter / Tech"
        if score <= 35.0:
            return "Anti-Synergistic / High Vulnerability Risk"
        return "Situational / Niche Specialist"

    def _get_defensive_multiplier(self, atk_type: str, def_types: List[str]) -> float:
        mult = 1.0
        for def_type in def_types:
            mult *= self.TYPE_CHART.get(atk_type, {}).get(def_type, 1.0)
        return mult

    def _get_offensive_multiplier(self, atk_type: str, def_types: List[str]) -> float:
        return self._get_defensive_multiplier(atk_type, def_types)

    def _extract_mon_tags(self, mon: MonMetaProfile) -> Set[str]:
        tags: Set[str] = set()
        for move in mon.common_moves.values():
            tags.update(move.tags)
        return tags

    def _is_setup_sweeper(self, mon: MonMetaProfile) -> bool:
        return any("setup" in move.tags for move in mon.common_moves.values())

    def _mon_beats_mon(self, attacker: MonMetaProfile, defender: MonMetaProfile) -> bool:
        stabs = [
            move
            for move in attacker.common_moves.values()
            if move.type in attacker.types and move.category != "Status"
        ]
        if not stabs:
            return False

        max_eff = max(
            (self._get_offensive_multiplier(move.type, defender.types) for move in stabs),
            default=1.0,
        )
        return max_eff >= 2.0

    def _normalize(self, val: float, min_val: float, max_val: float) -> float:
        clamped = max(min_val, min(max_val, val))
        return ((clamped - min_val) / (max_val - min_val)) * 100.0


def create_move_profile(name: str, raw_move_data: dict) -> MoveProfile:
    return MoveProfile(
        name=name,
        category=raw_move_data.get("category", "Physical"),
        type=raw_move_data.get("type", "Normal"),
        base_power=raw_move_data.get("base_power", 0),
        accuracy=raw_move_data.get("accuracy", 1.0),
        usage_rate=raw_move_data.get("usage_rate", 0.5),
        tags=set(raw_move_data.get("tags", [])),
    )


def build_meta_profiles_from_data(raw_meta_db: dict) -> Dict[str, MonMetaProfile]:
    meta_profiles: Dict[str, MonMetaProfile] = {}

    for mon_name, data in raw_meta_db.items():
        moves = {
            move_name: create_move_profile(move_name, move_data)
            for move_name, move_data in data.get("common_moves", {}).items()
        }

        meta_profiles[mon_name] = MonMetaProfile(
            name=mon_name,
            types=data.get("types", []),
            base_stats=data.get("base_stats", {}),
            common_moves=moves,
            common_abilities=data.get("common_abilities", {}),
            common_items=data.get("common_items", {}),
            meta_usage_tier=data.get("meta_usage_tier", 0.1),
            top_partners=data.get("top_partners", {}),
        )

    return meta_profiles
