"""Phase 10.1: validate cached Champions event snapshots.

Read-only diagnostic. Missing placement is treated as unknown rather than an
error because dropped/non-finalized standings can legitimately lack a final
placing. We never invent a placement.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List


def load_snapshots(cache_dir: Path) -> List[Dict[str, Any]]:
    snapshots: List[Dict[str, Any]] = []
    for path in sorted(cache_dir.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload["_file"] = path.name
            snapshots.append(payload)
        except Exception as exc:
            print(f"ERROR reading {path.name}: {exc}")
    return snapshots


def validate(snapshots: List[Dict[str, Any]]) -> Dict[str, Any]:
    issues: List[str] = []
    pokemon_counts: Counter[str] = Counter()
    form_names: set[str] = set()
    event_ids: set[str] = set()
    player_count = 0
    team_count = 0
    full_teams = 0
    short_teams = 0
    long_teams = 0
    missing_placement = 0
    invalid_record = 0
    top_cut_true = 0
    top_cut_false = 0
    top_cut_unknown = 0

    for snapshot in snapshots:
        event = snapshot.get("event") or {}
        event_id = str(event.get("event_id") or event.get("id") or "").strip()
        if event_id:
            if event_id in event_ids:
                issues.append(f"Duplicate event ID: {event_id}")
            event_ids.add(event_id)

        results = snapshot.get("results") or []
        teams = snapshot.get("teams") or []
        player_count += len(results)
        team_count += len(teams)

        for result in results:
            placement = result.get("placement")
            if placement is None:
                missing_placement += 1

            try:
                wins = int(result.get("wins", 0) or 0)
                losses = int(result.get("losses", 0) or 0)
                draws = int(result.get("draws", 0) or 0)
                if min(wins, losses, draws) < 0:
                    invalid_record += 1
            except (TypeError, ValueError):
                invalid_record += 1

            top_cut = result.get("top_cut")
            if top_cut is True:
                top_cut_true += 1
            elif top_cut is False:
                top_cut_false += 1
            else:
                top_cut_unknown += 1

        for team in teams:
            pokemon = team.get("pokemon") or []
            if len(pokemon) == 6:
                full_teams += 1
            elif len(pokemon) < 6:
                short_teams += 1
            else:
                long_teams += 1

            if len(set(pokemon)) != len(pokemon):
                issues.append(
                    f"Duplicate Pokémon in team for {team.get('player_name', '<unknown>')} "
                    f"({event_id or snapshot.get('_file')})"
                )

            for name in pokemon:
                value = str(name).strip()
                if value:
                    pokemon_counts[value.lower()] += 1
                    if any(marker in value.lower() for marker in (
                        "hisuian", "alolan", "galarian", "paldean", "dusk",
                        "eternal flower", "basculegion-f", "female", "male",
                    )):
                        form_names.add(value)

    if invalid_record:
        issues.append(f"{invalid_record} result(s) have invalid W/L/D values")
    if long_teams:
        issues.append(f"{long_teams} team(s) contain more than 6 Pokémon")

    return {
        "events": len(snapshots),
        "players": player_count,
        "teams": team_count,
        "full_teams": full_teams,
        "short_teams": short_teams,
        "long_teams": long_teams,
        "missing_placement": missing_placement,
        "invalid_records": invalid_record,
        "unique_pokemon": len(pokemon_counts),
        "form_variants": sorted(form_names),
        "top_cut_true": top_cut_true,
        "top_cut_false": top_cut_false,
        "top_cut_unknown": top_cut_unknown,
        "most_used": pokemon_counts.most_common(15),
        "issues": issues,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate Champions JSON cache")
    parser.add_argument("--cache", type=Path, default=Path("champions_cache"))
    args = parser.parse_args()

    print("=== Pokémon Champions Phase 10.1 cache validation ===")
    if not args.cache.exists():
        print(f"ERROR: cache directory does not exist: {args.cache.resolve()}")
        raise SystemExit(1)

    snapshots = load_snapshots(args.cache)
    report = validate(snapshots)

    print()
    print("--- Cache summary ---")
    print(f"Events:                 {report['events']}")
    print(f"Players:                {report['players']}")
    print(f"Teams:                  {report['teams']}")
    print(f"Teams with 6 Pokémon:   {report['full_teams']}")
    print(f"Teams with <6:          {report['short_teams']}")
    print(f"Teams with >6:          {report['long_teams']}")
    print(f"Placement available:    {report['players'] - report['missing_placement']}")
    print(f"Placement unknown:      {report['missing_placement']}")
    print(f"Invalid W/L/D records:  {report['invalid_records']}")
    print(f"Unique Pokémon:         {report['unique_pokemon']}")
    print(f"Top-cut true:           {report['top_cut_true']}")
    print(f"Top-cut false:          {report['top_cut_false']}")
    print(f"Top-cut unknown:        {report['top_cut_unknown']}")

    print()
    print("--- Form variants detected ---")
    if report["form_variants"]:
        for name in report["form_variants"]:
            print(f"  {name}")
    else:
        print("  None detected")

    print()
    print("--- Most-used Pokémon in cached teams ---")
    for name, count in report["most_used"]:
        print(f"  {name}: {count}")

    print()
    if report["issues"]:
        print("--- Issues ---")
        for issue in report["issues"]:
            print(f"  ERROR: {issue}")
        print()
        print("STATUS: REVIEW REQUIRED")
        raise SystemExit(2)

    print("STATUS: PASS")


if __name__ == "__main__":
    main()
