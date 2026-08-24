"""Whole-team candidate recommendations for the Pokémon Champions teambuilder."""
from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from champions.constants import CUSTOM_MEGAS_DATA
from champions.species_keys import canonical_species_key
from champions.history_data import history_revision
from champions.meta_utils import detect_archetypes
from champions.pokemon_data import fetch_pokemon_details_batch
from champions.roster_data import display_name_for_species_key
from champions.tournament_data import get_tournament_partners, load_champions_history
from champions.team_analyzer import TeamAnalyzer


def _family_key(name: str) -> str:
    """Return the base species family while preserving meaningful non-Mega forms."""
    text = str(name or "").strip()
    if text.lower().startswith("mega "):
        text = text[5:].strip()
    return canonical_species_key(text)


def _meta_record(records: Mapping[str, Any], name: str) -> Dict[str, Any]:
    """Find current meta data for a species, falling back from Mega to its base form."""
    key = canonical_species_key(name)
    record = records.get(key)
    if isinstance(record, dict):
        return record
    if str(name).lower().startswith("mega "):
        base_key = canonical_species_key(str(name)[5:].strip())
        record = records.get(base_key)
        if isinstance(record, dict):
            return record
    return {}


def _candidate_shortlist(active_names: Sequence[str], limit: int = 48) -> List[str]:
    history = load_champions_history() or {}
    records = history.get("pokemon") or {}
    if not isinstance(records, dict):
        records = {}

    active_keys = {canonical_species_key(name) for name in active_names}
    active_families = {_family_key(name) for name in active_names}
    regulation = str(history.get("active_regulation") or "").strip().upper()
    ranked: List[Tuple[float, str]] = []

    for species_key, raw_record in records.items():
        name = display_name_for_species_key(species_key)
        if not name:
            continue
        # A Mega and its base species occupy the same team slot. Never recommend
        # the ordinary form when that species is already present as a Mega (or vice versa).
        if canonical_species_key(name) in active_keys or _family_key(name) in active_families:
            continue

        record = raw_record if isinstance(raw_record, dict) else {}
        metrics = record.get("regulation_metrics") or {}
        current = metrics.get(regulation, {}) if regulation else {}
        current = current if isinstance(current, dict) else {}
        appearances = float(current.get("appearances", 0) or record.get("appearances", 0) or 0)
        usage = float(current.get("usage", 0) or record.get("usage", 0) or 0)
        top_cut = float(current.get("top_cut_rate", 0) or record.get("top_cut_rate", 0) or 0)
        recent = float(record.get("recent_usage_weight", 0) or 0)
        relevance = min(36.0, appearances / 18.0) + min(24.0, usage * 80.0) + min(20.0, top_cut * 40.0) + min(20.0, recent * 20.0)
        # A Mega can inherit its base species' tournament relevance when the
        # history registry records the species under the non-Mega key.
        ranked.append((relevance, name))

    # Make supported Champions Megas eligible even when history stores their
    # tournament statistics against the base species key.
    for mega_name in CUSTOM_MEGAS_DATA:
        if _family_key(mega_name) in active_families or canonical_species_key(mega_name) in active_keys:
            continue
        record = _meta_record(records, mega_name)
        if record:
            metrics = record.get("regulation_metrics") or {}
            current = metrics.get(regulation, {}) if regulation else {}
            current = current if isinstance(current, dict) else {}
            appearances = float(current.get("appearances", 0) or record.get("appearances", 0) or 0)
            usage = float(current.get("usage", 0) or record.get("usage", 0) or 0)
            top_cut = float(current.get("top_cut_rate", 0) or record.get("top_cut_rate", 0) or 0)
            recent = float(record.get("recent_usage_weight", 0) or 0)
            relevance = min(36.0, appearances / 18.0) + min(24.0, usage * 80.0) + min(20.0, top_cut * 40.0) + min(20.0, recent * 20.0)
        else:
            relevance = 0.0
        ranked.append((relevance + 0.5, mega_name))

    ranked.sort(key=lambda item: (-item[0], item[1].casefold()))
    names = [name for _, name in ranked]

    partner_pool: List[str] = []
    for active_name in active_names:
        try:
            for species_key, _count in get_tournament_partners(active_name, top_n=12) or []:
                partner = display_name_for_species_key(species_key)
                if partner and _family_key(partner) not in active_families:
                    partner_pool.append(partner)
        except Exception:
            continue

    # Tournament partners get first refusal, followed by meta-ranked candidates.
    return list(dict.fromkeys(partner_pool + names))[:limit]


def _team_types(team: Sequence[Mapping[str, Any]]) -> Counter[str]:
    return Counter(str(t).title() for member in team for t in (member.get("types") or []))


def _reason_summary(
    base: Dict[str, Any],
    improved: Dict[str, Any],
    candidate: Mapping[str, Any],
    partner_count: int = 0,
    partner_names: Sequence[str] = (),
) -> List[str]:
    reasons: List[str] = []

    # Only describe a defensive improvement when the candidate actually removes
    # an uncovered type. This prevents generic claims such as "answers Fairy"
    # when there was no relevant gap to solve.
    solved = sorted(set(base["defensive"]["uncovered_types"]) - set(improved["defensive"]["uncovered_types"]))
    if solved:
        reasons.append("Closes the " + ", ".join(solved[:3]) + " defensive gap")

    opened = sorted(set(base["offensive"]["uncovered_types"]) - set(improved["offensive"]["uncovered_types"]))
    if opened:
        reasons.append("Adds super-effective pressure into " + ", ".join(opened[:3]))

    newly_added: List[str] = []
    for key, label in (("speed_control", "speed control"), ("priority_moves", "priority"), ("disruption", "disruption"), ("support", "support"), ("setup", "setup")):
        if set(improved["functions"].get(key) or []) - set(base["functions"].get(key) or []):
            newly_added.append(label)
    if newly_added:
        reasons.append("Adds " + ", ".join(newly_added[:3]))

    base_types = _team_types(base["team"])
    candidate_types = [str(t).title() for t in candidate.get("types") or []]
    if candidate_types and all(base_types[t] == 0 for t in candidate_types):
        reasons.append("Introduces a new typing profile")

    # Tournament pairing evidence is stronger than a generic archetype label.
    if partner_count > 0 and partner_names:
        suffix = "times" if partner_count != 1 else "time"
        reasons.append(f"Tournament pairing with {', '.join(partner_names[:2])} ({partner_count} {suffix})")

    # Archetypes are only emitted when they came from the candidate's observed
    # tournament moves or abilities, not its entire theoretical learnset.
    if candidate.get("archetypes"):
        reasons.append("Fits " + ", ".join(candidate["archetypes"][:2]))

    return reasons[:4]


def _meta_relevance(name: str) -> float:
    history = load_champions_history() or {}
    records = history.get("pokemon") or {}
    if not isinstance(records, dict):
        return 0.0
    record = _meta_record(records, name)
    if not record:
        return 0.0
    regulation = str(history.get("active_regulation") or "").strip().upper()
    current = ((record.get("regulation_metrics") or {}).get(regulation) or {}) if regulation else {}
    return max(0.0, min(100.0,
        float(current.get("usage", 0) or record.get("usage", 0) or 0) * 55.0
        + float(current.get("top_cut_rate", 0) or record.get("top_cut_rate", 0) or 0) * 25.0
        + min(20.0, float(current.get("appearances", 0) or record.get("appearances", 0) or 0) / 5.0)
    ))


def _partner_evidence(active_names: Sequence[str]) -> Dict[str, Tuple[int, List[str]]]:
    """Build candidate-family -> strongest observed team pairing evidence."""
    evidence: Dict[str, Tuple[int, List[str]]] = {}
    for active_name in active_names:
        try:
            partners = get_tournament_partners(active_name, top_n=12) or []
        except Exception:
            partners = []
        for species_key, count in partners:
            partner_name = display_name_for_species_key(species_key)
            if not partner_name:
                continue
            family = _family_key(partner_name)
            current_count, current_names = evidence.get(family, (0, []))
            count = int(count or 0)
            if count > current_count:
                current_count = count
                current_names = [str(active_name)]
            elif count == current_count and str(active_name) not in current_names:
                current_names = current_names + [str(active_name)]
            evidence[family] = (current_count, current_names)
    return evidence


def recommend_team_additions(team: Sequence[Mapping[str, Any]], *, top_n: int = 4, candidate_limit: int = 48) -> List[Dict[str, Any]]:
    """Return candidates ranked by team fit, current meta relevance, and tournament pair evidence."""
    raw_team = [dict(member) for member in team if str(member.get("name") or "").strip()]
    if not raw_team or len(raw_team) >= 6:
        return []

    active_names = [str(member["name"]) for member in raw_team]
    candidate_names = _candidate_shortlist(active_names, limit=candidate_limit)
    resolved = fetch_pokemon_details_batch(active_names + candidate_names, max_workers=12)
    partner_evidence = _partner_evidence(active_names)

    # Enrich the raw Streamlit slot state with authoritative typing, stats, abilities,
    # and moves before TeamAnalyzer compares the candidate against the real team.
    active_team: List[Dict[str, Any]] = []
    for member in raw_team:
        name = str(member["name"])
        details = dict(resolved.get(name) or {})
        enriched = dict(member)
        enriched.update({
            "types": list(details.get("types") or member.get("types") or []),
            "stats": dict(details.get("stats") or member.get("stats") or {}),
            "abilities": list(details.get("abilities") or member.get("abilities") or []),
        })
        active_team.append(enriched)

    base_result = TeamAnalyzer(active_team).analyze()
    base_result["team"] = active_team
    results: List[Dict[str, Any]] = []

    for name in candidate_names:
        data = resolved.get(name)
        if not data or not data.get("types"):
            continue
        candidate = dict(data)
        candidate["name"] = name

        # Never use the full theoretical learnset as evidence for a recommendation.
        # Prefer moves actually observed in tournament data; abilities remain valid
        # evidence because they are intrinsic to the species/form.
        observed_moves = data.get("tournament_moves") or {}
        if isinstance(observed_moves, Mapping):
            candidate["moves"] = list(observed_moves.keys())
        elif observed_moves:
            candidate["moves"] = list(observed_moves)
        else:
            candidate["moves"] = []

        candidate["archetypes"] = [item.get("name") for item in detect_archetypes(candidate) if item.get("name")]
        improved = TeamAnalyzer(active_team + [candidate]).analyze()
        improved["team"] = active_team + [candidate]
        delta = float(improved["overall_score"]) - float(base_result["overall_score"])
        def_delta = len(base_result["defensive"]["uncovered_types"]) - len(improved["defensive"]["uncovered_types"])
        off_delta = len(base_result["offensive"]["uncovered_types"]) - len(improved["offensive"]["uncovered_types"])
        function_delta = float(improved["functions"]["score"]) - float(base_result["functions"]["score"])
        archetype_delta = float(improved["archetypes"]["score"]) - float(base_result["archetypes"]["score"])
        meta = _meta_relevance(name)

        partner_count, partner_names = partner_evidence.get(_family_key(name), (0, []))
        max_partner_count = max((count for count, _ in partner_evidence.values()), default=0)
        partner_strength = (partner_count / max_partner_count * 100.0) if max_partner_count else 0.0

        score = max(0.0, min(100.0,
            delta * 0.45
            + max(0.0, def_delta) * 4.0
            + max(0.0, off_delta) * 3.0
            + max(0.0, function_delta) * 0.12
            + max(0.0, archetype_delta) * 0.06
            + meta * 0.08
            + partner_strength * 0.20
        ))
        results.append({
            "name": name,
            "types": list(candidate.get("types") or []),
            "sprite": data.get("box_sprite") or data.get("sprite"),
            "score": round(score, 1),
            "team_delta": round(delta, 1),
            "defensive_delta": def_delta,
            "offensive_delta": off_delta,
            "function_delta": round(function_delta, 1),
            "archetype_delta": round(archetype_delta, 1),
            "meta_relevance": round(meta, 1),
            "partner_count": partner_count,
            "partner_names": partner_names,
            "is_mega": name.lower().startswith("mega "),
            "reasons": _reason_summary(base_result, improved, candidate, partner_count, partner_names),
            "archetypes": candidate["archetypes"],
        })

    results.sort(key=lambda row: (-row["score"], -row["team_delta"], -row["partner_count"], row["name"].casefold()))
    return results[: max(1, int(top_n))]


def recommendation_cache_token() -> str:
    return history_revision()
