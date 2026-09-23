from champions.registry import (
    get_species,
    get_species_key_by_display_name,
)


def canonical_species_key(name):
    """
    Convert a Pokémon/form name into the stable Champions history key.

    The generated registry owns form naming and canonical keys; this function
    only provides a generic fallback for an unseen key before the next sync.
    """
    if not name:
        return ""

    text = str(name).strip()
    if not text:
        return ""

    direct = get_species(text.casefold())
    if direct.get("canonical_key"):
        return str(direct["canonical_key"])

    generated = get_species_key_by_display_name(text)
    if generated:
        return generated

    lowered = text.casefold().replace("’", "").replace("'", "")
    lowered = lowered.replace("_", "-")
    lowered = lowered.replace("♀", "f").replace("♂", "m")
    lowered = lowered.replace(".", "")
    lowered = " ".join(lowered.split())

    if lowered.startswith("mega "):
        lowered = lowered[5:].strip()
        parts = lowered.split()
        if parts and parts[-1] in {"x", "y", "z"}:
            return f"{'-'.join(parts[:-1])}-{parts[-1]}"
        return "-".join(parts)

    return "-".join(lowered.split())
