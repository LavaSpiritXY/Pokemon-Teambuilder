from pathlib import Path

PATH = Path("champions/team_analyzer_ui.py")

IMPORT_LINE = "from champions.team_recommendations_ui import render_team_add_recommendations\n"
CALL_LINE = "    render_team_add_recommendations(active)\n"

# Team Snapshot is the stable section immediately after Functional Toolkit and
# before Field Control in the current analyzer layout. Recommendations belong
# between those sections so they remain visually tied to the team analysis.
ANCHOR = '    st.markdown("<div style=\'font-size:20px;font-weight:900;margin:16px 0 10px;color:#f0f6fc;\'>📌 Team Snapshot</div>", unsafe_allow_html=True)\n'


def main() -> None:
    text = PATH.read_text(encoding="utf-8")

    if IMPORT_LINE not in text:
        marker = "from champions.team_analyzer import TeamAnalyzer, build_team_analyzer_input\n"
        if marker not in text:
            raise RuntimeError("TeamAnalyzer import marker not found")
        text = text.replace(marker, marker + IMPORT_LINE, 1)

    if CALL_LINE not in text:
        if ANCHOR not in text:
            raise RuntimeError("Team Snapshot anchor not found")
        text = text.replace(ANCHOR, CALL_LINE + "\n" + ANCHOR, 1)

    PATH.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
