from pathlib import Path

APP = Path("app.py")

IMPORT_ANCHOR = "import pandas as pd\n"
IMPORT_INSERT = "from champions_phase18 import render_champions_profile_v3\n"
CALL_ANCHOR = "            render_champions_tournament_profile(slot_name)"
CALL_INSERT = "            render_champions_profile_v3(slot_name, meta=meta, sprite_resolver=get_mini_sprite_url)"


def replace_once(text: str, anchor: str, replacement: str, label: str) -> str:
    count = text.count(anchor)
    if count != 1:
        raise RuntimeError(f"Phase 18 patch anchor '{label}' expected once, found {count}.")
    return text.replace(anchor, replacement, 1)


def main() -> None:
    if not APP.exists():
        raise SystemExit(f"Could not find {APP}")

    text = APP.read_text(encoding="utf-8")

    if "from champions_phase18 import render_champions_profile_v3" in text:
        raise SystemExit("Phase 18 already appears to be applied; no changes made.")

    text = replace_once(text, IMPORT_ANCHOR, IMPORT_ANCHOR + IMPORT_INSERT, "Phase 18 import")
    text = replace_once(text, CALL_ANCHOR, CALL_INSERT, "Phase 18 UI call")

    APP.write_text(text, encoding="utf-8")
    print("Phase 18 patch applied successfully to app.py")
    print("Existing viability/scoring and metadata engines were not modified.")
    print("The legacy Phase 15/17 renderer remains defined but is no longer called.")


if __name__ == "__main__":
    main()
