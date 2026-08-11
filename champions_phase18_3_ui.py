"""Unified Champions profile UI used by the Phase 18.4 patch.

Display-only: it consumes existing metadata and tournament evidence without
mutating the Strategizer scoring engine.
"""
from __future__ import annotations

import html
from typing import Any, Dict, Iterable, Optional

import streamlit as st

from champions_phase18_4 import build_profile_18_4, rank_counters_with_evidence

_CSS = """
<style>
.ch183-wrap{border:1px solid rgba(148,163,184,.30);border-radius:16px;padding:18px 20px 20px;margin:10px 0 20px;background:linear-gradient(180deg,rgba(148,163,184,.08),rgba(148,163,184,.035));box-shadow:0 8px 26px rgba(0,0,0,.08)}
.ch183-head{display:flex;align-items:center;gap:14px;margin-bottom:16px}.ch183-head img{width:78px;height:78px;object-fit:contain}.ch183-title{font-size:1.52rem;font-weight:850;line-height:1.18}.ch183-sub{font-size:.88rem;color:rgba(180,190,205,.84);margin-top:5px}
.ch183-section{font-size:1.12rem;font-weight:800;margin:19px 0 9px}.ch183-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px}.ch183-card{border:1px solid rgba(148,163,184,.24);border-radius:12px;padding:12px 14px;background:rgba(148,163,184,.055)}.ch183-value{font-size:1.22rem;font-weight:800;line-height:1.2}.ch183-label{font-size:.78rem;color:rgba(180,190,205,.84);margin-top:4px}.ch183-note{font-size:.74rem;color:rgba(180,190,205,.68);margin-top:4px}
.ch183-score{font-size:2.15rem;font-weight:900}.ch183-bar{height:9px;border-radius:999px;background:rgba(148,163,184,.17);overflow:hidden;margin-top:8px}.ch183-fill{height:100%;background:linear-gradient(90deg,#6390F0,#7AC74C);border-radius:999px}
.ch183-row{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:9px 2px;border-bottom:1px solid rgba(148,163,184,.14)}.ch183-row:last-child{border-bottom:0}.ch183-entity{display:flex;align-items:center;gap:10px;min-width:0}.ch183-entity img{width:43px;height:43px;object-fit:contain}.ch183-name{font-weight:700}.ch183-detail{font-size:.77rem;color:rgba(180,190,205,.78);text-align:right}.ch183-muted{font-size:.82rem;color:rgba(180,190,205,.68)}
.ch184-stat-grid{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:8px}.ch184-stat{padding:10px 8px;border-radius:10px;background:rgba(148,163,184,.055);border:1px solid rgba(148,163,184,.18);text-align:center}.ch184-stat-name{font-size:.72rem;color:rgba(180,190,205,.78)}.ch184-stat-value{font-size:1.08rem;font-weight:800;margin-top:3px}.ch184-stat-bar{height:6px;margin-top:6px;border-radius:999px;background:rgba(148,163,184,.16);overflow:hidden}.ch184-stat-fill{height:100%;border-radius:999px;background:linear-gradient(90deg,#6390F0,#7AC74C)}
@media(max-width:800px){.ch183-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.ch184-stat-grid{grid-template-columns:repeat(3,minmax(0,1fr))}}
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
        rows.append(f"<div class='ch183-row'>{_entity(name, resolver)}<span class='ch183-detail'>{appearances:,} appearances · {relevance:.0f} evidence</span></div>")
    return "".join(rows)


def render_base_stats_bubble(stats: Optional[Dict[str, Any]]) -> None:
    """Render the Champions base-stat bubble directly under matchup coverage."""
    st.markdown("<div class='ch183-section'>📊 Base Stats</div>", unsafe_allow_html=True)
    if not stats:
        st.markdown("<div class='ch183-card'><span class='ch183-muted'>Base stats are not available for this form.</span></div>", unsafe_allow_html=True)
        return
    keys = [("hp", "HP"), ("attack", "Atk"), ("defense", "Def"), ("special-attack", "SpA"), ("special-defense", "SpD"), ("speed", "Spe")]
    parts = []
    for key, label in keys:
        raw = stats.get(key, stats.get(label, 0))
        try:
            value = int(raw or 0)
        except (TypeError, ValueError):
            value = 0
        width = max(0, min(100, round(value / 180 * 100)))
        parts.append(f"<div class='ch184-stat'><div class='ch184-stat-name'>{label}</div><div class='ch184-stat-value'>{value}</div><div class='ch184-stat-bar'><div class='ch184-stat-fill' style='width:{width}%'></div></div></div>")
    st.markdown("<div class='ch183-card'><div class='ch184-stat-grid'>" + "".join(parts) + "</div></div>", unsafe_allow_html=True)


def render_champions_profile_v5(
    pokemon_name: str,
    meta: Optional[Dict[str, Any]] = None,
    sprite_resolver: Any = None,
    type_summary: Any = None,
    offensive_summary: Any = None,
    base_stats: Optional[Dict[str, Any]] = None,
) -> bool:
    """Render one unified Champions profile, including a safe no-data state."""
    meta = dict(meta or {})
    try:
        base = float(str(meta.get("viability", "0")).split("/")[0].strip())
    except (TypeError, ValueError):
        base = 0.0

    payload = build_profile_18_4(pokemon_name, base, meta)
    tournament = payload.get("tournament") or {}
    score_data = payload["score"]
    score = float(score_data["score"])
    identity = payload.get("form_candidates") or []
    sprite = _sprite(pokemon_name, sprite_resolver)

    st.markdown(_CSS, unsafe_allow_html=True)
    st.markdown("<div class='ch183-wrap'>", unsafe_allow_html=True)
    image = f"<img src='{html.escape(sprite, quote=True)}' alt='{html.escape(pokemon_name)}'>" if sprite else ""
    st.markdown(f"<div class='ch183-head'>{image}<div><div class='ch183-title'>🏆 Champions Competitive Profile — {html.escape(_pretty(pokemon_name))}</div><div class='ch183-sub'>Tournament evidence, speed tiering, strategic diagnostics and Champions-aware recommendations</div></div></div>", unsafe_allow_html=True)

    if not tournament.get("available"):
        st.markdown("<div class='ch183-card'><div class='ch183-value'>Tournament data unavailable</div><div class='ch183-note'>This Pokémon/form is recognised by the builder, but no collected Champions tournament evidence is currently available. The existing Strategizer score has not been treated as a negative signal.</div></div>", unsafe_allow_html=True)
    else:
        cards = [
            ("Viability Index", f"{score:.0f} / 100", f"{payload['tier']} · {float(score_data.get('tournament') or 0):.0f} tournament evidence"),
            ("Team appearances", f"{int(tournament.get('appearances') or 0):,}", "Collected tournament teams"),
            ("Win rate", _pct(tournament.get("win_rate")), f"Recent {_pct(tournament.get('recent_win_rate'))}"),
            ("Top-cut rate", _pct(tournament.get("top_cut_rate")), f"Confidence {float(score_data.get('confidence') or 0):.2f}"),
        ]
        st.markdown("<div class='ch183-grid'>" + "".join(f"<div class='ch183-card'><div class='ch183-value'>{html.escape(v)}</div><div class='ch183-label'>{html.escape(l)}</div><div class='ch183-note'>{html.escape(n)}</div></div>" for l, v, n in cards) + "</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='ch183-card' style='margin-top:10px'><div class='ch183-label'>VIABILITY INDEX</div><div class='ch183-score'>{score:.0f} / 100</div><div class='ch183-bar'><div class='ch183-fill' style='width:{max(0,min(100,score)):.0f}%'></div></div><div class='ch183-note'>Established score: {score_data['base']:.0f} · tournament evidence: {score_data.get('tournament', 0):.0f}</div></div>", unsafe_allow_html=True)

        st.markdown("<div class='ch183-section'>Strategic profile</div>", unsafe_allow_html=True)
        strategic = [
            ("Speed tier", meta.get("speed_tier", "N/A")),
            ("Offensive profile", meta.get("offensive_profile", "N/A")),
            ("Momentum & pivoting", meta.get("momentum_rating", "N/A")),
            ("Role", payload.get("role", "Balanced Pick")),
        ]
        st.markdown("<div class='ch183-grid'>" + "".join(f"<div class='ch183-card'><div class='ch183-value' style='font-size:.95rem'>{html.escape(str(v))}</div><div class='ch183-label'>{html.escape(l)}</div></div>" for l, v in strategic) + "</div>", unsafe_allow_html=True)

        partners = payload.get("partners") or []
        if partners:
            st.markdown("<div class='ch183-section'>🤝 Common tournament partners</div>", unsafe_allow_html=True)
            st.markdown("<div class='ch183-card'>" + _partner_rows(partners, sprite_resolver) + "</div>", unsafe_allow_html=True)

        counters = rank_counters_with_evidence(pokemon_name, meta.get("counters") or [])
        st.markdown("<div class='ch183-section'>🛡️ Champions-aware meta checks & counters</div>", unsafe_allow_html=True)
        if counters:
            st.markdown("<div class='ch183-card'>" + _counter_rows(counters, sprite_resolver) + "</div>", unsafe_allow_html=True)
        else:
            st.markdown("<div class='ch183-card'><span class='ch183-muted'>No tournament-supported checks are available from the current matchup candidate pool yet. No counter claim is being fabricated.</span></div>", unsafe_allow_html=True)

    if identity and len(identity) > 1:
        st.markdown(f"<div class='ch183-note' style='margin-top:8px'>Form lookup aliases: {html.escape(', '.join(identity))}</div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)
    return True
