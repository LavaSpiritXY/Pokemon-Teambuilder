# Phase 17 — Champions-aware profile integration and visual alignment

## Goal
Bring the Champions tournament evidence into the existing profile presentation without replacing the existing viability engine or abruptly changing scoring.

## Scope
- Keep the existing Meta Profile as the primary viability presentation.
- Present Champions tournament evidence as a visually consistent companion section.
- Add a clear separation between model-derived viability and observed tournament evidence.
- Surface tournament partners using the existing card/table visual language.
- Preserve existing scoring and metadata functions.
- Do not remove legacy recommendations yet; Phase 18 will replace/augment recommendation sources after validation.

## Safety
- Missing Champions data must render safely.
- Tournament evidence must remain bounded/confidence-weighted.
- No changes to `calculate_meta_viability()` scoring in this phase.
- No destructive removal of existing profile sections.

## Validation
Run `python test_phase17.py` after pulling the phase files. Then run the Streamlit app and visually inspect Kingambit, Garchomp, and Farigiraf.
