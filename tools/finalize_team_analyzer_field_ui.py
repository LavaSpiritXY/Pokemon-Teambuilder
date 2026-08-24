from pathlib import Path

UI = Path("champions/team_analyzer_ui.py")
ENGINE = Path("champions/team_analyzer.py")


def main() -> None:
    # --- Engine: expose the actual weather/terrain source move or ability. ---
    text = ENGINE.read_text(encoding="utf-8")
    old = '''        weather = sorted({label for move, label in _WEATHER.items() if move in moves} | {label for ability, label in _WEATHER_ABILITIES.items() if ability in abilities})\n        terrain = sorted({label for move, label in _TERRAIN.items() if move in moves} | {label for ability, label in _TERRAIN_ABILITIES.items() if ability in abilities})\n        disruption = sorted(_display_move_name(move) for move in moves if move in _DISRUPTION)\n'''
    new = '''        weather = sorted({label for move, label in _WEATHER.items() if move in moves} | {label for ability, label in _WEATHER_ABILITIES.items() if ability in abilities})\n        terrain = sorted({label for move, label in _TERRAIN.items() if move in moves} | {label for ability, label in _TERRAIN_ABILITIES.items() if ability in abilities})\n\n        weather_sources = []\n        seen_weather_sources = set()\n        for move in moves:\n            if move in _WEATHER:\n                key = (\"move\", move)\n                if key not in seen_weather_sources:\n                    seen_weather_sources.add(key)\n                    weather_sources.append({\"label\": _display_move_name(move), \"type\": _move_type(move) or \"Normal\"})\n        weather_ability_types = {\n            \"drizzle\": \"Water\", \"primordial sea\": \"Water\",\n            \"drought\": \"Fire\", \"desolate land\": \"Fire\",\n            \"sand stream\": \"Rock\", \"snow warning\": \"Ice\",\n        }\n        for ability in abilities:\n            if ability in _WEATHER_ABILITIES:\n                key = (\"ability\", ability)\n                if key not in seen_weather_sources:\n                    seen_weather_sources.add(key)\n                    weather_sources.append({\"label\": _display_move_name(ability), \"type\": weather_ability_types.get(ability, \"Normal\")})\n\n        terrain_sources = []\n        seen_terrain_sources = set()\n        for move in moves:\n            if move in _TERRAIN:\n                key = (\"move\", move)\n                if key not in seen_terrain_sources:\n                    seen_terrain_sources.add(key)\n                    terrain_type = _TERRAIN[move].replace(\" Terrain\", \"\")\n                    terrain_sources.append({\"label\": _display_move_name(move), \"type\": terrain_type})\n        for ability in abilities:\n            if ability in _TERRAIN_ABILITIES:\n                key = (\"ability\", ability)\n                if key not in seen_terrain_sources:\n                    seen_terrain_sources.add(key)\n                    terrain_type = _TERRAIN_ABILITIES[ability].replace(\" Terrain\", \"\")\n                    terrain_sources.append({\"label\": _display_move_name(ability), \"type\": terrain_type})\n\n        disruption = sorted(_display_move_name(move) for move in moves if move in _DISRUPTION)\n'''
    if old not in text:
        raise RuntimeError("Could not find functional weather/terrain block")
    text = text.replace(old, new, 1)
    old_return = '''            "weather": weather,\n            "terrain": terrain,\n            "disruption": disruption,\n'''
    new_return = '''            "weather": weather,\n            "weather_sources": weather_sources,\n            "terrain": terrain,\n            "terrain_sources": terrain_sources,\n            "disruption": disruption,\n'''
    if old_return not in text:
        raise RuntimeError("Could not find functional result return block")
    text = text.replace(old_return, new_return, 1)
    ENGINE.write_text(text, encoding="utf-8")

    # --- UI: remove the redundant coverage cards entirely and display actual field sources. ---
    text = UI.read_text(encoding="utf-8")

    cov_start = text.find("    coverage_cols = st.columns(3)\n")
    verdict_start = text.find("    st.markdown(\"<div style='font-size:20px;font-weight:900;margin:16px 0 12px;color:#f0f6fc;'>🧠 Team Verdict</div>\", unsafe_allow_html=True)\n")
    if cov_start == -1 or verdict_start == -1 or cov_start >= verdict_start:
        raise RuntimeError("Could not find the redundant coverage-card block")
    text = text[:cov_start] + text[verdict_start:]

    old_weather = '''def _weather_pill(value: str) -> str:\n    display = " ".join(str(value or "").replace("-", " ").split()).title()\n    palette = {\n        "Sun": ("#e87922", "#fff7ed"),\n        "Rain": ("#3b82f6", "#eff6ff"),\n        "Sand": ("#a8873b", "#fff8df"),\n        "Snow": ("#69b8d8", "#effcff"),\n        "Hail": ("#69b8d8", "#effcff"),\n    }\n    background, text_colour = palette.get(display, ("#64748b", "#f8fafc"))\n    return f'<span style="display:inline-flex;align-items:center;justify-content:center;min-width:118px;height:40px;padding:0 13px;margin:6px 10px 6px 0;border-radius:12px;background:{background};color:{text_colour};font-weight:900;font-size:14px;box-shadow:0 4px 12px rgba(0,0,0,0.22);">{display}</span>'\n'''
    new_weather = '''def _weather_pill(source: Mapping[str, Any]) -> str:\n    label = " ".join(str(source.get("label") or "").replace("-", " ").split()).title()\n    weather_type = str(source.get("type") or "Normal").title()\n    background = TYPE_COLORS.get(weather_type, "#64748b")\n    icon = TYPE_SVG_URLS.get(weather_type, "")\n    icon_html = f'<img src="{icon}" width="20" height="20" style="filter: brightness(0) invert(1);" />' if icon else ""\n    return f'<span style="display:inline-flex;align-items:center;justify-content:center;gap:8px;min-width:148px;height:40px;padding:0 13px;margin:6px 10px 6px 0;border-radius:12px;background:{background};color:white;font-weight:900;font-size:14px;box-shadow:0 4px 12px rgba(0,0,0,0.22);">{icon_html}{label}</span>'\n'''
    if old_weather not in text:
        raise RuntimeError("Could not find weather pill helper")
    text = text.replace(old_weather, new_weather, 1)

    old_terrain = '''def _terrain_pill(value: str) -> str:\n    display = " ".join(str(value or "").replace("-", " ").split()).title()\n    type_for_terrain = {"Electric Terrain": "Electric", "Grassy Terrain": "Grass", "Misty Terrain": "Fairy", "Psychic Terrain": "Psychic"}\n    terrain_type = type_for_terrain.get(display, "Psychic")\n    background = TYPE_COLORS.get(terrain_type, "#777")\n    icon = TYPE_SVG_URLS.get(terrain_type, "")\n    icon_html = f'<img src="{icon}" width="18" height="18" style="filter: brightness(0) invert(1);" />' if icon else ""\n    return f'<span style="display:inline-flex;align-items:center;justify-content:center;gap:7px;min-width:150px;height:40px;padding:0 13px;margin:6px 10px 6px 0;border-radius:12px;background:{background};color:white;font-weight:900;font-size:14px;box-shadow:0 4px 12px rgba(0,0,0,0.22);">{icon_html}{display}</span>'\n'''
    new_terrain = '''def _terrain_pill(source: Mapping[str, Any]) -> str:\n    label = " ".join(str(source.get("label") or "").replace("-", " ").split()).title()\n    terrain_type = str(source.get("type") or "Psychic").title()\n    background = TYPE_COLORS.get(terrain_type, "#777")\n    icon = TYPE_SVG_URLS.get(terrain_type, "")\n    icon_html = f'<img src="{icon}" width="20" height="20" style="filter: brightness(0) invert(1);" />' if icon else ""\n    return f'<span style="display:inline-flex;align-items:center;justify-content:center;gap:7px;min-width:150px;height:40px;padding:0 13px;margin:6px 10px 6px 0;border-radius:12px;background:{background};color:white;font-weight:900;font-size:14px;box-shadow:0 4px 12px rgba(0,0,0,0.22);">{icon_html}{label}</span>'\n'''
    if old_terrain not in text:
        raise RuntimeError("Could not find terrain pill helper")
    text = text.replace(old_terrain, new_terrain, 1)

    old_tool = '''def _tool_pills(values, kind: str = "tool") -> None:\n    values = list(values or [])\n    if not values:\n        st.caption("Not detected")\n        return\n    if kind == "weather":\n        html = "".join(_weather_pill(value) for value in values[:6])\n    elif kind == "terrain":\n        html = "".join(_terrain_pill(value) for value in values[:6])\n    else:\n'''
    new_tool = '''def _tool_pills(values, kind: str = "tool") -> None:\n    values = list(values or [])\n    if not values:\n        st.caption("Not detected")\n        return\n    if kind == "weather":\n        html = "".join(_weather_pill(value) for value in values[:6])\n    elif kind == "terrain":\n        html = "".join(_terrain_pill(value) for value in values[:6])\n    else:\n'''
    if old_tool not in text:
        raise RuntimeError("Could not find tool-pill dispatcher")
    text = text.replace(old_tool, new_tool, 1)

    text = text.replace('if functions["weather"]:\n            _tool_pills(functions["weather"], "weather")', 'if functions.get("weather_sources"):\n            _tool_pills(functions["weather_sources"], "weather")', 1)
    text = text.replace('if functions["terrain"]:\n            _tool_pills(functions["terrain"], "terrain")', 'if functions.get("terrain_sources"):\n            _tool_pills(functions["terrain_sources"], "terrain")', 1)

    # The UI is already using the correct top-padding-aware score bar; keep the centered placement.
    UI.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
