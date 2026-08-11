"""Phase 5 diagnostic for the Champions tournament data layer.

This file is intentionally separate from both app.py and champions_data.py.
It does not build the meta database and it does not change any application
state.  It simply proves that the Phase 4 data layer can reach Limitless and
shows us the real shape of one completed Champions tournament payload before
we write the permanent parser.

Run locally with:

    python test_champions_data.py

Expected behaviour:
    1. Find recent VGC tournaments from Limitless.
    2. Keep only M-A / M-B events.
    3. Skip events that are still running or have no standings.
    4. Load the first suitable completed event.
    5. Print a compact diagnostic summary.
    6. Report the actual decklist/teamlist shape without dumping the entire
       payload.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, Optional

from champions_data import (
    CHAMPIONS_REGULATIONS,
    get_limitless_tournament_details,
    get_limitless_tournament_standings,
    list_limitless_tournaments,
    load_limitless_event_data,
)


MAX_EVENT_SEARCH_PAGES = 3
TOURNAMENTS_PER_PAGE = 50


def _type_name(value: Any) -> str:
    """Return a compact description of a Python payload value."""

    if isinstance(value, dict):
        keys = list(value.keys())[:10]
        suffix = "..." if len(value) > 10 else ""
        return f"dict(keys={keys!r}{suffix})"

    if isinstance(value, list):
        if not value:
            return "list(empty)"
        return f"list(len={len(value)}, first={_type_name(value[0])})"

    return type(value).__name__


def _iter_champions_candidates() -> Iterable[Dict[str, Any]]:
    """Yield recent M-A/M-B tournament candidates from the public API."""

    for page in range(1, MAX_EVENT_SEARCH_PAGES + 1):
        tournaments = list_limitless_tournaments(
            page=page,
            limit=TOURNAMENTS_PER_PAGE,
        )

        if not tournaments:
            return

        for tournament in tournaments:
            if tournament.get("format") in CHAMPIONS_REGULATIONS:
                yield tournament


def find_completed_event() -> Optional[str]:
    """Find the first suitable completed Champions tournament."""

    checked = 0

    for tournament in _iter_champions_candidates():
        event_id = str(tournament.get("id") or "").strip()
        if not event_id:
            continue

        checked += 1

        try:
            details = get_limitless_tournament_details(event_id)
            standings = get_limitless_tournament_standings(event_id)
        except Exception as exc:  # diagnostic script: continue to next event
            print(f"[SKIP] {event_id}: {type(exc).__name__}: {exc}")
            continue

        if details.get("format") not in CHAMPIONS_REGULATIONS:
            continue

        # A completed tournament must have standings.  We also prefer events
        # whose standings contain final placements.
        has_placement = any(
            isinstance(row, dict) and row.get("placing") is not None
            for row in standings
        )

        if standings and has_placement:
            print(
                f"[FOUND] {event_id} — {details.get('name', '')} "
                f"({details.get('format', '')}), "
                f"players={details.get('players', 0)}, checked={checked}"
            )
            return event_id

    return None


def print_decklist_shape(standings: list[Dict[str, Any]]) -> None:
    """Print the shape of the first available team/decklist payload."""

    for row in standings:
        if not isinstance(row, dict):
            continue

        if "decklist" not in row:
            continue

        decklist = row.get("decklist")
        print(f"  decklist type: {_type_name(decklist)}")

        if isinstance(decklist, dict):
            print(f"  decklist keys: {list(decklist.keys())[:20]}")
        elif isinstance(decklist, list):
            print(f"  decklist length: {len(decklist)}")
            if decklist:
                first = decklist[0]
                print(f"  first decklist item: {_type_name(first)}")
                if isinstance(first, dict):
                    print(f"  first item keys: {list(first.keys())[:20]}")
        else:
            print(f"  decklist value type: {type(decklist).__name__}")

        return

    print("  No decklist field was present in the sampled standings.")


def run_phase5_diagnostic() -> int:
    """Run the Phase 5 source-shape diagnostic."""

    print("=" * 72)
    print("POKÉMON CHAMPIONS — PHASE 5 DATA-SOURCE DIAGNOSTIC")
    print("=" * 72)
    print("Source: Limitless Tournament Platform")
    print(f"Accepted regulations: {sorted(CHAMPIONS_REGULATIONS)}")
    print()

    event_id = find_completed_event()
    if event_id is None:
        print("[FAIL] No suitable completed M-A/M-B tournament was found.")
        return 1

    print()
    print(f"Loading normalized event: {event_id}")

    try:
        data = load_limitless_event_data(event_id)
    except Exception as exc:
        print(f"[FAIL] Normalized event load failed: {type(exc).__name__}: {exc}")
        return 1

    event = data["event"]
    results = data["results"]
    teams = data["teams"]

    print()
    print("EVENT")
    print(f"  id:          {event.event_id}")
    print(f"  name:        {event.name}")
    print(f"  date:        {event.date}")
    print(f"  regulation:  {event.regulation}")
    print(f"  players:     {event.player_count}")
    print(f"  completed:   {event.completed}")
    print()

    print("RESULTS")
    print(f"  normalized results: {len(results)}")
    if results:
        sample = results[0]
        print(f"  sample player:      {sample.player_name}")
        print(f"  sample placement:   {sample.placement}")
        print(f"  sample record:      {sample.wins}-{sample.losses}-{sample.draws}")
        print(f"  sample top cut:     {sample.top_cut}")
        print(f"  sample drop round:  {sample.dropped_round}")
    print()

    print("TEAMLIST / DECKLIST SHAPE")
    raw_standings = get_limitless_tournament_standings(event_id)
    print_decklist_shape(raw_standings)
    print()

    nonempty_teams = sum(1 for team in teams if team.pokemon)
    print("TEAM EXTRACTION")
    print(f"  team records:       {len(teams)}")
    print(f"  non-empty teams:    {nonempty_teams}")

    if teams:
        sample_team = next((team for team in teams if team.pokemon), teams[0])
        print(f"  sample player:      {sample_team.player_name}")
        print(f"  extracted Pokémon:  {sample_team.pokemon}")

    print()
    if nonempty_teams == 0:
        print("[RESULT] API access works, but the Champions teamlist shape needs")
        print("         a dedicated parser before Pokémon statistics can be built.")
    else:
        print("[RESULT] API access and basic team extraction both work.")

    print("=" * 72)
    return 0


if __name__ == "__main__":
    raise SystemExit(run_phase5_diagnostic())
