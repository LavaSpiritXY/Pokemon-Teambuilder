"""Phase 12: aggregate cached Pokémon Champions tournaments into metrics.

Read-only with respect to the event cache. Produces a separate JSON dataset
so the main Strategizer database is not modified until the numbers are vetted.
"""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CACHE = ROOT / "champions_cache"
DEFAULT_OUTPUT = ROOT / "champions_meta_history.json"
RECENCY_HALF_LIFE_DAYS = 45.0


def _parse_date(value: Any) -> Optional[datetime]:
    if not value:
        return None
    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except ValueError:
        pass
    for fmt in ("%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(text[:10], fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _event_date(snapshot: Dict[str, Any]) -> Optional[datetime]:
    event = snapshot.get("event") or {}
    for key in ("start_date", "date", "created_at", "startDate"):
        parsed = _parse_date(event.get(key))
        if parsed:
            return parsed
    return None


def _placement(result: Dict[str, Any]) -> Optional[float]:
    value = result.get("placement")
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _record_stats(stats: Dict[str, Any], result: Dict[str, Any], weight: float) -> None:
    wins = int(result.get("wins", 0) or 0)
    losses = int(result.get("losses", 0) or 0)
    draws = int(result.get("draws", 0) or 0)
    stats["appearances"] += 1
    stats["wins"] += wins
    stats["losses"] += losses
    stats["draws"] += draws
    stats["weighted_appearances"] += weight
    stats["weighted_wins"] += wins * weight
    stats["weighted_losses"] += losses * weight
    placement = _placement(result)
    if placement is not None:
        stats["placement_sum"] += placement
        stats["placement_count"] += 1
        stats["best_placement"] = (
            placement if stats["best_placement"] is None
            else min(stats["best_placement"], placement)
        )
    if result.get("top_cut") is True:
        stats["top_cut_count"] += 1
        stats["weighted_top_cut"] += weight


def _empty_stats() -> Dict[str, Any]:
    return {
        "appearances": 0,
        "wins": 0,
        "losses": 0,
        "draws": 0,
        "weighted_appearances": 0.0,
        "weighted_wins": 0.0,
        "weighted_losses": 0.0,
        "top_cut_count": 0,
        "weighted_top_cut": 0.0,
        "placement_sum": 0.0,
        "placement_count": 0,
        "best_placement": None,
        "regulations": {},
    }


def _finalize_stats(stats: Dict[str, Any]) -> None:
    games = stats["wins"] + stats["losses"] + stats["draws"]
    stats["win_rate"] = stats["wins"] / games if games else 0.0
    stats["top_cut_rate"] = (
        stats["top_cut_count"] / stats["appearances"]
        if stats["appearances"] else 0.0
    )
    stats["average_placement"] = (
        stats["placement_sum"] / stats["placement_count"]
        if stats["placement_count"] else None
    )
    stats["recent_win_rate"] = (
        stats["weighted_wins"] /
        (stats["weighted_wins"] + stats["weighted_losses"])
        if (stats["weighted_wins"] + stats["weighted_losses"]) else 0.0
    )
    stats["recent_usage_weight"] = stats["weighted_appearances"]
    stats["recent_top_cut_rate"] = (
        stats["weighted_top_cut"] / stats["weighted_appearances"]
        if stats["weighted_appearances"] else 0.0
    )


def _empty_partner() -> Dict[str, Any]:
    return {
        "teams_together": 0,
        "shared_wins": 0,
        "shared_losses": 0,
        "weighted_teams_together": 0.0,
        "weighted_wins": 0.0,
        "weighted_losses": 0.0,
    }


def aggregate(cache_dir: Path) -> Dict[str, Any]:
    snapshots: List[Dict[str, Any]] = []
    for path in sorted(cache_dir.glob("*.json")):
        if path.name == "manifest.json":
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload["_file"] = path.name
            snapshots.append(payload)
        except Exception as exc:
            print(f"WARNING: could not read {path.name}: {exc}")

    dates = [d for d in (_event_date(s) for s in snapshots) if d]
    reference_date = max(dates) if dates else datetime.now(timezone.utc)

    pokemon: Dict[str, Dict[str, Any]] = defaultdict(_empty_stats)
    partners: Dict[str, Dict[str, Dict[str, Any]]] = defaultdict(
        lambda: defaultdict(_empty_partner)
    )
    regulations: Counter[str] = Counter()
    events_by_regulation: Counter[str] = Counter()

    for snapshot in snapshots:
        event = snapshot.get("event") or {}
        regulation = str(event.get("regulation") or "Unknown")
        regulations[regulation] += 1
        events_by_regulation[regulation] += 1
        date = _event_date(snapshot)
        age_days = max(0.0, (reference_date - date).total_seconds() / 86400.0) if date else 365.0
        weight = math.pow(0.5, age_days / RECENCY_HALF_LIFE_DAYS)

        results_by_player = {
            str(r.get("player_name") or r.get("player") or "").strip(): r
            for r in (snapshot.get("results") or [])
            if str(r.get("player_name") or r.get("player") or "").strip()
        }

        for team in snapshot.get("teams") or []:
            player = str(team.get("player_name") or team.get("player") or "").strip()
            result = results_by_player.get(player, {})
            names = [str(name).strip() for name in (team.get("pokemon") or []) if str(name).strip()]
            unique_names = list(dict.fromkeys(names))
            for name in unique_names:
                key = name.lower()
                _record_stats(pokemon[key], result, weight)
                pokemon[key]["display_name"] = name
                pokemon[key]["regulations"][regulation] = (
                    pokemon[key]["regulations"].get(regulation, 0) + 1
                )
            for left, right in combinations(sorted(set(n.lower() for n in unique_names)), 2):
                partner = partners[left][right]
                partner["teams_together"] += 1
                partner["shared_wins"] += int(result.get("wins", 0) or 0)
                partner["shared_losses"] += int(result.get("losses", 0) or 0)
                partner["weighted_teams_together"] += weight
                partner["weighted_wins"] += int(result.get("wins", 0) or 0) * weight
                partner["weighted_losses"] += int(result.get("losses", 0) or 0) * weight
                reverse = partners[right][left]
                reverse.update(partner)

    for stats in pokemon.values():
        _finalize_stats(stats)

    partner_output: Dict[str, List[Dict[str, Any]]] = {}
    for source, rows in partners.items():
        values = []
        for target, data in rows.items():
            shared_games = data["shared_wins"] + data["shared_losses"]
            values.append({
                "pokemon": target,
                **data,
                "shared_win_rate": data["shared_wins"] / shared_games if shared_games else 0.0,
            })
        partner_output[source] = sorted(
            values,
            key=lambda row: (row["teams_together"], row["shared_win_rate"]),
            reverse=True,
        )

    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "reference_date": reference_date.isoformat(),
        "recency_half_life_days": RECENCY_HALF_LIFE_DAYS,
        "events_processed": len(snapshots),
        "regulations": dict(regulations),
        "pokemon": dict(pokemon),
        "partners": partner_output,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Aggregate cached Champions events")
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    print("=== Pokémon Champions Phase 12 aggregation ===")
    report = aggregate(args.cache)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Events processed: {report['events_processed']}")
    print(f"Pokémon records:  {len(report['pokemon'])}")
    print(f"Partner records:  {sum(len(v) for v in report['partners'].values())}")
    print(f"Saved to:         {args.output.resolve()}")

    print("--- Most-used Pokémon ---")
    top = sorted(report["pokemon"].values(), key=lambda x: x["appearances"], reverse=True)[:15]
    for row in top:
        print(
            f"  {row['display_name']}: appearances={row['appearances']}, "
            f"wins={row['wins']}, losses={row['losses']}, "
            f"win_rate={row['win_rate']:.3f}, top_cut_rate={row['top_cut_rate']:.3f}"
        )


if __name__ == "__main__":
    main()
