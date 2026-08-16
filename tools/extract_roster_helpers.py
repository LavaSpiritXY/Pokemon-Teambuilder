from pathlib import Path

APP = Path("app.py")
ROSTER = Path("champions/roster_data.py")
POKEMON = Path("champions/pokemon_data.py")


def main():
    app = APP.read_text(encoding="utf-8")
    roster = ROSTER.read_text(encoding="utf-8")
    pokemon = POKEMON.read_text(encoding="utf-8")

    start = app.find("def get_clean_api_name(mon_name):")
    end = app.find("def get_champion_moves_for(mon_name):", start)
    if start != -1 and end != -1:
        block = app[start:end].rstrip() + "\n\n"
        if "def get_clean_api_name(mon_name):" not in roster:
            roster += "\n\n" + block
        app = app[:start] + app[end:]

    start = app.find("def get_champion_moves_for(mon_name):")
    end = app.find("TYPE_ORDER = list(TYPE_COLORS)", start)
    if start != -1 and end != -1:
        block = app[start:end].rstrip() + "\n\n"
        if "def get_champion_moves_for(mon_name):" not in pokemon:
            pokemon += "\n\n" + block
        app = app[:start] + app[end:]

    import_line = "    get_clean_api_name,\n    get_base_api_name,\n"
    anchor = "    display_name_for_species_key,\n"
    if "get_clean_api_name," not in app:
        if anchor not in app:
            raise SystemExit("Could not find roster_data import block in app.py")
        app = app.replace(anchor, anchor + import_line, 1)

    pokemon_import = "\nfrom champions.pokemon_data import (\n    get_champion_moves_for,\n    fetch_pokemon_details,\n    get_mini_sprite_url,\n)\n"
    if "from champions.pokemon_data import" not in app:
        anchor = "from champions.tournament_data import ("
        if anchor not in app:
            raise SystemExit("Could not find import anchor for pokemon_data")
        app = app.replace(anchor, pokemon_import + "\n" + anchor, 1)

    APP.write_text(app, encoding="utf-8")
    ROSTER.write_text(roster.rstrip() + "\n", encoding="utf-8")
    POKEMON.write_text(pokemon.rstrip() + "\n", encoding="utf-8")
    print("Roster and Pokémon data extraction completed.")


if __name__ == "__main__":
    main()
