"""One-time migration: wire app.py to the Champions held-item registry.

Run from the repository root:
    python tools/wire_champions_item_selector.py

This migration targets the current app.py structure rather than relying on a
fragile exact whitespace match. It removes the legacy generic item source and
Mega-stone derivation, then imports the Champions-only registry from
``champions.item_data``.
"""

from pathlib import Path
import re


APP_PATH = Path("app.py")

NEW_IMPORT = """from champions.constants import (
    TYPE_COLORS,
    TYPE_SVG_URLS,
    NATURES,
)

from champions.item_data import CHAMPIONS_HELD_ITEMS, MEGA_STONE_MAP"""


def _replace_constants_import(text: str) -> str:
    pattern = re.compile(
        r"from champions\.constants import \(.*?\)\n\nfrom typing import",
        re.DOTALL,
    )
    match = pattern.search(text)
    if not match:
        raise SystemExit(
            "Refusing to patch app.py because the champions.constants import block was not found."
        )

    replacement = NEW_IMPORT + "\n\nfrom typing import"
    return text[: match.start()] + replacement + text[match.end() :]


def _remove_legacy_registry(text: str) -> str:
    mega_pattern = re.compile(
        r"\nMEGA_STONE_MAP = \{name: f\"\{name\.replace\('Mega ', ''\)\}ite\" for name in CUSTOM_MEGAS_DATA\.keys\(\)\}\n"
    )
    if not mega_pattern.search(text):
        raise SystemExit(
            "Refusing to patch app.py because the legacy Mega-stone registry was not found."
        )
    text = mega_pattern.sub("\n", text, count=1)

    item_pattern = re.compile(
        r"\nCHAMPIONS_HELD_ITEMS = sorted\(list\(set\(BASE_HELD_ITEMS \+ list\(MEGA_STONE_MAP\.values\(\)\)\)\)\)"
    )
    if not item_pattern.search(text):
        raise SystemExit(
            "Refusing to patch app.py because the legacy held-item registry was not found."
        )
    return item_pattern.sub("", text, count=1)


def main() -> None:
    if not APP_PATH.exists():
        raise SystemExit("app.py was not found. Run this from the repository root.")

    text = APP_PATH.read_text(encoding="utf-8")

    if "from champions.item_data import CHAMPIONS_HELD_ITEMS, MEGA_STONE_MAP" in text:
        print("Item selector is already wired to champions.item_data; nothing to do.")
        return

    updated = _replace_constants_import(text)
    updated = _remove_legacy_registry(updated)

    APP_PATH.write_text(updated, encoding="utf-8")
    print("Wired app.py to champions.item_data successfully.")
    print("Next: run the item-selector validation commands from the assistant message.")


if __name__ == "__main__":
    main()
