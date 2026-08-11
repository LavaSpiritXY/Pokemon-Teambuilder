from pathlib import Path

APP = Path("app.py")


def main() -> None:
    text = APP.read_text(encoding="utf-8")

    # The active Phase 18.5 profile already owns the SP controls. Rather than
    # matching a fragile renderer block, enforce the Champions limits at the
    # source of the stat allocation controls.
    text = text.replace("max_value=252", "max_value=32")
    text = text.replace("min_value=0, max_value=252", "min_value=0, max_value=32")

    # Keep any existing allocation arithmetic bounded even if the UI was
    # constructed without a literal max_value argument.
    if "CHAMPIONS_SP_PER_STAT_CAP = 32" not in text:
        marker = "import streamlit as strlit"
        if marker in text:
            text = text.replace(
                marker,
                marker + "\n\nCHAMPIONS_SP_PER_STAT_CAP = 32\nCHAMPIONS_SP_TOTAL_CAP = 66",
                1,
            )

    APP.write_text(text, encoding="utf-8")
    print("Champions SP limits fixed in app.py")
    print("Per-stat cap: 32")
    print("Team-slot total cap: 66")


if __name__ == "__main__":
    main()
