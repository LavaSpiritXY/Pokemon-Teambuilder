"""One-time migration: wire app.py to the Champions held-item registry.

Run from the repository root:
    python tools/wire_champions_item_selector.py

The script is intentionally strict: it only performs the exact legacy replacements
we expect and refuses to continue if the source shape has already changed.
"""

from pathlib import Path


APP_PATH = Path("app.py")

OLD_IMPORT = """from champions.constants import (\n    TYPE_COLORS,\n    TYPE_SVG_URLS,\n    NATURES,\n    CUSTOM_MEGAS_DATA,\n    BASE_HELD_ITEMS,\n)"""

NEW_IMPORT = """from champions.constants import (\n    TYPE_COLORS,\n    TYPE_SVG_URLS,\n    NATURES,\n    CUSTOM_MEGAS_DATA,\n)\n\nfrom champions.item_data import CHAMPIONS_HELD_ITEMS, MEGA_STONE_MAP"""

OLD_REGISTRY = '''MEGA_STONE_MAP = {name: f"{name.replace('Mega ', '')}ite" for name in CUSTOM_MEGAS_DATA.keys()}\n\n\n\n\nCHAMPIONS_ALL_FORMS = fetch_pokemon_roster()\n\nCHAMPIONS_HELD_ITEMS = sorted(list(set(BASE_HELD_ITEMS + list(MEGA_STONE_MAP.values()))))'''

NEW_REGISTRY = '''CHAMPIONS_ALL_FORMS = fetch_pokemon_roster()'''


def main() -> None:
    if not APP_PATH.exists():
        raise SystemExit("app.py was not found. Run this from the repository root.")

    text = APP_PATH.read_text(encoding="utf-8")

    if "from champions.item_data import CHAMPIONS_HELD_ITEMS, MEGA_STONE_MAP" in text:
        print("Item selector is already wired to champions.item_data; nothing to do.")
        return

    missing = []
    if OLD_IMPORT not in text:
        missing.append("legacy constants import")
    if OLD_REGISTRY not in text:
        missing.append("legacy held-item registry")
    if missing:
        raise SystemExit(
            "Refusing to patch app.py because the expected legacy code was not found: "
            + ", ".join(missing)
        )

    updated = text.replace(OLD_IMPORT, NEW_IMPORT, 1)
    updated = updated.replace(OLD_REGISTRY, NEW_REGISTRY, 1)

    APP_PATH.write_text(updated, encoding="utf-8")
    print("Wired app.py to champions.item_data successfully.")
    print("Next: run the item-selector validation commands from the assistant message.")


if __name__ == "__main__":
    main()
