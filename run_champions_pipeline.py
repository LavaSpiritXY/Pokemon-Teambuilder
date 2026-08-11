"""Phase 7 diagnostic: run the Champions ingestion + aggregation pipeline.

This file is intentionally standalone. It does not import Streamlit or app.py.
Run locally with:
    python run_champions_pipeline.py

It prints a compact report so we can verify what the live source actually
returns before connecting anything to CHAMPIONS_META_DB.
"""

from __future__ import annotations

from champions_data import (
    CHAMPIONS_REGULATIONS,
    list_limitless_tournaments,
    load_limitless_event_data,
)
from champions_aggregation import aggregate_pokemon_statistics


def main() -> None:
    print("=== Pokémon Champions tournament pipeline diagnostic ===")
    print(f"Supported regulations: {', '.join(sorted(CHAMPIONS_REGULATIONS))}")
    print()

    tournaments = []
    for regulation in sorted(CHAMPIONS_REGULATIONS):
        try:
            rows = list_limitless_tournaments(
                page=1,
                limit=20,
                regulation=regulation,
            )
            tournaments.extend(rows)
            print(f"{regulation}: found {len(rows)} matching tournament(s)")
        except Exception as exc:
            print(f"{regulation}: ERROR while listing tournaments: {exc}")

    if not tournaments:
        print("No matching tournaments were returned. Stop here; do not modify app.py.")
        return

    event = next((row for row in tournaments if row.get("id")), None)
    if event is None:
        print("Returned tournament rows contain no usable IDs. Stop here.")
        return

    event_id = event["id"]
    print()
    print(f"Testing event: {event_id}")
    print(f"Name: {event.get('name', '')}")
    print(f"Format: {event.get('format', '')}")

    try:
        payload = load_limitless_event_data(event_id)
    except Exception as exc:
        print(f"ERROR loading event {event_id}: {exc}")
        return

    normalized_event = payload["event"]
    results = payload["results"]
    teams = payload["teams"]

    print()
    print("--- Normalized event ---")
    print(f"Players: {normalized_event.player_count}")
    print(f"Completed: {normalized_event.completed}")
    print(f"Regulation: {normalized_event.regulation}")
    print(f"Results: {len(results)}")
    print(f"Teams: {len(teams)}")

    teams_with_pokemon = [team for team in teams if team.pokemon]
    print(f"Teams with extracted Pokémon: {len(teams_with_pokemon)}")

    if teams:
        print()
        print("--- First five normalized teams ---")
        for team in teams[:5]:
            print(f"{team.player_name}: {team.pokemon}")

    print()
    print("--- First five normalized results ---")
    for result in results[:5]:
        print(
            f"{result.placement}: {result.player_name} "
            f"({result.wins}-{result.losses}-{result.draws}) "
            f"top_cut={result.top_cut}"
        )

    try:
        meta_db = aggregate_pokemon_statistics(
            event=normalized_event,
            results=results,
            teams=teams,
        )
    except Exception as exc:
        print()
        print(f"ERROR aggregating event {event_id}: {exc}")
        return

    print()
    print("--- Aggregation ---")
    print(f"Pokémon records produced: {len(meta_db)}")

    if meta_db:
        ranked = sorted(
            meta_db.items(),
            key=lambda item: item[1]["appearances"],
            reverse=True,
        )
        print("Most-used extracted Pokémon:")
        for key, record in ranked[:10]:
            print(
                f"  {key}: appearances={record['appearances']}, "
                f"wins={record['wins']}, losses={record['losses']}, "
                f"win_rate={record['win_rate']:.3f}, "
                f"partners={len(record['partners'])}"
            )


if __name__ == "__main__":
    main()
