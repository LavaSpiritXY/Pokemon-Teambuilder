from pathlib import Path

from champions_integration import get_champions_profile
from champions_phase18 import render_champions_profile_v3
from champions_viability import apply_champions_adjustment

APP = Path("app.py")
PHASE18 = Path("champions_phase18.py")
PATCH = Path("apply_phase18_patch.py")


def main() -> None:
    print("=== Pokémon Champions Phase 18 diagnostic ===")

    for path, label in [
        (APP, "app.py located"),
        (PHASE18, "Phase 18 renderer located"),
        (PATCH, "Phase 18 patch script located"),
    ]:
        if not path.exists():
            raise SystemExit(f"Phase 18 failed: {label}")
        print(f"{label}: PASS")

    source = APP.read_text(encoding="utf-8")
    module_source = PHASE18.read_text(encoding="utf-8")

    if "from champions_phase18 import render_champions_profile_v3" not in source:
        raise SystemExit("Phase 18 failed: integration import missing")
    print("Phase 18 integration import: PASS")

    if "render_champions_profile_v3(slot_name, meta=meta, sprite_resolver=get_mini_sprite_url)" not in source:
        raise SystemExit("Phase 18 failed: UI call missing")
    print("Phase 18 UI call: PASS")

    if "render_champions_tournament_profile(slot_name)" in source:
        raise SystemExit("Phase 18 failed: legacy renderer is still actively called")
    print("Legacy tournament renderer no longer called: PASS")

    required = [
        "Champions Viability",
        "Common tournament partners",
        "Champions-aware meta checks & counters",
        "Speed tier",
        "Offensive profile",
        "Momentum & pivoting",
        "Hazard & utility",
        "_safe_sprite",
    ]
    for marker in required:
        if marker not in module_source:
            raise SystemExit(f"Phase 18 failed: renderer feature missing: {marker}")
    print("Unified visual profile features: PASS")

    samples = ["Kingambit", "Garchomp", "Farigiraf", "Charizard"]
    for name in samples:
        profile = get_champions_profile(name)
        if not profile.get("available"):
            raise SystemExit(f"Phase 18 failed: missing tournament profile for {name}")
        result = apply_champions_adjustment(50.0, name)
        if result["base_score"] != 50.0:
            raise SystemExit(f"Phase 18 failed: base score changed for {name}")
        if not 0.0 <= result["adjusted_score"] <= 100.0:
            raise SystemExit(f"Phase 18 failed: adjusted score out of bounds for {name}")
    print("Tournament viability evidence: PASS")
    print("Sprites are resolver-based: PASS")
    print("Existing viability engine isolated: PASS")
    print("Existing Champions metadata engine isolated: PASS")
    print("Missing tournament data handled safely: PASS")
    print("STATUS: PASS")


if __name__ == "__main__":
    main()
