"""Phase 12.2: validate champions_meta_history.json.

This is a read-only diagnostic. It checks the generated historical dataset
before it is connected to the main Strategizer meta/viability system.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any, Dict


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def _between_01(value: Any) -> bool:
    return _is_number(value) and 0.0 <= float(value) <= 1.0


def validate(report: Dict[str, Any], expected_events: int | None = None) -> list[str]:
    issues: list[str] = []

    events = report.get("events_processed")
    if not isinstance(events, int) or events < 0:
        issues.append("events_processed is not a non-negative integer")
    elif expected_events is not None and events != expected_events:
        issues.append(f"events_processed={events}, expected {expected_events}")

    half_life = report.get("recency_half_life_days")
    if not _is_number(half_life) or float(half_life) <= 0:
        issues.append("recency_half_life_days must be positive")

    pokemon = report.get("pokemon")
    if not isinstance(pokemon, dict) or not pokemon:
        issues.append("pokemon section is missing or empty")
        pokemon = {}

    for key, stats in pokemon.items():
        prefix = f"pokemon[{key}]"
        if not isinstance(key, str) or not key.strip():
            issues.append("pokemon contains an empty/non-string key")
            continue
        if not isinstance(stats, dict):
            issues.append(f"{prefix} is not an object")
            continue

        appearances = stats.get("appearances")
        wins = stats.get("wins")
        losses = stats.get("losses")
        draws = stats.get("draws")
        top_cuts = stats.get("top_cut_count")

        for field in ("appearances", "wins", "losses", "draws", "top_cut_count", "placement_count"):
            value = stats.get(field)
            if not isinstance(value, int) or value < 0:
                issues.append(f"{prefix}.{field} must be a non-negative integer")

        if all(isinstance(v, int) and v >= 0 for v in (wins, losses, draws)):
            if wins + losses + draws <= 0 and appearances and appearances > 0:
                issues.append(f"{prefix} has appearances but no recorded games")

        if isinstance(top_cuts, int) and isinstance(appearances, int) and top_cuts > appearances:
            issues.append(f"{prefix}.top_cut_count exceeds appearances")

        for field in ("win_rate", "top_cut_rate", "recent_win_rate", "recent_top_cut_rate"):
            if not _between_01(stats.get(field)):
                issues.append(f"{prefix}.{field} is outside [0, 1]")

        for field in ("weighted_appearances", "weighted_wins", "weighted_losses", "weighted_top_cut"):
            value = stats.get(field)
            if not _is_number(value) or float(value) < 0:
                issues.append(f"{prefix}.{field} must be a non-negative finite number")

        best = stats.get("best_placement")
        average = stats.get("average_placement")
        placement_count = stats.get("placement_count")
        if best is not None and (not _is_number(best) or float(best) < 1):
            issues.append(f"{prefix}.best_placement is invalid")
        if average is not None and (not _is_number(average) or float(average) < 1):
            issues.append(f"{prefix}.average_placement is invalid")
        if placement_count == 0 and (best is not None or average is not None):
            issues.append(f"{prefix} has placement values but zero placement_count")

        regulations = stats.get("regulations", {})
        if not isinstance(regulations, dict):
            issues.append(f"{prefix}.regulations is not an object")
        else:
            reg_total = 0
            for reg, count in regulations.items():
                if not isinstance(reg, str) or not isinstance(count, int) or count < 0:
                    issues.append(f"{prefix}.regulations contains an invalid entry")
                else:
                    reg_total += count
            if isinstance(appearances, int) and reg_total != appearances:
                issues.append(f"{prefix}.regulations total {reg_total} != appearances {appearances}")

    partners = report.get("partners")
    if not isinstance(partners, dict):
        issues.append("partners section is missing or not an object")
        partners = {}

    pair_count = 0
    for source, rows in partners.items():
        if source not in pokemon:
            issues.append(f"partners contains unknown source Pokémon: {source}")
        if not isinstance(rows, list):
            issues.append(f"partners[{source}] is not a list")
            continue
        seen_targets: set[str] = set()
        for row in rows:
            pair_count += 1
            if not isinstance(row, dict):
                issues.append(f"partners[{source}] contains a non-object row")
                continue
            target = row.get("pokemon")
            if not isinstance(target, str) or not target:
                issues.append(f"partners[{source}] has an invalid target")
                continue
            if target in seen_targets:
                issues.append(f"partners[{source}] contains duplicate target {target}")
            seen_targets.add(target)
            if target not in pokemon:
                issues.append(f"partners[{source}] references unknown Pokémon {target}")
            if target == source:
                issues.append(f"partners[{source}] contains a self-pair")

            for field in ("teams_together", "shared_wins", "shared_losses"):
                value = row.get(field)
                if not isinstance(value, int) or value < 0:
                    issues.append(f"partners[{source}][{target}].{field} is invalid")
            for field in ("weighted_teams_together", "weighted_wins", "weighted_losses"):
                value = row.get(field)
                if not _is_number(value) or float(value) < 0:
                    issues.append(f"partners[{source}][{target}].{field} is invalid")
            if not _between_01(row.get("shared_win_rate")):
                issues.append(f"partners[{source}][{target}].shared_win_rate is outside [0, 1]")

    # Partner symmetry: A->B and B->A should carry the same aggregate values.
    rows_by_pair: dict[tuple[str, str], dict[str, Any]] = {}
    for source, rows in partners.items():
        if not isinstance(rows, list):
            continue
        for row in rows:
            target = row.get("pokemon")
            if isinstance(target, str):
                rows_by_pair[(source, target)] = row

    checked_pairs: set[tuple[str, str]] = set()
    for (source, target), row in rows_by_pair.items():
        pair = tuple(sorted((source, target)))
        if pair in checked_pairs:
            continue
        checked_pairs.add(pair)
        reverse = rows_by_pair.get((target, source))
        if reverse is None:
            issues.append(f"missing reverse partner record for {source} <-> {target}")
            continue
        for field in (
            "teams_together", "shared_wins", "shared_losses",
            "weighted_teams_together", "weighted_wins", "weighted_losses",
        ):
            if row.get(field) != reverse.get(field):
                issues.append(f"partner asymmetry for {source} <-> {target}: {field}")

    return issues


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate Champions aggregated history")
    parser.add_argument("--input", type=Path, default=Path("champions_meta_history.json"))
    parser.add_argument("--expected-events", type=int, default=50)
    args = parser.parse_args()

    print("=== Pokémon Champions Phase 12.2 aggregation validation ===")
    if not args.input.exists():
        print(f"ERROR: aggregation file does not exist: {args.input.resolve()}")
        raise SystemExit(1)

    try:
        report = json.loads(args.input.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"ERROR: could not parse aggregation JSON: {exc}")
        raise SystemExit(1)

    issues = validate(report, args.expected_events)
    pokemon = report.get("pokemon") if isinstance(report.get("pokemon"), dict) else {}
    partners = report.get("partners") if isinstance(report.get("partners"), dict) else {}
    pair_count = sum(len(rows) for rows in partners.values() if isinstance(rows, list))

    print()
    print("--- Aggregation summary ---")
    print(f"Events processed:      {report.get('events_processed', 'UNKNOWN')}")
    print(f"Pokémon records:       {len(pokemon)}")
    print(f"Partner records:       {pair_count}")
    print(f"Recency half-life:     {report.get('recency_half_life_days', 'UNKNOWN')} days")

    print()
    if issues:
        print("--- Issues ---")
        for issue in issues:
            print(f"  ERROR: {issue}")
        print()
        print("STATUS: REVIEW REQUIRED")
        raise SystemExit(2)

    print("All Pokémon metrics are structurally valid.")
    print("All partner metrics are structurally valid and symmetric.")
    print("STATUS: PASS")


if __name__ == "__main__":
    main()
