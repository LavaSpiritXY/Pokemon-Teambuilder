from typing import Callable, Dict, Any


def infer_slot_role(
    slot: Dict[str, Any],
    fetch_pokemon_details: Callable[[str], Dict[str, Any]] | None = None,
) -> str:
    """Infer a practical competitive role from a configured slot.

    The resolver is optional so the Streamlit app can use this helper without
    threading its Pokémon-data dependency through every call site.
    """
    if fetch_pokemon_details is None:
        from champions.pokemon_data import fetch_pokemon_details as _fetch_pokemon_details
        fetch_pokemon_details = _fetch_pokemon_details

    name = slot.get("name", "")
    moves = set(slot.get("moves", []))

    details = fetch_pokemon_details(name)
    stats = details.get("stats", {})

    atk = stats.get("attack", 100)
    spa = stats.get("special-attack", 100)
    spe = stats.get("speed", 100)
    hp = stats.get("hp", 100)
    defense = stats.get("defense", 100)
    sp_def = stats.get("special-defense", 100)

    if "Tailwind" in moves:
        return "Speed Control / Support"
    if "Trick Room" in moves:
        return "Trick Room / Support"
    if moves & {"Swords Dance", "Dragon Dance", "Nasty Plot", "Quiver Dance", "Calm Mind"}:
        return "Setup Sweeper"
    if moves & {"U-turn", "Volt Switch", "Flip Turn", "Parting Shot"}:
        return "Pivot"
    if max(atk, spa) >= 115 and spe >= 90:
        return "Physical Attacker" if atk >= spa else "Special Attacker"
    if hp >= 100 or defense >= 100 or sp_def >= 100:
        if moves & {"Recover", "Roost", "Synthesis", "Protect", "Helping Hand", "Follow Me", "Rage Powder"}:
            return "Defensive / Support"
    return "Balanced / Utility"
