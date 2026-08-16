"""Champions package bootstrap.

The counter engine historically fetched individual move metadata from PokeAPI.
Install the local bulk resolver immediately after package initialisation so
all existing counter-engine call sites transparently use the fast path.
"""

try:
    from functools import lru_cache

    from champions import counter_engine as _counter_engine
    from champions import tournament_data as _tournament_data
    from champions.counter_quality import apply_tournament_move_quality as _apply_tournament_move_quality
    from champions.counter_practical import apply_practical_counter_ranking as _apply_practical_counter_ranking
    from champions.history_data import history_revision as _history_revision
    from champions.move_metadata import get_move_metadata as _get_move_metadata

    # Preserve the counter engine's public API while replacing only the slow
    # per-move network resolver. Unknown moves still use the resolver's own
    # fallback path, so this remains backwards compatible.
    _counter_engine._fetch_move_metadata = _get_move_metadata

    # Cache tournament metrics by both Pokémon and history revision. The same
    # candidate can be inspected by the counter engine and then again by the
    # practical-ranking layer; both should reuse the exact same metrics object
    # instead of re-reading/reprocessing tournament history.
    _original_calculate_tournament_metrics = _tournament_data.calculate_tournament_metrics

    @lru_cache(maxsize=256)
    def _cached_tournament_metrics(name: str, revision: str):
        return _original_calculate_tournament_metrics(name)

    def _calculate_tournament_metrics_cached(name):
        return _cached_tournament_metrics(str(name or ""), str(_history_revision()))

    _tournament_data.calculate_tournament_metrics = _calculate_tournament_metrics_cached

    # ------------------------------------------------------------------
    # Hot-path matchup reuse
    # ------------------------------------------------------------------
    # The counter engine evaluates many candidates against the same target.
    # Its type-effectiveness helper is pure for a given attacking type and
    # defending type tuple, so memoize it globally. This removes repeated
    # construction of the same type-chart sets without changing any scores.
    _original_effectiveness = _counter_engine._effectiveness

    @lru_cache(maxsize=256)
    def _cached_effectiveness(attacking_type: str, defending_types: tuple[str, ...]):
        return _original_effectiveness(attacking_type, defending_types)

    def _effectiveness_cached(attacking_type, defending_types):
        return _cached_effectiveness(
            str(attacking_type),
            tuple(str(item) for item in defending_types),
        )

    _counter_engine._effectiveness = _effectiveness_cached

    # The target's legal STAB move list is also inspected once per candidate.
    # Cache that calculation by the target's immutable move/stat/type snapshot
    # and candidate typing. Tournament move frequencies remain part of the key,
    # so changing history data cannot reuse stale evidence.
    _original_target_damaging_stabs = _counter_engine._target_damaging_stabs

    @lru_cache(maxsize=512)
    def _cached_target_damaging_stabs(
        target_types: tuple[str, ...],
        attack: float,
        special_attack: float,
        moves: tuple[str, ...],
        candidate_types: tuple[str, ...],
        observed_items: tuple[tuple[str, float], ...],
    ):
        target = {
            "types": list(target_types),
            "stats": {"attack": attack, "special-attack": special_attack},
            "moves": list(moves),
            "tournament_moves": dict(observed_items),
        }
        return _original_target_damaging_stabs(target, candidate_types)

    def _target_damaging_stabs_cached(target, candidate_types):
        stats = target.get("stats", {}) or {}
        moves = tuple(str(move) for move in target.get("moves", []) if str(move).strip())
        observed = _counter_engine._observed_moves(target)
        return _cached_target_damaging_stabs(
            tuple(str(item) for item in target.get("types", [])),
            float(stats.get("attack", 0) or 0),
            float(stats.get("special-attack", 0) or 0),
            moves,
            tuple(str(item) for item in candidate_types),
            tuple(sorted(observed.items())),
        )

    _counter_engine._target_damaging_stabs = _target_damaging_stabs_cached

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
