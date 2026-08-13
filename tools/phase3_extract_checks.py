from pathlib import Path
import re

APP = Path("app.py")
ENGINE = Path("champions/meta_engine.py")
WORKFLOW = Path(".github/workflows/phase3-refactor.yml")
SCRIPT = Path("tools/phase3_extract_checks.py")

app = APP.read_text(encoding="utf-8")
engine = ENGINE.read_text(encoding="utf-8")

# Locate the complete standalone get_meta_relevant_checks function.
pattern = re.compile(
    r"\n# ==========================================\n"
    r"# 3\. META-GATED CHECKS, COUNTERS & SYNERGY\n"
    r"# ==========================================\n\n"
    r"def get_meta_relevant_checks\(.*?\n\n\n# -----------------------------------------------------------------------------\n"
    r"0\. COMPETITIVE META EVALUATION ENGINE & DATA MODELS\n"
    r"# -----------------------------------------------------------------------------\n",
    re.S,
)
match = pattern.search(app)
if not match:
    raise SystemExit("Phase 3: get_meta_relevant_checks block was not found in app.py")

block = match.group(0)
start = block.index("def get_meta_relevant_checks(")
end = block.index("\n\n\n# -----------------------------------------------------------------------------\n0. COMPETITIVE")
function = block[start:end]

# The extracted function should depend only on the shared type chart and move helper.
function = function.replace(
    "            relations = get_type_relationships(\n                candidate_type\n            )\n\n            resisted = {\n                r[\"name\"].title()\n                for r in relations.get(\n                    \"half_damage_from\",\n                    []\n                )\n            }\n\n            if any(\n                weakness in resisted\n                for weakness in target_weaknesses\n            ):\n                defensive_score += 5",
    "            matchup = TYPE_CHART_DATA.get(candidate_type, {})\n            if any(\n                matchup.get(weakness, 1.0) < 1.0\n                for weakness in target_weaknesses\n            ):\n                defensive_score += 5"
)

# Remove the old block from app.py while retaining the section marker.
replacement = "\n# -----------------------------------------------------------------------------\n# 0. COMPETITIVE META EVALUATION ENGINE & DATA MODELS\n# -----------------------------------------------------------------------------\n"
app = app[:match.start()] + replacement + app[match.end():]

# Add the new import for the extracted function if it is not already present.
old_import = "from champions.meta_engine import (\n    MoveProfile,\n    MonMetaProfile,\n    TeamEvaluator,\n    build_meta_profiles_from_data,\n    create_move_profile,\n)"
new_import = "from champions.meta_engine import (\n    MoveProfile,\n    MonMetaProfile,\n    TeamEvaluator,\n    build_meta_profiles_from_data,\n    create_move_profile,\n    get_meta_relevant_checks,\n)"
if old_import not in app:
    raise SystemExit("Phase 3: expected meta_engine import block was not found")
app = app.replace(old_import, new_import, 1)

# The function uses TYPE_CHART_DATA and fetch_move_type; both are module dependencies.
engine_import = "from champions.constants import TYPE_CHART_DATA\n"
engine_import_new = "from champions.constants import TYPE_CHART_DATA\nfrom champions.meta_utils import fetch_move_type\n"
if engine_import not in engine:
    raise SystemExit("Phase 3: expected constants import was not found in meta_engine.py")
engine = engine.replace(engine_import, engine_import_new, 1)

# Insert the function immediately before create_move_profile, keeping the engine organized.
marker = "\n\ndef create_move_profile(name: str, raw_move_data: dict) -> MoveProfile:\n"
if marker not in engine:
    raise SystemExit("Phase 3: create_move_profile marker was not found")
engine = engine.replace(marker, "\n\n" + function + marker, 1)

APP.write_text(app, encoding="utf-8")
ENGINE.write_text(engine, encoding="utf-8")

print("Phase 3 extraction complete.")
