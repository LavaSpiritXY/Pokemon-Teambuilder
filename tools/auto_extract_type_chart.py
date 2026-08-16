from pathlib import Path

APP = Path("app.py")


def main():
    text = APP.read_text(encoding="utf-8")
    start = text.find("TYPE_ORDER = list(TYPE_COLORS)\n")
    end = text.find("@strlit.cache_data(ttl=86400, show_spinner=False)\ndef get_type_relationships", start)

    if start == -1 or end == -1:
        print("Type chart helpers already extracted or markers not found.")
        return

    text = text[:start] + text[end:]

    import_line = (
        "from champions.type_chart import (\n"
        "    get_type_defense_summary,\n"
        "    get_offensive_type_summary,\n"
        "    format_type_multiplier,\n"
        "    render_type_chips,\n"
        ")\n"
    )
    anchor = "from champions.tournament_data import (\n"
    if import_line not in text:
        text = text.replace(anchor, import_line + "\n" + anchor, 1)

    APP.write_text(text, encoding="utf-8")
    print("Type chart helpers extracted successfully.")


if __name__ == "__main__":
    main()
