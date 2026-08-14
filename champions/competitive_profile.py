"""Phase 18.5: unified Champions competitive profile.

Display-only presentation layer. It consumes the existing Champions tournament
metadata and Strategizer values without changing the underlying scoring engine.
"""
from __future__ import annotations

import html
import math
from typing import Any, Dict, Iterable, Mapping, Optional

import streamlit as st

from champions_integration import get_champions_profile
from champions.counter_evidence import rank_counters_with_evidence

_CSS = """
<style>
.ch185-wrap{border:1px solid rgba(148,163,184,.30);border-radius:18px;padding:20px 22px 22px;margin:12px 0 20px;background:linear-gradient(180deg,rgba(148,163,184,.09),rgba(148,163,184,.035));box-shadow:0 10px 30px rgba(0,0,0,.09)}
.ch185-head{display:flex;align-items:center;gap:16px;margin-bottom:18px}.ch185-head img{width:88px;height:88px;object-fit:contain}.ch185-title{font-size:1.62rem;font-weight:900;line-height:1.16}.ch185-sub{font-size:.9rem;color:rgba(180,190,205,.86);margin-top:6px}
.ch185-section{font-size:1.18rem;font-weight:850;margin:20px 0 10px}.ch185-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px}.ch185-card{border:1px solid rgba(148,163,184,.24);border-radius:13px;padding:13px 15px;background:rgba(148,163,184,.055)}.ch185-value{font-size:1.18rem;font-weight:850;line-height:1.2}.ch185-label{font-size:.78rem;color:rgba(180,190,205,.86);margin-top:4px}.ch185-note{font-size:.75rem;color:rgba(180,190,205,.68);margin-top:5px}
.ch185-score{font-size:2.55rem;font-weight:950;line-height:1}.ch185-scorebar{height:13px;border-radius:999px;background:rgba(148,163,184,.17);overflow:hidden;margin-top:10px}.ch185-scorefill{height:100%;border-radius:999px;background:linear-gradient(90deg,#ef4444 0%,#f59e0b 48%,#7ac74c 100%)}
.ch185-row{display:flex;align-items:center;justify-content:space-between;gap:14px;padding:10px 2px;border-bottom:1px solid rgba(148,163,184,.14)}.ch185-row:last-child{border-bottom:0}.ch185-entity{display:flex;align-items:center;gap:11px;min-width:0}.ch185-entity img{width:52px;height:52px;object-fit:contain}.ch185-name{font-weight:750}.ch185-detail{font-size:.78rem;color:rgba(180,190,205,.80);text-align:right}.ch185-muted{font-size:.84rem;color:rgba(180,190,205,.70)}
.ch185-stats{display:grid;gap:8px}.ch185-statrow{display:grid;grid-template-columns:90px 1fr 48px;align-items:center;gap:10px}.ch185-statname{font-weight:750;font-size:.84rem}.ch185-statbar{height:16px;border-radius:999px;background:rgba(148,163,184,.13);overflow:hidden;border:1px solid rgba(148,163,184,.12)}.ch185-statfill{height:100%;border-radius:999px}.ch185-statvalue{text-align:right;font-weight:850;font-variant-numeric:tabular-nums}
.ch185-spbar{height:12px;border-radius:999px;background:rgba(148,163,184,.13);overflow:hidden;border:1px solid rgba(148,163,184,.12)}.ch185-spfill{height:100%;border-radius:999px;background:linear-gradient(90deg,#ef4444 0%,#f59e0b 48%,#7ac74c 100%)}
@media(max-width:800px){.ch185-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.ch185-statrow{grid-template-columns:70px 1fr 40px}}
</style>
"""

_STAT_KEYS = (("HP", "hp"), ("Attack", "attack"), ("Defense", "defense"), ("Sp. Atk", "special-attack"), ("Sp. Def", "special-defense"), ("Speed", "speed"))
_SP_KEYS = (("HP", "HP"), ("Attack", "Atk"), ("Defense", "Def"), ("Sp. Atk", "SpA"), ("Sp. Def", "SpD"), ("Speed", "Spe"))


def _pct(value: Any) -> str:
    try:
        return f"{float(value) * 100:.1f}%"
    except (TypeError, ValueError):
        return "—"


def _pretty(value: Any) -> str:
    return str(value or "Unknown").replace("-", " ").title()


def _sprite(name: str, resolver: Any) -> str:
    try:
        return str(resolver(name) or "") if resolver else ""
    except Exception:
        return ""


def _entity(name: str, resolver: Any) -> str:
    safe = html.escape(name)
    url = _sprite(name, resolver)
    image = f"<img src='{html.escape(url, quote=True)}' alt='{safe}'>" if url else ""
    return f"<div class='ch185-entity'>{image}<span class='ch185-name'>{safe}</span></div>"


def _stat_colour(value: int, maximum: int = 180) -> str:
    ratio = max(0.0, min(1.0, float(value) / float(maximum or 1)))
    hue = ratio * 120.0
    return f"hsl({hue:.0f}, 72%, 48%)"


def _base_stat_rows(stats: Optional[Mapping[str, Any]]) -> str:
    if not stats:
        return ""
    rows = []
    for label, key in _STAT_KEYS:
        raw = stats.get(key, stats.get(label, 0))
        try:
            value = max(0, int(raw or 0))
        except (TypeError, ValueError):
            value = 0
        width = max(0, min(100, round(value / 180 * 100)))
        colour = _stat_colour(value)
        rows.append(
            f"<div class='ch185-statrow'><span class='ch185-statname'>{label}</span>"
            f"<div class='ch185-statbar'><div class='ch185-statfill' style='width:{width}%;background:{colour}'></div></div>"
            f"<span class='ch185-statvalue'>{value}</span></div>"
        )
    return "".join(rows)


def _sp_rows(sp_values: Optional[Mapping[str, Any]]) -> tuple[str, int]:
    values = dict(sp_values or {})
    rows = []
    total = 0
    for label, key in _SP_KEYS:
        try:
            value = max(0, min(32, int(values.get(key, 0) or 0)))
        except (TypeError, ValueError):
            value = 0
        total += value
        width = round(value / 32 * 100)
        rows.append(
            f"<div class='ch185-statrow'><span class='ch185-statname'>{label}</span>"
            f"<div class='ch185-spbar'><div class='ch185-spfill' style='width:{width}%'></div></div>"
            f"<span class='ch185-statvalue'>{value}</span></div>"
        )
    return "".join(rows), total


def _tournament_index(tournament: Mapping[str, Any]) -> float:
    """Convert Champions evidence into a calibrated 0–100 dominance index.

    Usage is saturated rather than divided by an arbitrary 1,000-event ceiling;
    top-cut performance is measured against the 12.5% baseline expected from a
    Top-8 cut; recent results are used when the archive provides them.
    """
    appearances = max(0.0, float(tournament.get("appearances") or 0))
    weighted_appearances = max(0.0, float(tournament.get("weighted_appearances") or tournament.get("recent_usage_weight") or appearances))
    usage_signal = 1.0 - math.exp(-weighted_appearances / 300.0)

    win = max(0.0, min(1.0, float(tournament.get("win_rate") or 0.0)))
    recent_win = max(0.0, min(1.0, float(tournament.get("recent_win_rate") if tournament.get("recent_win_rate") is not None else win)))
    cut_raw = float(tournament.get("top_cut_rate") or 0.0)
    recent_cut_raw = float(tournament.get("recent_top_cut_rate") or 0.0)
    cut = max(0.0, min(1.0, cut_raw if cut_raw > 0 else recent_cut_raw))

    # If explicit top-cut data is absent, use average placement as a transparent
    # quality proxy instead of inventing a 20% top-cut rate.
    if cut <= 0.0:
        avg_placement = tournament.get("average_placement")
        try:
            avg = float(avg_placement)
        except (TypeError, ValueError):
            avg = 0.0
        if avg > 0:
            cut = max(0.0, min(1.0, 1.0 / (1.0 + max(0.0, avg - 1.0) / 8.0))) * 0.5

    # 12.5% is the neutral Top-8 baseline. Values above it receive a real
    # competitive lift; values below it are not treated as a total failure.
    cut_signal = max(0.0, min(1.0, 0.5 + (cut - 0.125) / 0.25))
    win_signal = max(0.0, min(1.0, 0.5 + (win - 0.5) * 2.0))
    recent_signal = max(0.0, min(1.0, 0.5 + (recent_win - 0.5) * 2.0))

    index = (
        usage_signal * 0.45
        + cut_signal * 0.25
        + win_signal * 0.20
        + recent_signal * 0.10
    ) * 100.0
    return round(max(0.0, min(100.0, index)), 1)


def _display_score(base_score: float, tournament: Mapping[str, Any]) -> tuple[float, float]:
    if not tournament.get("available"):
        return max(0.0, min(100.0, base_score)), 0.0
    index = _tournament_index(tournament)
    score = max(0.0, min(100.0, base_score * 0.25 + index * 0.75))
    return round(score, 1), index


def render_champions_profile_v6(
    pokemon_name: str,
    meta: Optional[Dict[str, Any]] = None,
    sprite_resolver: Any = None,
    base_stats: Optional[Dict[str, Any]] = None,
    sp_values: Optional[Mapping[str, Any]] = None,
) -> bool:
    """Render the single Phase 18.5 Champions profile."""
    meta = dict(meta or {})
    try:
        base_score = float(str(meta.get("viability", "0")).split("/")[0].strip())
    except (TypeError, ValueError):
        base_score = 0.0
    tournament = dict(get_champions_profile(pokemon_name) or {})
    score, tournament_index = _display_score(base_score, tournament)
    tier = "No tournament tier"
    if tournament.get("available"):
        if score >= 85: tier = "Elite"
        elif score >= 70: tier = "Strong"
        elif score >= 55: tier = "Viable"
        elif score >= 40: tier = "Situational"
        else: tier = "Niche"

    st.markdown(_CSS, unsafe_allow_html=True)
    st.markdown("<div class='ch185-wrap'>", unsafe_allow_html=True)
    sprite = _sprite(pokemon_name, sprite_resolver)
    image = f"<img src='{html.escape(sprite, quote=True)}' alt='{html.escape(pokemon_name)}'>" if sprite else ""
    st.markdown(f"<div class='ch185-head'>{image}<div><div class='ch185-title'>🏆 Champions Competitive Profile — {html.escape(_pretty(pokemon_name))}</div><div class='ch185-sub'>Tournament evidence, competitive role, partners, checks and Champions-aware training data</div></div></div>", unsafe_allow_html=True)

    if tournament.get("available"):
        cards = [
            ("Team appearances", f"{int(tournament.get('appearances') or 0):,}", "Collected tournament teams"),
            ("Win rate", _pct(tournament.get("win_rate")), f"Recent {_pct(tournament.get('recent_win_rate'))}"),
            ("Top-cut rate", _pct(tournament.get("top_cut_rate")), "Observed tournament performance"),
            ("Display tier", tier, f"Tournament index {tournament_index:.1f}"),
        ]
        st.markdown("<div class='ch185-grid'>" + "".join(f"<div class='ch185-card'><div class='ch185-value'>{html.escape(v)}</div><div class='ch185-label'>{html.escape(l)}</div><div class='ch185-note'>{html.escape(n)}</div></div>" for l,v,n in cards) + "</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='ch185-card' style='margin-top:10px'><div class='ch185-label'>TOURNAMENT-WEIGHTED VIABILITY INDEX</div><div class='ch185-score'>{score:.0f} / 100</div><div class='ch185-scorebar'><div class='ch185-scorefill' style='width:{score:.0f}%'></div></div><div class='ch185-note'>Base Strategizer score: {base_score:.0f} · Tournament evidence index: {tournament_index:.1f} · Display-only score</div></div>", unsafe_allow_html=True)

        role = str(meta.get("champions_role") or meta.get("role") or "Balanced Pick")
        strategic = [("Speed tier", meta.get("speed_tier", "N/A")), ("Offensive profile", meta.get("offensive_profile", "N/A")), ("Momentum", meta.get("momentum_rating", "N/A")), ("Role", role)]
        st.markdown("<div class='ch185-section'>Strategic profile</div>", unsafe_allow_html=True)
        st.markdown("<div class='ch185-grid'>" + "".join(f"<div class='ch185-card'><div class='ch185-value' style='font-size:.96rem'>{html.escape(str(v))}</div><div class='ch185-label'>{html.escape(l)}</div></div>" for l,v in strategic) + "</div>", unsafe_allow_html=True)

        partners = list(tournament.get("partners") or [])[:6]
        if partners:
            st.markdown("<div class='ch185-section'>🤝 Common tournament partners</div>", unsafe_allow_html=True)
            rows = []
            for item in partners:
                name = _pretty(item.get("pokemon")); teams = int(item.get("teams_together") or 0); rate = _pct(item.get("shared_win_rate"))
                rows.append(f"<div class='ch185-row'>{_entity(name, sprite_resolver)}<span class='ch185-detail'>{teams:,} teams · {rate} shared win rate</span></div>")
            st.markdown("<div class='ch185-card'>" + "".join(rows) + "</div>", unsafe_allow_html=True)

        counters = rank_counters_with_evidence(pokemon_name, meta.get("counters") or [])
        st.markdown("<div class='ch185-section'>🛡️ Evidence-ranked checks & counters</div>", unsafe_allow_html=True)
        if counters:
            rows = []
            for item in list(counters)[:6]:
                name = _pretty(item.get("pokemon")); appearances = int(item.get("appearances") or 0); relevance = float(item.get("relevance_score") or 0) * 100
                rows.append(f"<div class='ch185-row'>{_entity(name, sprite_resolver)}<span class='ch185-detail'>{appearances:,} appearances · {relevance:.0f} evidence</span></div>")
            st.markdown("<div class='ch185-card'>" + "".join(rows) + "</div>", unsafe_allow_html=True)
        else:
            st.markdown("<div class='ch185-card'><span class='ch185-muted'>No tournament-supported checks are available from the current evidence pool.</span></div>", unsafe_allow_html=True)
    else:
        st.markdown("<div class='ch185-card'><div class='ch185-value'>Tournament data unavailable</div><div class='ch185-note'>This Pokémon/form is recognised by the builder, but no collected Champions tournament evidence is currently available. The profile remains visible and the base Strategizer score is not penalised.</div></div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)
    return True
