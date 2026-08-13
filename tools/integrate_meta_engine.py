from pathlib import Path

APP = Path("app.py")
START_TOKEN = "@dataclass\nclass MoveProfile:"
END_TOKEN = "# -----------------------------------------------------------------------------\n# 1. CONFIG & VISUAL STYLING"
IMPORT_BLOCK = "from champions.meta_engine import (\n    MoveProfile,\n    MonMetaProfile,\n    TeamEvaluator,\n    build_meta_profiles_from_data,\n    create_move_profile,\n)\n"


def main() -> None:
    text = APP.read_text(encoding="utf-8")

    if "from champions.meta_engine import (" not in text:
        anchor = "from champions.constants import ("
        start = text.index(anchor)
        end = text.index(")\n", start) + 2
        text = text[:end] + "\n" + IMPORT_BLOCK + text[end:]

    if START_TOKEN not in text:
        if "from champions.meta_engine import (" in text:
            print("Meta engine is already integrated; nothing to do.")
            return
        raise SystemExit("Meta engine block was not found; refusing to modify app.py.")

    start = text.index(START_TOKEN)
    end = text.index(END_TOKEN, start)

    # CHAMPIONS_META_DB sits immediately before the dataclass block and remains
    # in app.py because it is runtime state rather than part of the engine.
    text = text[:start] + text[end:]

    APP.write_text(text, encoding="utf-8")
    print("Integrated champions.meta_engine into app.py")


if __name__ == "__main__":
    main()
