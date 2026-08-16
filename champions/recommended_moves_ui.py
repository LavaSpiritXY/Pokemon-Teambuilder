"""Presentation layer for tournament-backed recommended moves."""
from __future__ import annotations

import html
from typing import Any, Mapping, Sequence

import streamlit as st


_CSS = """
<style>
.rm-wrap{margin-top:14px}
.rm-legend{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 12px}
.rm-pill{display:inline-flex;align-items:center;gap:6px;padding:5px 9px;border-radius:999px;background:rgba(148,163,184,.09);border:1px solid rgba(148,163,184,.18);font-size:.74rem;font-weight:700}
.rm-dot{width:8px;height:8px;border-radius:50%;display:inline-block}
.rm-list{display:grid;gap:9px}
.rm-card{border:1px solid rgba(148,163,184,.22);border-radius:13px;padding:12px 14px;background:rgba(148,163,184,.045)}
.rm-top{display:flex;align-items:flex-start;justify-content:space-between;gap:12px}
.rm-name{font-size:1rem;font-weight:850}.rm-score{font-size:1.15rem;font-weight:900;white-space:nowrap}
.rm-meta{display:flex;flex-wrap:wrap;gap:7px;margin-top:5px;font-size:.76rem;color:rgba(180,190,205,.84)}
.rm-meta span{padding-right:7px;border-right:1px solid rgba(148,163,184,.22)}.rm-meta span:last-child{border-right:0}
.rm-reason{margin-top:8px;font-size:.78rem;color:rgba(180,190,205,.78)}
.rm-usage{margin-top:9px;height:7px;border-radius:999px;background:rgba(148,163,184,.13);overflow:hidden}.rm-usage-fill{height:100%;border-radius:999px}
.rm-badge{display:inline-flex;margin-left:7px;padding:3px 7px;border-radius:999px;font-size:.67rem;font-weight:850;vertical-align:middle}
</style>
"""


def _category(row: Mapping[str, Any]) -> tuple[str, str]:
    frequency = float(row.get("frequency", 0) or 0)
    reason = str(row.get("reason", ""))
    category = str(row.get("category", "status")).lower()
    effectiveness = float(row.get("effectiveness", 1) or 1)

    if frequency >= 50.0:
        return "Core", "#4ade80"
    if category == "status" or "utility" in reason.casefold():
        return "Utility", "#60a5fa"
    if effectiveness >= 2.0:
        return "Coverage", "#fb923c"
    return "Situational", "#cbd5e1"


def _category_badge(label: str, colour: str) -> str:
    return (
        f"<span class='rm-badge' style='background:{colour}22;color:{colour};"
        f"border:1px solid {colour}55'>{html.escape(label)}</span>"
    )


def _detail_line(row: Mapping[str, Any]) -> str:
    move_type = html.escape(str(row.get("type") or "Normal"))
    category = str(row.get("category") or "status").lower()
    category_label = {"physical": "Physical", "special": "Special", "status": "Status"}.get(category, category.title())
    parts = [move_type, category_label]

    try:
        power = int(row.get("power") or 0)
    except (TypeError, ValueError):
        power = 0
    if power > 0:
        parts.append(f"{power} BP")

    try:
        priority = int(row.get("priority") or 0)
    except (TypeError, ValueError):
        priority = 0
    if priority:
        parts.append(f"Priority {priority:+d}")

    return "".join(f"<span>{html.escape(str(part))}</span>" for part in parts)


def render_recommended_moves(rows: Sequence[Mapping[str, Any]] | None) -> bool:
    """Render the structured tournament move recommendations."""
    recommendations = [dict(row) for row in (rows or []) if row.get("move")]

    st.markdown("<div class='rm-wrap'>", unsafe_allow_html=True)
    st.markdown(_CSS, unsafe_allow_html=True)
    st.markdown("<div class='ch185-section'>⚔️ Recommended Moves</div>", unsafe_allow_html=True)

    if not recommendations:
        st.markdown(
            "<div class='ch185-card'><span class='ch185-muted'>No tournament-backed move recommendations are available yet.</span></div>",
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)
        return False

    legend = []
    for label, colour, description in (
        ("Core", "#4ade80", "Extremely common tournament move"),
        ("Utility", "#60a5fa", "Protect, support or other utility"),
        ("Coverage", "#fb923c", "Less common, but pressures a relevant target"),
        ("Situational", "#cbd5e1", "Useful, with weaker supporting evidence"),
    ):
        legend.append(
            f"<span class='rm-pill'><span class='rm-dot' style='background:{colour}'></span>{label} · {description}</span>"
        )
    st.markdown("<div class='rm-legend'>" + "".join(legend) + "</div>", unsafe_allow_html=True)

    cards = []
    for row in recommendations:
        label, colour = _category(row)
        name = html.escape(str(row.get("move") or "Unknown"))
        score = float(row.get("score", 0) or 0)
        frequency = max(0.0, min(100.0, float(row.get("frequency", 0) or 0)))
        confidence = float(row.get("confidence", 0) or 0)
        reason = html.escape(str(row.get("reason") or "Tournament evidence supports this recommendation."))
        badge = _category_badge(label, colour)
        details = _detail_line(row)
        usage_text = f"{frequency:.1f}% tournament usage"
        if confidence > 0:
            usage_text += f" · {confidence:.0f}% evidence confidence"

        cards.append(
            f"<div class='rm-card'>"
            f"<div class='rm-top'><div><span class='rm-name'>{name}</span>{badge}</div>"
            f"<span class='rm-score'>{score:.1f}</span></div>"
            f"<div class='rm-meta'>{details}</div>"
            f"<div class='rm-reason'>{reason}</div>"
            f"<div class='rm-reason' style='margin-top:7px'>{html.escape(usage_text)}</div>"
            f"<div class='rm-usage'><div class='rm-usage-fill' style='width:{frequency:.1f}%;background:{colour}'></div></div>"
            f"</div>"
        )

    st.markdown("<div class='rm-list'>" + "".join(cards) + "</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
    return True
