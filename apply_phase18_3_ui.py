from pathlib import Path
import re

APP = Path("app.py")


def main() -> None:
    text = APP.read_text(encoding="utf-8")
    if "from champions_phase18_3_ui import render_champions_profile_v5" in text:
        print("Phase 18.3 UI integration already applied.")
        return

    pattern = re.compile(
        r"            meta = compute_meta_analytics\(slot_name\).*?"
        r"            \"\"\"\)\n\n        with col_set:",
        re.S,
    )
    match = pattern.search(text)
    if not match:
        raise RuntimeError("Could not find the Phase 18.2 profile HTML block in app.py.")

    replacement = '''            meta = compute_meta_analytics(slot_name)\n            type_summary = get_type_defense_summary(mon_data["types"])\n            offensive_summary = get_offensive_type_summary(mon_data["types"])\n\n            if not meta:\n                meta = {\n                    "tier": "Unknown",\n                    "viability": "0 / 100",\n                    "teammates": [],\n                    "counters": [],\n                    "speed_tier": "N/A",\n                    "momentum_rating": "N/A",\n                    "hazard_utility": "N/A",\n                    "offensive_profile": "N/A",\n                }\n\n            from champions_phase18_3_ui import render_champions_profile_v5\n            render_champions_profile_v5(\n                slot_name,\n                meta=meta,\n                sprite_resolver=get_mini_sprite_url,\n                type_summary=type_summary,\n                offensive_summary=offensive_summary,\n            )\n\n        with col_set:'''

    text = text[:match.start()] + replacement + text[match.end():]
    APP.write_text(text, encoding="utf-8")
    print("Phase 18.3 UI integration applied successfully to app.py")
    print("Legacy tournament HTML block removed from the active profile path.")
    print("Existing viability/scoring and Champions metadata engines were not modified.")


if __name__ == "__main__":
    main()
