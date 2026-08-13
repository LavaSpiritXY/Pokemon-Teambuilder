import math
import random
import re
from typing import Dict, List, Set, Tuple

import requests
import streamlit as strlit
import pandas as pd
from champions.constants import (
    TYPE_COLORS,
    TYPE_SVG_URLS,
    NATURES,
    TYPE_CHART_DATA,
    CUSTOM_MEGAS_DATA,
    BASE_HELD_ITEMS,
    TYPE_DEFENSES,
)

from champions.move_data import (
    MASTER_MOVE_DICTIONARY,
    display_name_for_move,
    fetch_master_move_dictionary,
    fetch_move_type,
    get_champions_species_key,
    get_hardcoded_move_type,
    get_move_api_slug,
)

from champions.meta_utils import detect_archetypes

from champions.meta_viability import CHAMPIONS_META_DATA, calculate_meta_viability
from champions.smogon_data import fetch_smogon_usage_stats, get_smogon_stats_for

from champions.roles import infer_slot_role
from champions.team_moves import generate_synergistic_moveset, normalize_moves

from champions.species_keys import canonical_species_key

from champions.roster_data import (
    fetch_champions_learnsets,
    fetch_champions_pokedex_entries,
    display_name_for_species_key,
    get_clean_api_name,
    get_base_api_name,
)


from champions.pokemon_data import (
    get_champion_moves_for,
    fetch_pokemon_details,
    get_mini_sprite_url,
)

from champions.type_chart import (
    get_type_relationships,
    get_type_defense_summary,
    get_offensive_type_summary,
    format_type_multiplier,
    render_type_chips,
)

from champions.tournament_data import (
    CHAMPIONS_META_DB,
    import_champions_tournament,
    calculate_tournament_metrics,
    get_tournament_partners,
)

from champions.meta_engine import (
    MoveProfile,
    MonMetaProfile,
    TeamEvaluator,
    build_meta_profiles_from_data,
    create_move_profile,
    get_meta_relevant_checks,
)
from champions_phase18_5 import render_champions_profile_v6
from champions_phase18_6_ui import render_dynamic_stat_controls, render_dynamic_stat_graph
from champions_phase18 import render_champions_profile_v3
from champions_phase17 import render_champions_profile_v2
from champions.team_io import export_slot_to_showdown, export_team_to_showdown, parse_showdown_text

try:
    from champions_integration import get_champions_profile
except ImportError:
    get_champions_profile = None



# Fallback Smogon Usage Database
SMOGON_USAGE_DB = fetch_smogon_usage_stats(display_name_for_move)

# ==========================================
# 3. META-GATED CHECKS, COUNTERS & SYNERGY
# ==========================================



# -----------------------------------------------------------------------------
# 0. COMPETITIVE META EVALUATION ENGINE & DATA MODELS
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# 1. CONFIG & VISUAL STYLING
# -----------------------------------------------------------------------------
strlit.set_page_config(
    page_title="Pokémon Champions Teambuilder",
    page_icon="⚔️",
    layout="wide",
    initial_sidebar_state="expanded"
)


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


MEGA_STONE_MAP = {name: f"{name.replace('Mega ', '')}ite" for name in CUSTOM_MEGAS_DATA.keys()}




CHAMPIONS_LEARNSETS = fetch_champions_learnsets()
CHAMPIONS_ROSTER = fetch_champions_pokedex_entries()
VALID_CHAMPIONS = {
    display_name_for_species_key(species)
    for species in set(CHAMPIONS_ROSTER) | set(CHAMPIONS_LEARNSETS)
}
VALID_CHAMPIONS.update(CUSTOM_MEGAS_DATA)


@strlit.cache_data(ttl=86400, show_spinner=False)
def fetch_pokemon_roster():
    roster = list(CUSTOM_MEGAS_DATA.keys())
    for species_key in sorted(set(CHAMPIONS_ROSTER) | set(CHAMPIONS_LEARNSETS.keys())):
        roster.append(display_name_for_species_key(species_key))
    return ["-- Choose a Pokémon --"] + sorted(set(roster), key=lambda item: (not item.startswith("Mega "), item.lower()))

CHAMPIONS_ALL_FORMS = fetch_pokemon_roster()

CHAMPIONS_HELD_ITEMS = sorted(list(set(BASE_HELD_ITEMS + list(MEGA_STONE_MAP.values()))))

# -----------------------------------------------------------------------------
# 3. HELPER FUNCTIONS & API FETCHING
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# 3.5 SMOGON COMPETITIVE USAGE DATA SOURCE ENGINE
# -----------------------------------------------------------------------------
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
            infer_slot_role(
                {
                    "name": mon_name,
                    "moves": moves
                },
                fetch_pokemon_details
            ),
        "teammates": teammates,
        "counters": counters
    }

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
    recommended_moves = generate_synergistic_moveset(
        new_species,
        slot_idx,
        fetch_pokemon_details,
        get_smogon_stats_for,
        fetch_move_type
    )

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
            render_dynamic_stat_controls(
                slot_index=i,
                pokemon_name=slot_name,
                nature=slot.get("nature", "Hardy"),
            )


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

            render_dynamic_stat_graph(
                slot_index=i,
                pokemon_name=slot_name,
                base_stats=mon_data.get("stats"),
                nature=slot.get("nature", "Hardy"),
            )

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



