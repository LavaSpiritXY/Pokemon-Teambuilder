"""Champions package bootstrap.

The counter engine historically fetched individual move metadata from PokeAPI.
Install the local bulk resolver immediately after package initialisation so
all existing counter-engine call sites transparently use the fast path.
"""

try:
    from champions import counter_engine as _counter_engine
    from champions.move_metadata import get_move_metadata as _get_move_metadata
    from champions.counter_quality import apply_tournament_move_quality as _apply_tournament_move_quality
    from champions.counter_practical import apply_practical_counter_ranking as _apply_practical_counter_ranking

    # Preserve the counter engine's public API while replacing only its slow
    # per-move network resolver. Unknown moves still use the resolver's own
    # fallback path, so this remains backwards compatible.
    _counter_engine._fetch_move_metadata = _get_move_metadata

    # Keep matchup logic dominant, then apply tournament move evidence and a
    # separate practical ranking pass. Both layers operate on already-computed
    # assessments and therefore add no per-candidate network requests.
    _original_rank_counters = _counter_engine.rank_counters

    def _rank_counters_with_tournament_move_quality(*args, **kwargs):
        assessments = _original_rank_counters(*args, **kwargs)
        assessments = _apply_tournament_move_quality(assessments)
        return _apply_practical_counter_ranking(assessments)

    _counter_engine.rank_counters = _rank_counters_with_tournament_move_quality
except Exception:
    # Never make package import fail merely because an optional optimisation
    # cannot initialise. The original counter engine remains usable.
    pass
