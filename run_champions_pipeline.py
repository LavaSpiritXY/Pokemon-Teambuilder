"""Phase 8 diagnostic: verify historical discovery and exact tournament cuts."""

from __future__ import annotations

from champions_data import load_limitless_event_data
from champions_aggregation import aggregate_pokemon_statistics
from champions_phase8_safe import (
    discover_champions_tournaments,
    get_verified_cut,
    summarize_discovery,
)


def main() -> None:
    print("=== Pokémon Champions Phase 8 diagnostic ===")
    print()

    try:
        tournaments = discover_champions_tournaments(
            page_limit=100,
            max_pages=100,
        )
    except Exception as exc:
        print(f"ERROR during paginated tournament discovery: {exc}")
        return

    summary = summarize_discovery(tournaments)
    print("--- Historical discovery ---")
    print(f"M-A tournaments discovered: {summary.get('M-A', 0)}")
    print(f"M-B tournaments discovered: {summary.get('M-B', 0)}")
    print(f"Total discovered: {summary.get('total', 0)}")
    print(f"Marked completed by listing: {summary.get('completed', 0)}")

    if not tournaments:
        print("No Champions tournaments were discovered. Stop here.")
        return

    event = next((row for row in tournaments if row.get("id")), None)
    if event is None:
        print("No usable event IDs were returned. Stop here.")
        return

    event_id = str(event["id"])
    print()
    print(f"Testing event: {event_id}")
    print(f"Name: {event.get('name', '')}")
    print(f"Format: {event.get('format', '')}")

    try:
        payload = load_limitless_event_data(event_id)
        _, cut_size = get_verified_cut(event_id)
    except Exception as exc:
        print(f"ERROR loading event {event_id}: {exc}")
        return

    normalized_event = payload["event"]
    results = payload["results"]
    teams = payload["teams"]

    if cut_size is not None:
        for result in results:
            result.top_cut = (
                result.placement is not None
                and 1 <= result.placement <= cut_size
            )
    else:
        for result in results:
            result.top_cut = False

    print()
    print("--- Normalized event ---")
    print(f"Players: {normalized_event.player_count}")
    print(f"Completed: {normalized_event.completed}")
    print(f"Regulation: {normalized_event.regulation}")
    print(f"Results: {len(results)}")
    print(f"Teams: {len(teams)}")
    print(f"Teams with extracted Pokémon: {sum(bool(team.pokemon) for team in teams)}")
    print(f"Exact top-cut size: {cut_size if cut_size is not None else 'not exposed by source'}")

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
