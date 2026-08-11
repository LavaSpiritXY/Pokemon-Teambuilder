import math
import random
import re
from dataclasses import dataclass, field
from typing import Dict, List, Set, Tuple

import requests
import streamlit as strlit
import pandas as pd
from champions_phase18_5 import render_champions_profile_v6
from champions_phase18 import render_champions_profile_v3
from champions_phase17 import render_champions_profile_v2

try:
    from champions_integration import get_champions_profile
except ImportError:
    get_champions_profile = None

# ==========================================
# 1. ARCHETYPE & ENABLER REGISTRY
# ==========================================
ARCHETYPE_DEFINITIONS = {
    "Tailwind Enabler": {
        "abilities": ["Prankster", "Gale Wings", "Wind Power"],
        "moves": ["Tailwind"],
        "role_label": "Dedicated Speed Control / Tailwind Lead",
        "boost": 25
    },
    "Rain Setter": {
        "abilities": ["Drizzle"],
        "moves": ["Rain Dance"],
        "role_label": "Weather Anchor (Rain)",
        "boost": 20
    },
    "Sun Setter": {
        "abilities": ["Drought", "Orichalcum Pulse"],
        "moves": ["Sunny Day"],
        "role_label": "Weather Anchor (Sun)",
        "boost": 20
    },
    "Terrain Anchor": {
        "abilities": ["Psychic Surge", "Grassy Surge", "Electric Surge", "Misty Surge", "Sand Stream"],
        "moves": ["Psychic Terrain", "Grassy Terrain", "Electric Terrain", "Misty Terrain", "Sandstorm"],
        "role_label": "Terrain / Weather Anchor",
        "boost": 20
    },
    "Priority Blocker": {
        "abilities": ["Armor Tail", "Queenly Majesty", "Psychic Surge"],
        "moves": [],
        "role_label": "Defensive Utility / Anti-Priority",
        "boost": 18
    }
}

# Fallback Smogon Usage Database

SMOGON_USAGE_DB = {}

CHAMPIONS_META_DATA = {
    # Example structure.
    # Replace these values with your actual collected
    # Champions tournament/meta dataset.

    "whimsicott": {
        "usage_rate": 0.0,
        "win_rate": 0.0,
        "top_cut_rate": 0.0,
        "tournament_score": 0.0,
        "top_partners": {}
    },

    "farigiraf": {
        "usage_rate": 0.0,
        "win_rate": 0.0,
        "top_cut_rate": 0.0,
        "tournament_score": 0.0,
        "top_partners": {}
    }
}
def get_smogon_stats_for(mon_name):
    """
    Returns external competitive statistics when available.

    IMPORTANT:
    Missing data does NOT mean the Pokémon has low viability.
    It simply means we have no external signal.
    """

    if not mon_name:
        return {
            "meta_usage_tier": None,
            "common_moves": {},
            "common_abilities": {},
            "common_items": {},
            "top_partners": {}
        }

    # Try exact spelling first.
    stats = SMOGON_USAGE_DB.get(mon_name)

    if stats:
        return stats

    # Try case-insensitive matching.
    target = str(mon_name).strip().lower()

    for name, data in SMOGON_USAGE_DB.items():
        if str(name).strip().lower() == target:
            return data

    # No external data available.
    return {
        "meta_usage_tier": None,
        "common_moves": {},
        "common_abilities": {},
        "common_items": {},
        "top_partners": {}
    }

def get_hardcoded_move_type(move_name):
    move_map = {
        "Tailwind": "Flying", "Trick Room": "Psychic", "Rain Dance": "Water",
        "Sunny Day": "Fire", "Protect": "Normal", "Surf": "Water", "Eruption": "Fire"
    }
    return move_map.get(move_name, "Normal")

def fetch_move_type(move_name):
    return get_hardcoded_move_type(move_name)

def detect_archetypes(pkmn_data):
    """
    Scans a Pokémon's ability pool and relevant moveset to identify functional archetypes.
    Uses OR logic so anchors like Pelipper (Drizzle) are detected correctly.
    """
    matched_archetypes = []
    abilities = [str(a).lower() for a in pkmn_data.get("abilities", [])]
    moves = [str(m).lower() for m in pkmn_data.get("moves", [])]
    
    for arch_name, criteria in ARCHETYPE_DEFINITIONS.items():
        req_abs = [str(a).lower() for a in criteria.get("abilities", [])]
        req_moves = [str(m).lower() for m in criteria.get("moves", [])]
        
        has_ability = any(ab in abilities for ab in req_abs) if req_abs else False
        has_move = any(mv in moves for mv in req_moves) if req_moves else False
        
        # Match if EITHER ability or move condition is met
        if has_ability or has_move:
            matched_archetypes.append({
                "name": arch_name,
                "role_label": criteria.get("role_label", "Balanced Pick"),
                "boost": criteria.get("boost", 20)
            })
            
    return matched_archetypes

# ==========================================
# 2. META-INDEX AWARE VIABILITY & TIERING
# ==========================================
def calculate_meta_viability(
    pkmn_data,
    selected_format="Gen 9 OU",
    tournament_metrics=None
):
    """
    Calculate the Meta Viability Index.

    Priority:

    1. Tournament performance
    2. Tournament usage
    3. Tournament top-cut presence
    4. Tournament win rate
    5. External competitive data
    6. Strategic/archetype information

    Missing data is treated as UNKNOWN rather than BAD.
    """

    pkmn_name = pkmn_data.get(
        "name",
        "Unknown"
    )

    archetypes = detect_archetypes(
        pkmn_data
    )

    # =====================================================
    # 1. TOURNAMENT SIGNAL
    # =====================================================

    tournament_score = None

    if tournament_metrics:

        tournament_score = (
            tournament_metrics.get(
                "tournament_score"
            )
        )

        if tournament_score is not None:
            tournament_score = float(
                tournament_score
            )

            tournament_score = max(
                0.0,
                min(
                    1.0,
                    tournament_score
                )
            )

    # =====================================================
    # 2. EXTERNAL SIGNAL
    # =====================================================

    external_stats = get_smogon_stats_for(
        pkmn_name
    )

    external_usage = (
        external_stats.get(
            "meta_usage_tier"
        )
    )

    external_score = None

    if external_usage is not None:

        external_score = max(
            0.0,
            min(
                1.0,
                float(external_usage)
            )
        )

    # =====================================================
    # 3. STRATEGIC BASELINE
    # =====================================================

    default_score = float(
        pkmn_data.get(
            "default_score",
            50
        )
    )

    default_score = max(
        0.0,
        min(
            100.0,
            default_score
        )
    )

    # =====================================================
    # 4. COMBINE AVAILABLE EVIDENCE
    # =====================================================

    signals = []

    # Tournament data gets the largest weight.
    if tournament_score is not None:
        signals.append(
            (
                tournament_score * 100.0,
                0.70
            )
        )

    # External data is supplementary.
    if external_score is not None:
        signals.append(
            (
                external_score * 100.0,
                0.20
            )
        )

    # Strategic baseline fills only the remaining gap.
    signals.append(
        (
            default_score,
            0.10
        )
    )

    total_weight = sum(
        weight
        for _, weight in signals
    )

    weighted_score = (
        sum(
            score * weight
            for score, weight
            in signals
        )
        / total_weight
    )

    # =====================================================
    # 5. SMALL STRATEGIC BONUS
    # =====================================================

    archetype_boost = max(
        (
            float(
                archetype.get(
                    "boost",
                    0
                )
            )
            for archetype in archetypes
        ),
        default=0
    )

    # Do NOT let archetypes completely
    # override tournament performance.
    archetype_boost = max(
        -5,
        min(
            5,
            archetype_boost
        )
    )

    final_score = int(
        round(
            max(
                0,
                min(
                    100,
                    weighted_score
                    + archetype_boost
                )
            )
        )
    )

    # =====================================================
    # 6. DISPLAY TIER
    # =====================================================

    if final_score >= 90:
        tier_label = "S-Tier / Elite Meta Threat"

    elif final_score >= 80:
        tier_label = "A-Tier / Meta Staple"

    elif final_score >= 70:
        tier_label = "B-Tier / Strong Meta Pick"

    elif final_score >= 60:
        tier_label = "C-Tier / Viable Pick"

    elif final_score >= 45:
        tier_label = "D-Tier / Niche Pick"

    else:
        tier_label = "Low Meta Presence"

    # =====================================================
    # 7. ROLE
    # =====================================================

    roles = []

    for archetype in archetypes:

        role = archetype.get(
            "role_label"
        )

        if role and role not in roles:
            roles.append(role)

    if roles:

        team_role = " / ".join(
            roles
        )

    else:

        team_role = pkmn_data.get(
            "fallback_role",
            "Balanced Pick"
        )

    return {
        "viability_index": final_score,
        "tier_display": tier_label,
        "recommended_role": team_role,
        "archetypes_detected": [
            archetype.get("name")
            for archetype in archetypes
        ]
    }
# ==========================================
# 3. META-GATED CHECKS, COUNTERS & SYNERGY
# ==========================================

def get_meta_relevant_checks(
    pkmn_data,
    meta_pool,
    min_viability_threshold=0,
    top_n=3
):
    """
    Finds actual Champions checks/counters.

    Counter score considers:
    - STAB against target weakness
    - actual offensive moves
    - defensive resistance
    - speed
    - viability
    - ability interaction
    """

    target_types = set(pkmn_data.get("types", []))
    target_weaknesses = set(pkmn_data.get("weaknesses", []))
    target_moves = {
        str(m).lower()
        for m in pkmn_data.get("moves", [])
    }

    valid_checks = []

    for candidate_name, candidate_info in meta_pool.items():

        candidate_types = set(
            candidate_info.get("types", [])
        )

        candidate_moves = {
            str(m).lower()
            for m in candidate_info.get("moves", [])
        }

        candidate_abilities = {
            str(a).lower()
            for a in candidate_info.get("abilities", [])
        }

        candidate_stats = candidate_info.get(
            "stats",
            {}
        )

        candidate_speed = candidate_stats.get(
            "speed",
            0
        )

        viability = float(
            candidate_info.get(
                "viability_index",
                0
            )
        )

        score = 0.0
        reasons = []

        # -------------------------------------------------
        # 1. STAB TYPE ADVANTAGE
        # -------------------------------------------------

        stab_hits = candidate_types & target_weaknesses

        if stab_hits:
            score += len(stab_hits) * 25
            reasons.append(
                "STAB: " + ", ".join(sorted(stab_hits))
            )

        # -------------------------------------------------
        # 2. ACTUAL MOVE COVERAGE
        # -------------------------------------------------

        move_hits = set()

        for move in candidate_moves:

            move_type = fetch_move_type(move)

            if move_type in target_weaknesses:
                move_hits.add(move_type)

        if move_hits:
            score += len(move_hits) * 15
            reasons.append(
                "Coverage: "
                + ", ".join(sorted(move_hits))
            )

        # -------------------------------------------------
        # 3. SPEED ADVANTAGE
        # -------------------------------------------------

        target_speed = pkmn_data.get(
            "stats",
            {}
        ).get(
            "speed",
            100
        )

        if candidate_speed > target_speed:
            score += 10
            reasons.append("Speed advantage")

        # -------------------------------------------------
        # 4. DEFENSIVE PRESSURE
        # -------------------------------------------------

        defensive_score = 0

        for candidate_type in candidate_types:

            relations = get_type_relationships(
                candidate_type
            )

            resisted = {
                r["name"].title()
                for r in relations.get(
                    "half_damage_from",
                    []
                )
            }

            if any(
                weakness in resisted
                for weakness in target_weaknesses
            ):
                defensive_score += 5

        score += defensive_score

        # -------------------------------------------------
        # 5. ABILITY INTERACTION
        # -------------------------------------------------

        target_abilities = {
            str(a).lower()
            for a in pkmn_data.get(
                "abilities",
                []
            )
        }

        if "prankster" in target_abilities:

            if (
                "armor tail" in candidate_abilities
                or
                "queenly majesty"
                in candidate_abilities
            ):
                score += 20
                reasons.append(
                    "Anti-Prankster ability"
                )

        # -------------------------------------------------
        # 6. VIABILITY RANKING
        # -------------------------------------------------

        score += viability * 0.25

        # -------------------------------------------------
        # 7. REQUIRE ACTUAL COUNTERPLAY
        # -------------------------------------------------

        if not stab_hits and not move_hits:
            continue

        valid_checks.append({
            "name": candidate_name,
            "score": score,
            "viability": viability,
            "reason": (
                " • ".join(reasons)
                if reasons
                else "Competitive check"
            )
        })

    valid_checks.sort(
        key=lambda x: x["score"],
        reverse=True
    )

    return valid_checks[:top_n]


# -----------------------------------------------------------------------------
# 0. COMPETITIVE META EVALUATION ENGINE & DATA MODELS
# -----------------------------------------------------------------------------

CHAMPIONS_META_DB = {}

CURRENT_REGULATION = "M-B"

@dataclass
class MoveProfile:
    name: str
    category: str  # "Physical", "Special", "Status"
    type: str
    base_power: int
    accuracy: float
    usage_rate: float  # e.g., 0.85 for 85%
    tags: Set[str] = field(default_factory=set)  # {"priority", "setup", "spread", "speed_control", "redirection"}

@dataclass
class MonMetaProfile:
    name: str
    types: List[str]
    base_stats: Dict[str, int]
    common_moves: Dict[str, MoveProfile]  # Move name -> MoveProfile
    common_abilities: Dict[str, float]   # Ability -> usage rate
    common_items: Dict[str, float]       # Item -> usage rate
    meta_usage_tier: float               # Usage percentage in meta (0.0 to 1.0)
    top_partners: Dict[str, float]       # Partner name -> usage rate together

# Complete standard Type Chart Matrix mapping (Attacker -> Defender -> Multiplier)
TYPE_CHART_DATA: Dict[str, Dict[str, float]] = {
    "Normal": {"Rock": 0.5, "Ghost": 0.0, "Steel": 0.5},
    "Fire": {"Fire": 0.5, "Water": 0.5, "Grass": 2.0, "Ice": 2.0, "Bug": 2.0, "Rock": 0.5, "Dragon": 0.5, "Steel": 2.0},
    "Water": {"Fire": 2.0, "Water": 0.5, "Grass": 0.5, "Ground": 2.0, "Rock": 2.0, "Dragon": 0.5},
    "Electric": {"Water": 2.0, "Electric": 0.5, "Grass": 0.5, "Ground": 0.0, "Flying": 2.0, "Dragon": 0.5},
    "Grass": {"Fire": 0.5, "Water": 2.0, "Grass": 0.5, "Poison": 0.5, "Ground": 2.0, "Flying": 0.5, "Bug": 0.5, "Rock": 2.0, "Dragon": 0.5, "Steel": 0.5},
    "Ice": {"Fire": 0.5, "Water": 0.5, "Grass": 2.0, "Ice": 0.5, "Ground": 2.0, "Flying": 2.0, "Dragon": 2.0, "Steel": 0.5},
    "Fighting": {"Normal": 2.0, "Ice": 2.0, "Poison": 0.5, "Flying": 0.5, "Psychic": 0.5, "Bug": 0.5, "Rock": 2.0, "Ghost": 0.0, "Dark": 2.0, "Steel": 2.0, "Fairy": 0.5},
    "Poison": {"Grass": 2.0, "Poison": 0.5, "Ground": 0.5, "Rock": 0.5, "Ghost": 0.5, "Steel": 0.0, "Fairy": 2.0},
    "Ground": {"Fire": 2.0, "Electric": 2.0, "Grass": 0.5, "Poison": 2.0, "Flying": 0.0, "Bug": 0.5, "Rock": 2.0, "Steel": 2.0},
    "Flying": {"Electric": 0.5, "Grass": 2.0, "Fighting": 2.0, "Bug": 2.0, "Rock": 0.5, "Steel": 0.5},
    "Psychic": {"Fighting": 2.0, "Poison": 2.0, "Psychic": 0.5, "Steel": 0.5, "Dark": 0.0},
    "Bug": {"Fire": 0.5, "Grass": 2.0, "Fighting": 0.5, "Poison": 0.5, "Flying": 0.5, "Psychic": 2.0, "Ghost": 0.5, "Dark": 2.0, "Steel": 0.5, "Fairy": 0.5},
    "Rock": {"Fire": 2.0, "Ice": 2.0, "Fighting": 0.5, "Ground": 0.5, "Flying": 2.0, "Bug": 2.0, "Steel": 0.5},
    "Ghost": {"Normal": 0.0, "Psychic": 2.0, "Ghost": 2.0, "Dark": 0.5},
    "Dragon": {"Dragon": 2.0, "Steel": 0.5, "Fairy": 0.0},
    "Dark": {"Fighting": 0.5, "Psychic": 2.0, "Ghost": 2.0, "Dark": 0.5, "Fairy": 0.5},
    "Steel": {"Fire": 0.5, "Water": 0.5, "Electric": 0.5, "Ice": 2.0, "Rock": 2.0, "Steel": 0.5, "Fairy": 2.0},
    "Fairy": {"Fire": 0.5, "Fighting": 2.0, "Poison": 0.5, "Dragon": 2.0, "Dark": 2.0, "Steel": 0.5}
}

class TeamEvaluator:
    TYPE_CHART: Dict[str, Dict[str, float]] = TYPE_CHART_DATA

    def __init__(self, meta_profiles: Dict[str, MonMetaProfile]):
        self.meta = meta_profiles

    def evaluate_candidate(
        self, 
        candidate_name: str, 
        current_team: List[str]
    ) -> Dict[str, float]:
        candidate = self.meta.get(candidate_name)
        if not candidate:
            raise ValueError(f"Candidate {candidate_name} not found in meta profile.")

        team_profiles = [self.meta[name] for name in current_team if name in self.meta]

        defensive_score = self._calc_defensive_synergy(candidate, team_profiles)
        threat_coverage_score = self._calc_moveset_threat_coverage(candidate)
        archetype_synergy_score = self._calc_archetype_synergy(candidate, team_profiles)
        counter_index = self._calc_counter_index(candidate, team_profiles)

        raw_score = (
            (defensive_score * 0.30) +
            (threat_coverage_score * 0.25) +
            (archetype_synergy_score * 0.25) +
            (counter_index * 0.20)
        )

        sharpened_score = self._apply_variance_scaling(raw_score)

        return {
            "final_rating": round(sharpened_score, 2),
            "defensive_fit": round(defensive_score, 2),
            "meta_coverage": round(threat_coverage_score, 2),
            "synergy_index": round(archetype_synergy_score, 2),
            "counter_utility": round(counter_index, 2),
            "recommendation_class": self._classify_rating(sharpened_score)
        }

    def _calc_defensive_synergy(
        self, 
        candidate: MonMetaProfile, 
        team: List[MonMetaProfile]
    ) -> float:
        if not team:
            return 50.0

        type_vulnerabilities: Dict[str, float] = {}

        for atk_type in self.TYPE_CHART.keys():
            vulnerability_sum = 0.0
            for member in team:
                mult = self._get_defensive_multiplier(atk_type, member.types)
                if mult > 1.0:
                    vulnerability_sum += (mult - 1.0)
                elif mult < 1.0:
                    vulnerability_sum -= (1.0 - mult)
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
            for move_name, move in candidate.common_moves.items():
                if move.category == "Status":
                    continue

                eff = self._get_offensive_multiplier(move.type, target_mon.types)
                stab = 1.5 if move.type in candidate.types else 1.0
                
                effective_power = move.base_power * eff * stab * move.usage_rate
                if effective_power > best_effective_power:
                    best_effective_power = effective_power

            coverage_score += (best_effective_power / 100.0) * meta_weight

        return self._normalize(coverage_score, min_val=0, max_val=10)

    def _calc_archetype_synergy(
        self, 
        candidate: MonMetaProfile, 
        team: List[MonMetaProfile]
    ) -> float:
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

    def _calc_counter_index(
        self, 
        candidate: MonMetaProfile, 
        team: List[MonMetaProfile]
    ) -> float:
        counter_score = 0.0
        
        for meta_mon_name, meta_mon in self.meta.items():
            threat_to_team = 0.0
            for team_member in team:
                if self._mon_beats_mon(meta_mon, team_member):
                    threat_to_team += 1.0

            if threat_to_team > 0:
                if self._mon_beats_mon(candidate, meta_mon):
                    counter_score += threat_to_team * meta_mon.meta_usage_tier * 30.0

        return self._normalize(counter_score, min_val=0, max_val=50)

    def _apply_variance_scaling(self, score: float) -> float:
        centered = (score - 50.0) / 50.0
        sharpened = math.copysign(abs(centered) ** 1.35, centered)
        final_score = (sharpened * 50.0) + 50.0
        return max(0.0, min(100.0, final_score))

    def _classify_rating(self, score: float) -> str:
        if score >= 82.0:
            return "Core Synergistic Pick"
        elif score >= 65.0:
            return "Strong Meta Counter / Tech"
        elif score <= 35.0:
            return "Anti-Synergistic / High Vulnerability Risk"
        else:
            return "Situational / Niche Specialist"

    def _get_defensive_multiplier(self, atk_type: str, def_types: List[str]) -> float:
        mult = 1.0
        for dt in def_types:
            mult *= self.TYPE_CHART.get(atk_type, {}).get(dt, 1.0)
        return mult

    def _get_offensive_multiplier(self, atk_type: str, def_types: List[str]) -> float:
        return self._get_defensive_multiplier(atk_type, def_types)

    def _extract_mon_tags(self, mon: MonMetaProfile) -> Set[str]:
        tags = set()
        for move in mon.common_moves.values():
            tags.update(move.tags)
        return tags

    def _is_setup_sweeper(self, mon: MonMetaProfile) -> bool:
        return any("setup" in move.tags for move in mon.common_moves.values())

    def _mon_beats_mon(self, attacker: MonMetaProfile, defender: MonMetaProfile) -> bool:
        stabs = [m for m in attacker.common_moves.values() if m.type in attacker.types and m.category != "Status"]
        if not stabs:
            return False
        max_eff = max([self._get_offensive_multiplier(m.type, defender.types) for m in stabs], default=1.0)
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
        tags=set(raw_move_data.get("tags", []))
    )

def build_meta_profiles_from_data(raw_meta_db: dict) -> Dict[str, MonMetaProfile]:
    meta_profiles = {}
    for mon_name, data in raw_meta_db.items():
        moves = {
            m_name: create_move_profile(m_name, m_data)
            for m_name, m_data in data.get("common_moves", {}).items()
        }

        meta_profiles[mon_name] = MonMetaProfile(
            name=mon_name,
            types=data.get("types", []),
            base_stats=data.get("base_stats", {}),
            common_moves=moves,
            common_abilities=data.get("common_abilities", {}),
            common_items=data.get("common_items", {}),
            meta_usage_tier=data.get("meta_usage_tier", 0.1),
            top_partners=data.get("top_partners", {})
        )
    return meta_profiles

# -----------------------------------------------------------------------------
# 1. CONFIG & VISUAL STYLING
# -----------------------------------------------------------------------------
strlit.set_page_config(
    page_title="Pokémon Champions Teambuilder",
    page_icon="⚔️",
    layout="wide",
    initial_sidebar_state="expanded"
)

TYPE_COLORS = {
    "Normal": "#A8A77A", "Fire": "#EE8130", "Water": "#6390F0", "Electric": "#F7D02C",
    "Grass": "#7AC74C", "Ice": "#96D9D6", "Fighting": "#C22E28", "Poison": "#A33EA1",
    "Ground": "#E2BF65", "Flying": "#A98FF3", "Psychic": "#F95587", "Bug": "#A6B91A",
    "Rock": "#B6A136", "Ghost": "#735797", "Dragon": "#6F35FC", "Dark": "#705746",
    "Steel": "#B7B7CE", "Fairy": "#D685AD"
}

TYPE_SVG_URLS = {
    "Normal": "https://raw.githubusercontent.com/duiker101/pokemon-type-svg-icons/master/icons/normal.svg",
    "Fire": "https://raw.githubusercontent.com/duiker101/pokemon-type-svg-icons/master/icons/fire.svg",
    "Water": "https://raw.githubusercontent.com/duiker101/pokemon-type-svg-icons/master/icons/water.svg",
    "Electric": "https://raw.githubusercontent.com/duiker101/pokemon-type-svg-icons/master/icons/electric.svg",
    "Grass": "https://raw.githubusercontent.com/duiker101/pokemon-type-svg-icons/master/icons/grass.svg",
    "Ice": "https://raw.githubusercontent.com/duiker101/pokemon-type-svg-icons/master/icons/ice.svg",
    "Fighting": "https://raw.githubusercontent.com/duiker101/pokemon-type-svg-icons/master/icons/fighting.svg",
    "Poison": "https://raw.githubusercontent.com/duiker101/pokemon-type-svg-icons/master/icons/poison.svg",
    "Ground": "https://raw.githubusercontent.com/duiker101/pokemon-type-svg-icons/master/icons/ground.svg",
    "Flying": "https://raw.githubusercontent.com/duiker101/pokemon-type-svg-icons/master/icons/flying.svg",
    "Psychic": "https://raw.githubusercontent.com/duiker101/pokemon-type-svg-icons/master/icons/psychic.svg",
    "Bug": "https://raw.githubusercontent.com/duiker101/pokemon-type-svg-icons/master/icons/bug.svg",
    "Rock": "https://raw.githubusercontent.com/duiker101/pokemon-type-svg-icons/master/icons/rock.svg",
    "Ghost": "https://raw.githubusercontent.com/duiker101/pokemon-type-svg-icons/master/icons/ghost.svg",
    "Dragon": "https://raw.githubusercontent.com/duiker101/pokemon-type-svg-icons/master/icons/dragon.svg",
    "Dark": "https://raw.githubusercontent.com/duiker101/pokemon-type-svg-icons/master/icons/dark.svg",
    "Steel": "https://raw.githubusercontent.com/duiker101/pokemon-type-svg-icons/master/icons/steel.svg",
    "Fairy": "https://raw.githubusercontent.com/duiker101/pokemon-type-svg-icons/master/icons/fairy.svg"
}

NATURES = [
    "Adamant (+Atk, -SpA)", "Bold (+Def, -Atk)", "Brave (+Atk, -Spe)", "Calm (+SpD, -Atk)",
    "Careful (+SpD, -SpA)", "Gentle (+SpD, -Def)", "Hardy", "Hasty (+Spe, -Def)",
    "Impish (+Def, -SpA)", "Jolly (+Spe, -SpA)", "Lax (+Def, -SpD)", "Lonely (+Atk, -Def)",
    "Mild (+SpA, -Def)", "Modest (+SpA, -Atk)", "Naive (+Spe, -SpD)", "Naughty (+Atk, -SpD)",
    "Quiet (+SpA, -Spe)", "Rash (+SpA, -SpD)", "Relaxed (+Def, -Spe)", "Sassy (+SpD, -Spe)",
    "Serious", "Timid (+Spe, -Atk)"
]

SPECIES_DISPLAY_OVERRIDES = {

    # ==========================================
    # PALDEA FORMS (Squashed Fallbacks for UI)
    # ==========================================
    "taurospaldeacombat": "Tauros Paldea Combat",
    "taurospaldeacombatbreed": "Tauros Paldea Combat",
    "taurospaldeablaze": "Tauros Paldea Blaze",
    "taurospaldeaaqua": "Tauros Paldea Aqua",

    # ==========================================
    # PALDEA FORMS (Clean Endpoint Matches)
    # ==========================================
    "tauros-paldea-combat-breed": "Tauros Paldea Combat",
    "tauros-paldea-blaze": "Tauros Paldea Blaze",
    "tauros-paldea-aqua": "Tauros Paldea Aqua",

    # =========================================================
    # BASCULEGION
    # =========================================================

    "basculegion-male": "Basculegion",
    "basculegion-m": "Basculegion",
    "basculegionm": "Basculegion",
    "basculegion-f": "Basculegion Female",
    "basculegion-female": "Basculegion Female",
    "basculegionf": "Basculegion Female",

    # =========================================================
    # INDEEDEE
    # =========================================================

    "indeedeef": "Indeedee Female",
    "indeedee-f": "Indeedee Female",
    "indeedee-female": "Indeedee Female",

    "indeedeem": "Indeedee Male",
    "indeedee-m": "Indeedee Male",
    "indeedee-male": "Indeedee Male",

    # =========================================================
    # MEOWSTIC
    # =========================================================

    "meowsticmale": "Meowstic Male",
    "meowstic-m": "Meowstic Male",
    "meowstic-male": "Meowstic Male",

    "meowsticfemale": "Meowstic Female",
    "meowstic-f": "Meowstic Female",
    "meowstic-female": "Meowstic Female",

    # =========================================================
    # OINKOLOGNE
    # =========================================================

    "oinkolognem": "Oinkologne Male",
    "oinkologne-m": "Oinkologne Male",

    "oinkolognef": "Oinkologne Female",
    "oinkologne-f": "Oinkologne Female",

    # =========================================================
    # EXISTING SPECIAL NAMES
    # =========================================================

    "mr-mime": "Mr. Mime",
    "mime-jr": "Mime Jr.",
    "ho-oh": "Ho-Oh",
    "nidoran-f": "Nidoran Female",
    "nidoran-m": "Nidoran Male",
    "farfetchd": "Farfetch'd",
    "sirfetchd": "Sirfetch'd",
    "flabebe": "Flabébé",
    "type-null": "Type: Null",
}

strlit.markdown("""
<style>
    .stApp {
        background: linear-gradient(135deg, #0b0e14 0%, #1a1f2c 100%);
        color: #e6edf3;
    }
    header[data-testid="stHeader"] { background: transparent; }
    
    .type-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 700;
        font-size: 13px;
        color: white;
        white-space: nowrap;
    }
    
    .move-card {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 8px;
        padding: 10px 14px;
        border-radius: 8px;
        font-weight: 600;
        color: white;
        margin-top: -4px;
        margin-bottom: 14px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        width: 100%;
        box-sizing: border-box;
        overflow: hidden;
    }
    
    .move-name {
        flex: 1;
        min-width: 0;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    .move-type-badge {
        flex-shrink: 0;
        display: flex;
        align-items: center;
        gap: 4px;
        font-size: 11px;
    }

    .analytics-container {
        background: rgba(18, 23, 35, 0.8);
        border: 1px solid rgba(255, 255, 255, 0.15);
        border-radius: 12px;
        padding: 16px;
        margin-top: 14px;
        box-shadow: 0 8px 24px rgba(0,0,0,0.4);
    }

    .analytics-title {
        font-size: 16px;
        font-weight: 700;
        color: #f0f6fc;
        margin-bottom: 12px;
        display: flex;
        align-items: center;
        gap: 8px;
        border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        padding-bottom: 8px;
    }

    .stat-box-row {
        display: flex;
        gap: 12px;
        margin-bottom: 12px;
    }

    .stat-box {
        flex: 1;
        background: rgba(255, 255, 255, 0.04);
        border-left: 4px solid #6390F0;
        border-radius: 6px;
        padding: 10px 12px;
    }

    .stat-box.counter-box {
        border-left-color: #EE8130;
    }

    .stat-box.viability-box {
        border-left-color: #7AC74C;
    }

    .stat-label {
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        color: #8b949e;
        font-weight: 700;
        margin-bottom: 4px;
    }

    .stat-value {
        font-size: 15px;
        font-weight: 700;
        color: #e6edf3;
    }

    .type-chip {
        display: inline-flex;
        align-items: center;
        justify-content: space-between;
        gap: 4px;
        box-sizing: border-box;
        border-radius: 8px;
        color: white;
        font-size: 13px;
        font-weight: 700;
        margin: 10px 8px 0 0;
        min-height: 38px;
        padding: 5px 11px;
        width: 132px;
    }

    .type-chip img {
        height: 18px;
        width: 18px;
        filter: brightness(0) invert(1);
    }

    .type-multiplier {
        font-size: 13px;
        font-weight: 800;
        opacity: 0.9;
    }

    .type-chart-empty {
        color: #8b949e;
        font-size: 14px;
        font-weight: 700;
        margin-top: 4px;
    }

    .entity-pill {
        display: inline-flex;
        align-items: center;
        background: rgba(255, 255, 255, 0.08);
        border: 1px solid rgba(255, 255, 255, 0.12);
        border-radius: 20px;
        padding: 4px 10px 4px 4px;
        margin: 4px 6px 4px 0;
        font-size: 13px;
        font-weight: 600;
        color: #f0f6fc;
    }

    .entity-pill img {
        width: 38px;
        height: 38px;
        margin-right: 8px;
        border-radius: 50%;
        background: rgba(0,0,0,0.2);
        object-fit: contain;
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. DYNAMIC MASTER MOVE DICTIONARY & ROSTER DATA
# -----------------------------------------------------------------------------
@strlit.cache_data(ttl=86400, show_spinner=False)
def fetch_master_move_dictionary():
    urls = [
        "https://raw.githubusercontent.com/smogon/pokemon-showdown/master/data/moves.ts",
        "https://raw.githubusercontent.com/smogon/pokemon-showdown/master/data/mods/champions/moves.ts"
    ]
    move_dict = {}
    for url in urls:
        try:
            res = requests.get(url, timeout=15)
            if res.status_code == 200:
                matches = re.findall(r'([a-z0-9]+)\s*:\s*\{[^}]*?name\s*:\s*["\']([^"\']+)["\']', res.text, re.DOTALL)
                for move_id, display_name in matches:
                    move_dict[move_id.lower().replace("-", "").replace(" ", "")] = display_name
        except Exception:
            continue
    return move_dict

MASTER_MOVE_DICTIONARY = fetch_master_move_dictionary()

MOVE_DISPLAY_OVERRIDES = {
    "storedpower": "Stored Power",
    "stompingtantrum": "Stomping Tantrum",
    "doubleironbash": "Double Iron Bash",
    "populationbomb": "Population Bomb",
    "gigatonhammer": "Gigaton Hammer",
    "lastrespects": "Last Respects",
    "tripleaxel": "Triple Axel",
}

def canonical_species_key(name):
    """
    Converts a Pokémon name into ONE stable internal key.

    Important:
    - Keeps meaningful form information.
    - Does NOT squash words together.
    - Does NOT try to guess a PokeAPI ID.
    - Does NOT remove form names.
    """

    if not name:
        return ""

    text = str(name).strip().lower()

    # Normalise punctuation only.
    text = text.replace("’", "'")
    text = text.replace("_", "-")

    # Normalise repeated whitespace.
    text = " ".join(text.split())

    # Standardise common punctuation around hyphens.
    text = text.replace(" - ", "-")
    text = text.replace(" -", "-")
    text = text.replace("- ", "-")

    # Explicit aliases for forms whose names can be represented
    # differently by different data sources.
    aliases = {
        # Basculegion
        "basculegion male": "Basculegion",
        "basculegion female": "Basculegion Female",
        "basculegion-male": "Basculegion",
        "basculegion-female": "Basculegion Female",

        # Rotom
        "rotom wash": "rotom-wash",
        "rotom heat": "rotom-heat",
        "rotom frost": "rotom-frost",
        "rotom fan": "rotom-fan",
        "rotom mow": "rotom-mow",

        # Lycanroc
        "lycanroc midday": "lycanroc-midday",
        "lycanroc midnight": "lycanroc-midnight",
        "lycanroc dusk": "lycanroc-dusk",

        # Galarian forms
        "slowbro galar": "slowbro-galar",
        "slowking galar": "slowking-galar",
        "mr mime galar": "mr-mime-galar",

        # Hisuian forms
        "braviary hisui": "braviary-hisui",
        "decidueye hisui": "decidueye-hisui",
        "electrode hisui": "electrode-hisui",
        "goodra hisui": "goodra-hisui",
        "lilligant hisui": "lilligant-hisui",
        "qwilfish hisui": "qwilfish-hisui",
        "samurott hisui": "samurott-hisui",
        "sliggoo hisui": "sliggoo-hisui",
        "typhlosion hisui": "typhlosion-hisui",
        "voltorb hisui": "voltorb-hisui",
        "zoroark hisui": "zoroark-hisui",
        "avalugg hisui": "avalugg-hisui",
        "arcanine hisui": "arcanine-hisui",
        "decidueye hisuian": "decidueye-hisui",
        "lilligant hisuian": "lilligant-hisui",
        "zoroark hisuian": "zoroark-hisui",

        # Alolan forms
        "raichu alola": "raichu-alola",
        "rattata alola": "rattata-alola",
        "raticate alola": "raticate-alola",
        "sandshrew alola": "sandshrew-alola",
        "sandslash alola": "sandslash-alola",
        "vulpix alola": "vulpix-alola",
        "ninetales alola": "ninetales-alola",
        "diglett alola": "diglett-alola",
        "dugtrio alola": "dugtrio-alola",
        "meowth alola": "meowth-alola",
        "persian alola": "persian-alola",
        "geodude alola": "geodude-alola",
        "graveler alola": "graveler-alola",
        "golem alola": "golem-alola",
        "grimer alola": "grimer-alola",
        "muk alola": "muk-alola",

        # Paldean forms
        "wooper paldea": "wooper-paldea",
    }
    # Force fix squashed Paldean Tauros inputs
    if text == "taurospaldeacombat" or text == "taurospaldeacombatbreed":
        text = "tauros-paldea-combat-breed"
    elif text == "taurospaldeablaze":
        text = "tauros-paldea-blaze"
    elif text == "taurospaldeaaqua":
        text = "tauros-paldea-aqua"

    # This will now safely check the aliases dictionary using the fixed text variable
    return aliases.get(text, text)

def display_name_for_move(move_id):
    if not move_id:
        return ""

    raw = str(move_id).strip()

    clean_id = (
        raw
        .lower()
        .replace("_", "")
        .replace("-", "")
        .replace(" ", "")
    )

    # 1. Explicit canonical edge cases
    if clean_id in MOVE_DISPLAY_OVERRIDES:
        return MOVE_DISPLAY_OVERRIDES[clean_id]

    # 2. Canonical Pokémon Showdown dictionary
    if clean_id in MASTER_MOVE_DICTIONARY:
        return MASTER_MOVE_DICTIONARY[clean_id]

    # 3. Readable fallback
    spaced = re.sub(
        r'([a-z])([A-Z])',
        r'\1 \2',
        raw
    )

    return " ".join(
        part.title()
        for part in spaced.replace("-", " ").split()
    )

CUSTOM_MEGAS_DATA = {
    "Mega Venusaur": {"ability": "Thick Fat", "hp": 80, "atk": 100, "def": 123, "spa": 122, "spd": 120, "spd_stat": 80},
    "Mega Charizard X": {"ability": "Tough Claws", "hp": 78, "atk": 130, "def": 111, "spa": 130, "spd": 85, "spd_stat": 100},
    "Mega Charizard Y": {"ability": "Drought", "hp": 78, "atk": 104, "def": 78, "spa": 159, "spd": 115, "spd_stat": 100},
    "Mega Blastoise": {"ability": "Mega Launcher", "hp": 79, "atk": 103, "def": 120, "spa": 135, "spd": 115, "spd_stat": 78},
    "Mega Beedrill": {"ability": "Adaptability", "hp": 65, "atk": 150, "def": 40, "spa": 15, "spd": 80, "spd_stat": 145},
    "Mega Pidgeot": {"ability": "No Guard", "hp": 83, "atk": 80, "def": 80, "spa": 135, "spd": 80, "spd_stat": 121},
    "Mega Raichu X": {"ability": "Electric Surge", "hp": 60, "atk": 135, "def": 95, "spa": 90, "spd": 95, "spd_stat": 110},
    "Mega Raichu Y": {"ability": "No Guard", "hp": 60, "atk": 100, "def": 55, "spa": 160, "spd": 80, "spd_stat": 130},
    "Mega Clefable": {"ability": "Magic Bounce", "hp": 95, "atk": 80, "def": 93, "spa": 135, "spd": 110, "spd_stat": 70},
    "Mega Alakazam": {"ability": "Trace", "hp": 55, "atk": 50, "def": 65, "spa": 175, "spd": 105, "spd_stat": 150},
    "Mega Victreebel": {"ability": "Innards Out", "hp": 80, "atk": 125, "def": 85, "spa": 135, "spd": 95, "spd_stat": 70},
    "Mega Slowbro": {"ability": "Shell Armor", "hp": 95, "atk": 75, "def": 180, "spa": 130, "spd": 80, "spd_stat": 30},
    "Mega Gengar": {"ability": "Shadow Tag", "hp": 60, "atk": 65, "def": 80, "spa": 170, "spd": 95, "spd_stat": 130},
    "Mega Kangaskhan": {"ability": "Parental Bond", "hp": 105, "atk": 125, "def": 100, "spa": 60, "spd": 100, "spd_stat": 100},
    "Mega Starmie": {"ability": "Huge Power", "hp": 60, "atk": 100, "def": 105, "spa": 130, "spd": 105, "spd_stat": 120},
    "Mega Pinsir": {"ability": "Aerilate", "hp": 65, "atk": 155, "def": 120, "spa": 65, "spd": 90, "spd_stat": 105},
    "Mega Gyarados": {"ability": "Mold Breaker", "hp": 95, "atk": 155, "def": 109, "spa": 70, "spd": 130, "spd_stat": 81},
    "Mega Aerodactyl": {"ability": "Tough Claws", "hp": 80, "atk": 135, "def": 85, "spa": 70, "spd": 95, "spd_stat": 150},
    "Mega Dragonite": {"ability": "Multiscale", "hp": 91, "atk": 124, "def": 115, "spa": 145, "spd": 125, "spd_stat": 100},
    "Mega Tyranitar": {"ability": "Sand Stream", "hp": 100, "atk": 164, "def": 150, "spa": 95, "spd": 120, "spd_stat": 71},
    "Mega Sceptile": {"ability": "Lightning Rod", "hp": 70, "atk": 110, "def": 75, "spa": 145, "spd": 85, "spd_stat": 145},
    "Mega Blaziken": {"ability": "Speed Boost", "hp": 80, "atk": 160, "def": 80, "spa": 130, "spd": 80, "spd_stat": 100},
    "Mega Swampert": {"ability": "Swift Swim", "hp": 100, "atk": 150, "def": 110, "spa": 95, "spd": 110, "spd_stat": 70},
    "Mega Gardevoir": {"ability": "Pixilate", "hp": 68, "atk": 85, "def": 65, "spa": 165, "spd": 135, "spd_stat": 100},
    "Mega Sableye": {"ability": "Magic Bounce", "hp": 50, "atk": 85, "def": 125, "spa": 85, "spd": 115, "spd_stat": 20},
    "Mega Mawile": {"ability": "Huge Power", "hp": 50, "atk": 105, "def": 125, "spa": 55, "spd": 95, "spd_stat": 50},
    "Mega Aggron": {"ability": "Filter", "hp": 70, "atk": 140, "def": 230, "spa": 60, "spd": 80, "spd_stat": 50},
    "Mega Medicham": {"ability": "Pure Power", "hp": 60, "atk": 100, "def": 85, "spa": 80, "spd": 85, "spd_stat": 100},
    "Mega Manectric": {"ability": "Intimidate", "hp": 70, "atk": 75, "def": 80, "spa": 135, "spd": 80, "spd_stat": 135},
    "Mega Sharpedo": {"ability": "Strong Jaw", "hp": 70, "atk": 140, "def": 70, "spa": 110, "spd": 65, "spd_stat": 105},
    "Mega Camerupt": {"ability": "Sheer Force", "hp": 70, "atk": 120, "def": 100, "spa": 145, "spd": 105, "spd_stat": 20},
    "Mega Altaria": {"ability": "Pixilate", "hp": 75, "atk": 110, "def": 110, "spa": 110, "spd": 105, "spd_stat": 80},
    "Mega Banette": {"ability": "Prankster", "hp": 64, "atk": 165, "def": 75, "spa": 93, "spd": 83, "spd_stat": 75},
    "Mega Absol": {"ability": "Magic Bounce", "hp": 65, "atk": 150, "def": 60, "spa": 115, "spd": 60, "spd_stat": 115},
    "Mega Glalie": {"ability": "Refrigerate", "hp": 80, "atk": 120, "def": 80, "spa": 120, "spd": 80, "spd_stat": 100},
    "Mega Metagross": {"ability": "Tough Claws", "hp": 80, "atk": 145, "def": 150, "spa": 105, "spd": 110, "spd_stat": 110},
    "Mega Staraptor": {"ability": "Contrary", "hp": 85, "atk": 140, "def": 100, "spa": 60, "spd": 90, "spd_stat": 110},
    "Mega Lopunny": {"ability": "Scrappy", "hp": 65, "atk": 136, "def": 94, "spa": 54, "spd": 96, "spd_stat": 135},
    "Mega Garchomp": {"ability": "Sand Force", "hp": 108, "atk": 170, "def": 115, "spa": 120, "spd": 95, "spd_stat": 92},
    "Mega Lucario": {"ability": "Adaptability", "hp": 70, "atk": 145, "def": 88, "spa": 140, "spd": 70, "spd_stat": 112},
    "Mega Gallade": {"ability": "Inner Focus", "hp": 68, "atk": 165, "def": 95, "spa": 65, "spd": 115, "spd_stat": 110},
    "Mega Emboar": {"ability": "Mold Breaker", "hp": 110, "atk": 148, "def": 75, "spa": 110, "spd": 110, "spd_stat": 75},
    "Mega Excadrill": {"ability": "Piercing Drill", "hp": 110, "atk": 165, "def": 100, "spa": 65, "spd": 65, "spd_stat": 103},
    "Mega Audino": {"ability": "Healer", "hp": 103, "atk": 60, "def": 126, "spa": 80, "spd": 126, "spd_stat": 50},
    "Mega Scrafty": {"ability": "Intimidate", "hp": 65, "atk": 130, "def": 135, "spa": 55, "spd": 135, "spd_stat": 68},
    "Mega Chandelure": {"ability": "Infiltrator", "hp": 60, "atk": 75, "def": 110, "spa": 175, "spd": 110, "spd_stat": 90},
    "Mega Golurk": {"ability": "Unseen Fist", "hp": 89, "atk": 159, "def": 105, "spa": 70, "spd": 105, "spd_stat": 55},
    "Mega Greninja": {"ability": "Protean", "hp": 72, "atk": 125, "def": 77, "spa": 133, "spd": 81, "spd_stat": 142},
    "Mega Floette": {"ability": "Fairy Aura", "hp": 74, "atk": 85, "def": 87, "spa": 155, "spd": 148, "spd_stat": 102},
    "Mega Meowstic Male": {"ability": "Trace", "hp": 74, "atk": 48, "def": 76, "spa": 143, "spd": 101, "spd_stat": 124},
    "Mega Meowstic Female": {"ability": "Trace", "hp": 74, "atk": 48, "def": 76, "spa": 83, "spd": 81, "spd_stat": 104},
    "Mega Malamar": {"ability": "Contrary", "hp": 86, "atk": 102, "def": 88, "spa": 98, "spd": 120, "spd_stat": 88},
    "Mega Barbaracle": {"ability": "Tough Claws", "hp": 72, "atk": 140, "def": 130, "spa": 64, "spd": 106, "spd_stat": 88},
    "Mega Dragalge": {"ability": "Regenerator", "hp": 65, "atk": 85, "def": 105, "spa": 132, "spd": 163, "spd_stat": 44},
    "Mega Hawlucha": {"ability": "No Guard", "hp": 78, "atk": 137, "def": 100, "spa": 74, "spd": 93, "spd_stat": 118},
    "Mega Glimmora": {"ability": "Adaptability", "hp": 83, "atk": 90, "def": 105, "spa": 150, "spd": 96, "spd_stat": 101}
}

MEGA_STONE_MAP = {name: f"{name.replace('Mega ', '')}ite" for name in CUSTOM_MEGAS_DATA.keys()}

@strlit.cache_data(ttl=86400, show_spinner=False)
def fetch_champions_learnsets():
    url = "https://raw.githubusercontent.com/smogon/pokemon-showdown/master/data/mods/champions/learnsets.ts"
    try:
        res = requests.get(url, timeout=20)
        if res.status_code != 200:
            return {}

        text = res.text
        lines = text.splitlines()
        parsed = {}
        current_species = None
        current_block_lines = []
        in_species_block = False
        brace_depth = 0

        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith("//"):
                continue

            if not in_species_block:
                match = re.match(r"^\t([a-z0-9]+(?:-[a-z0-9]+)*)\s*:\s*\{$", line)
                if match:
                    current_species = match.group(1)
                    current_block_lines = [line]
                    in_species_block = True
                    brace_depth = line.count("{") - line.count("}")
                continue

            current_block_lines.append(line)
            brace_depth += line.count("{") - line.count("}")

            if brace_depth <= 0:
                in_species_block = False
                moves = []
                in_learnset = False
                learnset_depth = 0
                for block_line in current_block_lines:
                    if not in_learnset:
                        if re.match(r"^\s*learnset\s*:\s*\{", block_line):
                            in_learnset = True
                            learnset_depth = block_line.count("{") - block_line.count("}")
                        continue

                    move_match = re.match(r"^\s*([a-z0-9]+(?:-[a-z0-9]+)*)\s*:\s*\[", block_line)
                    if move_match:
                        moves.append(move_match.group(1))

                    learnset_depth += block_line.count("{") - block_line.count("}")
                    if learnset_depth <= 0:
                        in_learnset = False

                if moves:
                    parsed[current_species] = sorted(set(moves))

                current_species = None
                current_block_lines = []
                brace_depth = 0

        return parsed
    except Exception:
        return {}

@strlit.cache_data(ttl=86400, show_spinner=False)
def fetch_champions_pokedex_entries():
    url = "https://raw.githubusercontent.com/smogon/pokemon-showdown/master/data/mods/champions/pokedex.ts"
    try:
        res = requests.get(url, timeout=20)
        if res.status_code != 200:
            return []

        entries = []
        for match in re.finditer(r"(?m)^\s*([a-z0-9]+(?:-[a-z0-9]+)*)\s*:\s*\{\s*$", res.text):
            species_id = match.group(1)
            if species_id not in {"export"}:
                entries.append(species_id)
        return sorted(set(entries))
    except Exception:
        return []

def display_name_for_species_key(species_key):
    """
    Convert a Champions/Showdown species ID into a stable,
    human-readable Pokémon name.

    This function deliberately handles multiple possible spellings
    of the same form so that:
        rotomwash
        rotom-wash
        Rotom Wash
    all become:
        Rotom Wash
    """

    if not species_key:
        return species_key

    raw = str(species_key).strip().lower()

    # ---------------------------------------------------------
    # NORMALISE THE INPUT FOR FORM LOOKUP
    # ---------------------------------------------------------

    # Remove punctuation and separators ONLY for the purpose
    # of matching against our aliases.
    lookup = re.sub(r"[^a-z0-9]", "", raw)

    FORM_NAMES = {

        # =====================================================
        # BASCULEGION
        # =====================================================

        "basculegionm": "Basculegion",
        "basculegion-male": "Basculegion",

        "basculegionf": "Basculegion Female",
        "basculegionfemale": "Basculegion Female",

        # =====================================================
        # FLOETTE
        # =====================================================

        "floette": "Floette",
        "floetteeternal": "Floette Eternal",

        # =====================================================
        # MEOWSTIC
        # =====================================================

        "meowstic": "Meowstic Male",
        "meowsticm": "Meowstic Male",
        "meowsticmale": "Meowstic Male",
        "meowsticf": "Meowstic Female",
        "meowsticfemale": "Meowstic Female",

        # =====================================================
        # MR. RIME
        # =====================================================

        "mrrime": "Mr. Rime",

        # =====================================================
        # ROTOM
        # =====================================================

        "rotom": "Rotom",

        "rotomheat": "Rotom Heat",
        "rotomwash": "Rotom Wash",
        "rotomfrost": "Rotom Frost",
        "rotomfan": "Rotom Fan",
        "rotommow": "Rotom Mow",

        # =====================================================
        # TAUROS PALDEA
        # =====================================================

        "tauros": "Tauros",

        "tauros-paldea-combat-breed": "Tauros Paldea Combat Breed",
        "tauros-paldea-aqua-breed": "Tauros Paldea Aqua Breed",
        "tauros-paldea-blaze-breed": "Tauros Paldea Blaze Breed",

        # =====================================================
        # LYCANROC
        # =====================================================

        "lycanroc": "Lycanroc Midday",
        "lycanrocmidday": "Lycanroc Midday",
        "lycanrocday": "Lycanroc Midday",

        "lycanrocmidnight": "Lycanroc Midnight",
        "lycanrocnight": "Lycanroc Midnight",

        "lycanrocdusk": "Lycanroc Dusk",

        # =====================================================
        # HISUI
        # =====================================================

        "growlithehisui": "Growlithe Hisui",
        "arcaninehisui": "Arcanine Hisui",

        "voltorbhisui": "Voltorb Hisui",
        "electrodehisui": "Electrode Hisui",

        "qwilfishhisui": "Qwilfish Hisui",
        "sneaselhisui": "Sneasel Hisui",

        "samurotthisui": "Samurott Hisui",
        "samurotthisuian": "Samurott Hisui",

        "lilliganthisui": "Lilligant Hisui",

        "zoruahisui": "Zorua Hisui",
        "zoroarkhisui": "Zoroark Hisui",

        "braviaryhisui": "Braviary Hisui",

        "sliggoohisui": "Sliggoo Hisui",
        "goodrahisui": "Goodra Hisui",

        "avalugghisui": "Avalugg Hisui",

        "decidueyehisui": "Decidueye Hisui",

        "typhlosionhisui": "Typhlosion Hisui",

        # =====================================================
        # ALOLA
        # =====================================================

        "raichualola": "Raichu Alola",

        "rattataalola": "Rattata Alola",
        "raticatealola": "Raticate Alola",

        "sandshrewalola": "Sandshrew Alola",
        "sandslashalola": "Sandslash Alola",

        "vulpixalola": "Vulpix Alola",
        "ninetalesalola": "Ninetales Alola",

        "diglettalola": "Diglett Alola",
        "dugtrioalola": "Dugtrio Alola",

        "meowthalola": "Meowth Alola",
        "persianalola": "Persian Alola",

        "geodudealola": "Geodude Alola",
        "graveleralola": "Graveler Alola",
        "golemalola": "Golem Alola",

        "grimeralola": "Grimer Alola",
        "mukalola": "Muk Alola",

        # =====================================================
        # GALAR
        # =====================================================

        "slowbrogalar": "Slowbro Galar",
        "slowkinggalar": "Slowking Galar",

        "mrmimegalar": "Mr. Mime Galar",

        "stunfiskgalar": "Stunfisk Galar",

        "meowthgalar": "Meowth Galar",
        "ponytagalar": "Ponyta Galar",
        "rapidashgalar": "Rapidash Galar",

        "farfetchdgalar": "Farfetch'd Galar",
        "weezinggalar": "Weezing Galar",

        "corsolagalar": "Corsola Galar",
        "zigzagoongalar": "Zigzagoon Galar",
        "linoonegalar": "Linoone Galar",

        "darumakagalar": "Darumaka Galar",
        "darmanitangalar": "Darmanitan Galar",

        "yamaskgalar": "Yamask Galar",

        # =====================================================
        # OTHER SPECIAL NAMES
        # =====================================================

        "mrmime": "Mr. Mime",
        "mimejr": "Mime Jr.",
        "farfetchd": "Farfetch'd",
        "sirfetchd": "Sirfetch'd",
        "flabebe": "Flabébé",
        "type-null": "Type: Null",
        "typenull": "Type: Null",
        "hooh": "Ho-Oh",
    }

    # ---------------------------------------------------------
    # FIRST: FORM ALIAS LOOKUP
    # ---------------------------------------------------------

    if lookup in FORM_NAMES:
        return FORM_NAMES[lookup]

    # ---------------------------------------------------------
    # SECOND: EXISTING OVERRIDES
    # ---------------------------------------------------------

    if raw in SPECIES_DISPLAY_OVERRIDES:
        return SPECIES_DISPLAY_OVERRIDES[raw]

    # ---------------------------------------------------------
    # THIRD: GENERIC FALLBACK
    # ---------------------------------------------------------

    pretty = (
        raw
        .replace("_", "-")
        .replace("-", " ")
        .replace("’", "'")
    )

    return " ".join(
        word.title()
        for word in pretty.split()
    )

CHAMPIONS_LEARNSETS = fetch_champions_learnsets()
CHAMPIONS_ROSTER = fetch_champions_pokedex_entries()
VALID_CHAMPIONS = {
    display_name_for_species_key(species)
    for species in set(CHAMPIONS_ROSTER) | set(CHAMPIONS_LEARNSETS)
}
VALID_CHAMPIONS.update(CUSTOM_MEGAS_DATA)

def get_move_api_slug(move_name):
    if not move_name:
        return ""
    slug = str(move_name).strip().lower().split(" (")[0].replace("’", "").replace("'", "").replace(".", "")
    return re.sub(r'[^a-z0-9]+', '-', slug).strip("-")

@strlit.cache_data(ttl=86400, show_spinner=False)
def fetch_pokemon_roster():
    roster = list(CUSTOM_MEGAS_DATA.keys())
    for species_key in sorted(set(CHAMPIONS_ROSTER) | set(CHAMPIONS_LEARNSETS.keys())):
        roster.append(display_name_for_species_key(species_key))
    return ["-- Choose a Pokémon --"] + sorted(set(roster), key=lambda item: (not item.startswith("Mega "), item.lower()))

CHAMPIONS_ALL_FORMS = fetch_pokemon_roster()

BASE_HELD_ITEMS = [
    "Air Balloon", "Assault Vest", "Babiri Berry", "Binding Band", "Black Belt", "Black Sludge",
    "Choice Band", "Choice Scarf", "Choice Specs", "Clear Amulet", "Covert Cloak", "Damp Rock",
    "Eviolite", "Expert Belt", "Focus Sash", "Heat Rock", "Heavy-Duty Boots", "Iapapa Berry",
    "Ice Rock", "Kee Berry", "Kings Rock", "Leftovers", "Life Orb", "Light Clay", "Loaded Dice",
    "Lum Berry", "Maranga Berry", "Mental Herb", "Miracle Seed", "Mystic Water", "Never-Melt Ice",
    "Normal Gem", "Occa Berry", "Passho Berry", "Payapa Berry", "Protective Pads", "Punching Glove",
    "Rawst Berry", "Red Card", "Rindo Berry", "Rocky Helmet", "Safety Goggles", "Salac Berry",
    "Scope Lens", "Shuca Berry", "Silk Scarf", "Sitrus Berry", "Smooth Rock", "Soft Sand",
    "Spell Tag", "Throat Spray", "Toxic Orb", "Twisted Spoon", "Weakness Policy", "White Herb", "Yache Berry"
]
CHAMPIONS_HELD_ITEMS = sorted(list(set(BASE_HELD_ITEMS + list(MEGA_STONE_MAP.values()))))

# -----------------------------------------------------------------------------
# 3. HELPER FUNCTIONS & API FETCHING
# -----------------------------------------------------------------------------
def get_hardcoded_move_type(move_name):
    move_lower = str(move_name).strip().lower()
    types_map = {
        "dragon dance": "Dragon", "dragon claw": "Dragon", "draco meteor": "Dragon", "outrage": "Dragon",
        "flare blitz": "Fire", "flamethrower": "Fire", "fire blast": "Fire", "overheat": "Fire", "heat wave": "Fire",
        "roost": "Flying", "brave bird": "Flying", "air slash": "Flying", "hurricane": "Flying", "acrobatics": "Flying",
        "earthquake": "Ground", "earth power": "Ground", "high horsepower": "Ground", "spikes": "Ground",
        "stealth rock": "Rock", "stone edge": "Rock", "rock slide": "Rock", "rock blast": "Rock",
        "close combat": "Fighting", "drain punch": "Fighting", "aura sphere": "Fighting", "focus blast": "Fighting",
        "ice punch": "Ice", "ice beam": "Ice", "blizzard": "Ice", "icicle spear": "Ice", "freeze-dry": "Ice",
        "thunder punch": "Electric", "thunderbolt": "Electric", "thunder": "Electric", "volt switch": "Electric",
        "swords dance": "Normal", "protect": "Normal", "substitute": "Normal", "extreme speed": "Normal", "rapid spin": "Normal",
        "toxic": "Poison", "sludge wave": "Poison", "sludge bomb": "Poison", "gunk shot": "Poison", "mortal spin": "Poison",
        "shadow ball": "Ghost", "shadow claw": "Ghost", "poltergeist": "Ghost", "destiny bond": "Ghost", "hex": "Ghost",
        "psychic": "Psychic", "psyshock": "Psychic", "zen headbutt": "Psychic", "calm mind": "Psychic", "trick room": "Psychic",
        "play rough": "Fairy", "moonblast": "Fairy", "dazzling gleam": "Fairy", "spirit break": "Fairy",
        "iron head": "Steel", "bullet punch": "Steel", "meteor mash": "Steel", "flash cannon": "Steel", "defog": "Flying",
        "hydro pump": "Water", "surf": "Water", "liquidation": "Water", "flip turn": "Water", "water shuriken": "Water",
        "giga drain": "Grass", "leaf blade": "Grass", "power whip": "Grass", "energy ball": "Grass", "wood hammer": "Grass",
        "dark pulse": "Dark", "crunch": "Dark", "sucker punch": "Dark", "knock off": "Dark", "parting shot": "Dark",
        "u-turn": "Bug", "quiver dance": "Bug", "bug buzz": "Bug", "first impression": "Bug"
    }
    return types_map.get(move_lower, "")

@strlit.cache_data(ttl=86400, show_spinner=False)
def fetch_move_type(move_name):
    hardcoded = get_hardcoded_move_type(move_name)
    if hardcoded:
        return hardcoded
    slug = get_move_api_slug(move_name)
    if not slug:
        return "Normal"
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(f"https://pokeapi.co/api/v2/move/{slug}", headers=headers, timeout=3)
        if res.status_code == 200:
            t_name = res.json().get("type", {}).get("name")
            if t_name:
                return t_name.title()
    except Exception:
        pass
    return "Normal"

def get_clean_api_name(mon_name):
    """
    Convert the app's human-readable Pokémon name into
    the exact PokeAPI species/form slug.
    """

    if not mon_name or mon_name == "-- Choose a Pokémon --":
        return "charizard-mega-x"

    name = str(mon_name).strip()

    FORM_API_NAMES = {

        # =====================================================
        # SPECIAL / GENDER FORMS
        # =====================================================

        "Mr. Mime": "mr-mime",
        "Mime Jr.": "mime-jr",
        "Ho-Oh": "ho-oh",

        "Nidoran♀": "nidoran-f",
        "Nidoran♂": "nidoran-m",

        "Farfetch'd": "farfetchd",
        "Sirfetch'd": "sirfetchd",

        "Flabébé": "flabebe",
        "Type: Null": "type-null",

        # =====================================================
        # TAUROS
        # =====================================================

        "Tauros Paldea Combat": "tauros-paldea-combat-breed",
        "Tauros Paldea Blaze": "tauros-paldea-blaze-breed",
        "Tauros Paldea Aqua": "tauros-paldea-aqua-breed",

        # =====================================================
        # ROTOM
        # =====================================================

        "Rotom": "rotom",

        "Rotom Heat": "rotom-heat",
        "Rotom Wash": "rotom-wash",
        "Rotom Frost": "rotom-frost",
        "Rotom Fan": "rotom-fan",
        "Rotom Mow": "rotom-mow",

        # =====================================================
        # MR. RIME/SLOWBRO/SLOWKING GALAR
        # =====================================================
        "Slowbro Galar": "slowbro-galar",
        "Slowking Galar": "slowking-galar",

        "Mr. Rime": "mr-rime",

        # =====================================================
        # BASCULEGION
        # =====================================================

        "Basculegion": "basculegion-male",
        "Basculegion Female": "basculegion-female",

        # =====================================================
        # FLOETTE
        # =====================================================

        "Floette Eternal": "floette-eternal",

        # =====================================================
        # INDEEDEE
        # =====================================================

        "Indeedee Male": "indeedee-male",
        "Indeedee Female": "indeedee-female",

        # =====================================================
        # MEOWSTIC
        # =====================================================

        "Meowstic Male": "meowstic-male",
        "Meowstic Female": "meowstic-female",

        # =====================================================
        # OINKOLOGNE
        # =====================================================

        "Oinkologne Male": "oinkologne-male",
        "Oinkologne Female": "oinkologne-female",

        # =====================================================
        # LYCANROC
        # =====================================================

        "Lycanroc Midday": "lycanroc-midday",
        "Lycanroc Midnight": "lycanroc-midnight",
        "Lycanroc Dusk": "lycanroc-dusk",

        # =====================================================
        # HISUI
        # =====================================================

        "Growlithe Hisui": "growlithe-hisui",
        "Arcanine Hisui": "arcanine-hisui",
        "Voltorb Hisui": "voltorb-hisui",
        "Electrode Hisui": "electrode-hisui",
        "Qwilfish Hisui": "qwilfish-hisui",
        "Sneasel Hisui": "sneasel-hisui",
        "Samurott Hisui": "samurott-hisui",
        "Lilligant Hisui": "lilligant-hisui",
        "Zorua Hisui": "zorua-hisui",
        "Zoroark Hisui": "zoroark-hisui",
        "Braviary Hisui": "braviary-hisui",
        "Sliggoo Hisui": "sliggoo-hisui",
        "Goodra Hisui": "goodra-hisui",
        "Avalugg Hisui": "avalugg-hisui",
        "Decidueye Hisui": "decidueye-hisui",
        "Typhlosion Hisui": "typhlosion-hisui",

        # =====================================================
        # ALOLA
        # =====================================================

        "Growlithe Alola": "growlithe-alola",
        "Arcanine Alola": "arcanine-alola",
        "Geodude Alola": "geodude-alola",
        "Graveler Alola": "graveler-alola",
        "Golem Alola": "golem-alola",
        "Vulpix Alola": "vulpix-alola",
        "Ninetales Alola": "ninetales-alola",
        "Sandshrew Alola": "sandshrew-alola",
        "Sandslash Alola": "sandslash-alola",
        "Meowth Alola": "meowth-alola",
        "Persian Alola": "persian-alola",
        "Diglett Alola": "diglett-alola",
        "Dugtrio Alola": "dugtrio-alola",
        "Grimer Alola": "grimer-alola",
        "Muk Alola": "muk-alola",
        "Raichu Alola": "raichu-alola",

        # =====================================================
        # GALAR
        # =====================================================

        "Meowth Galar": "meowth-galar",
        "Ponyta Galar": "ponyta-galar",
        "Rapidash Galar": "rapidash-galar",
        "Farfetch'd Galar": "farfetchd-galar",
        "Weezing Galar": "weezing-galar",
        "Mr. Mime Galar": "mr-mime-galar",
        "Corsola Galar": "corsola-galar",
        "Zigzagoon Galar": "zigzagoon-galar",
        "Linoone Galar": "linoone-galar",
        "Darumaka Galar": "darumaka-galar",
        "Darmanitan Galar": "darmanitan-galar",
        "Yamask Galar": "yamask-galar",
        "Stunfisk Galar": "stunfisk-galar",
    }

    if name in FORM_API_NAMES:
        return FORM_API_NAMES[name]

    # =====================================================
    # MEGA POKÉMON
    # =====================================================

    lower_name = name.lower()

    if lower_name.startswith("mega "):

        base = name[5:].strip()

        if base.lower().endswith(" x"):
            base = base[:-2].strip()
            return f"{base.lower().replace(' ', '-')}-mega-x"

        if base.lower().endswith(" y"):
            base = base[:-2].strip()
            return f"{base.lower().replace(' ', '-')}-mega-y"

        return f"{base.lower().replace(' ', '-')}-mega"

    # =====================================================
    # STANDARD FALLBACK
    # =====================================================

    clean = (
        lower_name
        .replace("’", "")
        .replace("'", "")
        .replace(".", "")
    )

    return (
        clean
        .replace(" (", "-")
        .replace(")", "")
        .replace(" ", "-")
    )

def get_champions_species_key(mon_name):
    """
    Convert a displayed Pokémon name into the exact
    Champions/Showdown species key.

    IMPORTANT:
    Forms are deliberately preserved.
    """

    if not mon_name:
        return ""

    name = str(mon_name).strip()

    SPECIES_KEYS = {

        # =====================================================
        # TAUROS
        # =====================================================

        "Tauros Paldea Combat Breed": "tauros-paldea-combat-breed",
        "Tauros Paldea Blaze Breed": "tauros-paldea-blaze-breed",
        "Tauros Paldea Aqua Breed": "tauros-paldea-aqua-breed",

        # =====================================================
        # BASCULEGION
        # =====================================================

        "Basculegion": "basculegion-male",
        "Basculegion Female": "basculegion-female",

        # =====================================================
        # FLOETTE
        # =====================================================

        "Floette Eternal": "floetteeternal",

        # =====================================================
        # INDEEDEE
        # =====================================================

        "Indeedee Male": "indeedeem",
        "Indeedee Female": "indeedeef",

        # =====================================================
        # MEOWSTIC
        # =====================================================

        "Meowstic Male": "meowsticm",
        "Meowstic Female": "meowsticf",

        # =====================================================
        # OINKOLOGNE
        # =====================================================

        "Oinkologne Male": "oinkolognem",
        "Oinkologne Female": "oinkolognef",

        # =====================================================
        # LYCANROC
        # =====================================================

        "Lycanroc Midday": "lycanrocmidday",
        "Lycanroc Midnight": "lycanrocmidnight",
        "Lycanroc Dusk": "lycanrocdusk",

        # =====================================================
        # HISUI
        # =====================================================

        "Growlithe Hisui": "growlithehisui",
        "Arcanine Hisui": "arcaninehisui",
        "Voltorb Hisui": "voltorbhisui",
        "Electrode Hisui": "electrodehisui",
        "Qwilfish Hisui": "qwilfishhisui",
        "Sneasel Hisui": "sneaselhisui",
        "Samurott Hisui": "samurotthisui",
        "Lilligant Hisui": "lilliganthisui",
        "Zorua Hisui": "zoruahisui",
        "Zoroark Hisui": "zoroarkhisui",
        "Braviary Hisui": "braviaryhisui",
        "Sliggoo Hisui": "sliggoohisui",
        "Goodra Hisui": "goodrahisui",
        "Avalugg Hisui": "avalugghisui",
        "Decidueye Hisui": "decidueyehisui",
        "Typhlosion Hisui": "typhlosionhisui",
    }

    if name in SPECIES_KEYS:
        return SPECIES_KEYS[name]

    # =====================================================
    # NORMAL SPECIES
    # =====================================================

    clean = (
        name
        .lower()
        .replace("’", "")
        .replace("'", "")
        .replace(".", "")
        .replace("♀", "f")
        .replace("♂", "m")
    )

    # Preserve the form separator rather than deleting it.
    clean = clean.replace(" ", "-")

    # Remove Mega prefix only for Mega lookup compatibility.
    if clean.startswith("mega-"):
        clean = clean[5:]

    return clean

def get_base_api_name(mon_name):
    base_name = re.sub(r"^Mega\s+", "", mon_name).strip()
    base_name = re.sub(r"\s*\([^)]*\)$", "", base_name)
    base_name = re.sub(r"\s+[XY]$", "", base_name, flags=re.IGNORECASE)
    return get_clean_api_name(base_name)

def get_champion_moves_for(mon_name):
    """
    Return the Champions learnset for the exact Pokémon/form.
    """

    if not CHAMPIONS_LEARNSETS:
        return []

    species_key = get_champions_species_key(mon_name)

    # Exact form match first
    if species_key in CHAMPIONS_LEARNSETS:
        return [
            display_name_for_move(move_id)
            for move_id in CHAMPIONS_LEARNSETS[species_key]
        ]

    # Mega Pokémon use their base species learnset
    if mon_name.startswith("Mega "):

        base_name = mon_name.replace(
            "Mega ",
            "",
            1
        ).strip()

        base_key = get_champions_species_key(
            base_name
        )

        if base_key in CHAMPIONS_LEARNSETS:
            return [
                display_name_for_move(move_id)
                for move_id in CHAMPIONS_LEARNSETS[base_key]
            ]

    return []

@strlit.cache_data(ttl=86400, show_spinner=False)
def fetch_pokemon_details(mon_name):
    clean_api_name = get_clean_api_name(mon_name)
    sprite_url = f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/{clean_api_name}.png"
    box_sprite_url = f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/{clean_api_name}.png"
    
    custom_data = CUSTOM_MEGAS_DATA.get(mon_name, {})
    stats = {
        "hp": custom_data.get("hp", 80),
        "attack": custom_data.get("atk", 100),
        "defense": custom_data.get("def", 100),
        "special-attack": custom_data.get("spa", 100),
        "special-defense": custom_data.get("spd", 100),
        "speed": custom_data.get("spd_stat", 100),
    }
    custom_ability = custom_data.get("ability", "Standard")
    champion_moves = list(get_champion_moves_for(mon_name))
    
    types = ["Normal"]
    abilities = [custom_ability] if custom_ability else ["Standard"]
    moves = champion_moves if champion_moves else ["Tackle", "Protect", "Rest", "Substitute"]

    try:
        res = requests.get(f"https://pokeapi.co/api/v2/pokemon/{clean_api_name}", timeout=3)
        if res.status_code != 200 and mon_name.startswith("Mega "):
            res = requests.get(
                f"https://pokeapi.co/api/v2/pokemon/{get_base_api_name(mon_name)}",
                timeout=3,
            )
        if res.status_code == 200:
            data = res.json()
            sprite_url = data.get("sprites", {}).get("other", {}).get("official-artwork", {}).get("front_default") or sprite_url
            box_sprite_url = data.get("sprites", {}).get("front_default") or box_sprite_url
            types = [t["type"]["name"].title() for t in data.get("types", [])]
            if not custom_data:
                api_stats = {
                    entry["stat"]["name"]: entry["base_stat"]
                    for entry in data.get("stats", [])
                }
                if api_stats:
                    stats = api_stats
            api_abilities = [a["ability"]["name"].replace("-", " ").title() for a in data.get("abilities", [])]
            if custom_ability and custom_ability != "Standard":
                abilities = [custom_ability] + [ab for ab in api_abilities if ab != custom_ability]
            elif api_abilities:
                abilities = api_abilities
            if not champion_moves:
                fetched_moves = [m["move"]["name"].replace("-", " ").title() for m in data.get("moves", [])]
                if fetched_moves:
                    moves = fetched_moves
    except Exception:
        pass

    return {
        "sprite": sprite_url,
        "box_sprite": box_sprite_url,
        "types": types,
        "stats": stats,
        "abilities": abilities,
        "moves": sorted(list(set(moves)))
    }

def get_mini_sprite_url(mon_name):
    return fetch_pokemon_details(mon_name)["box_sprite"]

TYPE_ORDER = list(TYPE_COLORS)
TYPE_DEFENSES = {
    "Normal": {"weak": ["Fighting"], "immune": ["Ghost"]},
    "Fire": {"weak": ["Water", "Ground", "Rock"], "resist": ["Fire", "Grass", "Ice", "Bug", "Steel", "Fairy"]},
    "Water": {"weak": ["Electric", "Grass"], "resist": ["Fire", "Water", "Ice", "Steel"]},
    "Electric": {"weak": ["Ground"], "resist": ["Electric", "Flying", "Steel"]},
    "Grass": {"weak": ["Fire", "Ice", "Poison", "Flying", "Bug"], "resist": ["Water", "Electric", "Grass", "Ground"]},
    "Ice": {"weak": ["Fire", "Fighting", "Rock", "Steel"], "resist": ["Ice"]},
    "Fighting": {"weak": ["Flying", "Psychic", "Fairy"], "resist": ["Bug", "Rock", "Dark"]},
    "Poison": {"weak": ["Ground", "Psychic"], "resist": ["Grass", "Fighting", "Poison", "Bug", "Fairy"]},
    "Ground": {"weak": ["Water", "Grass", "Ice"], "resist": ["Poison", "Rock"], "immune": ["Electric"]},
    "Flying": {"weak": ["Electric", "Ice", "Rock"], "resist": ["Grass", "Fighting", "Bug"], "immune": ["Ground"]},
    "Psychic": {"weak": ["Bug", "Ghost", "Dark"], "resist": ["Fighting", "Psychic"]},
    "Bug": {"weak": ["Fire", "Flying", "Rock"], "resist": ["Grass", "Fighting", "Ground"]},
    "Rock": {"weak": ["Water", "Grass", "Fighting", "Ground", "Steel"], "resist": ["Normal", "Fire", "Poison", "Flying"]},
    "Ghost": {"weak": ["Ghost", "Dark"], "resist": ["Poison", "Bug"], "immune": ["Normal", "Fighting"]},
    "Dragon": {"weak": ["Ice", "Dragon", "Fairy"], "resist": ["Fire", "Water", "Grass", "Electric"]},
    "Dark": {"weak": ["Fighting", "Bug", "Fairy"], "resist": ["Ghost", "Dark"], "immune": ["Psychic"]},
    "Steel": {"weak": ["Fire", "Fighting", "Ground"], "resist": ["Normal", "Grass", "Ice", "Flying", "Psychic", "Bug", "Rock", "Dragon", "Steel", "Fairy"], "immune": ["Poison"]},
    "Fairy": {"weak": ["Poison", "Steel"], "resist": ["Fighting", "Bug", "Dark"], "immune": ["Dragon"]},
}

def get_type_defense_summary(defending_types):
    multipliers = {type_name: 1 for type_name in TYPE_ORDER}
    for defending_type in defending_types:
        matchup = TYPE_DEFENSES.get(defending_type, {})
        for type_name in matchup.get("weak", []):
            multipliers[type_name] *= 2
        for type_name in matchup.get("resist", []):
            multipliers[type_name] *= 0.5
        for type_name in matchup.get("immune", []):
            multipliers[type_name] = 0
    return {
        "weak": [type_name for type_name in TYPE_ORDER if multipliers[type_name] > 1],
        "resist": [type_name for type_name in TYPE_ORDER if 0 < multipliers[type_name] < 1],
        "immune": [type_name for type_name in TYPE_ORDER if multipliers[type_name] == 0],
        "multipliers": multipliers,
    }

def get_offensive_type_summary(attacking_types):
    """
    Calculates the best offensive STAB multiplier against
    every defending type.

    Returns the multiplier alongside each category so the
    UI can display x2, x1/2, x1/4 and x0.
    """

    strong_against = []
    resisted_by = []

    for defending_type in TYPE_ORDER:

        matchup = TYPE_DEFENSES.get(
            defending_type,
            {}
        )

        multipliers = []

        for attacking_type in attacking_types:

            if attacking_type in matchup.get(
                "immune",
                []
            ):
                multipliers.append(0.0)

            elif attacking_type in matchup.get(
                "resist",
                []
            ):
                multipliers.append(0.5)

            elif attacking_type in matchup.get(
                "weak",
                []
            ):
                multipliers.append(2.0)

            else:
                multipliers.append(1.0)

        best_multiplier = max(
            multipliers,
            default=1.0
        )

        if best_multiplier > 1:
            strong_against.append(
                (defending_type, best_multiplier)
            )

        elif best_multiplier < 1:
            resisted_by.append(
                (defending_type, best_multiplier)
            )

    return {
        "strong_against": strong_against,
        "resisted_by": resisted_by
    }

def format_type_multiplier(multiplier):
    if multiplier == 0:
        return "x0"
    if multiplier == 0.25:
        return "x1/4"
    if multiplier == 0.5:
        return "x1/2"
    return f"x{int(multiplier)}"

def render_type_chips(type_names, multipliers=None):
    if not type_names:
        return '<div class="type-chart-empty">None</div>'
    return "".join(
        f'<span class="type-chip" style="background-color: {TYPE_COLORS[type_name]};">'
        f'<span>{type_name}</span>'
        f'{f"<span class=\"type-multiplier\">{format_type_multiplier(multipliers[type_name])}</span>" if multipliers else ""}'
        f'<img src="{TYPE_SVG_URLS[type_name]}" alt="" /></span>'
        for type_name in type_names
    )

@strlit.cache_data(ttl=86400, show_spinner=False)
def get_type_relationships(type_name):
    try:
        url = f"https://pokeapi.co/api/v2/type/{type_name.lower()}"
        response = requests.get(url, timeout=5)

        if response.status_code == 200:
            return response.json().get("damage_relations", {})

    except Exception:
        pass
    return {}

# -----------------------------------------------------------------------------
# 3.5 SMOGON COMPETITIVE USAGE DATA SOURCE ENGINE
# -----------------------------------------------------------------------------
@strlit.cache_data(ttl=86400, show_spinner=False)
def fetch_smogon_usage_stats() -> Dict[str, dict]:
    """
    Fetches real competitive usage statistics directly from Smogon's official
    public Chaos JSON repository (Gen 9 OU usage benchmark).
    Provides accurate move usage percentages, meta tiering weights, item/ability
    spreads, and teammate synergy scores.
    """
    url = "https://smogon.com/stats/2024-05/chaos/gen9ou-1825.json"
    usage_map = {}
    try:
        res = requests.get(url, timeout=15)
        if res.status_code != 200:
            return {}
        data = res.json()
        total_battles = max(1, data.get("info", {}).get("number of battles", 10000))
        mon_data = data.get("data", {})

        for raw_name, details in mon_data.items():
            clean_key = raw_name.strip().lower()
            usage_count = details.get("usage", 0)
            meta_usage_tier = min(1.0, (usage_count / total_battles) * 2.0)

            raw_moves = details.get("Moves", {})
            move_sum = sum(raw_moves.values()) or 1
            common_moves_rates = {
                display_name_for_move(m_key): round(cnt / move_sum, 3)
                for m_key, cnt in raw_moves.items()
                if (cnt / move_sum) > 0.02
            }

            raw_abilities = details.get("Abilities", {})
            ab_sum = sum(raw_abilities.values()) or 1
            common_abilities_rates = {
                ab_name: round(cnt / ab_sum, 3)
                for ab_name, cnt in raw_abilities.items()
            }

            raw_items = details.get("Items", {})
            item_sum = sum(raw_items.values()) or 1
            common_items_rates = {
                item_name: round(cnt / item_sum, 3)
                for item_name, cnt in raw_items.items()
            }

            raw_teammates = details.get("Teammates", {})
            top_partners_rates = {
                tm_name.title(): min(1.0, val / usage_count)
                for tm_name, val in raw_teammates.items()
                if usage_count > 0 and (val / usage_count) > 0.05
            }

            usage_map[clean_key] = {
                "meta_usage_tier": meta_usage_tier,
                "common_moves": common_moves_rates,
                "common_abilities": common_abilities_rates,
                "common_items": common_items_rates,
                "top_partners": top_partners_rates
            }
        return usage_map
    except Exception:
        return {}

SMOGON_USAGE_DB = fetch_smogon_usage_stats()

def get_smogon_stats_for(mon_name: str) -> dict:
    clean = mon_name.strip().lower()
    if clean in SMOGON_USAGE_DB:
        return SMOGON_USAGE_DB[clean]
    base = re.sub(r"^mega\s+", "", clean).strip()
    if base in SMOGON_USAGE_DB:
        return SMOGON_USAGE_DB[base]
    return {
        "meta_usage_tier": 0.15,
        "common_moves": {},
        "common_abilities": {},
        "common_items": {},
        "top_partners": {}
    }
@strlit.cache_data(
    ttl=3600,
    show_spinner=False
)
def get_cached_meta_candidate(name):

    try:

        c_data = fetch_pokemon_details(
            name
        )

        if not c_data.get(
            "types"
        ):
            return None

        tournament = (
            calculate_tournament_metrics(
                name
            )
        )

        if tournament["usage"] > 0:

            tournament_viability = (
                tournament[
                    "tournament_score"
                ]
                * 100
            )

        else:

            smogon = (
                get_smogon_stats_for(
                    name
                )
            )

            tournament_viability = (
                smogon.get(
                    "meta_usage_tier",
                    0.15
                )
                * 60
            )

        return {
            "types":
                c_data.get(
                    "types",
                    []
                ),

            "stats":
                c_data.get(
                    "stats",
                    {}
                ),

            "abilities":
                c_data.get(
                    "abilities",
                    []
                ),

            "moves":
                c_data.get(
                    "moves",
                    []
                ),

            "viability_index":
                int(
                    max(
                        0,
                        min(
                            100,
                            tournament_viability
                        )
                    )
                )
        }

    except Exception:

        return None   

@strlit.cache_data(
    ttl=3600,
    show_spinner=False
)
def compute_meta_analytics(mon_name):

    if (
        not mon_name
        or
        mon_name == "-- Choose a Pokémon --"
    ):
        return {
            "tier": "Unknown",
            "viability": "0 / 100",
            "speed_tier": "Unknown",
            "momentum_rating": "None",
            "hazard_utility": "None",
            "offensive_profile": "Balanced",
            "role": "Balanced Pick",
            "teammates": [],
            "counters": []
        }

    # =====================================================
    # 1. LOAD TARGET DATA
    # =====================================================

    mon_data = fetch_pokemon_details(
        mon_name
    )

    types = mon_data.get(
        "types",
        ["Normal"]
    )

    stats = mon_data.get(
        "stats",
        {}
    )

    moves = mon_data.get(
        "moves",
        []
    )

    abilities = mon_data.get(
        "abilities",
        []
    )

    atk = stats.get(
        "attack",
        100
    )

    spa = stats.get(
        "special-attack",
        100
    )

    spe = stats.get(
        "speed",
        100
    )

    hp = stats.get(
        "hp",
        80
    )

    defense = stats.get(
        "defense",
        80
    )

    sp_def = stats.get(
        "special-defense",
        80
    )

    bst = sum(
        stats.values()
    ) if stats else 500

    # =====================================================
    # 2. TOURNAMENT METRICS
    # =====================================================

    tournament = calculate_tournament_metrics(
        mon_name
    )

    tournament_score = (
        tournament["tournament_score"]
        * 100
    )

    usage_score = (
        tournament["usage"]
        * 100
    )

    win_score = (
        tournament["win_rate"]
        * 100
    )

    top_cut_score = (
        tournament["top_cut_rate"]
        * 100
    )

    # =====================================================
    # 3. FALLBACK COMPETITIVE SIGNAL
    # =====================================================

    smogon = get_smogon_stats_for(
        mon_name
    )

    smogon_signal = (
        smogon.get(
            "meta_usage_tier",
            0.15
        )
        * 100
    )

    # Smogon is deliberately capped.
    #
    # Champions tournament data should dominate
    # whenever tournament data exists.

    if tournament["usage"] > 0:

        external_signal = min(
            60.0,
            smogon_signal
        )

    else:

        external_signal = smogon_signal

    # =====================================================
    # 4. BASE STRATEGIC SCORE
    # =====================================================

    offensive_stat = max(
        atk,
        spa
    )

    raw_strength = min(
        100.0,
        (
            (bst / 720.0) * 50.0
            +
            (offensive_stat / 160.0) * 30.0
        )
    )
    # =====================================================
    # 5. TYPE MATCHUP PROFILE
    # =====================================================

    type_multipliers = {}

    for attacking_type in TYPE_CHART_DATA:

        multiplier = 1.0

        for defending_type in types:

            relations = get_type_relationships(
                attacking_type
            )

            if not relations:
                continue

            double_damage = {
                x["name"].title()
                for x in relations.get(
                    "double_damage_to",
                    []
                )
            }

            half_damage = {
                x["name"].title()
                for x in relations.get(
                    "half_damage_to",
                    []
                )
            }

            no_damage = {
                x["name"].title()
                for x in relations.get(
                    "no_damage_to",
                    []
                )
            }

            if attacking_type.title() in double_damage:
                multiplier *= 2.0

            elif attacking_type.title() in half_damage:
                multiplier *= 0.5

            elif attacking_type.title() in no_damage:
                multiplier *= 0.0

        type_multipliers[
            attacking_type.title()
        ] = multiplier

    weaknesses = {
        attacking_type
        for attacking_type, multiplier
        in type_multipliers.items()
        if multiplier >= 2.0
    }

    # =====================================================
    # 6. ARCHETYPE SCORE
    # =====================================================

    payload = {
        "name": mon_name,
        "types": types,
        "abilities": abilities,
        "moves": moves,
        "default_score": raw_strength
    }

    archetypes = detect_archetypes(
        payload
    )

    archetype_score = min(
        100.0,
        sum(
            a.get(
                "boost",
                0
            )
            for a in archetypes
        )
    )

    # =====================================================
    # 6. FINAL VIABILITY
    # =====================================================

    if tournament["usage"] > 0:

        viability_value = (
            tournament_score * 0.40
            +
            usage_score * 0.20
            +
            top_cut_score * 0.15
            +
            win_score * 0.10
            +
            archetype_score * 0.10
            +
            raw_strength * 0.05
        )

    else:

        viability_value = (
            external_signal * 0.45
            +
            raw_strength * 0.35
            +
            archetype_score * 0.20
        )

    viability_value = int(
        max(
            0,
            min(
                100,
                viability_value
            )
        )
    )

    # =====================================================
    # 7. TIER LABEL
    # =====================================================

    if viability_value >= 90:

        tier = (
            "S+ / Tournament Defining"
        )

    elif viability_value >= 80:

        tier = (
            "S / Elite Meta"
        )

    elif viability_value >= 70:

        tier = (
            "A / High Viability"
        )

    elif viability_value >= 60:

        tier = (
            "B / Solid Meta Pick"
        )

    elif viability_value >= 45:

        tier = (
            "C / Niche Pick"
        )

    else:

        tier = (
            "D / Low Meta Presence"
        )

    # =====================================================
    # 8. SPEED PROFILE
    # =====================================================

    if spe >= 130:
        speed_tier = "Extremely Fast"

    elif spe >= 110:
        speed_tier = "Very Fast"

    elif spe >= 90:
        speed_tier = "Fast"

    elif spe >= 70:
        speed_tier = "Average"

    elif spe >= 50:
        speed_tier = "Slow"

    else:
        speed_tier = "Very Slow"

    # =====================================================
    # 9. OFFENSIVE PROFILE
    # =====================================================

    if atk >= spa + 20:
        offensive_profile = (
            "Physical Attacker"
        )

    elif spa >= atk + 20:
        offensive_profile = (
            "Special Attacker"
        )

    else:
        offensive_profile = (
            "Mixed / Flexible"
        )

    # =====================================================
    # 10. MOMENTUM
    # =====================================================

    pivot_moves = {
        "U-turn",
        "Volt Switch",
        "Flip Turn",
        "Parting Shot"
    }

    if any(
        move in pivot_moves
        for move in moves
    ):

        momentum_rating = (
            "High Momentum"
        )

    elif (
        "Tailwind" in moves
        or
        "Trick Room" in moves
    ):

        momentum_rating = (
            "Speed Control"
        )

    else:

        momentum_rating = (
            "Direct Pressure"
        )

    # =====================================================
    # 11. HAZARD / UTILITY
    # =====================================================

    utility_tags = []

    hazard_moves = {
        "Stealth Rock",
        "Spikes",
        "Toxic Spikes"
    }

    removal_moves = {
        "Rapid Spin",
        "Defog"
    }

    if any(
        move in hazard_moves
        for move in moves
    ):
        utility_tags.append(
            "Hazard Setter"
        )

    if any(
        move in removal_moves
        for move in moves
    ):
        utility_tags.append(
            "Hazard Removal"
        )

    if any(
        move in {
            "Recover",
            "Roost",
            "Synthesis",
            "Soft-Boiled"
        }
        for move in moves
    ):
        utility_tags.append(
            "Reliable Recovery"
        )

    hazard_utility = (
        ", ".join(utility_tags)
        if utility_tags
        else
        "Direct Offensive / Defensive Focus"
    )

    # =====================================================
    # 12. BUILD LEGAL CHAMPIONS POOL
    # =====================================================

    source_roster = (
        CHAMPIONS_ROSTER
        if CHAMPIONS_ROSTER
        else
        list(
            CHAMPIONS_LEARNSETS.keys()
        )
    )

    candidates = []

    for species_key in source_roster:

        candidate_name = (
            display_name_for_species_key(
                species_key
            )
        )

        if not candidate_name:
            continue

        if (
            candidate_name.lower()
            ==
            mon_name.lower()
        ):
            continue

        if (
            candidate_name.lower()
            .startswith("mega ")
        ):
            continue

        candidates.append(
            candidate_name
        )

    candidates = list(
        dict.fromkeys(
            candidates
        )
    )

    # =====================================================
    # 13. BUILD META POOL
    # =====================================================

    meta_pool = {}

    for candidate_name in candidates:

        cached = get_cached_meta_candidate(
            candidate_name
        )

        if not cached:
            continue

        meta_pool[candidate_name] = {
            "viability_index":
                cached.get(
                    "viability_index",
                    0
                ),
            "types":
                cached.get(
                    "types",
                    []
                ),
            "stats":
                cached.get(
                    "stats",
                    {}
                ),
            "abilities":
                cached.get(
                    "abilities",
                    []
                ),
            "moves":
                cached.get(
                    "moves",
                    []
                )
        }

    # =====================================================
    # 14. COUNTER ENGINE
    # =====================================================

    meta_checks = (
        get_meta_relevant_checks(
            pkmn_data=payload,
            meta_pool=meta_pool,
            min_viability_threshold=0,
            top_n=3
        )
    )

    counters = []

    for check in meta_checks:

        check_name = check[
            "name"
        ]

        check_types = (
            meta_pool
            .get(
                check_name,
                {}
            )
            .get(
                "types",
                []
            )
        )

        if check_types:

            counters.append(
                (
                    check_name,
                    check_types[0]
                )
            )

    # =====================================================
    # 15. TOURNAMENT PARTNERS
    # =====================================================

    tournament_partners = dict(
        get_tournament_partners(
            mon_name,
            top_n=10
        )
    )

    teammate_scores = []

    # =====================================================
    # 16. TEAMMATE SCORING
    # =====================================================

    for candidate_name in candidates:

        try:

            cached = (
                meta_pool.get(
                    candidate_name
                )
            )

            if not cached:
                continue

            candidate_types = (
                cached["types"]
            )

            candidate_stats = (
                cached["stats"]
            )

            if not candidate_types:
                continue

            candidate_data = (
                fetch_pokemon_details(
                    candidate_name
                )
            )

            score = 0.0

            # ---------------------------------------------
            # Tournament partnership
            # ---------------------------------------------

            candidate_key = (
                get_champions_species_key(
                    candidate_name
                )
            )

            partner_frequency = (
                tournament_partners.get(
                    candidate_key,
                    0
                )
            )

            score += min(
                40.0,
                partner_frequency * 8.0
            )

            # ---------------------------------------------
            # Archetype synergy
            # ---------------------------------------------

            target_archetypes = detect_archetypes(
                mon_data
            )

            candidate_archetypes = detect_archetypes(
                candidate_data
            )

            target_archetype_names = {
                a.get("name")
                for a in target_archetypes
            }

            candidate_archetype_names = {
                a.get("name")
                for a in candidate_archetypes
            }

            archetype_overlap = (
                target_archetype_names
                &
                candidate_archetype_names
            )

            score += (
                len(archetype_overlap) * 4.0
            )

            # ---------------------------------------------
            # Defensive synergy
            # ---------------------------------------------

            for candidate_type in candidate_types:

                relations = (
                    get_type_relationships(
                        candidate_type
                    )
                )

                resistances = {
                    r["name"].title()
                    for r in relations.get(
                        "half_damage_from",
                        []
                    )
                }

                immunities = {
                    r["name"].title()
                    for r in relations.get(
                        "no_damage_from",
                        []
                    )
                }

                for weakness in weaknesses:

                    if weakness in immunities:

                        score += 8.0

                    elif weakness in resistances:

                        score += 5.0

            # ---------------------------------------------
            # Offensive coverage
            # ---------------------------------------------

            for candidate_type in candidate_types:

                relations = (
                    get_type_relationships(
                        candidate_type
                    )
                )

                offensive_targets = {
                    r["name"].title()
                    for r in relations.get(
                        "double_damage_to",
                        []
                    )
                }

                for weakness in weaknesses:

                    if weakness in offensive_targets:

                        score += 3.0

            # ---------------------------------------------
            # Role diversity
            # ---------------------------------------------

            candidate_atk = (
                candidate_stats.get(
                    "attack",
                    100
                )
            )

            candidate_spa = (
                candidate_stats.get(
                    "special-attack",
                    100
                )
            )

            target_physical = (
                atk >= spa
            )

            candidate_physical = (
                candidate_atk >= candidate_spa
            )

            if (
                target_physical
                !=
                candidate_physical
            ):
                score += 2.0

            # ---------------------------------------------
            # Tournament viability
            # ---------------------------------------------

            candidate_viability = (
                cached.get(
                    "viability_index",
                    0
                )
            )

            score += (
                float(
                    candidate_viability
                )
                * 0.05
            )

            if score > 0:

                teammate_scores.append(
                    (
                        score,
                        candidate_name,
                        candidate_types[0]
                    )
                )

        except Exception:

            continue

    teammate_scores.sort(
        key=lambda item: item[0],
        reverse=True
    )

    teammates = [
        (
            name,
            pokemon_type
        )
        for score, name, pokemon_type
        in teammate_scores[:3]
    ]

    # =====================================================
    # 17. RETURN COMPLETE PROFILE
    # =====================================================

    return {
        "tier": tier,
        "viability": (
            f"{viability_value} / 100"
        ),
        "speed_tier": speed_tier,
        "momentum_rating": momentum_rating,
        "hazard_utility": hazard_utility,
        "offensive_profile":
            offensive_profile,
        "role":
            infer_slot_role({
                "name": mon_name,
                "moves": moves
            }),
        "teammates": teammates,
        "counters": counters
    }

def infer_slot_role(slot):

    name = slot.get(
        "name",
        ""
    )

    moves = set(
        slot.get(
            "moves",
            []
        )
    )

    details = fetch_pokemon_details(
        name
    )

    stats = details.get(
        "stats",
        {}
    )

    atk = stats.get(
        "attack",
        100
    )

    spa = stats.get(
        "special-attack",
        100
    )

    spe = stats.get(
        "speed",
        100
    )

    hp = stats.get(
        "hp",
        100
    )

    defense = stats.get(
        "defense",
        100
    )

    sp_def = stats.get(
        "special-defense",
        100
    )

    # Speed control
    if "Tailwind" in moves:
        return "Speed Control / Support"

    if "Trick Room" in moves:
        return "Trick Room / Support"

    # Setup sweepers
    if moves & {
        "Swords Dance",
        "Dragon Dance",
        "Nasty Plot",
        "Quiver Dance",
        "Calm Mind"
    }:
        return "Setup Sweeper"

    # Pivot
    if moves & {
        "U-turn",
        "Volt Switch",
        "Flip Turn",
        "Parting Shot"
    }:
        return "Pivot"

    # Strong attackers
    if max(atk, spa) >= 115:

        if spe >= 90:

            if atk >= spa:
                return "Physical Attacker"

            return "Special Attacker"

    # Defensive support
    if (
        hp >= 100
        or defense >= 100
        or sp_def >= 100
    ):

        if moves & {
            "Recover",
            "Roost",
            "Synthesis",
            "Protect",
            "Helping Hand",
            "Follow Me",
            "Rage Powder"
        }:
            return "Defensive / Support"

    return "Balanced / Utility"

def ensure_slot_structure(slot_idx, fallback_name="-- Choose a Pokémon --"):
    if "team_slots" not in strlit.session_state:
        strlit.session_state.team_slots = {}
    if slot_idx not in strlit.session_state.team_slots:
        strlit.session_state.team_slots[slot_idx] = {
            "name": fallback_name,
            "ability": "Standard",
            "item": "",
            "nature": "Hardy",
            "moves": ["Protect", "Substitute", "Toxic", "Rest"],
            "evs": {"HP": 0, "Atk": 0, "Def": 0, "SpA": 0, "SpD": 0, "Spe": 0}
        }
    return strlit.session_state.team_slots[slot_idx]

def normalize_moves(moves, available_moves):
    available_moves = list(dict.fromkeys(available_moves)) or ["Protect"]
    valid_moves = [move for move in moves if move in available_moves]
    for move in available_moves:
        if len(valid_moves) >= 4:
            break
        if move not in valid_moves:
            valid_moves.append(move)
    while len(valid_moves) < 4:
        valid_moves.append(available_moves[0])
    return valid_moves[:4]

def generate_synergistic_moveset(new_species, target_slot_idx):
    if new_species == "-- Choose a Pokémon --":
        return ["Protect", "Substitute", "Toxic", "Rest"]
    mon_data = fetch_pokemon_details(new_species)
    learnset = mon_data["moves"]
    mon_types = mon_data["types"]
    
    # Check if authoritative Smogon move usage statistics exist for this species
    smogon_stats = get_smogon_stats_for(new_species)
    smogon_moves = smogon_stats.get("common_moves", {})
    if smogon_moves:
        sorted_by_usage = sorted(
            [m for m in learnset if m in smogon_moves],
            key=lambda x: smogon_moves.get(x, 0.0),
            reverse=True
        )
        if len(sorted_by_usage) >= 4:
            return sorted_by_usage[:4]

    priority_STABs = []
    priority_Coverage = []
    for m in learnset:
        m_type = fetch_move_type(m)
        if m_type in mon_types and m not in priority_STABs:
            priority_STABs.append(m)
        else:
            priority_Coverage.append(m)
            
    final_set = (priority_STABs[:2] + priority_Coverage[:2])
    while len(final_set) < 4 and learnset:
        for m in learnset:
            if m not in final_set:
                final_set.append(m)
                break
    return list(dict.fromkeys(final_set))[:4]

def on_species_change(slot_idx):
    new_species = strlit.session_state.get(f"species_select_{slot_idx}", "-- Choose a Pokémon --")
    slot = ensure_slot_structure(slot_idx, new_species)
    if new_species == "-- Choose a Pokémon --":
        return
    ability = CUSTOM_MEGAS_DATA.get(new_species, {}).get("ability", "Standard")
    item = MEGA_STONE_MAP.get(new_species, "Focus Sash")
    mon_data = fetch_pokemon_details(new_species)
    atk = mon_data["stats"].get("attack", 80)
    spa = mon_data["stats"].get("special-attack", 80)
    nature = "Jolly (+Spe, -SpA)" if atk >= spa else "Timid (+Spe, -Atk)"
    evs = {"HP": 0, "Atk": 252, "Def": 4, "SpA": 0, "SpD": 0, "Spe": 252} if atk >= spa else {"HP": 0, "Atk": 0, "Def": 4, "SpA": 252, "SpD": 0, "Spe": 252}
    recommended_moves = generate_synergistic_moveset(new_species, slot_idx)

    slot.update({
        "name": new_species, "ability": ability, "item": item,
        "nature": nature, "moves": normalize_moves(recommended_moves, mon_data["moves"]), "evs": evs,
    })

# Helper to convert slot state into MonMetaProfile for TeamEvaluator using real Smogon stats
def slot_to_mon_meta_profile(slot) -> MonMetaProfile:
    name = slot.get("name", "Unknown")
    details = fetch_pokemon_details(name)
    types = details.get("types", ["Normal"])
    stats = details.get("stats", {})
    
    # 1. Run centralized archetype detection
    pkmn_payload = {
        "name": name,
        "abilities": [slot.get("ability", "Standard")],
        "moves": slot.get("moves", []),
        "weaknesses": []
    }
    detected = detect_archetypes(pkmn_payload)
    detected_names = {a["name"] for a in detected}

    base_stats = {
        "hp": stats.get("hp", 80),
        "atk": stats.get("attack", 100),
        "def": stats.get("defense", 100),
        "spa": stats.get("special-attack", 100),
        "spd": stats.get("special-defense", 100),
        "spe": stats.get("speed", 100)
    }
    
    smogon_stats = get_smogon_stats_for(name)
    smogon_move_rates = smogon_stats.get("common_moves", {})

    moves_dict = {}
    for move_name in slot.get("moves", []):
        m_type = get_hardcoded_move_type(move_name) or fetch_move_type(move_name)
        tags = set()
        m_lower = move_name.lower()
        
        # Inherit official archetype tags
        if "Tailwind Enabler" in detected_names and "tailwind" in m_lower:
            tags.add("tailwind")
        if "Trick Room Setter" in detected_names and "trick room" in m_lower:
            tags.add("trick_room")
        if "Priority Blocker" in detected_names:
            tags.add("anti_priority")
            
        # Move mechanics tags
        if any(w in m_lower for w in ["dance", "plot", "calm mind", "swords"]):
            tags.add("setup")
        if any(w in m_lower for w in ["sucker", "extreme speed", "aqua jet", "bullet punch", "mach punch"]):
            tags.add("priority")
        if any(w in m_lower for w in ["follow me", "rage powder"]):
            tags.add("redirection")

        move_usage_val = smogon_move_rates.get(move_name, 0.5)

        moves_dict[move_name] = MoveProfile(
            name=move_name,
            category="Status" if "protect" in m_lower or "substitute" in m_lower or "toxic" in m_lower else "Physical",
            type=m_type,
            base_power=80,
            accuracy=1.0,
            usage_rate=move_usage_val,
            tags=tags
        )
        
    ability = slot.get("ability", "Standard")
    item = slot.get("item", "")
    
    return MonMetaProfile(
        name=name,
        types=types,
        base_stats=base_stats,
        common_moves=moves_dict,
        common_abilities=smogon_stats.get("common_abilities", {ability: 1.0}),
        common_items=smogon_stats.get("common_items", {item: 1.0}) if item else {},
        meta_usage_tier=smogon_stats.get("meta_usage_tier", 0.15),
        top_partners=smogon_stats.get("top_partners", {})
    )

# Showdown export/import utilities
def export_slot_to_showdown(slot):
    if not slot or slot.get("name", "-- Choose a Pokémon --") == "-- Choose a Pokémon --":
        return ""
    lines = []
    item_str = f" @ {slot['item']}" if slot.get("item") else ""
    lines.append(f"{slot['name']}{item_str}")
    if slot.get("ability"):
        lines.append(f"Ability: {slot['ability']}")
    
    ev_parts = []
    for k in ["HP", "Atk", "Def", "SpA", "SpD", "Spe"]:
        val = slot.get("evs", {}).get(k, 0)
        if val > 0:
            ev_parts.append(f"{val} {k}")
    if ev_parts:
        lines.append(f"EVs: {' / '.join(ev_parts)}")
    
    if slot.get("nature"):
        nat_name = slot["nature"].split(" ")[0]
        lines.append(f"{nat_name} Nature")
        
    for m in slot.get("moves", []):
        if m:
            lines.append(f"- {m}")
    return "\n".join(lines)

def export_team_to_showdown(team_slots):
    exported = []
    for i in range(6):
        slot = team_slots.get(i)
        if slot and slot.get("name") != "-- Choose a Pokémon --":
            exported.append(export_slot_to_showdown(slot))
    return "\n\n".join(exported)

def parse_showdown_text(text):
    blocks = [b.strip() for b in text.strip().split("\n\n") if b.strip()]
    parsed_slots = []
    
    for block in blocks[:6]:
        lines = [l.strip() for l in block.split("\n") if l.strip()]
        if not lines:
            continue
        
        line1 = lines[0]
        item = ""
        if " @ " in line1:
            line1_parts = line1.split(" @ ")
            item = line1_parts[1].strip()
            name_part = line1_parts[0].strip()
        else:
            name_part = line1.strip()
            
        species = name_part
        if "(" in name_part and ")" in name_part:
            m = re.search(r'\(([^)]+)\)', name_part)
            if m:
                potential_species = m.group(1).strip()
                if potential_species not in ["M", "F"]:
                    species = potential_species
                else:
                    species = name_part.split("(")[0].strip()
        
        matched_species = "-- Choose a Pokémon --"
        for option in CHAMPIONS_ALL_FORMS:
            if option.lower() == species.lower():
                matched_species = option
                break
        if matched_species == "-- Choose a Pokémon --":
            for option in CHAMPIONS_ALL_FORMS:
                if species.lower() in option.lower():
                    matched_species = option
                    break

        ability = "Standard"
        nature = "Hardy"
        evs = {"HP": 0, "Atk": 0, "Def": 0, "SpA": 0, "SpD": 0, "Spe": 0}
        moves = []

        for line in lines[1:]:
            if line.startswith("Ability:"):
                ability = line.replace("Ability:", "").strip()
            elif line.startswith("EVs:"):
                ev_str = line.replace("EVs:", "").strip()
                for part in ev_str.split("/"):
                    p = part.strip().split()
                    if len(p) == 2 and p[0].isdigit():
                        stat_key = p[1].strip()
                        k_map = {"HP": "HP", "Atk": "Atk", "Def": "Def", "SpA": "SpA", "SpD": "SpD", "Spe": "Spe"}
                        if stat_key in k_map:
                            evs[k_map[stat_key]] = int(p[0])
            elif "Nature" in line:
                nat_word = line.replace("Nature", "").strip()
                for n_opt in NATURES:
                    if n_opt.startswith(nat_word):
                        nature = n_opt
                        break
            elif line.startswith("-"):
                m_name = line.replace("-", "").strip()
                if m_name:
                    moves.append(m_name)

        final_species = matched_species if matched_species != "-- Choose a Pokémon --" else species.title()
        parsed_slots.append({
            "name": final_species,
            "ability": ability,
            "item": item if item else MEGA_STONE_MAP.get(final_species, "Focus Sash"),
            "nature": nature,
            "moves": moves[:4] if moves else ["Protect", "Substitute", "Rest", "Toxic"],
            "evs": evs
        })
    return parsed_slots


def import_champions_tournament(event):
    """
    Import one Champions tournament into CHAMPIONS_META_DB.

    The event must contain:
        {
            "regulation": "...",
            "players": [
                {
                    "team": [...],
                    "placing": 1
                }
            ]
        }
    """

    regulation = event.get(
        "regulation",
        ""
    )

    if (
        regulation
        and CURRENT_REGULATION
        and regulation != CURRENT_REGULATION
    ):
        return

    for player in event.get(
        "players",
        []
    ):

        team = player.get(
            "team",
            []
        )

        placing = player.get(
            "placing"
        )

        canonical_team = [
            get_champions_species_key(
                pokemon
            )
            for pokemon in team
            if pokemon
        ]

        canonical_team = list(
            dict.fromkeys(
                canonical_team
            )
        )
        for pokemon in canonical_team:

            if pokemon not in CHAMPIONS_META_DB:

                CHAMPIONS_META_DB[pokemon] = {
                    "appearances": 0,
                    "wins": 0,
                    "losses": 0,
                    "top_cuts": 0,
                    "usage": 0.0,
                    "win_rate": 0.0,
                    "top_cut_rate": 0.0,
                    "partners": {},
                    "roles": {},
                    "moves": {},
                    "abilities": {},
                    "items": {}
                }

            record = CHAMPIONS_META_DB[pokemon]

            record["appearances"] += 1

            if (
                placing is not None
                and placing <= 8
            ):
                record["top_cuts"] += 1

            for partner in canonical_team:

                if partner == pokemon:
                    continue

                record["partners"][partner] = (
                    record["partners"].get(
                        partner,
                        0
                    ) + 1
                )

def calculate_tournament_metrics(
    pokemon_name
):
    """
    Converts raw Champions tournament data
    into normalized competitive metrics.
    """

    key = get_champions_species_key(
        pokemon_name
    )

    record = CHAMPIONS_META_DB.get(
        key
    )

    if not record:
        return {
            "usage": 0.0,
            "top_cut_rate": 0.0,
            "win_rate": 0.0,
            "tournament_score": 0.0,
            "partner_score": 0.0
        }

    appearances = max(
        1,
        record.get(
            "appearances",
            0
        )
    )

    wins = record.get(
        "wins",
        0
    )

    losses = record.get(
        "losses",
        0
    )

    top_cuts = record.get(
        "top_cuts",
        0
    )

    total_games = wins + losses

    if total_games > 0:
        win_rate = (
            wins / total_games
        )
    else:
        win_rate = 0.0

    top_cut_rate = (
        top_cuts / appearances
    )

    partner_values = list(
        record.get(
            "partners",
            {}
        ).values()
    )

    if partner_values:

        partner_score = min(
            1.0,
            sum(partner_values)
            /
            max(1, appearances * 5)
        )

    else:
        partner_score = 0.0

    usage_score = min(
        1.0,
        appearances / 200.0
    )

    tournament_score = (
        usage_score * 0.30
        +
        win_rate * 0.25
        +
        top_cut_rate * 0.35
        +
        partner_score * 0.10
    )

    return {
        "usage": usage_score,
        "top_cut_rate": top_cut_rate,
        "win_rate": win_rate,
        "tournament_score": tournament_score,
        "partner_score": partner_score
    }

def get_tournament_partners(
    pokemon_name,
    top_n=10
):
    """
    Returns the strongest tournament partners for a Pokémon.

    Results are based on actual Champions tournament
    team appearances stored in CHAMPIONS_META_DB.
    """

    key = get_champions_species_key(
        pokemon_name
    )

    record = CHAMPIONS_META_DB.get(
        key
    )

    if not record:
        return []

    partners = record.get(
        "partners",
        {}
    )

    ranked = sorted(
        partners.items(),
        key=lambda item: item[1],
        reverse=True
    )

    results = []

    for partner_key, frequency in ranked:

        display_name = display_name_for_species_key(
            partner_key
        )

        if not display_name:
            continue

        if display_name.lower().startswith(
            "mega "
        ):
            continue

        results.append(
            (
                partner_key,
                frequency
            )
        )

        if len(results) >= top_n:
            break

    return results
# -----------------------------------------------------------------------------
# Phase 15: Champions tournament profile display
# -----------------------------------------------------------------------------
def render_champions_tournament_profile(pokemon_name):
    """Render tournament statistics without changing existing app scoring."""
    if get_champions_profile is None:
        return

    try:
        profile = get_champions_profile(pokemon_name)
    except Exception:
        return

    if not profile.get("available"):
        return

    appearances = int(profile.get("appearances") or 0)
    wins = int(profile.get("wins") or 0)
    losses = int(profile.get("losses") or 0)
    win_rate = profile.get("win_rate")
    top_cut_rate = profile.get("top_cut_rate")
    recent_win_rate = profile.get("recent_win_rate")
    partners = profile.get("partners") or []

    with strlit.expander("🏆 Champions Tournament Profile", expanded=True):
        strlit.caption("Historical Champions tournament data. This display does not alter the existing Strategizer score.")
        cols = strlit.columns(4)
        cols[0].metric("Team Appearances", f"{appearances:,}")
        cols[1].metric("Win Rate", f"{float(win_rate) * 100:.1f}%" if win_rate is not None else "N/A")
        cols[2].metric("Top-Cut Rate", f"{float(top_cut_rate) * 100:.1f}%" if top_cut_rate is not None else "N/A")
        cols[3].metric("Recent Win Rate", f"{float(recent_win_rate) * 100:.1f}%" if recent_win_rate is not None else "N/A")
        strlit.caption(f"Tournament game record: {wins:,} wins · {losses:,} losses")

        if partners:
            strlit.markdown("**Most common tournament partners**")
            partner_rows = []
            for partner in partners[:5]:
                partner_name = partner.get("pokemon")
                if not partner_name:
                    continue
                partner_rows.append({
                    "Partner": display_name_for_species_key(partner_name) or partner_name,
                    "Teams Together": int(partner.get("teams_together") or 0),
                    "Shared Win Rate": f"{float(partner.get('shared_win_rate') or 0) * 100:.1f}%",
                })
            if partner_rows:
                strlit.dataframe(partner_rows, hide_index=True, use_container_width=True)
        else:
            strlit.caption("No tournament partner data available.")

# -----------------------------------------------------------------------------
# 4. INITIALIZE SESSION STATE
# -----------------------------------------------------------------------------
if "team_slots" not in strlit.session_state:
    strlit.session_state.team_slots = {}
for i in range(6):
    ensure_slot_structure(i, "-- Choose a Pokémon --")

# -----------------------------------------------------------------------------
# 5. APP INTERFACE
# -----------------------------------------------------------------------------
strlit.title("⚔️ Pokémon Champions Teambuilder")

with strlit.sidebar:
    strlit.header("🛠️ Team Actions")
    if strlit.button("Reset Team"):
        strlit.session_state.team_slots = {}
        for idx in range(6):
            for key in (f"species_select_{idx}", f"ab_{idx}", f"item_{idx}", f"nat_{idx}"):
                strlit.session_state.pop(key, None)
            for move_idx in range(4):
                strlit.session_state.pop(f"move_{idx}_{move_idx}", None)
            for ev_key in ("HP", "Atk", "Def", "SpA", "SpD", "Spe"):
                strlit.session_state.pop(f"stat_ev_{idx}_{ev_key}", None)
            ensure_slot_structure(idx, "-- Choose a Pokémon --")
        strlit.rerun()

    strlit.checkbox("Only show legal moves", value=True, key="legal_moves_only")
    strlit.caption("Uses Smogon Showdown learnsets for legal verification.")

tabs = strlit.tabs([f"Slot {i+1}" for i in range(6)] + ["📊 Team Overview"])

for i in range(6):
    with tabs[i]:
        slot = ensure_slot_structure(i, "-- Choose a Pokémon --")
        slot_name = slot.get('name', '-- Choose a Pokémon --')
        strlit.subheader(f"Slot {i+1}: {slot_name if slot_name != '-- Choose a Pokémon --' else '(Empty Slot)'}")
        
        try:
            default_index = CHAMPIONS_ALL_FORMS.index(slot_name)
        except ValueError:
            default_index = 0

        selected_mon = strlit.selectbox(
            f"Species (Slot {i+1})",
            options=CHAMPIONS_ALL_FORMS,
            index=default_index,
            key=f"species_select_{i}",
            on_change=on_species_change,
            args=(i,)
        )

        slot = strlit.session_state.team_slots[i]
        slot_name = slot.get('name', selected_mon)

        if slot_name == "-- Choose a Pokémon --":
            strlit.info("👆 Please select a Pokémon from the dropdown above to begin building this slot.")
            continue

        col_mon, col_set = strlit.columns([1, 2])
        
        with col_mon:
            mon_data = fetch_pokemon_details(slot_name)
            strlit.image(mon_data["sprite"], width=170)
            
            badge_html = "".join([
                f'<div class="type-badge" style="background-color: {TYPE_COLORS.get(t, "#777")}; margin-right: 6px;">'
                f'<img src="{TYPE_SVG_URLS.get(t, "")}" width="14" height="14" style="filter: brightness(0) invert(1);" />'
                f'<span>{t.upper()}</span>'
                f'</div>'
                for t in mon_data["types"]
            ])
            strlit.markdown(f'<div style="display:flex; margin-bottom:12px;">{badge_html}</div>', unsafe_allow_html=True)

            ability_options = mon_data.get("abilities", ["Standard"])
            current_ability = slot.get("ability", ability_options[0])
            if current_ability not in ability_options:
                current_ability = ability_options[0]

            slot["ability"] = strlit.selectbox("Ability", options=ability_options, index=ability_options.index(current_ability), key=f"ab_{i}")
            strlit.caption(f"Suggested role: {infer_slot_role(slot)}")

            if slot_name in MEGA_STONE_MAP:
                correct_stone = MEGA_STONE_MAP[slot_name]
                slot["item"] = correct_stone
                strlit.text_input("Held Item", value=correct_stone, key=f"item_locked_{i}_{slot_name}", disabled=True)
            else:
                item_opts = CHAMPIONS_HELD_ITEMS
                current_item = slot.get("item", item_opts[0])
                if current_item not in item_opts:
                    current_item = item_opts[0]
                slot["item"] = strlit.selectbox("Held Item", options=item_opts, index=item_opts.index(current_item), key=f"item_{i}")

            nat_opts = NATURES
            current_nature = slot.get("nature", "Hardy")
            nat_match = [n for n in nat_opts if n.startswith(current_nature.split(" ")[0])]
            nat_idx = nat_opts.index(nat_match[0]) if nat_match else 0
            slot["nature"] = strlit.selectbox("Nature", options=nat_opts, index=nat_idx, key=f"nat_{i}")

            meta = compute_meta_analytics(slot_name)
            type_summary = get_type_defense_summary(mon_data["types"])
            offensive_summary = get_offensive_type_summary(mon_data["types"])

            if not meta:
                meta = {
                    "tier": "Unknown",
                    "viability": "0 / 100",
                    "teammates": [],
                    "counters": [],
                    "speed_tier": "N/A",
                    "momentum_rating": "N/A",
                    "hazard_utility": "N/A",
                    "offensive_profile": "N/A",
                }
        render_champions_profile_v6(
            slot_name,
            meta=meta,
            sprite_resolver=get_mini_sprite_url,
            base_stats=mon_data.get("stats"),
            sp_values=slot.get("evs") or {},
        )

        with col_set:
            strlit.markdown("##### ⚔️ Moveset Configuration")
            all_moves = mon_data.get("moves", ["Protect", "Tackle"])
            slot["moves"] = normalize_moves(slot.get("moves", []), all_moves)

            for row_idx in range(2):
                m_col1, m_col2 = col_set.columns(2)
                for c_i, col in enumerate([m_col1, m_col2]):
                    m_idx = row_idx * 2 + c_i
                    current_selected = slot["moves"][m_idx]
                    available_options = [m for m in all_moves if m not in slot["moves"] or m == current_selected]
                    if current_selected not in available_options:
                        current_selected = available_options[0] if available_options else all_moves[0]
                        slot["moves"][m_idx] = current_selected

                    selected_move = col.selectbox(
                        f"Move {m_idx+1}",
                        options=available_options,
                        index=available_options.index(current_selected) if current_selected in available_options else 0,
                        key=f"move_{i}_{m_idx}"
                    )
                    slot["moves"][m_idx] = selected_move

                    m_type = get_hardcoded_move_type(selected_move) or fetch_move_type(selected_move)
                    col.markdown(f'''
                        <div class="move-card" style="background-color: {TYPE_COLORS.get(m_type, "#555")};">
                            <span class="move-name">{selected_move}</span>
                            <div class="move-type-badge">
                                <img src="{TYPE_SVG_URLS.get(m_type, "")}" width="14" height="14" style="filter: brightness(0) invert(1);" />
                                <span>{m_type.upper()}</span>
                            </div>
                        </div>
                    ''', unsafe_allow_html=True)
            strlit.markdown("##### 📊 Champions SP Allocation")
            sp_cols = col_set.columns(3)
            sp_keys = ["HP", "Atk", "Def", "SpA", "SpD", "Spe"]
            sp_labels = ["HP", "Attack", "Defense", "Sp. Atk", "Sp. Def", "Speed"]
            if "evs" not in slot or not isinstance(slot["evs"], dict):
                slot["evs"] = {k: 0 for k in sp_keys}
            current_sp = {k: max(0, min(32, int(slot["evs"].get(k, 0) or 0))) for k in sp_keys}
            used_sp = sum(current_sp.values())
            for idx, (key, label) in enumerate(zip(sp_keys, sp_labels)):
                with sp_cols[idx % 3]:
                    other_sp = used_sp - current_sp[key]
                    max_allowed = min(32, 66 - other_sp)
                    current_value = current_sp[key]
                    new_value = strlit.number_input(
                        label, min_value=0, max_value=max_allowed, step=1,
                        value=min(current_value, max_allowed), key=f"stat_sp_{i}_{key}"
                    )
                    current_sp[key] = int(new_value)
                    slot["evs"][key] = int(new_value)
                    used_sp = other_sp + int(new_value)
            strlit.caption(f"Champions SP: {sum(current_sp.values())}/66 total · maximum 32 per stat")


            strlit.markdown("##### Type matchup")
            with strlit.container(border=True):
                weak_col, resist_col, immune_col = strlit.columns(3)
                with weak_col:
                    strlit.caption("Weak to")
                    strlit.html(render_type_chips(type_summary["weak"], type_summary["multipliers"]))
                with resist_col:
                    strlit.caption("Resists")
                    strlit.html(render_type_chips(type_summary["resist"], type_summary["multipliers"]))
                with immune_col:
                    strlit.caption("Immune to")
                    strlit.html(render_type_chips(type_summary["immune"], type_summary["multipliers"]))

            strlit.markdown("##### Offensive coverage")

            with strlit.container(border=True):

                strong_col, resisted_col = strlit.columns(2)

                with strong_col:
                    strlit.caption(
                        "STAB attacks are strong against"
                    )

                    strong_types = [
                        type_name
                        for type_name, multiplier
                        in offensive_summary["strong_against"]
                    ]

                    strong_multipliers = {
                        type_name: multiplier
                        for type_name, multiplier
                        in offensive_summary["strong_against"]
                    }

                    strlit.html(
                        render_type_chips(
                            strong_types,
                            strong_multipliers
                        )
                    )

                with resisted_col:
                    strlit.caption(
                        "STAB attacks are resisted by"
                    )

                    resisted_types = [
                        type_name
                        for type_name, multiplier
                        in offensive_summary["resisted_by"]
                    ]

                    resisted_multipliers = {
                        type_name: multiplier
                        for type_name, multiplier
                        in offensive_summary["resisted_by"]
                    }

                    strlit.html(
                        render_type_chips(
                            resisted_types,
                            resisted_multipliers
                        )
                    )

            render_base_stats_bubble(mon_data.get("stats"))

# -----------------------------------------------------------------------------
# 6. TAB 7: TEAM OVERVIEW & TEAM EVALUATOR INTEGRATION
# -----------------------------------------------------------------------------
with tabs[6]:
    strlit.subheader("📊 Comprehensive Team Overview & Meta Evaluator")

    active_slots = [
        (idx, slot) for idx, slot in strlit.session_state.team_slots.items()
        if slot.get("name") and slot.get("name") != "-- Choose a Pokémon --"
    ]

    # Showdown Import / Export Section
    exp_col, imp_col = strlit.columns(2)
    with exp_col:
        with strlit.expander("📤 Export Showdown Pokepaste Text", expanded=False):
            exported_text = export_team_to_showdown(strlit.session_state.team_slots)
            strlit.code(exported_text if exported_text else "No Pokémon selected.", language="text")

    with imp_col:
        with strlit.expander("📥 Import Showdown Format", expanded=False):
            import_input = strlit.text_area("Paste Showdown format team below:", height=120)
            if strlit.button("Import Team"):
                if import_input.strip():
                    parsed = parse_showdown_text(import_input)
                    for idx in range(6):
                        if idx < len(parsed):
                            strlit.session_state.team_slots[idx] = parsed[idx]
                        else:
                            ensure_slot_structure(idx, "-- Choose a Pokémon --")
                    strlit.success(f"Imported {len(parsed)} Pokémon into team slots!")
                    strlit.rerun()

    strlit.divider()

    if not active_slots:
        strlit.info("💡 Add Pokémon to your team slots to run dynamic competitive evaluation.")
    else:
        # Build meta profiles for current team and evaluation candidates
        active_names = [slot["name"] for _, slot in active_slots]
        meta_db: Dict[str, MonMetaProfile] = {}

        for _, slot in active_slots:
            meta_db[slot["name"]] = slot_to_mon_meta_profile(slot)

        # Pre-populate meta DB with a sample pool of candidate threats for counter / synergy calculation
        top_candidates = ["Garchomp", "Gengar", "Dragonite", "Tyranitar", "Lucario", "Rotom Wash", "Ferrothorn", "Corviknight", "Clefable"]
        for cand_name in top_candidates:
            if cand_name not in meta_db:
                cand_slot = {"name": cand_name, "moves": ["Earthquake", "Swords Dance", "Stealth Rock", "Protect"], "ability": "Standard", "item": "Leftovers"}
                meta_db[cand_name] = slot_to_mon_meta_profile(cand_slot)

        evaluator = TeamEvaluator(meta_db)

        strlit.markdown("### 🏆 Team Synergy & Fit Ratings (`TeamEvaluator`)")
        
        slot_eval_cols = strlit.columns(len(active_slots))
        team_ratings = []

        for col_idx, (slot_i, slot) in enumerate(active_slots):
            mon_name = slot["name"]
            other_team = [n for n in active_names if n != mon_name]

            eval_res = evaluator.evaluate_candidate(mon_name, other_team)
            team_ratings.append(eval_res["final_rating"])

            with slot_eval_cols[col_idx]:
                mon_info = fetch_pokemon_details(mon_name)
                strlit.image(mon_info["box_sprite"], width=60)
                strlit.markdown(f"**{mon_name}**")
                strlit.metric("Fit Score", f"{eval_res['final_rating']} / 100")
                strlit.caption(f"**Class:** {eval_res['recommendation_class']}")
                strlit.markdown(
                    f"- **Defensive Fit:** {eval_res['defensive_fit']}\n"
                    f"- **Meta Coverage:** {eval_res['meta_coverage']}\n"
                    f"- **Synergy Index:** {eval_res['synergy_index']}\n"
                    f"- **Counter Utility:** {eval_res['counter_utility']}"
                )

        avg_score = round(sum(team_ratings) / len(team_ratings), 1) if team_ratings else 0
        strlit.markdown(f"#### 📊 Overall Composite Team Rating: **{avg_score} / 100**")

        # Candidate Suggestions for Open Slots
        if len(active_slots) < 6:
            strlit.markdown("### 💡 Top Recommended Picks for Next Slot")
            candidate_pool = [c for c in CHAMPIONS_ALL_FORMS if c != "-- Choose a Pokémon --" and c not in active_names][:12]
            
            recommendations = []
            for cand in candidate_pool:
                if cand not in meta_db:
                    meta_db[cand] = slot_to_mon_meta_profile({"name": cand, "moves": ["Protect"], "ability": "Standard", "item": ""})
                evaluator.meta = meta_db
                score = evaluator.evaluate_candidate(cand, active_names)
                recommendations.append((score["final_rating"], cand, score["recommendation_class"]))

            recommendations.sort(key=lambda x: -x[0])
            rec_cols = strlit.columns(min(4, len(recommendations)))
            for i_rec, (score_val, cand_name, rec_class) in enumerate(recommendations[:4]):
                with rec_cols[i_rec]:
                    c_info = fetch_pokemon_details(cand_name)
                    strlit.image(c_info["box_sprite"], width=50)
                    strlit.markdown(f"**{cand_name}**")
                    strlit.metric("Fit Score", f"{score_val} / 100")
                    strlit.caption(rec_class)

    strlit.divider()
    strlit.success("✓ `TeamEvaluator` integrated: candidate scoring, defensive weakness mitigation, and threat coverage active.")
    strlit.success("✓ Authoritative Smogon Chaos usage statistics engine integrated for tiering, abilities, items, and partner metrics.")
    strlit.success("✓ Dynamic moveset names fetched directly from Pokémon Showdown's GitHub repository.")
    strlit.success("✓ Showdown text format Pokepaste import and export functional.")



