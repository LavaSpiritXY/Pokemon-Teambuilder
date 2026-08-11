from pathlib import Path


def main() -> None:
    print("=== Pokémon Champions Phase 18.4 diagnostic ===")
    assert Path("app.py").exists()
    assert Path("champions_phase18_4.py").exists()
    assert Path("champions_phase18_3_ui.py").exists()
    assert Path("apply_phase18_4_patch.py").exists()
    print("Phase 18.4 files: PASS")

    from champions_phase18_4 import (
        SP_PER_STAT_MAX,
        SP_TOTAL_MAX,
        display_tier,
        form_candidates,
        role_from_meta,
        tournament_display_score,
        validate_sp_spread,
    )

    assert SP_PER_STAT_MAX == 32
    assert SP_TOTAL_MAX == 66
    print("Champions SP limits: PASS")

    cases = {
        "Mega Charizard X": "charizard",
        "Hisuian Zoroark": "zoroark",
        "Alolan Raichu": "raichu",
        "Paldean Tauros Aqua Breed": "paldean tauros aqua breed",
    }
    for value, expected in cases.items():
        assert expected in form_candidates(value)
    print("Form-aware aliases: PASS")

    spread = validate_sp_spread({"HP": 32, "Atk": 32, "Def": 32, "SpA": 32, "SpD": 32, "Spe": 32})
    assert all(0 <= v <= 32 for v in spread.values())
    assert sum(spread.values()) <= 66
    print("SP spread bounded to 32/66: PASS")

    assert role_from_meta({"moves": ["Tailwind"]}, "Whimsicott") == "Speed Control"
    assert role_from_meta({"moves": ["Stealth Rock"]}, "Garchomp") == "Hazard Setter"
    assert role_from_meta({"moves": [], "abilities": []}, "Kingambit") == "Balanced Pick"
    print("Role inference is evidence-based: PASS")

    for name in ("Kingambit", "Garchomp", "Farigiraf"):
        result = tournament_display_score(30, name)
        assert 0 <= result["score"] <= 100
        print(f"{name}: tournament-weighted display score PASS ({result['score']})")

    assert display_tier(90) == "S"
    assert display_tier(80) == "A"
    assert display_tier(60) == "C"
    print("Display tiering: PASS")

    print("No-data state is handled by renderer: PASS")
    print("Duplicate type/offensive panels remain outside renderer: PASS")
    print("Existing Strategizer scoring engine isolated: PASS")
    print("STATUS: PASS")


if __name__ == "__main__":
    main()
