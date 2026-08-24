from pathlib import Path


PATH = Path("champions/team_analyzer_ui.py")


def main() -> None:
    text = PATH.read_text(encoding="utf-8")

    # Compact, readable move cards using the same type system as the main move selector.
    start = text.index("def _move_card(move: str) -> str:")
    end = text.index("\ndef _coverage_count_card", start)
    helpers = '''def _move_card(move: str) -> str:
    """Compact move card using the same type colour/icon system as the teambuilder."""
    display_name = _display_move_name(move)
    if not display_name:
        return ""
    move_type = _type_for_move(display_name)
    background = TYPE_COLORS.get(move_type, "#555")
    icon = TYPE_SVG_URLS.get(move_type, "")
    icon_html = f'<img src="{icon}" width="18" height="18" style="filter: brightness(0) invert(1);" />' if icon else ""
    return (
        '<div style="display:inline-flex;align-items:center;justify-content:space-between;gap:8px;'
        'width:118px;min-height:42px;padding:7px 9px;margin:4px 9px 5px 0;border-radius:10px;'
        'background:' + background + ';color:white;box-sizing:border-box;box-shadow:0 4px 10px rgba(0,0,0,0.25);vertical-align:top;">'
        f'<span style="min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-weight:850;font-size:13px;line-height:1.1;">{display_name}</span>'
        '<span style="display:flex;align-items:center;gap:4px;flex:0 0 auto;font-size:9px;font-weight:900;">'
        f'{icon_html}<span>{str(move_type).upper()}</span></span>'
        '</div>'
    )


def _move_cards(values, *, max_items: int = 6) -> None:
    values = list(values or [])
    if not values:
        st.caption("Not detected")
        return
    st.markdown("".join(_move_card(value) for value in values[:max_items]), unsafe_allow_html=True)


def _weather_pill(value: str) -> str:
    display = " ".join(str(value or "").replace("-", " ").split()).title()
    palette = {
        "Sun": ("#e87922", "#fff7ed"),
        "Rain": ("#3b82f6", "#eff6ff"),
        "Sand": ("#a8873b", "#fff8df"),
        "Snow": ("#69b8d8", "#effcff"),
        "Hail": ("#69b8d8", "#effcff"),
    }
    background, text_colour = palette.get(display, ("#64748b", "#f8fafc"))
    return f'<span style="display:inline-flex;align-items:center;justify-content:center;min-width:105px;height:38px;padding:0 12px;margin:4px 9px 5px 0;border-radius:11px;background:{background};color:{text_colour};font-weight:900;font-size:13px;box-shadow:0 4px 12px rgba(0,0,0,0.22);">☁️ {display}</span>'


def _terrain_pill(value: str) -> str:
    display = " ".join(str(value or "").replace("-", " ").split()).title()
    type_for_terrain = {"Electric Terrain": "Electric", "Grassy Terrain": "Grass", "Misty Terrain": "Fairy", "Psychic Terrain": "Psychic"}
    terrain_type = type_for_terrain.get(display, "Psychic")
    background = TYPE_COLORS.get(terrain_type, "#777")
    icon = TYPE_SVG_URLS.get(terrain_type, "")
    icon_html = f'<img src="{icon}" width="18" height="18" style="filter: brightness(0) invert(1);" />' if icon else ""
    return f'<span style="display:inline-flex;align-items:center;justify-content:center;gap:7px;min-width:140px;height:38px;padding:0 12px;margin:4px 9px 5px 0;border-radius:11px;background:{background};color:white;font-weight:900;font-size:13px;box-shadow:0 4px 12px rgba(0,0,0,0.22);">{icon_html}{display}</span>'


def _tool_pills(values, kind: str = "tool") -> None:
    values = list(values or [])
    if not values:
        st.caption("Not detected")
        return
    if kind == "weather":
        html = "".join(_weather_pill(value) for value in values[:6])
    elif kind == "terrain":
        html = "".join(_terrain_pill(value) for value in values[:6])
    else:
        html = "".join(f'<span style="display:inline-flex;align-items:center;justify-content:center;min-width:105px;height:38px;padding:0 11px;margin:4px 9px 5px 0;border-radius:11px;background:rgba(255,255,255,0.09);border:1px solid rgba(255,255,255,0.16);color:#f0f6fc;font-weight:850;font-size:13px;">{" ".join(str(value).replace("-", " ").split()).title()}</span>' for value in values[:6])
    st.markdown(html, unsafe_allow_html=True)


def _analyzer_type_chips(values, multipliers=None) -> None:
    values = list(values or [])
    if not values:
        st.caption("None")
        return
    multipliers = multipliers or {}
    cards = []
    for type_name in values:
        t = str(type_name).title()
        background = TYPE_COLORS.get(t, "#777")
        icon = TYPE_SVG_URLS.get(t, "")
        icon_html = f'<img src="{icon}" width="20" height="20" style="filter: brightness(0) invert(1);" />' if icon else ""
        mult = multipliers.get(t)
        suffix = f'<span style="font-size:12px;font-weight:900;opacity:.95;">×{mult:g}</span>' if isinstance(mult, (int, float)) and mult != 1 else ""
        cards.append(f'<span style="display:inline-flex;align-items:center;justify-content:space-between;gap:7px;min-width:112px;height:40px;padding:0 11px;margin:5px 10px 5px 0;border-radius:11px;background:{background};color:white;font-weight:900;font-size:13px;box-sizing:border-box;box-shadow:0 3px 9px rgba(0,0,0,0.20);">{icon_html}<span style="flex:1;text-align:left;">{t}</span>{suffix}</span>')
    st.markdown("".join(cards), unsafe_allow_html=True)


'''
    text = text[:start] + helpers + text[end:]

    replacements = {
        'st.markdown("### 📊 Performance Profile")': 'st.markdown("<div style=\'font-size:20px;font-weight:900;margin:6px 0 12px;color:#f0f6fc;\'>📊 Performance Profile</div>", unsafe_allow_html=True)',
        'st.markdown("### 🧩 Functional Toolkit")': 'st.markdown("<div style=\'font-size:20px;font-weight:900;margin:14px 0 12px;color:#f0f6fc;\'>🧩 Functional Toolkit</div>", unsafe_allow_html=True)',
        'st.markdown("### 🔍 Coverage Snapshot")': 'st.markdown("<div style=\'font-size:20px;font-weight:900;margin:14px 0 12px;color:#f0f6fc;\'>🔍 Coverage Snapshot</div>", unsafe_allow_html=True)',
        'st.markdown("### 🧠 Team Verdict")': 'st.markdown("<div style=\'font-size:20px;font-weight:900;margin:14px 0 12px;color:#f0f6fc;\'>🧠 Team Verdict</div>", unsafe_allow_html=True)',
        'st.markdown("#### ✅ Strengths")': 'st.markdown("<div style=\'font-size:16px;font-weight:900;margin-bottom:8px;color:#f0f6fc;\'>✅ Strengths</div>", unsafe_allow_html=True)',
        'st.markdown("#### ⚠️ Things to watch")': 'st.markdown("<div style=\'font-size:16px;font-weight:900;margin-bottom:8px;color:#f0f6fc;\'>⚠️ Things to watch</div>", unsafe_allow_html=True)',
        'toolkit_cols = st.columns(3)': 'toolkit_cols = st.columns(2)',
        'with toolkit_cols[index % 3]:': 'with toolkit_cols[index % 2]:',
    }
    for old, new in replacements.items():
        text = text.replace(old, new)

    old_block = '''            if renderer == "moves":\n                _move_cards(values)\n            else:\n                _tool_pills(values)'''
    new_block = '''            if renderer == "moves":\n                _move_cards(values)\n            elif label == "Weather":\n                _tool_pills(values, "weather")\n            elif label == "Terrain":\n                _tool_pills(values, "terrain")\n            else:\n                _tool_pills(values)'''
    text = text.replace(old_block, new_block)

    replacements = {
        'st.html(render_type_chips(defensive["uncovered_types"], {t: 2.0 for t in defensive["uncovered_types"]}))': '_analyzer_type_chips(defensive["uncovered_types"], {t: 2.0 for t in defensive["uncovered_types"]})',
        'st.html(render_type_chips(defensive["covered_types"], {t: 1.0 for t in defensive["covered_types"]}))': '_analyzer_type_chips(defensive["covered_types"], {t: 1.0 for t in defensive["covered_types"]})',
        'st.html(render_type_chips(offensive["quad_coverage"], {t: 4.0 for t in offensive["quad_coverage"]}))': '_analyzer_type_chips(offensive["quad_coverage"], {t: 4.0 for t in offensive["quad_coverage"]})',
        'st.html(render_type_chips(sorted(duplicates), {t: float(c) for t, c in duplicates.items()}))': '_analyzer_type_chips(sorted(duplicates), {t: float(c) for t, c in duplicates.items()})',
        'st.html(render_type_chips([t for t, _ in resistance_types], {t: float(c) for t, c in resistance_types}))': '_analyzer_type_chips([t for t, _ in resistance_types], {t: float(c) for t, c in resistance_types})',
        'st.html(render_type_chips(offensive["covered_types"], {t: float(offensive["best_multipliers"].get(t, 2.0)) for t in offensive["covered_types"]}))': '_analyzer_type_chips(offensive["covered_types"], {t: float(offensive["best_multipliers"].get(t, 2.0)) for t in offensive["covered_types"]})',
        'st.html(render_type_chips(offensive["uncovered_types"], {t: 1.0 for t in offensive["uncovered_types"]}))': '_analyzer_type_chips(offensive["uncovered_types"], {t: 1.0 for t in offensive["uncovered_types"]})',
    }
    for old, new in replacements.items():
        text = text.replace(old, new)

    PATH.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
