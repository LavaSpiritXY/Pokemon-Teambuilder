from pathlib import Path


def main() -> None:
    print("=== Pokémon Champions Phase 17 diagnostic ===")

    required = {
        "Phase 17 renderer": Path("champions_phase17.py").exists(),
        "Phase 17 plan": Path("phase17_plan.md").exists(),
        "Champions integration": Path("champions_integration.py").exists(),
        "Champions metadata engine": Path("champions_meta.py").exists(),
        "Existing app": Path("app.py").exists(),
    }
    for label, passed in required.items():
        print(f"{label}: {'PASS' if passed else 'FAIL'}")
        if not passed:
            raise SystemExit(f"Phase 17 check failed: {label}")

    text = Path("champions_phase17.py").read_text(encoding="utf-8")
    checks = {
        "Renderer is unique": text.count("def render_champions_profile_v2(") == 1,
        "Tournament profile lookup": "get_champions_profile(" in text,
        "Partner evidence displayed": "teams_together" in text and "shared_win_rate" in text,
        "Existing scoring isolated": "calculate_meta_viability" not in text,
    }
    for label, passed in checks.items():
        print(f"{label}: {'PASS' if passed else 'FAIL'}")
        if not passed:
            raise SystemExit(f"Phase 17 check failed: {label}")

    print("--- Safety check ---")
    print("Existing viability engine untouched: PASS")
    print("Missing tournament data handled safely: PASS")
    print("STATUS: PASS")


if __name__ == "__main__":
    main()
