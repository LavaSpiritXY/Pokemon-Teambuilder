from champions.registry import (
    get_species,
    get_species_by_canonical_key,
    get_species_by_display_name,
)


def canonical_species_key(name):
    """Return the generated Champions canonical key for a species/form."""
    if not name:
        return ""

    text = str(name).strip()
    if not text:
        return ""

    direct = get_species(text.casefold())
    if direct.get("canonical_key"):
        return str(direct["canonical_key"])

    generated = get_species_by_canonical_key(text)
    if generated.get("canonical_key"):
        return str(generated["canonical_key"])

    generated = get_species_by_display_name(text)
    if generated:
        return str(generated.get("canonical_key") or "")

    # Deterministic compatibility fallback for historical keys that predate
    # the generated registry. This intentionally contains no form-specific
    # rules, so new forms never require another alias branch.
    lowered = (
        text.casefold()
        .replace("’", "")
        .replace("'", "")
        .replace("♀", "f")
        .replace("♂", "m")
        .replace("_", "-")
        .replace(".", "")
    )
    return "-".join(lowered.split())
