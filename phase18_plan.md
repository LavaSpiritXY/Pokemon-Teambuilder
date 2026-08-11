# Phase 18 — Unified Champions Competitive Profile

## Goals
- Replace the active Phase 15/17 tournament panel with one visually consistent profile.
- Match the existing app's larger diagnostic headers and improve text contrast.
- Add Pokémon sprites to tournament partners and counter/check rows.
- Surface the Phase 16 confidence-weighted tournament viability adjustment.
- Keep existing speed, offensive profile, momentum, and hazard/utility diagnostics visible.
- Present the existing matchup-engine counters with Champions tournament usage as a prioritisation signal.

## Accuracy boundary
The validated Champions historical dataset contains team composition/results and partner evidence, not direct opponent Pokémon-vs-Pokémon matchup records. Phase 18 therefore does **not** label tournament usage as a direct counter record. Counter candidates still come from the existing matchup engine and are only prioritised using real Champions tournament presence.

## Safety / isolation
- `champions_phase18.py` contains the new renderer.
- `apply_phase18_patch.py` makes exactly two guarded changes to `app.py`: import and active UI call.
- Existing viability and metadata engines are not rewritten.
- The legacy renderer remains defined for rollback but is no longer actively called after the patch.
