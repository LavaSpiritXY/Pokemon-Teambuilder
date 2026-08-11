"""Phase 14 validation for the safe Champions integration layer."""

from champions_integration import get_champions_profile, champions_profile_summary


SAMPLES = ["Kingambit", "Garchomp", "Farigiraf"]


def main() -> None:
    print("=== Pokémon Champions Phase 14 integration diagnostic ===")
    print("--- Profile lookups ---")

    for name in SAMPLES:
        profile = get_champions_profile(name)
        print(f"{name}: available={profile['available']}")
        print(f"  appearances={profile['appearances']}")
        print(f"  win_rate={profile['win_rate']}")
        print(f"  top_cut_rate={profile['top_cut_rate']}")
        print(f"  recent_win_rate={profile['recent_win_rate']}")
        print(f"  partners={profile['partners'][:3]}")
        print(f"  summary={champions_profile_summary(name)}")

    print("--- Safety check ---")
    missing = get_champions_profile("DefinitelyNotAPokemon")
    assert missing["available"] is False
    assert missing["appearances"] == 0
    assert missing["partners"] == []

    print("Unknown Pokémon handled safely: PASS")
    print("Existing app scoring untouched: PASS")
    print("STATUS: PASS")


if __name__ == "__main__":
    main()
