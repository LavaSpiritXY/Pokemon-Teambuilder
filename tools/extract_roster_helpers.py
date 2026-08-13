from pathlib import Path

APP = Path("app.py")
ROSTER = Path("champions/roster_data.py")


def main():
    app = APP.read_text(encoding="utf-8")
    roster = ROSTER.read_text(encoding="utf-8")

    start = app.find("def get_clean_api_name(mon_name):")
    end = app.find("def get_champion_moves_for(mon_name):", start)
    if start == -1 or end == -1:
        raise SystemExit("Could not locate roster helper block in app.py")

    block = app[start:end].rstrip() + "\n\n"

    if "def get_clean_api_name(mon_name):" not in roster:
        roster += "\n\n" + block

    app = app[:start] + app[end:]

    import_line = "    get_clean_api_name,\n    get_base_api_name,\n"
    anchor = "    display_name_for_species_key,\n"
    if "get_clean_api_name," not in app:
        if anchor not in app:
            raise SystemExit("Could not find roster_data import block in app.py")
        app = app.replace(anchor, anchor + import_line, 1)

    APP.write_text(app, encoding="utf-8")
    ROSTER.write_text(roster.rstrip() + "\n", encoding="utf-8")
    print("Roster helper extraction completed.")


if __name__ == "__main__":
    main()
