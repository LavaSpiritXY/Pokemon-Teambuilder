from champions.meta_utils import detect_archetypes


SMOGON_USAGE_DB = {}

CHAMPIONS_META_DATA = {
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
    """Return external competitive statistics when available."""
    if not mon_name:
        return {
            "meta_usage_tier": None,
            "common_moves": {},
            "common_abilities": {},
            "common_items": {},
            "top_partners": {}
        }

    stats = SMOGON_USAGE_DB.get(mon_name)
    if stats:
        return stats

    target = str(mon_name).strip().lower()
    for name, data in SMOGON_USAGE_DB.items():
        if str(name).strip().lower() == target:
            return data

    return {
        "meta_usage_tier": None,
        "common_moves": {},
        "common_abilities": {},
        "common_items": {},
        "top_partners": {}
    }


def _tournament_score_from_metrics(tournament_metrics):
    """Extract or derive a normalized tournament signal.

    The normal application path supplies ``tournament_score`` from
    ``calculate_tournament_metrics``.  Some callers, however, intentionally
    pass only the regulation-level ``current`` payload.  That payload contains
    real performance evidence but no precomputed score, so it must not silently
    fall back to the strategic default of 50.

    Win rate is centred around 50%, while top-cut rate is scaled against a
    12.5% benchmark (roughly one top-cut place per eight teams).  Both inputs
    remain clamped to [0, 1], and missing win rate is simply omitted.
    """
    if not isinstance(tournament_metrics, dict):
        return None

    explicit_score = tournament_metrics.get("tournament_score")
    if explicit_score is not None:
        try:
            return max(0.0, min(1.0, float(explicit_score)))
        except (TypeError, ValueError):
            pass

    current = tournament_metrics.get("current")
    if not isinstance(current, dict):
        current = tournament_metrics

    win_rate = current.get("win_rate")
    top_cut_rate = current.get("top_cut_rate")

    components = []
    try:
        if win_rate is not None:
            components.append((max(0.0, min(1.0, float(win_rate))), 0.55))
    except (TypeError, ValueError):
        pass

    try:
        if top_cut_rate is not None:
            top_cut_score = max(
                0.0,
                min(1.0, float(top_cut_rate) / 0.125),
            )
            components.append((top_cut_score, 0.45))
    except (TypeError, ValueError):
        pass

    if not components:
        return None

    total_weight = sum(weight for _, weight in components)
    return sum(score * weight for score, weight in components) / total_weight


# ==========================================
# META-INDEX AWARE VIABILITY & TIERING
# ==========================================
def calculate_meta_viability(
    pkmn_data,
    selected_format="Gen 9 OU",
    tournament_metrics=None,
    external_stats=None,
):
    """Calculate the Meta Viability Index from available evidence.

    Tournament evidence is the primary signal. External competitive data is
    supplementary, while the strategic/default score provides the baseline.
    Missing evidence is ignored rather than treated as a zero.
    """
    pkmn_name = pkmn_data.get("name", "Unknown")
    archetypes = detect_archetypes(pkmn_data)

    tournament_score = _tournament_score_from_metrics(tournament_metrics)

    # Allow callers/tests to supply an already-fetched external signal. This
    # also avoids coupling this scoring function to a particular data source.
    if external_stats is None:
        external_stats = get_smogon_stats_for(pkmn_name)

    external_usage = external_stats.get("meta_usage_tier")
    external_score = None
    if external_usage is not None:
        external_score = max(0.0, min(1.0, float(external_usage)))

    default_score = max(
        0.0,
        min(100.0, float(pkmn_data.get("default_score", 50)))
    )

    signals = []

    # Tournament data is deliberately dominant.
    if tournament_score is not None:
        signals.append((tournament_score * 100.0, 0.70))

    # External data is useful context, but must not overpower tournament data.
    if external_score is not None:
        signals.append((external_score * 100.0, 0.10))

    # The strategic baseline carries the remaining 20% when stronger evidence
    # exists, and becomes the sole signal when no external/tournament data is
    # available.
    signals.append((default_score, 0.20))

    total_weight = sum(weight for _, weight in signals)
    weighted_score = (
        sum(score * weight for score, weight in signals) / total_weight
    )

    archetype_boost = max(
        (
            float(archetype.get("boost", 0))
            for archetype in archetypes
        ),
        default=0,
    )
    archetype_boost = max(-5, min(5, archetype_boost))

    final_score = int(round(max(0, min(100, weighted_score + archetype_boost))))

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

    roles = []
    for archetype in archetypes:
        role = archetype.get("role_label")
        if role and role not in roles:
            roles.append(role)

    team_role = (
        " / ".join(roles)
        if roles
        else pkmn_data.get("fallback_role", "Balanced Pick")
    )

    return {
        "viability_index": final_score,
        "tier_display": tier_label,
        "recommended_role": team_role,
        "archetypes_detected": [
            archetype.get("name") for archetype in archetypes
        ],
    }
