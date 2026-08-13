from champions.meta_utils import detect_archetypes


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
