from __future__ import annotations

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
APP = ROOT / "app.py"
UI = ROOT / "champions_phase18_6_ui.py"
PROFILE = ROOT / "champions_phase18_5.py"
COUNTERS = ROOT / "champions_phase18_4.py"


def replace_once(text: str, pattern: str, replacement: str, label: str, flags: int = 0) -> str:
    new, count = re.subn(pattern, replacement, text, count=1, flags=flags)
    if count != 1:
        raise RuntimeError(f"{label}: expected 1 match, found {count}; no write made to that file")
    return new


def patch_ui_module() -> None:
    text = UI.read_text(encoding="utf-8")

    # Add split renderers so the controls can live in the left Pokémon column
    # while the graph gets the full right set column.
    if "def render_dynamic_stat_controls(" not in text:
        text += '''\n\n\ndef render_dynamic_stat_controls(\n    slot_index: int,\n    pokemon_name: str,\n    nature: str,\n) -> Dict[str, int]:\n    """Render the single authoritative Champions SP slider editor."""\n    st.markdown(\n        "<div class='ch186-card'><div class='ch186-title'>🎯 EV Training</div>"\n        "<div class='ch186-sub'>Each stat: 0–32 · Team total: 0–66.</div></div>",\n        unsafe_allow_html=True,\n    )\n    slot = st.session_state.team_slots[slot_index]\n    values = _sanitize(slot)\n    species_key = f"stat_sp_species_{slot_index}"\n    if st.session_state.get(species_key) != pokemon_name:\n        for _, key in _STAT_KEYS:\n            st.session_state[f"stat_sp_slider_{slot_index}_{key}"] = values[key]\n        st.session_state[species_key] = pokemon_name\n    else:\n        for _, key in _STAT_KEYS:\n            widget_key = f"stat_sp_slider_{slot_index}_{key}"\n            if widget_key not in st.session_state:\n                st.session_state[widget_key] = values[key]\n\n    for label, key in _STAT_KEYS:\n        st.slider(\n            f"{label} EVs",\n            min_value=0,\n            max_value=32,\n            value=values[key],\n            step=1,\n            key=f"stat_sp_slider_{slot_index}_{key}",\n            on_change=_sync_slider,\n            args=(slot_index, key),\n        )\n        current = int(st.session_state.team_slots[slot_index].get("evs", {}).get(key, 0) or 0)\n        st.caption(f"{current}/32")\n\n    values = _sanitize(slot)\n    total = sum(values.values())\n    notice_key = f"stat_sp_limit_notice_{slot_index}"\n    if st.session_state.pop(notice_key, False):\n        st.warning("EV limit reached: maximum 32 in one stat and 66 total.")\n    st.caption(f"Champions SP: {total}/66 total · maximum 32 per stat")\n    return values\n\n\ndef render_dynamic_stat_graph(\n    slot_index: int,\n    pokemon_name: str,\n    base_stats: Optional[Mapping[str, Any]],\n    nature: str,\n) -> Dict[str, int]:\n    """Render the live stat graph from the same session-state values as the sliders."""\n    slot = st.session_state.team_slots[slot_index]\n    values = _sanitize(slot)\n    boosted, lowered = _nature_effect(nature)\n    total = sum(values.values())\n\n    st.markdown(\n        f"<div class='ch186-card'><div class='ch186-title'>📊 Dynamic Stat Training</div>"\n        f"<div class='ch186-sub'>Live totals · {total}/66 EVs allocated · {html.escape(str(nature))}</div></div>",\n        unsafe_allow_html=True,\n    )\n\n    rows = []\n    for label, key in _STAT_KEYS:\n        base = _base_stat(base_stats, key)\n        ev = values[key]\n        pre_nature = base + ev\n        multiplier = 1.10 if key == boosted else (0.90 if key == lowered else 1.0)\n        adjusted = round(pre_nature * multiplier)\n        width = max(0.5, min(100.0, adjusted / 180.0 * 100.0))\n        colour = _stat_colour(adjusted)\n        badge = (\n            "<span class='ch186-badge ch186-up'>+ Nature</span>"\n            if key == boosted\n            else "<span class='ch186-badge ch186-down'>− Nature</span>"\n            if key == lowered\n            else "<span class='ch186-badge ch186-neutral'>Neutral</span>"\n        )\n        max_class = "ch186-max" if ev == 32 else ""\n        rows.append(\n            f"<div class='ch186-row {max_class}'>"\n            f"<div><div class='ch186-name'>{label} {badge}</div>"\n            f"<div class='ch186-note'>Base {base} · EV +{ev} · Nature ×{multiplier:.2f}</div></div>"\n            f"<div class='ch186-track'><div class='ch186-fill' style='width:{width:.1f}%;background:{colour}'></div></div>"\n            f"<div class='ch186-total'>{adjusted}</div></div>"\n        )\n\n    st.markdown("<div class='ch186-card'>" + "".join(rows) + "</div>", unsafe_allow_html=True)\n    return values\n'''

    # The bar colour must represent the final displayed stat, not the base stat.
    text = replace_once(
        text,
        r"def _stat_colour\(value: int\) -> str:\n    ratio = max\(0\.0, min\(1\.0, value / 180\.0\)\)\n    return f\"hsl\(\{ratio \* 120:\.0f\}, 72%, 48%\)\"",
        "def _stat_colour(value: int) -> str:\n    ratio = max(0.0, min(1.0, float(value) / 180.0))\n    return f\"hsl({ratio * 120:.0f}, 72%, 48%)\"",
        "dynamic stat colour",
    )

    UI.write_text(text, encoding="utf-8")


def patch_app() -> None:
    text = APP.read_text(encoding="utf-8")

    if "from champions_phase18_6_ui import render_dynamic_stat_controls, render_dynamic_stat_graph" not in text:
        text = replace_once(
            text,
            r"from champions_phase18_5 import render_champions_profile_v6\n",
            "from champions_phase18_5 import render_champions_profile_v6\nfrom champions_phase18_6_ui import render_dynamic_stat_controls, render_dynamic_stat_graph\n",
            "Phase 19 stat UI imports",
        )

    # Remove the duplicate inline number-input editor.
    old_sp = re.compile(
        r"            strlit\.markdown\(\"##### 📊 Champions SP Allocation\"\)\n"
        r".*?"
        r"            strlit\.caption\(f\"Champions SP: \{sum\(current_sp\.values\(\)\)\}/66 total · maximum 32 per stat\"\)\n",
        re.S,
    )
    text, sp_count = old_sp.subn("", text, count=1)
    if sp_count != 1 and "render_dynamic_stat_controls(" not in text:
        raise RuntimeError("Phase 19 could not find the old duplicate SP editor")

    # Put the authoritative sliders immediately below Nature in the left column.
    anchor = '            slot["nature"] = strlit.selectbox("Nature", options=nat_opts, index=nat_idx, key=f"nat_{i}")\n'
    if "render_dynamic_stat_controls(" not in text:
        if anchor not in text:
            raise RuntimeError("Phase 19 could not find the Nature control anchor")
        text = text.replace(
            anchor,
            anchor
            + '            render_dynamic_stat_controls(\n'
            + '                slot_index=i,\n'
            + '                pokemon_name=slot_name,\n'
            + '                nature=slot.get("nature", "Hardy"),\n'
            + '            )\n\n',
            1,
        )

    # The graph belongs in the right set column and reads the exact same values.
    if "render_dynamic_stat_graph(" not in text:
        stale = '            render_base_stats_bubble(mon_data.get("stats"))\n'
        if stale not in text:
            raise RuntimeError("Phase 19 could not find the old graph renderer")
        text = text.replace(
            stale,
            '            render_dynamic_stat_graph(\n'
            '                slot_index=i,\n'
            '                pokemon_name=slot_name,\n'
            '                base_stats=mon_data.get("stats"),\n'
            '                nature=slot.get("nature", "Hardy"),\n'
            '            )\n',
            1,
        )

    APP.write_text(text, encoding="utf-8")


def patch_profile() -> None:
    text = PROFILE.read_text(encoding="utf-8")
    if "ch185-section'>📊 Base Stats" not in text:
        return
    pattern = re.compile(
        r"    st\.markdown\(\"<div class='ch185-section'>📊 Base Stats.*?"
        r"    st\.markdown\(\"</div>\", unsafe_allow_html=True\)\n"
        r"    return True",
        re.S,
    )
    text = replace_once(
        text,
        pattern.pattern,
        '    st.markdown("</div>", unsafe_allow_html=True)\n    return True',
        "Phase 18.5 duplicate stat panel removal",
        flags=re.S,
    )
    PROFILE.write_text(text, encoding="utf-8")


def patch_counter_ranking() -> None:
    text = COUNTERS.read_text(encoding="utf-8")
    old = '''    rows: List[Dict[str, Any]] = []\n    seen = set()\n    for candidate in existing_candidates or []:\n        if isinstance(candidate, (tuple, list)):\n            name = candidate[0] if candidate else ""\n        elif isinstance(candidate, dict):\n            name = candidate.get("pokemon") or candidate.get("name") or ""\n        else:\n            name = candidate\n        name = str(name or "").strip()\n        key = " ".join(name.lower().split())\n        if not name or key in seen or key == " ".join(pokemon_name.lower().split()):\n            continue\n        seen.add(key)\n        profile = resolved_tournament_profile(name)\n        if not profile.get("available") or int(profile.get("appearances") or 0) <= 0:\n            continue\n        appearances = int(profile.get("appearances") or 0)\n        win = float(profile.get("win_rate") or 0.5)\n        relevance = min(1.0, appearances / 500.0) * 0.55 + max(0.0, min(1.0, win)) * 0.45\n        rows.append({"pokemon": name, "appearances": appearances, "win_rate": win, "relevance_score": relevance})\n    rows.sort(key=lambda x: (x["relevance_score"], x["appearances"]), reverse=True)\n    return rows[: max(0, int(limit))]'''
    new = '''    rows: List[Dict[str, Any]] = []\n    fallback_rows: List[Dict[str, Any]] = []\n    seen = set()\n    for candidate in existing_candidates or []:\n        if isinstance(candidate, (tuple, list)):\n            name = candidate[0] if candidate else ""\n        elif isinstance(candidate, dict):\n            name = candidate.get("pokemon") or candidate.get("name") or ""\n        else:\n            name = candidate\n        name = str(name or "").strip()\n        key = " ".join(name.lower().split())\n        if not name or key in seen or key == " ".join(pokemon_name.lower().split()):\n            continue\n        seen.add(key)\n        profile = resolved_tournament_profile(name)\n        if profile.get("available") and int(profile.get("appearances") or 0) > 0:\n            appearances = int(profile.get("appearances") or 0)\n            win = max(0.0, min(1.0, float(profile.get("win_rate") or 0.5)))\n            cut = max(0.0, min(1.0, float(profile.get("top_cut_rate") or 0.0)))\n            relevance = min(1.0, appearances / 500.0) * 0.45 + cut * 0.30 + win * 0.25\n            rows.append({"pokemon": name, "appearances": appearances, "win_rate": win, "relevance_score": relevance})\n        else:\n            # A strategic counter is still useful when the tournament archive has\n            # no record for that candidate. Keep it visible rather than rendering\n            # an empty counters panel.\n            fallback_rows.append({"pokemon": name, "appearances": 0, "win_rate": 0.0, "relevance_score": 0.0})\n    rows.sort(key=lambda x: (x["relevance_score"], x["appearances"]), reverse=True)\n    ordered = rows + fallback_rows\n    return ordered[: max(0, int(limit))]'''
    if old in text:
        text = text.replace(old, new, 1)
    COUNTERS.write_text(text, encoding="utf-8")


def tournament_index_body() -> str:
    return '''def _tournament_index(tournament: Mapping[str, Any]) -> float:\n    """Convert Champions evidence into a calibrated 0–100 dominance index.\n\n    Usage is saturated rather than divided by an arbitrary 1,000-event ceiling;\n    top-cut performance is measured against the 12.5% baseline expected from a\n    Top-8 cut; recent results are used when the archive provides them.\n    """\n    appearances = max(0.0, float(tournament.get("appearances") or 0))\n    weighted_appearances = max(0.0, float(tournament.get("weighted_appearances") or tournament.get("recent_usage_weight") or appearances))\n    usage_signal = 1.0 - math.exp(-weighted_appearances / 300.0)\n\n    win = max(0.0, min(1.0, float(tournament.get("win_rate") or 0.0)))\n    recent_win = max(0.0, min(1.0, float(tournament.get("recent_win_rate") if tournament.get("recent_win_rate") is not None else win)))\n    cut_raw = float(tournament.get("top_cut_rate") or 0.0)\n    recent_cut_raw = float(tournament.get("recent_top_cut_rate") or 0.0)\n    cut = max(0.0, min(1.0, cut_raw if cut_raw > 0 else recent_cut_raw))\n\n    # If explicit top-cut data is absent, use average placement as a transparent\n    # quality proxy instead of inventing a 20% top-cut rate.\n    if cut <= 0.0:\n        avg_placement = tournament.get("average_placement")\n        try:\n            avg = float(avg_placement)\n        except (TypeError, ValueError):\n            avg = 0.0\n        if avg > 0:\n            cut = max(0.0, min(1.0, 1.0 / (1.0 + max(0.0, avg - 1.0) / 8.0))) * 0.5\n\n    # 12.5% is the neutral Top-8 baseline. Values above it receive a real\n    # competitive lift; values below it are not treated as a total failure.\n    cut_signal = max(0.0, min(1.0, 0.5 + (cut - 0.125) / 0.25))\n    win_signal = max(0.0, min(1.0, 0.5 + (win - 0.5) * 2.0))\n    recent_signal = max(0.0, min(1.0, 0.5 + (recent_win - 0.5) * 2.0))\n\n    index = (\n        usage_signal * 0.45\n        + cut_signal * 0.25\n        + win_signal * 0.20\n        + recent_signal * 0.10\n    ) * 100.0\n    return round(max(0.0, min(100.0, index)), 1)\n'''


def patch_profile_index() -> None:
    text = PROFILE.read_text(encoding="utf-8")
    pattern = r"def _tournament_index\(tournament: Mapping\[str, Any\]\) -> float:.*?\n\ndef _display_score"
    replacement = tournament_index_body() + "\n\ndef _display_score"
    text = replace_once(text, pattern, replacement, "Phase 19 tournament index", flags=re.S)
    PROFILE.write_text(text, encoding="utf-8")


def patch_phase18_4_index() -> None:
    text = COUNTERS.read_text(encoding="utf-8")
    pattern = r"def tournament_display_score\(base_score: float, pokemon_name: str\) -> Dict\[str, Any\]:.*?\n\ndef display_tier"
    replacement = '''def tournament_display_score(base_score: float, pokemon_name: str) -> Dict[str, Any]:\n    """Create the same calibrated tournament score used by Phase 19 profile UI."""\n    profile = resolved_tournament_profile(pokemon_name)\n    base = _clamp(float(base_score))\n    if not profile.get("available"):\n        return {"score": round(base, 1), "base": round(base, 1), "tournament": None, "confidence": 0.0}\n\n    appearances = max(0.0, float(profile.get("appearances") or 0))\n    weighted_appearances = max(0.0, float(profile.get("weighted_appearances") or profile.get("recent_usage_weight") or appearances))\n    usage_signal = 1.0 - math.exp(-weighted_appearances / 300.0)\n    win = max(0.0, min(1.0, float(profile.get("win_rate") or 0.0)))\n    recent_win = max(0.0, min(1.0, float(profile.get("recent_win_rate") if profile.get("recent_win_rate") is not None else win)))\n    cut = max(0.0, min(1.0, float(profile.get("top_cut_rate") or profile.get("recent_top_cut_rate") or 0.0)))\n    if cut <= 0.0:\n        try:\n            avg = float(profile.get("average_placement") or 0.0)\n        except (TypeError, ValueError):\n            avg = 0.0\n        if avg > 0:\n            cut = max(0.0, min(1.0, 1.0 / (1.0 + max(0.0, avg - 1.0) / 8.0))) * 0.5\n    cut_signal = max(0.0, min(1.0, 0.5 + (cut - 0.125) / 0.25))\n    win_signal = max(0.0, min(1.0, 0.5 + (win - 0.5) * 2.0))\n    recent_signal = max(0.0, min(1.0, 0.5 + (recent_win - 0.5) * 2.0))\n    tournament_score = (usage_signal * 0.45 + cut_signal * 0.25 + win_signal * 0.20 + recent_signal * 0.10) * 100.0\n    confidence = min(1.0, math.sqrt(appearances / 100.0)) if appearances else 0.0\n    blend = 0.80 * confidence\n    score = (base * (1.0 - blend)) + (tournament_score * blend)\n    return {"score": round(_clamp(score), 1), "base": round(base, 1), "tournament": round(_clamp(tournament_score), 1), "confidence": confidence, "appearances": int(appearances)}\n\n\ndef display_tier'''
    text = replace_once(text, pattern, replacement, "Phase 19 tournament display score", flags=re.S)
    COUNTERS.write_text(text, encoding="utf-8")


def main() -> None:
    for path in (APP, UI, PROFILE, COUNTERS):
        if not path.exists():
            raise RuntimeError(f"Missing expected file: {path.name}")

    patch_ui_module()
    patch_app()
    patch_profile()
    patch_counter_ranking()
    patch_profile_index()
    patch_phase18_4_index()

    print("Phase 19 UI + tournament/meta fixes applied.")
    print("- Sliders are the single authoritative SP editor.")
    print("- Sliders sit under Held Item/Nature in the left column.")
    print("- The stat graph reads the same session-state values and colours by final stat.")
    print("- Duplicate Phase 18.5 stat panels are removed.")
    print("- Counter ranking keeps strategic counters visible when tournament evidence is absent.")
    print("- Tournament index uses weighted appearances, real top-cut data, recent performance, and placement fallback.")


if __name__ == "__main__":
    main()
