"""Streamlit presentation layer for the whole-team analyzer."""
from __future__ import annotations

from typing import Any, Dict, Mapping

import streamlit as st

from champions.pokemon_data import fetch_pokemon_details
from champions.team_analyzer import TeamAnalyzer, build_team_analyzer_input


def _active_slots(team_slots: Mapping[int, Mapping[str, Any]]):
    return [
        (idx, slot)
        for idx, slot in sorted(team_slots.items())
        if isinstance(slot, Mapping)
        and slot.get("name")
        and slot.get("name") != "-- Choose a Pokémon --"
    ]


def _bar(label: str, value: float, width: float = 100.0):
    value = max(0.0, min(width, float(value)))
    st.markdown(f"**{label}** · {value:.0f}/100")
    st.progress(int(value), text="")


def render_team_analyzer_main(team_slots: Mapping[int, Mapping[str, Any]]) -> None:
    """Render the whole-team analyzer as a full-width Team Overview dashboard."""
    active = _active_slots(team_slots)

    st.markdown("## 🧠 Whole-Team Analysis")
    st.caption("A team-wide view of defensive coverage, offensive pressure, competitive functions, redundancy, and archetype structure.")

    if not active:
        st.info("Add Pokémon to your team slots to unlock the full team analysis.")
        return

    details: Dict[str, Dict[str, Any]] = {}
    with st.spinner("Analyzing team…"):
        for _, slot in active:
            name = str(slot["name"])
            details[name] = fetch_pokemon_details(name)

    team = build_team_analyzer_input(active, details)
    result = TeamAnalyzer(team).analyze()

    hero_cols = st.columns([1.35, 1, 1, 1, 1])
    with hero_cols[0]:
        st.metric("Overall Team Score", f"{result['overall_score']:.1f} / 100", result["grade"])
    with hero_cols[1]:
        st.metric("🛡️ Defense", f"{result['defensive']['score']:.0f}")
    with hero_cols[2]:
        st.metric("⚔️ Offense", f"{result['offensive']['score']:.0f}")
    with hero_cols[3]:
        st.metric("🎛️ Function", f"{result['functions']['score']:.0f}")
    with hero_cols[4]:
        st.metric("♻️ Variety", f"{result['redundancy']['score']:.0f}")

    st.divider()

    graph_cols = st.columns(2)
    with graph_cols[0]:
        st.markdown("### 📊 Team Performance Profile")
        _bar("Defensive Coverage", result["defensive"]["score"])
        _bar("Offensive Coverage", result["offensive"]["score"])
        _bar("Competitive Function", result["functions"]["score"])
        _bar("Team Variety", result["redundancy"]["score"])
        _bar("Archetype Coherence", result["archetypes"]["score"])

    with graph_cols[1]:
        st.markdown("### 🧩 Functional Toolkit")
        function_rows = [
            ("Speed Control", bool(result["functions"]["speed_control"])),
            ("Priority", bool(result["functions"]["priority_moves"])),
            ("Weather", bool(result["functions"]["weather"])),
            ("Terrain", bool(result["functions"]["terrain"])),
            ("Disruption", bool(result["functions"]["disruption"])),
            ("Support", bool(result["functions"]["support"])),
            ("Setup", bool(result["functions"]["setup"])),
        ]
        for label, present in function_rows:
            status = "✅ Present" if present else "— Not detected"
            st.markdown(f"**{label}**  ")
            st.caption(status)
            st.divider()

    st.markdown("### 🔍 Coverage Overview")
    coverage_cols = st.columns(3)
    defensive = result["defensive"]
    offensive = result["offensive"]
    with coverage_cols[0]:
        st.markdown("**🛡️ Defensive answers**")
        st.metric("Types covered", f"{len(defensive['covered_types'])} / 18")
        if defensive["best_answers"]:
            st.caption("Multiple answers: " + ", ".join(defensive["best_answers"]))
        else:
            st.caption("No attacking type currently has multiple clear defensive answers.")

    with coverage_cols[1]:
        st.markdown("**⚔️ Offensive pressure**")
        st.metric("Super-effective coverage", f"{len(offensive['covered_types'])} / 18")
        if offensive["quad_coverage"]:
            st.caption("4× pressure: " + ", ".join(offensive["quad_coverage"]))
        else:
            st.caption("No 4× offensive coverage detected from the current moves.")

    with coverage_cols[2]:
        st.markdown("**⚠️ Major gaps**")
        if defensive["severe_gaps"]:
            for gap in defensive["severe_gaps"][:6]:
                st.markdown(f"⚠️ **{gap}**")
        else:
            st.success("No severe team-wide defensive gap detected.")

    st.markdown("### 🧠 What this team is doing")
    summary = result["summary"]
    strengths_col, concerns_col = st.columns(2)
    with strengths_col:
        st.markdown("#### ✅ Strengths")
        if summary["strengths"]:
            for item in summary["strengths"][:6]:
                st.markdown(f"✅ {item}")
        else:
            st.caption("No standout strengths detected yet.")
    with concerns_col:
        st.markdown("#### ⚠️ Watch-outs")
        if summary["concerns"]:
            for item in summary["concerns"][:6]:
                st.markdown(f"⚠️ {item}")
        else:
            st.success("No major concerns detected yet.")

    with st.expander("📋 Detailed coverage data", expanded=False):
        detail_cols = st.columns(2)
        with detail_cols[0]:
            st.markdown("**Defensively uncovered**")
            st.write(", ".join(defensive["uncovered_types"]) or "None")
            st.markdown("**Resistance counts**")
            st.write(defensive["resistance_counts"] or "None")
            st.markdown("**Immunity counts**")
            st.write(defensive["immunity_counts"] or "None")
        with detail_cols[1]:
            st.markdown("**Offensively uncovered**")
            st.write(", ".join(offensive["uncovered_types"]) or "None")
            st.markdown("**Move-type usage**")
            st.write(offensive["move_type_counts"] or "None")
            st.markdown("**Archetypes detected**")
            st.write(result["archetypes"]["counts"] or "None")


def render_team_analyzer_sidebar(team_slots: Mapping[int, Mapping[str, Any]]) -> None:
    """Legacy compatibility wrapper; the analyzer now belongs in Team Overview."""
    return
