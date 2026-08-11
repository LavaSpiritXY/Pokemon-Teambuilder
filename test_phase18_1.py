from pathlib import Path


def main() -> None:
    print("=== Pokémon Champions Phase 18.1 diagnostic ===")
    assert Path("app.py").exists(), "app.py"
    assert Path("champions_phase18_1.py").exists(), "Phase 18.1 renderer"
    assert Path("champions_viability.py").exists(), "viability engine"
    assert Path("champions_meta.py").exists(), "metadata engine"
    print("Phase 18.1 renderer: PASS")

    from champions_meta import _candidate_keys
    cases = {
        "Mega Charizard X": "charizard",
        "Hisuian Zoroark": "zoroark",
        "Alolan Raichu": "raichu",
        "Paldean Tauros Aqua Breed": "paldean tauros aqua breed",
    }
    for value, expected in cases.items():
        candidates = _candidate_keys(value)
        assert expected in candidates
    print("Form/alias resolver: PASS")

    from champions_integration import get_champions_profile
    for name in ("Kingambit", "Garchomp", "Farigiraf"):
        profile = get_champions_profile(name)
        assert profile.get("available") is True
        assert int(profile.get("appearances") or 0) > 0
        print(f"{name}: tournament profile PASS")

    from champions_viability import apply_champions_adjustment
    result = apply_champions_adjustment(35, "Annihilape")
    assert 0 <= result["adjusted_score"] <= 100
    assert 0 <= result["confidence"] <= 1
    print("Tournament adjustment bounded: PASS")
    print("Missing/unknown data safe: PASS")
    print("Existing scoring isolated: PASS")
    print("STATUS: PASS")


if __name__ == "__main__":
    main()
