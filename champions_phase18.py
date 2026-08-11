"""Phase 18: unified Champions competitive profile.

This renderer combines the validated Champions tournament evidence with the
existing Strategizer diagnostics without replacing the underlying engine.
It is intentionally isolated from app.py so the large legacy application
remains the source of Pokémon data, sprites, speed/role diagnostics, and the
existing matchup candidate engine.
"""

from __future__ import annotations

import html
import re
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

import streamlit as st

from champions_integration import get_champions_profile
from champions_viability import apply_champions_adjustment


SpriteResolver = Callable[[str], str]

_CSS = """
<style>
.champ18-wrap { margin: .25rem 0 1.4rem 0; }
.champ18-title { font-size: 1.25rem; line-height: 1.25; font-weight: 800; margin: .1rem 0 .2rem 0; }
.champ18-subtitle { color: rgba(210,215,222,.88); font-size: .86rem; margin-bottom: .9rem; }
.champ18-section { font-size: 1.00rem; font-weight: 750; margin: 1.0rem 0 .45rem 0; }
.champ18-card { border: 1px solid rgba(148,163,184,.25); border-radius: 12px; padding: 13px 15px; margin-bottom: 10px; background: rgba(148,163,184,.055); }
.champ18-card-strong { border: 1px solid rgba(99,144,240,.35); background: rgba(99,144,240,.07); }
.champ18-value { font-size: 1.28rem; font-weight: 800; line-height: 1.12; }
.champ18-value-small { font-size: .96rem; font-weight: 700; line-height: 1.25; }
.champ18-label { font-size: .76rem; color: rgba(210,215,222,.78); margin-top: 5px; }
.champ18-note { font-size: .78rem; color: rgba(210,215,222,.72); margin-top: 5px; }
.champ18-row { display:flex; align-items:center; justify-content:space-between; gap:12px; padding:9px 0; border-bottom:1px solid rgba(148,163,184,.16); }
.champ18-row:last-child { border-bottom:0; }
.champ18-entity { display:flex; align-items:center; gap:9px; min-width:0; }
.champ18-sprite { width:34px; height:34px; object-fit:contain; image-rendering:auto; }
.champ18-name { font-weight:700; }
.champ18-detail { font-size:.78rem; color:rgba(210,215,222,.76); text-align:right; white-space:nowrap; }
.champ18-badge { display:inline-block; padding:3px 7px; border-radius:999px; background:rgba(99,144,240,.14); font-size:.72rem; font-weight:700; }
.champ18-positive { color:#7AC74C; }
.champ18-negative { color:#FF6B6B; }
.champ18-muted { color:rgba(210,215,222,.60); }
</style>
"""


def _pct(value: Any) -> str:
    if value is None:
        return "—"
    try:
        return f"{float(value) * 100:.1f}%"
    except (TypeError, ValueError):
        return "—"


def _score(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        match = re.search(r"\d+(?:\.\d+)?", str(value))
        return float(match.group()) if match else None
    except (TypeError, ValueError):
        return None


def _name(value: Any) -> str:
    return str(value or "Unknown").replace("-", " ").title()


def _safe_sprite(resolver: Optional[SpriteResolver], name: str) -> str:
    if resolver is None:
        return ""
    try:
        return str(resolver(name) or "")
    except Exception:
        return ""


def _entity(name: str, sprite_url: str) -> str:
    safe_name = html.escape(name)
    if sprite_url:
        return (
            f"<div class='champ18-entity'><img class='champ18-sprite' "
            f"src='{html.escape(sprite_url, quote=True)}' alt='{safe_name}' />"
            f"<span class='champ18-name'>{safe_name}</span></div>"
        )
    return f"<div class='champ18-entity'><span class='champ18-name'>{safe_name}</span></div>"


def _counter_rows(meta: Dict[str, Any], resolver: Optional[SpriteResolver]) -> List[str]:
    """Render existing matchup checks, prioritised by collected tournament usage.

    The underlying matchup engine remains authoritative for candidate checks;
    tournament evidence is only used to prioritise candidates that are actually
    present in the Champions dataset. This avoids presenting a usage statistic
    as if it were a direct Pokémon-vs-Pokémon win/loss record.
    """
    raw = meta.get("counters") or []
    rows: List[Tuple[float, int, str, str, str]] = []
    for entry in raw:
        if isinstance(entry, (list, tuple)):
            candidate = entry[0] if entry else None
        elif isinstance(entry, dict):
            candidate = entry.get("pokemon") or entry.get("name")
        else:
            candidate = entry
        if not candidate:
            continue
        display = _name(candidate)
        profile = get_champions_profile(display)
        appearances = int(profile.get("appearances") or 0) if profile.get("available") else 0
        win_rate = profile.get("win_rate") if profile.get("available") else None
        # Established tournament presence is a tie-breaker, not a matchup score.
        rows.append((min(appearances, 1000) / 1000.0, appearances, display, _pct(win_rate), _safe_sprite(resolver, display)))
    rows.sort(key=lambda row: (row[0], row[1]), reverse=True)
    return [
        "<div class='champ18-row'>"
        + _entity(display, sprite)
        + f"<span class='champ18-detail'>{appearances} tournament appearances · {wr} win rate</span>"
        + "</div>"
        for _, appearances, display, wr, sprite in rows[:6]
    ]


def render_champions_profile_v3(
    pokemon_name: str,
    meta: Optional[Dict[str, Any]] = None,
    sprite_resolver: Optional[SpriteResolver] = None,
) -> bool:
    """Render the unified Phase 18 competitive profile.

    ``meta`` is the existing app diagnostic result. It is displayed and used
    for the matchup/speed/role sections but is never mutated. Tournament data
    contributes a bounded, confidence-weighted viability adjustment through
    ``champions_viability``.
    """
    profile: Dict[str, Any] = get_champions_profile(pokemon_name)
    if not profile.get("available"):
        return False

    meta = dict(meta or {})
    base_score = _score(meta.get("viability"))
    if base_score is None:
        base_score = 0.0
    adjusted = apply_champions_adjustment(base_score, pokemon_name)
    adjusted_score = float(adjusted.get("adjusted_score", base_score))
    adjustment = float(adjusted.get("adjustment", 0.0))
    confidence = float(adjusted.get("confidence", 0.0))

    st.markdown(_CSS, unsafe_allow_html=True)
    st.markdown("<div class='champ18-wrap'>", unsafe_allow_html=True)
    st.markdown(
        f"<div class='champ18-title'>🏆 Champions Competitive Profile — {html.escape(_name(pokemon_name))}</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<div class='champ18-subtitle'>Tournament evidence, existing strategic diagnostics, and Champions-aware recommendations</div>",
        unsafe_allow_html=True,
    )

    top = st.columns(4)
    top_metrics = [
        ("Champions Viability", f"{adjusted_score:.0f} / 100", f"Base {base_score:.0f} · {adjustment:+.1f} tournament"),
        ("Team appearances", f"{int(profile.get('appearances') or 0):,}", "Collected tournament teams"),
        ("Win rate", _pct(profile.get("win_rate")), f"Recent {_pct(profile.get('recent_win_rate'))}"),
        ("Top-cut rate", _pct(profile.get("top_cut_rate")), f"Evidence confidence {confidence:.2f}"),
    ]
    for col, (label, value, note) in zip(top, top_metrics):
        with col:
            st.markdown(
                f"<div class='champ18-card champ18-card-strong'><div class='champ18-value'>{value}</div>"
                f"<div class='champ18-label'>{html.escape(label)}</div><div class='champ18-note'>{html.escape(note)}</div></div>",
                unsafe_allow_html=True,
            )

    st.markdown("<div class='champ18-section'>Strategic profile</div>", unsafe_allow_html=True)
    strategic = st.columns(4)
    strategic_metrics = [
        ("Speed tier", meta.get("speed_tier", "N/A")),
        ("Offensive profile", meta.get("offensive_profile", "N/A")),
        ("Momentum & pivoting", meta.get("momentum_rating", "N/A")),
        ("Hazard & utility", meta.get("hazard_utility", "N/A")),
    ]
    for col, (label, value) in zip(strategic, strategic_metrics):
        with col:
            st.markdown(
                f"<div class='champ18-card'><div class='champ18-value-small'>{html.escape(str(value))}</div>"
                f"<div class='champ18-label'>{html.escape(label)}</div></div>",
                unsafe_allow_html=True,
            )

    partners: Iterable[Dict[str, Any]] = profile.get("partners") or []
    partners = list(partners)[:6]
    if partners:
        st.markdown("<div class='champ18-section'>Common tournament partners</div>", unsafe_allow_html=True)
        rows: List[str] = []
        for partner in partners:
            display = _name(partner.get("pokemon"))
            teams = int(partner.get("teams_together") or 0)
            shared = _pct(partner.get("shared_win_rate"))
            sprite = _safe_sprite(sprite_resolver, display)
            rows.append(
                "<div class='champ18-row'>"
                + _entity(display, sprite)
                + f"<span class='champ18-detail'>{teams:,} teams together · {shared} shared win rate</span>"
                + "</div>"
            )
        st.markdown("<div class='champ18-card'>" + "".join(rows) + "</div>", unsafe_allow_html=True)

    counter_rows = _counter_rows(meta, sprite_resolver)
    if counter_rows:
        st.markdown("<div class='champ18-section'>Champions-aware meta checks & counters</div>", unsafe_allow_html=True)
        st.markdown(
            "<div class='champ18-card'>"
            + "".join(counter_rows)
            + "<div class='champ18-note'>Candidates come from the existing matchup engine; tournament usage is used only to prioritise established Champions options.</div>"
            + "</div>",
            unsafe_allow_html=True,
        )

    role = meta.get("role") or meta.get("recommended_role")
    if not role:
        role = "Strategic role inferred from the existing team engine"
    st.markdown(
        f"<div class='champ18-card'><div class='champ18-label'>Recommended team role</div>"
        f"<div class='champ18-value-small'>{html.escape(str(role))}</div></div>",
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)
    return True
