from pathlib import Path

APP = Path("app.py")
IMPORT_ANCHOR = "from champions_phase18 import render_champions_profile_v3"
INSERT = "\nfrom champions_phase18_1 import render_champions_profile_v4 as _render_champions_profile_v4\nrender_champions_profile_v3 = _render_champions_profile_v4\n"


def main() -> None:
    if not APP.exists():
        raise SystemExit(f"Could not find {APP}")
    text = APP.read_text(encoding="utf-8")
    if "from champions_phase18_1 import render_champions_profile_v4" in text:
        raise SystemExit("Phase 18.1 already appears to be applied; no changes made.")
    if IMPORT_ANCHOR not in text:
        raise SystemExit("Could not find the Phase 18 renderer import in app.py. Run the Phase 18 patch first.")
    text = text.replace(IMPORT_ANCHOR, IMPORT_ANCHOR + INSERT, 1)
    APP.write_text(text, encoding="utf-8")
    print("Phase 18.1 patch applied successfully to app.py")
    print("Existing viability/meta engines were not modified.")
    print("The existing Phase 18 call is redirected to the 18.1 renderer.")


if __name__ == "__main__":
    main()
