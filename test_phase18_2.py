from champions_phase18_2 import build_phase18_2_profile, rank_meta_checks, resolve_tournament_identity


def main() -> None:
    print("=== Pokémon Champions Phase 18.2 diagnostic ===")

    cases = {
        "Mega Charizard X": "charizard",
        "Hisuian Zoroark": "zoroark",
        "Alolan Raichu": "raichu",
        "Paldean Tauros Aqua Breed": "paldean tauros aqua breed",
    }
    for name, expected in cases.items():
        identity = resolve_tournament_identity(name)
        assert expected in identity["candidates"], (name, identity["candidates"])
    print("Form-aware tournament identity: PASS")

    for name in ("Kingambit", "Garchomp", "Farigiraf"):
        profile = build_phase18_2_profile(name, 60, {"counters": [], "speed_tier": "Fast"})
        assert profile["tournament"]["available"] is True
        assert 0 <= profile["viability"]["adjusted_score"] <= 100
        assert 0 <= profile["viability"]["evidence_confidence"] <= 1
        print(f"{name}: tournament analytics PASS")

    checks = rank_meta_checks(
        "Kingambit",
        [{"pokemon": "Garchomp"}, {"pokemon": "Farigiraf"}, {"pokemon": "Charizard"}],
    )
    assert all("relevance_score" in row for row in checks)
    assert all(0 <= row["confidence"] <= 1 for row in checks)
    print("Evidence-ranked checks: PASS")

    missing = build_phase18_2_profile("Definitely Unknownmon", 35, {"counters": []})
    assert missing["tournament"]["available"] is False
    assert missing["viability"]["adjusted_score"] == 35
    print("Missing tournament data safe: PASS")
    print("Existing base score isolated: PASS")
    print("STATUS: PASS")


if __name__ == "__main__":
    main()
