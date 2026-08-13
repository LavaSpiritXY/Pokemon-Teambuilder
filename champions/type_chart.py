from champions.constants import TYPE_CHART_DATA


def _relation_entries(names):
    return [{"name": name.lower()} for name in names]


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
    """Return PokeAPI-compatible type relationships from the local chart."""
    canonical = str(type_name or "").strip().title()
    matchups = TYPE_CHART_DATA.get(canonical, {})

    double_damage_to = [
        name for name, multiplier in matchups.items()
        if multiplier == 2.0
    ]
    half_damage_to = [
        name for name, multiplier in matchups.items()
        if multiplier == 0.5
    ]
    no_damage_to = [
        name for name, multiplier in matchups.items()
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


def _relation_names(relations, key):
    return [
        item.get("name", "")
        for item in relations.get(key, [])
        if item.get("name")
    ]


def get_type_defense_summary(type_name):
    relations = get_type_relationships(type_name)
    return {
        "double_damage_from": _relation_names(
            relations,
            "double_damage_from",
        ),
        "half_damage_from": _relation_names(
            relations,
            "half_damage_from",
        ),
        "no_damage_from": _relation_names(
            relations,
            "no_damage_from",
        ),
    }


def get_offensive_type_summary(type_name):
    relations = get_type_relationships(type_name)
    return {
        "double": _relation_names(
            relations,
            "double_damage_to",
        ),
        "half": _relation_names(
            relations,
            "half_damage_to",
        ),
        "immune": _relation_names(
            relations,
            "no_damage_to",
        ),
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


def render_type_chips(types):
    return " ".join(f"`{t}`" for t in types)
