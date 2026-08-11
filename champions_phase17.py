"""Phase 17: visually consistent Champions profile presentation.

This module is intentionally isolated from app.py. It provides a reusable
Streamlit renderer that can replace the Phase 15 tournament diagnostic panel
without changing the existing viability engine.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List

import streamlit as st

from champions_integration import get_champions_profile


_CSS = """
<style>
.champions17-wrap { margin: 0.25rem 0 1.25rem 0; }
.champions17-title { font-size: 1.05rem; font-weight: 700; margin-bottom: .2rem; }
.champions17-subtitle { color: rgba(128,128,128,.95); font-size: .84rem; margin-bottom: .8rem; }
.champions17-card { border: 1px solid rgba(128,128,128,.22); border-radius: 12px; padding: 14px 16px; margin-bottom: 10px; background: rgba(128,128,128,.045); }
.champions17-value { font-size: 1.25rem; font-weight: 700; line-height: 1.1; }
.champions17-label { font-size: .75rem; color: rgba(128,128,128,.95); margin-top: 4px; }
.champions17-partner { display:flex; justify-content:space-between; gap:12px; padding:9px 0; border-bottom:1px solid rgba(128,128,128,.15); }
.champions17-partner:last-child { border-bottom:0; }
.champions17-name { font-weight:600; }
.champions17-detail { font-size:.78rem; color:rgba(128,128,128,.95); text-align:right; }
</style>
"""


def _pct(value: Any) -> str:
    return "—" if value is None else f"{float(value) * 100:.1f}%"


def _partner_name(value: Any) -> str:
    return str(value or "Unknown").replace("-", " ").title()


def render_champions_profile_v2(pokemon_name: str) -> bool:
    """Render a compact Champions profile using the app's neutral card style.

    Returns True when a profile was rendered and False when tournament data is
    unavailable. No viability score is changed here.
    """
    profile: Dict[str, Any] = get_champions_profile(pokemon_name)
    if not profile.get("available"):
        return False

    st.markdown(_CSS, unsafe_allow_html=True)
    st.markdown('<div class="champions17-wrap">', unsafe_allow_html=True)
    st.markdown("<div class='champions17-title'>Champions Tournament Profile</div>", unsafe_allow_html=True)
    st.markdown(
        "<div class='champions17-subtitle'>Observed competitive results from the collected Champions tournament dataset</div>",
        unsafe_allow_html=True,
    )

    cols = st.columns(4)
    metrics = [
        ("Team appearances", int(profile.get("appearances") or 0)),
        ("Win rate", _pct(profile.get("win_rate"))),
        ("Top-cut rate", _pct(profile.get("top_cut_rate"))),
        ("Recent win rate", _pct(profile.get("recent_win_rate"))),
    ]
    for col, (label, value) in zip(cols, metrics):
        with col:
            st.markdown(
                f"<div class='champions17-card'><div class='champions17-value'>{value}</div>"
                f"<div class='champions17-label'>{label}</div></div>",
                unsafe_allow_html=True,
            )

    partners: Iterable[Dict[str, Any]] = profile.get("partners") or []
    partners = list(partners)[:5]
    if partners:
        st.markdown("**Common tournament partners**")
        rows: List[str] = []
        for partner in partners:
            name = _partner_name(partner.get("pokemon"))
            teams = int(partner.get("teams_together") or 0)
            shared = _pct(partner.get("shared_win_rate"))
            rows.append(
                f"<div class='champions17-partner'><span class='champions17-name'>{name}</span>"
                f"<span class='champions17-detail'>{teams} teams together · {shared} shared win rate</span></div>"
            )
        st.markdown(
            "<div class='champions17-card'>" + "".join(rows) + "</div>",
            unsafe_allow_html=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)
    return True
