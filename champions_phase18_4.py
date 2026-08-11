"""Phase 18.4: data-first Champions profile fixes."""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from champions_integration import get_champions_profile
from champions_meta import _candidate_keys

SP_PER_STAT_MAX = 32
SP_TOTAL_MAX = 66


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def form_candidates(name: str) -> List[str]:
    """Expand the shared resolver with common Champions display spellings."""
    raw = str(name or "").strip().lower().replace("_", " ").replace("-", " ")
    candidates = list(_candidate_keys(name) or [])

    def add(value: str) -> None:
        value = " ".join(value.split()).strip()
        if value and value not in candidates:
            candidates.append(value)

    add(raw)
    for prefix in ("alolan", "galarian", "hisuian", "paldean", "kantonian"):
        if raw.startswith(prefix + " "):
            add(raw[len(prefix) + 1:])
    if raw.startswith("mega "):
        base = raw[5:].strip()
        add(base)
        add(base.split(" ")[0])
    if raw.startswith("rotom "):
        form = raw[6:].strip()
        add(f"rotom {form}")
        add(f"rotom-{form}")
        add("rotom")
    return candidates


def resolved_tournament_profile(name: str) -> Dict[str, Any]:
    """Try the exact form and safe aliases until tournament data is found."""
    best: Dict[str, Any] = {"available": False, "pokemon": name}
    for candidate in form_candidates(name):
        try:
            profile = get_champions_profile(candidate)
        except Exception:
            continue
        if profile.get("available"):
            profile = dict(profile)
            profile["resolved_identity"] = candidate
            return profile
    return best


def tournament_display_score(base_score: float, pokemon_name: str) -> Dict[str, Any]:
    """Create a stronger display-only score without mutating the old engine."""
    profile = resolved_tournament_profile(pokemon_name)
    base = _clamp(float(base_score))
    if not profile.get("available"):
        return {"score": round(base, 1), "base": round(base, 1), "tournament": None, "confidence": 0.0}

    appearances = int(profile.get("appearances") or 0)
    confidence = min((appearances / 100.0) ** 0.5, 1.0) if appearances else 0.0
    win = max(0.0, min(1.0, float(profile.get("win_rate") or 0.50)))
    recent = max(0.0, min(1.0, float(profile.get("recent_win_rate") or win)))
    cut = max(0.0, min(1.0, float(profile.get("top_cut_rate") or 0.20)))
    partners = profile.get("partners") or []
    rates = []
    for partner in partners[:6]:
        try:
            if int(partner.get("teams_together") or 0) > 0:
                rates.append(float(partner.get("shared_win_rate") or 0.50))
        except (TypeError, ValueError):
            continue
    partner_quality = max(0.0, min(1.0, sum(rates) / len(rates) if rates else 0.50))

    performance_signal = ((win * 0.50) + (recent * 0.25) + (cut * 0.25)) * 100.0
    usage_signal = min(appearances / 800.0, 1.0) * 100.0
    partner_signal = partner_quality * 100.0
    tournament_score = (performance_signal * 0.48) + (usage_signal * 0.34) + (partner_signal * 0.18)

    blend = 0.72 * confidence
    score = (base * (1.0 - blend)) + (tournament_score * blend)
    return {"score": round(_clamp(score), 1), "base": round(base, 1), "tournament": round(tournament_score, 1), "confidence": confidence, "appearances": appearances}


def display_tier(score: float) -> str:
    if score >= 85:
        return "S"
    if score >= 75:
        return "A"
    if score >= 65:
        return "B"
    if score >= 50:
        return "C"
    if score >= 35:
        return "D"
    return "E"


def role_from_meta(meta: Optional[Dict[str, Any]], pokemon_name: str) -> str:
    """Only claim a specific utility role when there is supporting evidence."""
    meta = dict(meta or {})
    moves = {str(m).strip().lower() for m in meta.get("moves", [])}
    abilities = {str(a).strip().lower() for a in meta.get("abilities", [])}
    if "tailwind" in moves or "gale wings" in abilities or "wind power" in abilities:
        return "Speed Control"
    if "trick room" in moves:
        return "Trick Room Support"
    if {"rain dance", "sunny day", "sandstorm", "hail"} & moves:
        return "Weather Support"
    if {"stealth rock", "spikes", "toxic spikes", "sticky web"} & moves:
        return "Hazard Setter"
    if {"rapid spin", "defog", "mortal spin"} & moves:
        return "Hazard Control"
    if "protect" in moves and ({"parting shot", "u-turn", "volt switch"} & moves):
        return "Pivot / Positioning"
    return str(meta.get("recommended_role") or meta.get("role") or "Balanced Pick")


def validate_sp_spread(values: Dict[str, Any]) -> Dict[str, int]:
    keys = ["HP", "Atk", "Def", "SpA", "SpD", "Spe"]
    out = {k: max(0, min(SP_PER_STAT_MAX, int(values.get(k, 0) or 0))) for k in keys}
    overflow = max(0, sum(out.values()) - SP_TOTAL_MAX)
    for key in reversed(keys):
        if overflow <= 0:
            break
        reduction = min(out[key], overflow)
        out[key] -= reduction
        overflow -= reduction
    return out


def build_profile_18_4(pokemon_name: str, base_score: float, meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    meta = dict(meta or {})
    tournament = resolved_tournament_profile(pokemon_name)
    score_data = tournament_display_score(base_score, pokemon_name)
    return {
        "pokemon": pokemon_name,
        "form_candidates": form_candidates(pokemon_name),
        "tournament": tournament,
        "score": score_data,
        "tier": display_tier(score_data["score"]),
        "role": role_from_meta(meta, pokemon_name),
        "has_tournament_data": bool(tournament.get("available")),
        "partners": list(tournament.get("partners") or [])[:6],
    }


def rank_counters_with_evidence(pokemon_name: str, existing_candidates: Iterable[Any], limit: int = 6) -> List[Dict[str, Any]]:
    """Return only candidates that have real tournament evidence."""
    rows: List[Dict[str, Any]] = []
    seen = set()
    for candidate in existing_candidates or []:
        if isinstance(candidate, (tuple, list)):
            name = candidate[0] if candidate else ""
        elif isinstance(candidate, dict):
            name = candidate.get("pokemon") or candidate.get("name") or ""
        else:
            name = candidate
        name = str(name or "").strip()
        key = " ".join(name.lower().split())
        if not name or key in seen or key == " ".join(pokemon_name.lower().split()):
            continue
        seen.add(key)
        profile = resolved_tournament_profile(name)
        if not profile.get("available") or int(profile.get("appearances") or 0) <= 0:
            continue
        appearances = int(profile.get("appearances") or 0)
        win = float(profile.get("win_rate") or 0.5)
        relevance = min(1.0, appearances / 500.0) * 0.55 + max(0.0, min(1.0, win)) * 0.45
        rows.append({"pokemon": name, "appearances": appearances, "win_rate": win, "relevance_score": relevance})
    rows.sort(key=lambda x: (x["relevance_score"], x["appearances"]), reverse=True)
    return rows[: max(0, int(limit))]
