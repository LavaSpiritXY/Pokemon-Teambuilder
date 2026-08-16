"""Phase 18.4: data-first Champions profile fixes."""
from __future__ import annotations
import math

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
    """Create the same calibrated tournament score used by Phase 19 profile UI."""
    profile = resolved_tournament_profile(pokemon_name)
    base = _clamp(float(base_score))
    if not profile.get("available"):
        return {"score": round(base, 1), "base": round(base, 1), "tournament": None, "confidence": 0.0}

    appearances = max(0.0, float(profile.get("appearances") or 0))
    weighted_appearances = max(0.0, float(profile.get("weighted_appearances") or profile.get("recent_usage_weight") or appearances))
    usage_signal = 1.0 - math.exp(-weighted_appearances / 300.0)
    win = max(0.0, min(1.0, float(profile.get("win_rate") or 0.0)))
    recent_win = max(0.0, min(1.0, float(profile.get("recent_win_rate") if profile.get("recent_win_rate") is not None else win)))
    cut = max(0.0, min(1.0, float(profile.get("top_cut_rate") or profile.get("recent_top_cut_rate") or 0.0)))
    if cut <= 0.0:
        try:
            avg = float(profile.get("average_placement") or 0.0)
        except (TypeError, ValueError):
            avg = 0.0
        if avg > 0:
            cut = max(0.0, min(1.0, 1.0 / (1.0 + max(0.0, avg - 1.0) / 8.0))) * 0.5
    cut_signal = max(0.0, min(1.0, 0.5 + (cut - 0.125) / 0.25))
    win_signal = max(0.0, min(1.0, 0.5 + (win - 0.5) * 2.0))
    recent_signal = max(0.0, min(1.0, 0.5 + (recent_win - 0.5) * 2.0))
    tournament_score = (usage_signal * 0.45 + cut_signal * 0.25 + win_signal * 0.20 + recent_signal * 0.10) * 100.0
    confidence = min(1.0, math.sqrt(appearances / 100.0)) if appearances else 0.0
    blend = 0.80 * confidence
    score = (base * (1.0 - blend)) + (tournament_score * blend)
    return {"score": round(_clamp(score), 1), "base": round(base, 1), "tournament": round(_clamp(tournament_score), 1), "confidence": confidence, "appearances": int(appearances)}


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
    fallback_rows: List[Dict[str, Any]] = []
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
        if profile.get("available") and int(profile.get("appearances") or 0) > 0:
            appearances = int(profile.get("appearances") or 0)
            win = max(0.0, min(1.0, float(profile.get("win_rate") or 0.5)))
            cut = max(0.0, min(1.0, float(profile.get("top_cut_rate") or 0.0)))
            relevance = min(1.0, appearances / 500.0) * 0.45 + cut * 0.30 + win * 0.25
            rows.append({"pokemon": name, "appearances": appearances, "win_rate": win, "relevance_score": relevance})
        else:
            # A strategic counter is still useful when the tournament archive has
            # no record for that candidate. Keep it visible rather than rendering
            # an empty counters panel.
            fallback_rows.append({"pokemon": name, "appearances": 0, "win_rate": 0.0, "relevance_score": 0.0})
    rows.sort(key=lambda x: (x["relevance_score"], x["appearances"]), reverse=True)
    ordered = rows + fallback_rows
    return ordered[: max(0, int(limit))]
