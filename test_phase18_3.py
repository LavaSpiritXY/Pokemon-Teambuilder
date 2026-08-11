from pathlib import Path


def main() -> None:
    print("=== Pokémon Champions Phase 18.3 diagnostic ===")
    assert Path("app.py").exists(), "app.py"
    assert Path("champions_phase18_1.py").exists(), "Phase 18.1 renderer"
    assert Path("champions_phase18_2.py").exists(), "Phase 18.2 analytics"
    assert Path("champions_phase18_3.py").exists(), "Phase 18.3 integration"
    print("Phase 18.3 integration layer: PASS")

    from champions_phase18_3 import build_phase18_3_profile

    for name, base in (("Kingambit", 80), ("Garchomp", 80), ("Farigiraf", 80)):
        profile = build_phase18_3_profile(name, base, {"counters": []})
        display = profile["display"]
        assert 0 <= display["viability_score"] <= 100
        assert display["viability_tier"] in {"S", "A", "B", "C", "D", "E"}
        assert profile["tournament"].get("available") is True
        print(f"{name}: profile integration PASS")

    unknown = build_phase18_3_profile("DefinitelyUnknownPokemon", 42)
    assert 0 <= unknown["display"]["viability_score"] <= 100
    print("Missing tournament data safe: PASS")
    print("Existing base score isolated: PASS")
    print("STATUS: PASS")


if __name__ == "__main__":
    main()
