"""Incrementally update Champions history without retaining the raw event cache.

The full historical backfill is performed once locally.  After that, GitHub
Actions only needs the already-committed aggregate plus newly downloaded event
snapshots.  This module decays the existing recency-weighted metrics from the
old reference date, then adds the new events.
"""

from __future__ import annotations

from datetime import datetime, timezone
from itertools import combinations
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional

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


def _weight(date: Optional[datetime], reference: datetime) -> float:
    if date is None:
        return math.pow(0.5, 365.0 / RECENCY_HALF_LIFE_DAYS)
    age_days = max(0.0, (reference - date).total_seconds() / 86400.0)
    return math.pow(0.5, age_days / RECENCY_HALF_LIFE_DAYS)


def _new_stats() -> Dict[str, Any]:
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


def _new_partner() -> Dict[str, Any]:
    return {
        "teams_together": 0,
        "shared_wins": 0,
        "shared_losses": 0,
        "weighted_teams_together": 0.0,
        "weighted_wins": 0.0,
        "weighted_losses": 0.0,
    }


def _finalize(stats: Dict[str, Any]) -> None:
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
    weighted_games = stats["weighted_wins"] + stats["weighted_losses"]
    stats["recent_win_rate"] = (
        stats["weighted_wins"] / weighted_games if weighted_games else 0.0
    )
    stats["recent_usage_weight"] = stats["weighted_appearances"]
    stats["recent_top_cut_rate"] = (
        stats["weighted_top_cut"] / stats["weighted_appearances"]
        if stats["weighted_appearances"] else 0.0
    )


def _decay_existing(report: Dict[str, Any], reference: datetime) -> None:
    old_reference = _parse_date(report.get("reference_date"))
    if old_reference is None:
        return
    elapsed_days = max(0.0, (reference - old_reference).total_seconds() / 86400.0)
    factor = math.pow(0.5, elapsed_days / RECENCY_HALF_LIFE_DAYS)

    for stats in (report.get("pokemon") or {}).values():
        for key in (
            "weighted_appearances",
            "weighted_wins",
            "weighted_losses",
            "weighted_top_cut",
        ):
            stats[key] = float(stats.get(key, 0.0) or 0.0) * factor

    for rows in (report.get("partners") or {}).values():
        for row in rows:
            for key in (
                "weighted_teams_together",
                "weighted_wins",
                "weighted_losses",
            ):
                row[key] = float(row.get(key, 0.0) or 0.0) * factor


def _add_snapshot(report: Dict[str, Any], snapshot: Dict[str, Any], reference: datetime) -> None:
    event = snapshot.get("event") or {}
    regulation = str(event.get("regulation") or "Unknown")
    event_date = _event_date(snapshot)
    weight = _weight(event_date, reference)

    pokemon = report.setdefault("pokemon", {})
    partners = report.setdefault("partners", {})
    regulations = report.setdefault("regulations", {})
    regulations[regulation] = int(regulations.get(regulation, 0) or 0) + 1

    results_by_player = {
        str(row.get("player_name") or row.get("player") or "").strip(): row
        for row in (snapshot.get("results") or [])
        if str(row.get("player_name") or row.get("player") or "").strip()
    }

    for team in snapshot.get("teams") or []:
        player = str(team.get("player_name") or team.get("player") or "").strip()
        result = results_by_player.get(player, {})
        names = list(dict.fromkeys(
            str(name).strip()
            for name in (team.get("pokemon") or [])
            if str(name).strip()
        ))

        wins = int(result.get("wins", 0) or 0)
        losses = int(result.get("losses", 0) or 0)
        draws = int(result.get("draws", 0) or 0)

        for name in names:
            key = name.lower()
            stats = pokemon.setdefault(key, _new_stats())
            stats["display_name"] = name
            stats["appearances"] += 1
            stats["wins"] += wins
            stats["losses"] += losses
            stats["draws"] += draws
            stats["weighted_appearances"] += weight
            stats["weighted_wins"] += wins * weight
            stats["weighted_losses"] += losses * weight
            if result.get("top_cut") is True:
                stats["top_cut_count"] += 1
                stats["weighted_top_cut"] += weight
            placement = result.get("placement")
            try:
                placement_value = float(placement) if placement is not None else None
            except (TypeError, ValueError):
                placement_value = None
            if placement_value is not None:
                stats["placement_sum"] += placement_value
                stats["placement_count"] += 1
                best = stats.get("best_placement")
                stats["best_placement"] = placement_value if best is None else min(best, placement_value)
            regulation_counts = stats.setdefault("regulations", {})
            regulation_counts[regulation] = int(regulation_counts.get(regulation, 0) or 0) + 1

        keys = sorted(set(name.lower() for name in names))
        for left, right in combinations(keys, 2):
            left_rows = partners.setdefault(left, [])
            existing = next((row for row in left_rows if row.get("pokemon") == right), None)
            if existing is None:
                existing = {"pokemon": right, **_new_partner()}
                left_rows.append(existing)
            existing["teams_together"] += 1
            existing["shared_wins"] += wins
            existing["shared_losses"] += losses
            existing["weighted_teams_together"] += weight
            existing["weighted_wins"] += wins * weight
            existing["weighted_losses"] += losses * weight

            right_rows = partners.setdefault(right, [])
            reverse = next((row for row in right_rows if row.get("pokemon") == left), None)
            if reverse is None:
                reverse = {"pokemon": left, **_new_partner()}
                right_rows.append(reverse)
            reverse.update(existing)
            reverse["pokemon"] = left


def _finalize_partners(report: Dict[str, Any]) -> None:
    for rows in (report.get("partners") or {}).values():
        for row in rows:
            shared_games = int(row.get("shared_wins", 0) or 0) + int(row.get("shared_losses", 0) or 0)
            row["shared_win_rate"] = (
                int(row.get("shared_wins", 0) or 0) / shared_games
                if shared_games else 0.0
            )
        rows.sort(
            key=lambda row: (
                int(row.get("teams_together", 0) or 0),
                float(row.get("shared_win_rate", 0.0) or 0.0),
            ),
            reverse=True,
        )


def incremental_update(previous_history: Path, new_cache_dir: Path) -> Dict[str, Any]:
    """Merge newly cached event snapshots into the committed aggregate."""
    if previous_history.exists():
        try:
            report = json.loads(previous_history.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            report = {}
    else:
        report = {}

    if not isinstance(report, dict) or not report.get("pokemon"):
        raise RuntimeError(
            "No usable Champions history exists. Seed champions_meta_history.json "
            "from the completed local backfill before running automatic sync."
        )

    snapshots: List[Dict[str, Any]] = []
    for path in sorted(new_cache_dir.glob("*.json")):
        if path.name == "manifest.json":
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                snapshots.append(payload)
        except (OSError, json.JSONDecodeError) as exc:
            print(f"WARNING: could not read {path.name}: {exc}")

    dates = [date for date in (_event_date(s) for s in snapshots) if date]
    previous_reference = _parse_date(report.get("reference_date"))
    reference = max(dates + ([previous_reference] if previous_reference else []), default=datetime.now(timezone.utc))

    _decay_existing(report, reference)
    for snapshot in snapshots:
        _add_snapshot(report, snapshot, reference)

    for stats in (report.get("pokemon") or {}).values():
        _finalize(stats)
    _finalize_partners(report)

    report["schema_version"] = 1
    report["generated_at"] = datetime.now(timezone.utc).isoformat()
    report["reference_date"] = reference.isoformat()
    report["recency_half_life_days"] = RECENCY_HALF_LIFE_DAYS
    report["events_processed"] = int(report.get("events_processed", 0) or 0) + len(snapshots)

    return report
