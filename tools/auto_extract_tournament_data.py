from pathlib import Path
import re

APP = Path("app.py")
MODULE = Path("champions/tournament_data.py")


def extract_function(text, name):
    match = re.search(rf"(?ms)^def {re.escape(name)}\s*\(.*?(?=^def |^# -----------------------------------------------------------------------------|\Z)", text)
    if not match:
        raise RuntimeError(f"Could not find {name} in app.py")
    return match.group(0).rstrip()


def remove_function(text, name):
    pattern = rf"(?ms)^def {re.escape(name)}\s*\(.*?(?=^def |^# -----------------------------------------------------------------------------|\Z)"
    updated, count = re.subn(pattern, "", text, count=1)
    if count != 1:
        raise RuntimeError(f"Could not remove {name} from app.py")
    return updated


def main():
    text = APP.read_text(encoding="utf-8")

    function_names = [
        "import_champions_tournament",
        "calculate_tournament_metrics",
        "get_tournament_partners",
    ]

    extracted = [extract_function(text, name) for name in function_names]

    module_text = '''from champions.constants import CURRENT_REGULATION\nfrom champions.move_data import get_champions_species_key\nfrom champions.roster_data import display_name_for_species_key\n\n\nCHAMPIONS_META_DB = {}\n\n\n'''
    module_text += "\n\n".join(extracted) + "\n"
    MODULE.write_text(module_text, encoding="utf-8")

    updated = text

    # The tournament database now belongs to champions.tournament_data.
    updated, count = re.subn(r"(?m)^CHAMPIONS_META_DB = \{\}\s*\n", "", updated, count=1)
    if count != 1:
        raise RuntimeError("CHAMPIONS_META_DB definition was not found")

    for name in function_names:
        updated = remove_function(updated, name)

    import_block = (
        "from champions.tournament_data import (\n"
        "    CHAMPIONS_META_DB,\n"
        "    import_champions_tournament,\n"
        "    calculate_tournament_metrics,\n"
        "    get_tournament_partners,\n"
        ")\n"
    )

    anchor = "from champions.meta_engine import ("
    if "from champions.tournament_data import (" not in updated:
        if anchor not in updated:
            raise RuntimeError("Could not find meta_engine import anchor")
        updated = updated.replace(anchor, import_block + "\n" + anchor, 1)

    # Clean up the empty section left by the removed tournament engine block.
    updated = re.sub(
        r"\n# -----------------------------------------------------------------------------\n# 3\. META-GATED CHECKS, COUNTERS & SYNERGY\n# -----------------------------------------------------------------------------\n\s*\n# -----------------------------------------------------------------------------\n# 0\. COMPETITIVE META EVALUATION ENGINE & DATA MODELS\n# -----------------------------------------------------------------------------\n\s*\n",
        "\n",
        updated,
        count=1,
    )

    APP.write_text(updated, encoding="utf-8")
    print("Tournament data extraction completed successfully.")


if __name__ == "__main__":
    main()
