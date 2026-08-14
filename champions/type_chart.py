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
    """Calculate final damage multipliers against a Pokémon's defending types."""

    normalised_types = _normalise_types(types)
    multipliers = {}

    for attacking_type in TYPE_CHART_DATA:
        multiplier = 1.0

        attacking_matchups = TYPE_CHART_DATA.get(
            attacking_type,
            {}
        )

        for defending_type in normalised_types:
            multiplier *= attacking_matchups.get(
                defending_type,
                1.0,
            )

        multipliers[attacking_type] = multiplier

    return multipliers


def get_type_defense_summary(type_names):
    """
    Return the complete defensive matchup profile for a Pokémon.

    For dual-type Pokémon the individual type multipliers are multiplied,
    e.g. Fire/Dark correctly combines both Fire and Dark interactions.
    """

    types = _normalise_types(type_names)
    multipliers = _calculate_defensive_multipliers(types)

    weak = sorted(
        attacking_type
        for attacking_type, multiplier in multipliers.items()
        if multiplier > 1.0
    )

    resist = sorted(
        attacking_type
        for attacking_type, multiplier in multipliers.items()
        if 0.0 < multiplier < 1.0
    )

    immune = sorted(
        attacking_type
        for attacking_type, multiplier in multipliers.items()
        if multiplier == 0.0
    )

    return {
        "weak": weak,
        "resist": resist,
        "immune": immune,
        "multipliers": multipliers,

        # Compatibility fields used elsewhere in the project.
        "double_damage_from": [
            name.lower()
            for name, multiplier in multipliers.items()
            if multiplier > 1.0
        ],

        "half_damage_from": [
            name.lower()
            for name, multiplier in multipliers.items()
            if 0.0 < multiplier < 1.0
        ],

        "no_damage_from": [
            name.lower()
            for name, multiplier in multipliers.items()
            if multiplier == 0.0
        ],
    }

def get_offensive_type_summary(type_names):
    """
    Calculate offensive coverage for a Pokémon's STAB types.

    Each defending type is evaluated against every STAB type and the
    strongest available STAB multiplier is retained.

    Example:
        Fire/Dark

    against Grass:
        Fire = 2x
        Dark = 1x
        final = 2x

    against Psychic:
        Fire = 1x
        Dark = 2x
        final = 2x
    """

    types = _normalise_types(type_names)

    target_multipliers = {}

    for defending_type in TYPE_CHART_DATA:

        combined_multiplier = 1.0

        for attacking_type in types:
            attacking_matchups = TYPE_CHART_DATA.get(
                attacking_type,
                {}
            )

            multiplier = attacking_matchups.get(
                defending_type,
                1.0,
            )

            combined_multiplier *= multiplier

        target_multipliers[defending_type] = combined_multiplier

    strong_against = {
        name: multiplier
        for name, multiplier in target_multipliers.items()
        if multiplier > 1.0
    }

    resisted_by = {
        name: multiplier
        for name, multiplier in target_multipliers.items()
        if 0.0 < multiplier < 1.0
    }

    immune = {
        name: multiplier
        for name, multiplier in target_multipliers.items()
        if multiplier == 0.0
    }

    return {
        "strong_against": sorted(
            strong_against.items()
        ),

        "resisted_by": sorted(
            resisted_by.items()
        ),

        "immune": [
            name.lower()
            for name, multiplier in immune.items()
            if multiplier == 0.0
        ],

        # Explicit multiplier dictionaries for the UI.
        "strong_multipliers": strong_against,
        "resisted_multipliers": resisted_by,
        "immune_multipliers": immune,

        # Full matchup table.
        "multipliers": target_multipliers,

        # Compatibility names expected by existing tests/code.
        "double": sorted({
            defending_type.lower()
            for attacking_type in types
            for defending_type, multiplier in TYPE_CHART_DATA.get(
                attacking_type,
                {}
            ).items()
            if multiplier == 2.0
        }),

        "half": sorted({
            defending_type.lower()
            for attacking_type in types
            for defending_type, multiplier in TYPE_CHART_DATA.get(
                attacking_type,
                {}
            ).items()
            if multiplier == 0.5
        }),

        "no_damage": sorted({
            defending_type.lower()
            for attacking_type in types
            for defending_type, multiplier in TYPE_CHART_DATA.get(
                attacking_type,
                {}
            ).items()
            if multiplier == 0.0
        }),
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
    """Render Pokémon-style type chips with optional effectiveness multipliers."""
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

            if multiplier is None:
                multiplier = multipliers.get(display_name.upper())

        color = TYPE_COLORS.get(display_name, "#777")
        icon_url = TYPE_SVG_URLS.get(display_name, "")

        multiplier_text = ""
        if multiplier is not None:
            multiplier_text = (
                f"<span style='font-size:0.8em;"
                f"opacity:0.85;"
                f"margin-left:3px'>"
                f"{format_type_multiplier(multiplier)}"
                f"</span>"
            )

        icon_html = ""
        if icon_url:
            icon_html = (
                f"<img src='{icon_url}' "
                f"width='18' height='18' "
                f"style='display:block;"
                f"filter:brightness(0) invert(1);"
                f"flex:0 0 auto;'>"
            )

        chips.append(
            f"<span style='display:inline-flex;"
            f"align-items:center;"
            f"justify-content:center;"
            f"gap:6px;"
            f"padding:6px 11px;"
            f"margin:3px;"
            f"border-radius:8px;"
            f"background:{color};"
            f"color:white;"
            f"font-weight:700;"
            f"font-size:0.88rem;"
            f"line-height:1;"
            f"white-space:nowrap;"
            f"box-sizing:border-box;'>"
            f"{icon_html}"
            f"<span>{display_name.upper()}</span>"
            f"{multiplier_text}"
            f"</span>"
        )

    return " ".join(chips)
