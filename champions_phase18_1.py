"""Phase 18.1: unified Champions profile polish and form-safe presentation.

Keeps the Phase 18 data contract, but adds a cohesive outer profile card,
sprite-aware header, stronger typography, matchup/speed sections, and safer
role/counter presentation. Tournament identity resolution is delegated to
champions_meta so forms can fall back to their base species when appropriate.
"""
from __future__ import annotations

import html
from typing import Any, Callable, Dict, Iterable, List, Optional

import streamlit as st

from champions_integration import get_champions_profile
from champions_viability import apply_champions_adjustment

SpriteResolver = Callable[[str], str]

_CSS = """
<style>
.ch181-wrap{border:1px solid rgba(148,163,184,.32);border-radius:16px;padding:18px 20px 16px;margin:8px 0 18px;background:linear-gradient(180deg,rgba(148,163,184,.075),rgba(148,163,184,.035));box-shadow:0 8px 28px rgba(0,0,0,.08)}
.ch181-head{display:flex;align-items:center;gap:14px;margin-bottom:4px}.ch181-head img{width:64px;height:64px;object-fit:contain}.ch181-title{font-size:1.35rem;font-weight:800;line-height:1.2}.ch181-sub{font-size:.88rem;color:rgba(210,215,222,.78);margin-bottom:14px}.ch181-section{font-size:1.05rem;font-weight:800;margin:18px 0 8px}.ch181-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px}.ch181-card{border:1px solid rgba(148,163,184,.25);border-radius:11px;padding:12px 13px;background:rgba(148,163,184,.055)}.ch181-card strong{font-size:1.18rem}.ch181-label{font-size:.76rem;color:rgba(210,215,222,.78);margin-top:4px}.ch181-note{font-size:.75rem;color:rgba(210,215,222,.64);margin-top:4px}.ch181-row{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:9px 2px;border-bottom:1px solid rgba(148,163,184,.14)}.ch181-row:last-child{border-bottom:0}.ch181-entity{display:flex;align-items:center;gap:9px;min-width:0}.ch181-entity img{width:34px;height:34px;object-fit:contain}.ch181-name{font-weight:700}.ch181-detail{font-size:.77rem;color:rgba(210,215,222,.75);text-align:right}.ch181-pill{display:inline-block;padding:4px 8px;border-radius:999px;background:rgba(99,144,240,.13);font-size:.75rem;font-weight:700;margin:2px}.ch181-score{font-size:2rem;font-weight:900}.ch181-bar{height:8px;border-radius:99px;background:rgba(148,163,184,.18);overflow:hidden;margin-top:8px}.ch181-fill{height:100%;background:linear-gradient(90deg,#6390F0,#7AC74C);border-radius:99px}.ch181-muted{color:rgba(210,215,222,.6);font-size:.8rem}
@media(max-width:800px){.ch181-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}
</style>
"""

def _pct(v: Any)->str:
    try:return f"{float(v)*100:.1f}%"
    except (TypeError,ValueError):return "—"

def _score(v: Any)->float:
    try:return float(str(v).split("/")[0].strip())
    except (TypeError,ValueError):return 0.0

def _name(v: Any)->str:
    return str(v or "Unknown").replace("-"," ").title()

def _sprite(resolver: Optional[SpriteResolver], name: str)->str:
    if not resolver:return ""
    try:return str(resolver(name) or "")
    except Exception:return ""

def _entity(name:str,url:str)->str:
    n=html.escape(name)
    img=f"<img src='{html.escape(url,quote=True)}' alt='{n}' />" if url else ""
    return f"<div class='ch181-entity'>{img}<span class='ch181-name'>{n}</span></div>"

def _rows(items:Iterable[Dict[str,Any]], resolver:Optional[SpriteResolver], partner:bool=True)->str:
    out=[]
    for item in list(items)[:6]:
        name=_name(item.get("pokemon")); url=_sprite(resolver,name)
        if partner:
            detail=f"{int(item.get('teams_together') or 0):,} teams together · {_pct(item.get('shared_win_rate'))} shared win rate"
        else:
            detail=f"{int(item.get('appearances') or 0):,} appearances · {_pct(item.get('win_rate'))} win rate"
        out.append(f"<div class='ch181-row'>{_entity(name,url)}<span class='ch181-detail'>{html.escape(detail)}</span></div>")
    return "".join(out)

def render_champions_profile_v4(pokemon_name:str, meta:Optional[Dict[str,Any]]=None, sprite_resolver:Optional[SpriteResolver]=None, type_summary:Any=None, offensive_summary:Any=None)->bool:
    profile=get_champions_profile(pokemon_name)
    if not profile.get("available"): return False
    meta=dict(meta or {})
    base=_score(meta.get("viability"))
    adj=apply_champions_adjustment(base,pokemon_name)
    final=float(adj.get("adjusted_score",base))
    delta=float(adj.get("adjustment",0.0))
    confidence=float(adj.get("confidence",0.0))
    display=_name(pokemon_name); sprite=_sprite(sprite_resolver,display)
    st.markdown(_CSS,unsafe_allow_html=True)
    st.markdown("<div class='ch181-wrap'>",unsafe_allow_html=True)
    st.markdown(f"<div class='ch181-head'>{_entity('',sprite) if sprite else ''}<div><div class='ch181-title'>🏆 Champions Competitive Profile — {html.escape(display)}</div><div class='ch181-sub'>Tournament evidence, strategic diagnostics and Champions-aware recommendations</div></div></div>",unsafe_allow_html=True)
    cards=[("Champions Viability",f"{final:.0f} / 100",f"Base {base:.0f} · {delta:+.1f} tournament"),("Team appearances",f"{int(profile.get('appearances') or 0):,}","Collected tournament teams"),("Win rate",_pct(profile.get('win_rate')),f"Recent {_pct(profile.get('recent_win_rate'))}"),("Top-cut rate",_pct(profile.get('top_cut_rate')),f"Confidence {confidence:.2f}")]
    st.markdown("<div class='ch181-grid'>"+"".join(f"<div class='ch181-card'><strong>{html.escape(v)}</strong><div class='ch181-label'>{html.escape(l)}</div><div class='ch181-note'>{html.escape(n)}</div></div>" for l,v,n in cards)+"</div>",unsafe_allow_html=True)
    fill=max(0,min(100,final))
    st.markdown(f"<div class='ch181-card' style='margin-top:10px'><div class='ch181-label'>VIABILITY INDEX</div><div class='ch181-score'>{final:.0f} / 100</div><div class='ch181-bar'><div class='ch181-fill' style='width:{fill:.0f}%'></div></div></div>",unsafe_allow_html=True)
    st.markdown("<div class='ch181-section'>Strategic profile</div>",unsafe_allow_html=True)
    strategic=[("Speed tier",meta.get("speed_tier","N/A")),("Offensive profile",meta.get("offensive_profile","N/A")),("Momentum & pivoting",meta.get("momentum_rating","N/A")),("Hazard & utility",meta.get("hazard_utility","N/A"))]
    st.markdown("<div class='ch181-grid'>"+"".join(f"<div class='ch181-card'><strong style='font-size:.94rem'>{html.escape(str(v))}</strong><div class='ch181-label'>{html.escape(l)}</div></div>" for l,v in strategic)+"</div>",unsafe_allow_html=True)
    partners=list(profile.get("partners") or [])[:6]
    if partners:
        st.markdown("<div class='ch181-section'>Common tournament partners</div>",unsafe_allow_html=True); st.markdown("<div class='ch181-card'>"+_rows(partners,sprite_resolver,True)+"</div>",unsafe_allow_html=True)
    counters=[]
    for entry in list(meta.get("counters") or []):
        if isinstance(entry,(list,tuple)) and entry: counters.append({"pokemon":entry[0]})
        elif isinstance(entry,dict) and (entry.get("pokemon") or entry.get("name")): counters.append({"pokemon":entry.get("pokemon") or entry.get("name")})
        elif entry: counters.append({"pokemon":entry})
    if counters:
        enriched=[]
        for c in counters:
            p=get_champions_profile(str(c["pokemon"])); enriched.append({"pokemon":c["pokemon"],"appearances":p.get("appearances",0),"win_rate":p.get("win_rate")})
        enriched.sort(key=lambda x:int(x.get("appearances") or 0),reverse=True)
        st.markdown("<div class='ch181-section'>Champions-aware meta checks & counters</div>",unsafe_allow_html=True); st.markdown("<div class='ch181-card'>"+_rows(enriched,sprite_resolver,False)+"</div>",unsafe_allow_html=True)
    if type_summary or offensive_summary:
        st.markdown("<div class='ch181-section'>Type matchup profile</div>",unsafe_allow_html=True)
        for label,data in (("Defensive matchups",type_summary),("Offensive coverage",offensive_summary)):
            if data: st.markdown(f"<div class='ch181-card'><div class='ch181-label'>{label}</div><div style='margin-top:6px'>{html.escape(str(data))}</div></div>",unsafe_allow_html=True)
    role=meta.get("role") or meta.get("recommended_role") or "Role data unavailable"
    st.markdown(f"<div class='ch181-card' style='margin-top:10px'><div class='ch181-label'>Recommended team role</div><strong style='font-size:.98rem'>{html.escape(str(role))}</strong></div>",unsafe_allow_html=True)
    st.markdown("</div>",unsafe_allow_html=True)
    return True
