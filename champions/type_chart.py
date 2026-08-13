from champions.constants import TYPE_COLORS, TYPE_DEFENSES, TYPE_SVG_URLS
import requests

TYPE_ORDER = list(TYPE_COLORS)


def get_type_relationships(type_name):
    """Fetch raw PokeAPI damage relations for one attacking type."""
    try:
        response = requests.get(
            f"https://pokeapi.co/api/v2/type/{str(type_name).lower()}",
            timeout=5,
        )
        if response.status_code == 200:
            return response.json().get("damage_relations", {})
    except Exception:
        pass
    return {}


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
    """Calculates offensive STAB coverage and combined resistance multipliers."""
    strong_against = []
    resisted_by = []
    for defending_type in TYPE_ORDER:
        matchup = TYPE_DEFENSES.get(defending_type, {})
        multipliers = []
        for attacking_type in attacking_types:
            if attacking_type in matchup.get("immune", []):
                multiplier = 0.0
            elif attacking_type in matchup.get("resist", []):
                multiplier = 0.5
            elif attacking_type in matchup.get("weak", []):
                multiplier = 2.0
            else:
                multiplier = 1.0
            multipliers.append(multiplier)
        if not multipliers:
            continue
        best_multiplier = max(multipliers)
        if best_multiplier > 1:
            strong_against.append((defending_type, best_multiplier))
        if any(multiplier == 0 for multiplier in multipliers):
            combined_multiplier = 0.0
        else:
            combined_multiplier = 1.0
            for multiplier in multipliers:
                combined_multiplier *= multiplier
        if combined_multiplier < 1:
            resisted_by.append((defending_type, combined_multiplier))
    return {"strong_against": strong_against, "resisted_by": resisted_by}


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
