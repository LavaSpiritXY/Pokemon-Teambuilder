from pathlib import Path

APP = Path("app.py")
IMPORT_ANCHOR = "import pandas as pd\n"
IMPORT_INSERT = "from champions_phase17 import render_champions_profile_v2\n"
CALL_ANCHORS = (
    "render_champions_tournament_profile(slot_name)",
    "render_champions_profile_v2(slot_name)",
)


def replace_once(text: str, anchor: str, replacement: str, label: str) -> str:
    count = text.count(anchor)
    if count != 1:
        raise RuntimeError(
            f"Phase 17 patch anchor '{label}' expected once, found {count}."
        )
    return text.replace(anchor, replacement, 1)


def main() -> None:
    if not APP.exists():
        raise SystemExit(f"Could not find {APP}")

    text = APP.read_text(encoding="utf-8")

    if "from champions_phase17 import render_champions_profile_v2" not in text:
        text = replace_once(
            text,
            IMPORT_ANCHOR,
            IMPORT_ANCHOR + IMPORT_INSERT,
            "Phase 17 integration import",
        )

    if "render_champions_profile_v2(slot_name)" in text:
        print("Phase 17 renderer call already present; no call change needed.")
    else:
        text = replace_once(
            text,
            "render_champions_tournament_profile(slot_name)",
            "render_champions_profile_v2(slot_name)",
            "Phase 17 UI call",
        )

    APP.write_text(text, encoding="utf-8")
    print("Phase 17 patch applied successfully to app.py")
    print("Existing viability scoring and metadata engines were not modified.")


if __name__ == "__main__":
    main()
