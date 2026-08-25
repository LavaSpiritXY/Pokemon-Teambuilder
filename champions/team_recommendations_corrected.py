"""Correctness layer for Team Recommendations.

Keeps the existing scoring engine intact while enforcing Mega-family rules and
using form-specific tournament partnership evidence where it matters.
"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, Sequence

from champions.constants import CUSTOM_MEGAS_DATA
from champions.species_keys import canonical_species_key
from champions.roster_data import display_name_for_species_key
from champions.tournament_data import get_tournament_partners
from champions.team_recommendations import recommend_team_additions as _legacy_recommend


def _family(name: str) -> str:
    text = str(name or "").strip()
    if text.lower().startswith("mega "):
        text = text[5:].strip()
    return canonical_species_key(text)


def _is_mega(name: str) -> bool:
    return str(name or "").strip().lower().startswith("mega ")


def _mega_count(team: Sequence[Mapping[str, Any]]) -> int:
    return sum(1 for member in team if _is_mega(member.get("name", "")))


def _form_partner_evidence(active_name: str) -> Dict[str, int]:
    """Return partnership counts for the exact selected form, not its base family."""
    evidence: Dict[str, int] = {}
    try:
        partners = get_tournament_partners(active_name, top_n=30) or []
    except Exception:
        return evidence
    for species_key, count in partners:
        partner = display_name_for_species_key(species_key)
        if not partner:
            continue
        family = _family(partner)
        evidence[family] = max(evidence.get(family, 0), int(count or 0))
    return evidence


def _best_form_evidence(team: Sequence[Mapping[str, Any]]) -> Dict[str, tuple[int, str]]:
    """Prefer exact-form evidence for Mega members, then normal team evidence."""
    result: Dict[str, tuple[int, str]] = {}
    for member in team:
        name = str(member.get("name") or "").strip()
        if not name:
            continue
        evidence = _form_partner_evidence(name)
        for family, count in evidence.items():
            old_count, old_source = result.get(family, (0, ""))
            if count > old_count:
                result[family] = (count, name)
    return result


def recommend_team_additions(
    team: Sequence[Mapping[str, Any]],
    *,
    top_n: int = 4,
    candidate_limit: int = 48,
) -> List[Dict[str, Any]]:
    """Correct Mega handling around the established team-fit scoring engine.

    Rules:
    * A Mega and its base species are one family/team slot.
    * Never return the base form when its Mega family is already on the team.
    * With fewer than two Megas on the team, at most one Mega may appear in the
      final recommendation group.
    * Once two Megas are already present, Mega recommendations are suppressed.
    * Partnership explanations prefer exact-form tournament evidence, so
      Mega Charizard Y evidence is not silently presented as generic Charizard.
    """
    raw_team = [dict(member) for member in team if str(member.get("name") or "").strip()]
    if not raw_team or len(raw_team) >= 6:
        return []

    existing_mega_count = _mega_count(raw_team)
    active_families = {_family(member.get("name", "")) for member in raw_team}
    exact_evidence = _best_form_evidence(raw_team)

    results = _legacy_recommend(raw_team, top_n=max(top_n * 3, 12), candidate_limit=candidate_limit)
    corrected: List[Dict[str, Any]] = []
    mega_added = False

    for candidate in results:
        name = str(candidate.get("name") or "").strip()
        family = _family(name)
        is_mega = _is_mega(name)

        # Family exclusion is enforced again here at the final boundary so a
        # future change in the scoring shortlist cannot leak a base/Mega duplicate.
        if family in active_families:
            continue
        if existing_mega_count >= 2 and is_mega:
            continue
        if is_mega and mega_added:
            continue

        corrected_candidate = dict(candidate)
        partner_count, source = exact_evidence.get(family, (0, ""))
        if partner_count:
            corrected_candidate["partner_count"] = partner_count
            corrected_candidate["partner_names"] = [source]
            corrected_candidate["reasons"] = [
                reason for reason in corrected_candidate.get("reasons", [])
                if not str(reason).startswith("Tournament pairing with ")
            ]
            suffix = "time" if partner_count == 1 else "times"
            corrected_candidate["reasons"].insert(
                0,
                f"Tournament pairing with {source} ({partner_count} {suffix})",
            )
            corrected_candidate["reasons"] = corrected_candidate["reasons"][:4]

        corrected.append(corrected_candidate)
        if is_mega:
            mega_added = True
        if len(corrected) >= top_n:
            break

    return corrected


def recommendation_cache_token() -> str:
    from champions.team_recommendations import recommendation_cache_token as _token
    return _token()
