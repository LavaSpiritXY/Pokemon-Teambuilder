"""Phase 18.3: unified Champions profile UI.

The renderer is intentionally isolated from app.py. It consumes the Phase 18.2
analytics contract and existing app metadata without changing scoring logic.
"""
from __future__ import annotations

import html
from typing import Any, Dict, Iterable, Optional

import streamlit as st

from champions_phase18_3 import build_phase18_3_profile
from champions_integration import get_champions_profile


_CSS = """
<style>
.ch183-wrap{border:1px solid rgba(148,163,184,.30);border-radius:16px;padding:18px 20px 18px;margin:10px 0 20px;background:linear-gradient(180deg,rgba(148,163,184,.08),rgba(148,163,184,.035));box-shadow:0 8px 26px rgba(0,0,0,.08)}
.ch183-head{display:flex;align-items:center;gap:14px;margin-bottom:16px}.ch183-head img{width:70px;height:70px;object-fit:contain}.ch183-title{font-size:1.45rem;font-weight:850;line-height:1.18}.ch183-sub{font-size:.86rem;color:rgba(180,190,205,.82);margin-top:4px}
.ch183-section{font-size:1.08rem;font-weight:800;margin:18px 0 9px}.ch183-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px}.ch183-card{border:1px solid rgba(148,163,184,.24);border-radius:12px;padding:12px 14px;background:rgba(148,163,184,.055)}.ch183-value{font-size:1.22rem;font-weight:800;line-height:1.2}.ch183-label{font-size:.76rem;color:rgba(180,190,205,.82);margin-top:4px}.ch183-note{font-size:.73rem;color:rgba(180,190,205,.65);margin-top:4px}
.ch183-score{font-size:2.05rem;font-weight:900}.ch183-bar{height:8px;border-radius:999px;background:rgba(148,163,184,.17);overflow:hidden;margin-top:8px}.ch183-fill{height:100%;background:linear-gradient(90deg,#6390F0,#7AC74C);border-radius:999px}
.ch183-row{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:9px 2px;border-bottom:1px solid rgba(148,163,184,.14)}.ch183-row:last-child{border-bottom:0}.ch183-entity{display:flex;align-items:center;gap:9px;min-width:0}.ch183-entity img{width:35px;height:35px;object-fit:contain}.ch183-name{font-weight:700}.ch183-detail{font-size:.76rem;color:rgba(180,190,205,.76);text-align:right}.ch183-pill{display:inline-block;padding:5px 9px;border-radius:999px;background:rgba(99,144,240,.13);font-size:.75rem;font-weight:700;margin:2px}.ch183-muted{font-size:.8rem;color:rgba(180,190,205,.65)}
@media(max-width:800px){.ch183-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}
</style>
"""


def _pct(value: Any) -> str:
    try:
        return f"{float(value) * 100:.1f}%"
    except (TypeError, ValueError):
        return "—"


def _pretty(value: Any) -> str:
    return str(value or "N/A").replace("-", " ").title()


def _sprite(name: str, resolver: Any) -> str:
    try:
        return str(resolver(name) or "") if resolver else ""
    except Exception:
        return ""


def _entity(name: str, resolver: Any) -> str:
    safe = html.escape(name)
    url = _sprite(name, resolver)
    image = f"<img src='{html.escape(url, quote=True)}' alt='{safe}'>" if url else ""
    return f"<div class='ch183-entity'>{image}<span class='ch183-name'>{safe}</span></div>"


def _partner_rows(items: Iterable[Dict[str, Any]], resolver: Any) -> str:
    rows = []
    for item in list(items)[:6]:
        name = _pretty(item.get("pokemon"))
        teams = int(item.get("teams_together") or 0)
        rate = _pct(item.get("shared_win_rate"))
        rows.append(f"<div class='ch183-row'>{_entity(name, resolver)}<span class='ch183-detail'>{teams:,} teams · {rate} shared win rate</span></div>")
    return "".join(rows)


def _counter_rows(items: Iterable[Dict[str, Any]], resolver: Any) -> str:
    rows = []
    for item in list(items)[:6]:
        name = _pretty(item.get("pokemon"))
        appearances = int(item.get("appearances") or 0)
        relevance = float(item.get("relevance_score") or 0) * 100
        rows.append(f"<div class='ch183-row'>{_entity(name, resolver)}<span class='ch183-detail'>{appearances:,} appearances · {relevance:.0f} relevance</span></div>")
    return "".join(rows)


def render_champions_profile_v5(
    pokemon_name: str,
    meta: Optional[Dict[str, Any]] = None,
    sprite_resolver: Any = None,
    type_summary: Any = None,
    offensive_summary: Any = None,
) -> bool:
    """Render the single unified Champions profile and return availability."""
    meta = dict(meta or {})
    try:
        base = float(str(meta.get("viability", "0")).split("/")[0].strip())
    except (TypeError, ValueError):
        base = 0.0

    payload = build_phase18_3_profile(pokemon_name, base, meta)
    tournament = payload.get("tournament") or {}
    if not tournament.get("available"):
        return False

    display = payload["display"]
    score = float(display["viability_score"])
    identity = payload.get("identity") or {}
    profile = payload.get("tournament") or {}
    sprite = _sprite(pokemon_name, sprite_resolver)

    st.markdown(_CSS, unsafe_allow_html=True)
    st.markdown("<div class='ch183-wrap'>", unsafe_allow_html=True)

    image = f"<img src='{html.escape(sprite, quote=True)}' alt='{html.escape(pokemon_name)}'>" if sprite else ""
    st.markdown(
        f"<div class='ch183-head'>{image}<div><div class='ch183-title'>🏆 Champions Competitive Profile — {html.escape(_pretty(pokemon_name))}</div><div class='ch183-sub'>Tournament evidence, speed tiering, strategic diagnostics and Champions-aware recommendations</div></div></div>",
        unsafe_allow_html=True,
    )

    cards = [
        ("Viability Index", f"{score:.0f} / 100", f"{display['viability_tier']} · {float(payload['viability'].get('adjustment', 0.0)):+.1f} tournament"),
        ("Team appearances", f"{int(profile.get('appearances') or 0):,}", "Collected tournament teams"),
        ("Win rate", _pct(profile.get("win_rate")), f"Recent {_pct(profile.get('recent_win_rate'))}"),
        ("Top-cut rate", _pct(profile.get("top_cut_rate")), f"Confidence {float(display.get('confidence') or 0):.2f}"),
    ]
    st.markdown("<div class='ch183-grid'>" + "".join(f"<div class='ch183-card'><div class='ch183-value'>{html.escape(v)}</div><div class='ch183-label'>{html.escape(l)}</div><div class='ch183-note'>{html.escape(n)}</div></div>" for l, v, n in cards) + "</div>", unsafe_allow_html=True)

    st.markdown(f"<div class='ch183-card' style='margin-top:10px'><div class='ch183-label'>VIABILITY INDEX</div><div class='ch183-score'>{score:.0f} / 100</div><div class='ch183-bar'><div class='ch183-fill' style='width:{max(0,min(100,score)):.0f}%'></div></div></div>", unsafe_allow_html=True)

    st.markdown("<div class='ch183-section'>Strategic profile</div>", unsafe_allow_html=True)
    strategic = [
        ("Speed tier", payload.get("speed_tier", "N/A")),
        ("Offensive profile", payload.get("offensive_profile", "N/A")),
        ("Momentum & pivoting", payload.get("momentum_rating", "N/A")),
        ("Hazard & utility", payload.get("hazard_utility", "N/A")),
    ]
    st.markdown("<div class='ch183-grid'>" + "".join(f"<div class='ch183-card'><div class='ch183-value' style='font-size:.95rem'>{html.escape(str(v))}</div><div class='ch183-label'>{html.escape(l)}</div></div>" for l, v in strategic) + "</div>", unsafe_allow_html=True)

    partners = payload.get("partners") or []
    if partners:
        st.markdown("<div class='ch183-section'>🤝 Common tournament partners</div>", unsafe_allow_html=True)
        st.markdown("<div class='ch183-card'>" + _partner_rows(partners, sprite_resolver) + "</div>", unsafe_allow_html=True)

    counters = payload.get("counters") or []
    if counters:
        st.markdown("<div class='ch183-section'>🛡️ Champions-aware meta checks & counters</div>", unsafe_allow_html=True)
        st.markdown("<div class='ch183-card'>" + _counter_rows(counters, sprite_resolver) + "</div>", unsafe_allow_html=True)
    else:
        st.markdown("<div class='ch183-section'>🛡️ Champions-aware meta checks & counters</div><div class='ch183-card'><span class='ch183-muted'>No evidence-ranked checks available for this Pokémon.</span></div>", unsafe_allow_html=True)

    if type_summary or offensive_summary:
        st.markdown("<div class='ch183-section'>Type matchup profile</div>", unsafe_allow_html=True)
        if type_summary:
            st.markdown(f"<div class='ch183-card'><div class='ch183-label'>Defensive matchups</div><div style='margin-top:6px'>{html.escape(str(type_summary))}</div></div>", unsafe_allow_html=True)
        if offensive_summary:
            st.markdown(f"<div class='ch183-card' style='margin-top:8px'><div class='ch183-label'>Offensive coverage</div><div style='margin-top:6px'>{html.escape(str(offensive_summary))}</div></div>", unsafe_allow_html=True)

    role = meta.get("recommended_role") or meta.get("role") or infer_role_fallback(meta)
    st.markdown(f"<div class='ch183-card' style='margin-top:10px'><div class='ch183-label'>Recommended team role</div><div class='ch183-value' style='font-size:1rem'>{html.escape(str(role))}</div></div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
    return True


def infer_role_fallback(meta: Dict[str, Any]) -> str:
    return str(meta.get("fallback_role") or "Balanced Pick")
