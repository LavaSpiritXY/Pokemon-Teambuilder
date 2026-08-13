import requests
import streamlit as strlit


@strlit.cache_data(ttl=86400, show_spinner=False)
def get_type_relationships(type_name):
    """Fetch PokeAPI type relationships for a single type."""
    try:
        response = requests.get(
            f"https://pokeapi.co/api/v2/type/{type_name.lower()}",
            timeout=10,
        )
        response.raise_for_status()
        relations = response.json().get("damage_relations", {})

        return {
            "double_damage_from": relations.get("double_damage_from", []),
            "half_damage_from": relations.get("half_damage_from", []),
            "no_damage_from": relations.get("no_damage_from", []),
            "double_damage_to": relations.get("double_damage_to", []),
            "half_damage_to": relations.get("half_damage_to", []),
            "no_damage_to": relations.get("no_damage_to", []),
        }
    except Exception:
        return {
            "double_damage_from": [],
            "half_damage_from": [],
            "no_damage_from": [],
            "double_damage_to": [],
            "half_damage_to": [],
            "no_damage_to": [],
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
        "double_damage_from": _relation_names(relations, "double_damage_from"),
        "half_damage_from": _relation_names(relations, "half_damage_from"),
        "no_damage_from": _relation_names(relations, "no_damage_from"),
    }


def get_offensive_type_summary(type_name):
    relations = get_type_relationships(type_name)
    return {
        "double": _relation_names(relations, "double_damage_to"),
        "half": _relation_names(relations, "half_damage_to"),
        "immune": _relation_names(relations, "no_damage_to"),
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
