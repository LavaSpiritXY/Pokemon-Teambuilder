from pathlib import Path

APP = Path("app.py")


def main():
    text = APP.read_text(encoding="utf-8")

    start = text.find("@strlit.cache_data(ttl=86400, show_spinner=False)\ndef fetch_smogon_usage_stats")
    if start == -1:
        print("Smogon fetch function not found; nothing changed.")
        return

    end = text.find("@strlit.cache_data(\n    ttl=3600,\n    show_spinner=False\n)\ndef get_cached_meta_candidate", start)
    if end == -1:
        print("Smogon block end not found; nothing changed.")
        return

    text = text[:start] + text[end:]

    old_import = "from champions.meta_viability import (\n    CHAMPIONS_META_DATA,\n    SMOGON_USAGE_DB,\n    calculate_meta_viability,\n    get_smogon_stats_for,\n)"
    new_import = "from champions.meta_viability import CHAMPIONS_META_DATA, calculate_meta_viability\nfrom champions.smogon_data import fetch_smogon_usage_stats, get_smogon_stats_for, set_smogon_usage_db"
    if old_import in text:
        text = text.replace(old_import, new_import, 1)

    marker = "SMOGON_USAGE_DB = fetch_smogon_usage_stats()\n"
    if marker not in text:
        anchor = "# Fallback Smogon Usage Database\n"
        replacement = anchor + "SMOGON_USAGE_DB = fetch_smogon_usage_stats(display_name_for_move)\nset_smogon_usage_db(SMOGON_USAGE_DB)\n"
        text = text.replace(anchor, replacement, 1)

    APP.write_text(text, encoding="utf-8")
    print("Smogon data extraction completed.")


if __name__ == "__main__":
    main()
