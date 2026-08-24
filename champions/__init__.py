"""Champions package bootstrap.

The counter engine historically fetched individual move metadata from PokeAPI.
Install the local bulk resolver immediately after package initialisation so
all existing counter-engine call sites transparently use the fast path.
"""

try:
    from functools import lru_cache

    from champions import counter_engine as _counter_engine
    from champions import tournament_data as _tournament_data
    from champions import meta_analytics as _meta_analytics
    from champions.counter_quality import apply_tournament_move_quality as _apply_tournament_move_quality
    from champions.counter_practical import apply_practical_counter_ranking as _apply_practical_counter_ranking
    from champions.history_data import history_revision as _history_revision
    from champions.move_metadata import get_move_metadata as _get_move_metadata

    # Preserve the counter engine's public API while replacing only the slow
    # per-move network resolver. Unknown moves still use the resolver's own
    # fallback path, so this remains backwards compatible.
    _counter_engine._fetch_move_metadata = _get_move_metadata

    # Cache the already-local move resolver too. The counter hot path can ask
    # for the same move from pressure, utility/priority, and target-STAB checks.
    # The resolver returns fresh dicts and the engine only reads them, so an
    # immutable-key cache is safe and avoids repeated normalisation/dict work.
    _original_move_metadata = _counter_engine._move_metadata

    @lru_cache(maxsize=4096)
    def _cached_move_metadata(move_name: str):
        return _original_move_metadata(str(move_name))

    _counter_engine._move_metadata = _cached_move_metadata

    # Cache tournament metrics by both Pokémon and history revision. The same
    # candidate can be inspected by the counter engine and then again by the
    # practical-ranking layer; both should reuse the exact same metrics object
    # instead of re-reading/reprocessing tournament history.
    _original_calculate_tournament_metrics = _tournament_data.calculate_tournament_metrics

    @lru_cache(maxsize=256)
    def _cached_tournament_metrics(name: str, revision: str):
        return _original_calculate_tournament_metrics(name)

    def _calculate_tournament_metrics_cached(name):
        lookup_name = str(name or "")
        lookup_key = lookup_name.strip().lower()

        # Explicit tournament imports are mutable test/runtime state and are
        # intentionally independent of the generated historical JSON. Never
        # reuse a history-only cached result for one of these records because
        # the in-memory CHAMPIONS_META_DB may have changed without a history
        # file revision.
        explicit_record = _tournament_data.CHAMPIONS_META_DB.get(lookup_key)
        if isinstance(explicit_record, dict) and explicit_record.get("_explicit_import"):
            return _original_calculate_tournament_metrics(lookup_name)

        return _cached_tournament_metrics(
            lookup_name,
            str(_history_revision()),
        )

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

    # ------------------------------------------------------------------
    # Teammate candidate-score reuse
    # ------------------------------------------------------------------
    # _candidate_score is called once per candidate, but the old implementation
    # rebuilt the target's archetypes and weakness set on every call. Cache that
    # target-wide context for the current target and memoize the small type-chart
    # relation sets used by each candidate type. This changes no score formula;
    # it only moves repeated deterministic work out of the 60-candidate loop.
    _candidate_context_cache = {"key": None, "archetypes": frozenset(), "weaknesses": frozenset()}

    @lru_cache(maxsize=32)
    def _candidate_type_relations(type_name: str):
        relations = _meta_analytics.get_type_relationships(type_name) or {}
        resistances = frozenset(
            item["name"].title()
            for item in relations.get("half_damage_from", [])
            if isinstance(item, dict) and item.get("name")
        )
        immunities = frozenset(
            item["name"].title()
            for item in relations.get("no_damage_from", [])
            if isinstance(item, dict) and item.get("name")
        )
        return resistances, immunities

    def _candidate_score_optimized(
        target_data,
        candidate_data,
        tournament_partners,
        candidate_name,
    ):
        target_types = tuple(str(item) for item in target_data.get("types", []))
        target_stats = target_data.get("stats", {}) or {}
        target_moves = tuple(str(item) for item in target_data.get("moves", []))
        target_abilities = tuple(str(item) for item in target_data.get("abilities", []))
        context_key = (
            target_types,
            tuple(sorted((str(k), float(v or 0)) for k, v in target_stats.items())),
            target_moves,
            target_abilities,
        )
        if _candidate_context_cache["key"] != context_key:
            _candidate_context_cache["key"] = context_key
            _candidate_context_cache["archetypes"] = frozenset(
                a.get("name") for a in _meta_analytics.detect_archetypes(target_data)
            )
            _candidate_context_cache["weaknesses"] = frozenset(
                _meta_analytics._type_weaknesses(list(target_types))
            )

        score = 0.0
        key = _meta_analytics.canonical_species_key(candidate_name)
        score += min(40.0, float(tournament_partners.get(key, 0) or 0) * 8.0)

        candidate_archetypes = {
            a.get("name") for a in _meta_analytics.detect_archetypes(candidate_data)
        }
        score += len(_candidate_context_cache["archetypes"] & candidate_archetypes) * 4.0

        for candidate_type in candidate_data.get("types", []):
            resistances, immunities = _candidate_type_relations(str(candidate_type))
            score += sum(
                8.0 if weakness in immunities else 5.0
                for weakness in _candidate_context_cache["weaknesses"]
                if weakness in immunities or weakness in resistances
            )

        candidate_stats = candidate_data.get("stats", {}) or {}
        if (target_stats.get("attack", 100) >= target_stats.get("special-attack", 100)) != (
            candidate_stats.get("attack", 100) >= candidate_stats.get("special-attack", 100)
        ):
            score += 2.0
        return score

    _meta_analytics._candidate_score = _candidate_score_optimized

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
