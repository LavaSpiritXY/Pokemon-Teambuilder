from champions.constants import TYPE_CHART_DATA, TYPE_COLORS, TYPE_SVG_URLS

def _relation_entries(names):
    return [{"name": str(name).lower()} for name in names]


def _normalise_types(type_names):
    if isinstance(type_names, str):
        return [type_names.strip().title()]

    if not type_names:
        return []

    return [
        str(type_name).strip().title()
        for type_name in type_names
        if str(type_name).strip()
    ]


def _build_reverse_relations():
    reverse = {
        type_name: {
            "double_damage_from": [],
            "half_damage_from": [],
            "no_damage_from": [],
        }
        for type_name in TYPE_CHART_DATA
    }

    for attacking_type, matchups in TYPE_CHART_DATA.items():
        for defending_type, multiplier in matchups.items():
            if defending_type not in reverse:
                continue

            if multiplier == 2.0:
                reverse[defending_type]["double_damage_from"].append(
                    attacking_type
                )
            elif multiplier == 0.5:
                reverse[defending_type]["half_damage_from"].append(
                    attacking_type
                )
            elif multiplier == 0.0:
                reverse[defending_type]["no_damage_from"].append(
                    attacking_type
                )

    return reverse


_REVERSE_RELATIONS = _build_reverse_relations()


def get_type_relationships(type_name):
    """Return PokeAPI-compatible relationships for one type."""

    canonical = str(type_name or "").strip().title()
    matchups = TYPE_CHART_DATA.get(canonical, {})

    double_damage_to = [
        name
        for name, multiplier in matchups.items()
        if multiplier == 2.0
    ]

    half_damage_to = [
        name
        for name, multiplier in matchups.items()
        if multiplier == 0.5
    ]

    no_damage_to = [
        name
        for name, multiplier in matchups.items()
        if multiplier == 0.0
    ]

    reverse = _REVERSE_RELATIONS.get(
        canonical,
        {
            "double_damage_from": [],
            "half_damage_from": [],
            "no_damage_from": [],
        },
    )

    return {
        "double_damage_from": _relation_entries(
            reverse["double_damage_from"]
        ),
        "half_damage_from": _relation_entries(
            reverse["half_damage_from"]
        ),
        "no_damage_from": _relation_entries(
            reverse["no_damage_from"]
        ),
        "double_damage_to": _relation_entries(
            double_damage_to
        ),
        "half_damage_to": _relation_entries(
            half_damage_to
        ),
        "no_damage_to": _relation_entries(
            no_damage_to
        ),
    }


def _calculate_defensive_multipliers(types):
    """Calculate the final attacking-type multiplier against a Pokémon."""

    multipliers = {}

    for attacking_type in TYPE_CHART_DATA:
        multiplier = 1.0

        for defending_type in types:
            matchup = TYPE_CHART_DATA.get(
                attacking_type,
                {}
            ).get(
                defending_type,
                1.0
            )

            multiplier *= matchup

        multipliers[attacking_type] = multiplier

    return multipliers


def get_type_defense_summary(type_names):
    """
    Return the defensive matchup summary expected by the app.

    Supports both single-type and dual-type Pokémon.
    """

    types = _normalise_types(type_names)
    multipliers = _calculate_defensive_multipliers(types)

    weak = {
        attacking_type
        for attacking_type, multiplier in multipliers.items()
        if multiplier >= 2.0
    }

    resist = {
        attacking_type
        for attacking_type, multiplier in multipliers.items()
        if 0.0 < multiplier <= 0.5
    }

    immune = {
        attacking_type
        for attacking_type, multiplier in multipliers.items()
        if multiplier == 0.0
    }

    return {
        "weak": sorted(weak),
        "resist": sorted(resist),
        "immune": sorted(immune),
        "multipliers": multipliers,

        # Compatibility with the newer relationship naming.
        "double_damage_from": sorted(
            name.lower() for name in weak
        ),
        "half_damage_from": sorted(
            name.lower() for name in resist
        ),
        "no_damage_from": sorted(
            name.lower() for name in immune
        ),
    }

def get_offensive_type_summary(type_names):
    """
    Calculate offensive coverage for a Pokémon's STAB types.

    strong_against:
        Targets hit for 2x or 4x by at least one STAB type.

    resisted_by:
        Targets where the best STAB hit is 0.5x or 0.25x.

    immune:
        Targets where the best available STAB hit is 0x.
    """
    types = _normalise_types(type_names)

    target_multipliers = {}

    for defending_type in TYPE_CHART_DATA:
        stab_multipliers = []

        for attacking_type in types:
            multiplier = (
                TYPE_CHART_DATA
                .get(attacking_type, {})
                .get(defending_type, 1.0)
            )
            stab_multipliers.append(multiplier)

        target_multipliers[defending_type] = (
            max(stab_multipliers)
            if stab_multipliers
            else 1.0
        )

    strong_against = {
        name: multiplier
        for name, multiplier in target_multipliers.items()
        if multiplier >= 2.0
    }

    resisted_by = {
        name: multiplier
        for name, multiplier in target_multipliers.items()
        if 0.0 < multiplier <= 0.5
    }

    immune = {
        name: multiplier
        for name, multiplier in target_multipliers.items()
        if multiplier == 0.0
    }

    return {
        # App-facing lists
        "strong_against": [name.lower() for name in strong_against],
        "resisted_by": [name.lower() for name in resisted_by],
        "immune": [name.lower() for name in immune],

        # Multiplier dictionaries
        "strong_multipliers": strong_against,
        "resisted_multipliers": resisted_by,
        "immune_multipliers": immune,

        # Full chart
        "multipliers": target_multipliers,

        # Old compatibility names expected by the tests
        "double": [
            name.lower()
            for name in strong_against
        ],
        "half": [
            name.lower()
            for name in resisted_by
        ],
        "no_damage": [
            name.lower()
            for name in immune
        ],
    }

def format_type_multiplier(multiplier):
    if multiplier == 0:
        return "0×"

    if multiplier == 0.25:
        return "¼×"

    if multiplier == 0.5:
        return "½×"

    if multiplier == 2:
        return "2×"

    if multiplier == 4:
        return "4×"

    return f"{multiplier:g}×"


def render_type_chips(types, multipliers=None):
    """Render official Pokémon type SVG icons with the existing type colours."""
    if not types:
        return "<span style='opacity:0.6'>None</span>"

    chips = []

    for type_name in types:
        display_name = str(type_name).strip().title()

        multiplier = None
        if multipliers:
            multiplier = multipliers.get(type_name)
            if multiplier is None:
                multiplier = multipliers.get(display_name)
            if multiplier is None:
                multiplier = multipliers.get(display_name.lower())

        color = TYPE_COLORS.get(display_name, "#777")
        icon_url = TYPE_SVG_URLS.get(display_name, "")

        multiplier_text = ""
        if multiplier is not None:
            multiplier_text = (
                f"<span style='font-size:0.8em;opacity:0.85;"
                f"margin-left:4px'>"
                f"{format_type_multiplier(multiplier)}"
                f"</span>"
            )

        icon_html = ""
        if icon_url:
            icon_html = (
                f"<img src='{icon_url}' "
                f"width='28' height='28' "
                f"style='display:block;filter:brightness(0) invert(1);'>"
            )

            chips.append(
                f"<span style='display:inline-flex;"
                f"align-items:center;"
                f"justify-content:center;"
                f"gap:8px;"
                f"padding:8px 14px;"
                f"margin:4px;"
                f"border-radius:10px;"
                f"background:{color};"
                f"color:white;"
                f"font-weight:700;"
                f"font-size:0.95rem;"
                f"white-space:nowrap'>"
                f"{icon_html}"
                f"<span>{display_name.upper()}</span>"
                f"{multiplier_text}"
                f"</span>"
            )

    return " ".join(chips)
