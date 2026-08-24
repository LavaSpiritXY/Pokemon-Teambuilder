"""Streamlit presentation for explainable team-add recommendations."""
from __future__ import annotations

from typing import Any, Mapping, Sequence

import streamlit as st

from champions.constants import TYPE_COLORS, TYPE_SVG_URLS
from champions.team_recommendations import recommendation_cache_token, recommend_team_additions


def _type_pill(type_name: str) -> str:
    label = str(type_name).title()
    background = TYPE_COLORS.get(label, "#777")
    icon = TYPE_SVG_URLS.get(label, "")
    icon_html = f'<img src="{icon}" width="16" height="16" style="filter:brightness(0) invert(1);" />' if icon else ""
    return (
        f'<span style="display:inline-flex;align-items:center;gap:5px;padding:4px 8px;'
        f'margin:2px 5px 2px 0;border-radius:9px;background:{background};color:white;'
        f'font-size:11px;font-weight:850;">{icon_html}{label}</span>'
    )


def _reason_pill(text: str) -> str:
    return (
        '<span style="display:inline-flex;align-items:center;padding:5px 9px;margin:3px 5px 3px 0;'
        'border-radius:999px;background:rgba(255,255,255,0.07);'
        'border:1px solid rgba(255,255,255,0.12);color:#dce4ec;'
        'font-size:11px;font-weight:750;line-height:1.2;">'
        f'{text}</span>'
    )


def render_team_add_recommendations(
    active_slots: Sequence[tuple[int, Mapping[str, Any]]],
    *,
    top_n: int = 4,
) -> None:
    """Render the "what should I add?" panel below the core team analysis."""
    if not active_slots or len(active_slots) >= 6:
        return

    team = []
    for _, slot in active_slots:
        team.append(dict(slot))

    st.markdown(
        "<div style='font-size:21px;font-weight:900;margin:18px 0 10px;color:#f0f6fc;'>💡 What should I add?</div>",
        unsafe_allow_html=True,
    )
    st.caption("Candidates are ranked by how much they improve your current team, then refined with tournament relevance.")

    signature = tuple(
        (
            str(member.get("name") or ""),
            tuple(member.get("moves") or []),
            str(member.get("ability") or ""),
            str(member.get("item") or ""),
        )
        for member in team
    )

    @st.cache_data(ttl=1800, show_spinner=False)
    def _cached(signature, history_token):
        current_team = []
        for name, moves, ability, item in signature:
            current_team.append({"name": name, "moves": list(moves), "ability": ability, "item": item})
        return recommend_team_additions(current_team, top_n=top_n)

    with st.spinner("Finding the best additions…"):
        recommendations = _cached(signature, recommendation_cache_token())

    if not recommendations:
        st.info("There isn't enough tournament data yet to produce a confident recommendation for this team.")
        return

    cols = st.columns(min(4, len(recommendations)))
    for index, candidate in enumerate(recommendations):
        with cols[index]:
            with st.container(border=True):
                if candidate.get("sprite"):
                    st.image(candidate["sprite"], width=82)
                st.markdown(f"<div style='font-size:17px;font-weight:900;color:#f0f6fc;'>{candidate['name']}</div>", unsafe_allow_html=True)
                st.markdown("".join(_type_pill(t) for t in candidate.get("types", [])), unsafe_allow_html=True)
                score = candidate.get("score", 0)
                delta = candidate.get("team_delta", 0)
                st.markdown(
                    f"<div style='margin-top:8px;display:flex;align-items:baseline;gap:8px;'>"
                    f"<span style='font-size:26px;font-weight:950;color:#7ac74c;'>+{delta:.1f}</span>"
                    f"<span style='font-size:11px;color:#8b949e;font-weight:750;'>team score improvement</span></div>",
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f"<div style='font-size:11px;color:#8b949e;font-weight:800;margin:4px 0 6px;'>Recommendation strength {score:.0f}/100</div>",
                    unsafe_allow_html=True,
                )
                reasons = candidate.get("reasons") or ["Improves overall team balance"]
                st.markdown("".join(_reason_pill(reason) for reason in reasons), unsafe_allow_html=True)
