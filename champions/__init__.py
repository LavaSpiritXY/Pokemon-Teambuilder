"""Champions package bootstrap.

The counter engine historically fetched individual move metadata from PokeAPI.
Install the local bulk resolver immediately after package initialisation so
all existing counter-engine call sites transparently use the fast path.
"""

try:
    from champions import counter_engine as _counter_engine
    from champions.move_metadata import get_move_metadata as _get_move_metadata

    # Preserve the counter engine's public API while replacing only its slow
    # per-move network resolver. Unknown moves still use the resolver's own
    # fallback path, so this remains backwards compatible.
    _counter_engine._fetch_move_metadata = _get_move_metadata
except Exception:
    # Never make package import fail merely because the optional optimisation
    # cannot initialise. The original counter engine remains usable.
    pass
