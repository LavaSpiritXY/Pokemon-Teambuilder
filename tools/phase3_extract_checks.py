from pathlib import Path
import re

APP = Path("app.py")
ENGINE = Path("champions/meta_engine.py")

app = APP.read_text(encoding="utf-8")
engine = ENGINE.read_text(encoding="utf-8")

# Extract the complete standalone function without depending on the older
# section-header formatting that caused the first automated attempt to fail.
match = re.search(
    r"\ndef get_meta_relevant_checks\(.*?(?=\n\n# -----------------------------------------------------------------------------\n# 0\. COMPETITIVE META EVALUATION ENGINE & DATA MODELS)",
    app,
    re.S,
)

if not match:
    raise SystemExit("Phase 3: get_meta_relevant_checks function was not found in app.py")

function = match.group(0).strip("\n")

# Keep the extracted function self-contained inside the meta engine.
function = function.replace(
    "            relations = get_type_relationships(\n                candidate_type\n            )\n\n            resisted = {\n                r[\"name\"].title()\n                for r in relations.get(\n                    \"half_damage_from\",\n                    []\n                )\n            }\n\n            if any(\n                weakness in resisted\n                for weakness in target_weaknesses\n            ):\n                defensive_score += 5",
    "            matchup = TYPE_CHART_DATA.get(candidate_type, {})\n            if any(\n                matchup.get(weakness, 1.0) < 1.0\n                for weakness in target_weaknesses\n            ):\n                defensive_score += 5",
)

# Remove the old implementation from app.py.
app = app[:match.start()] + "\n" + app[match.end():]

# Wire the extracted function into app.py.
old_import = "from champions.meta_engine import (\n    MoveProfile,\n    MonMetaProfile,\n    TeamEvaluator,\n    build_meta_profiles_from_data,\n    create_move_profile,\n)"
new_import = "from champions.meta_engine import (\n    MoveProfile,\n    MonMetaProfile,\n    TeamEvaluator,\n    build_meta_profiles_from_data,\n    create_move_profile,\n    get_meta_relevant_checks,\n)"
if old_import in app:
    app = app.replace(old_import, new_import, 1)
elif "get_meta_relevant_checks" not in app[:3000]:
    raise SystemExit("Phase 3: meta_engine import block was not found")

# Give the extracted function access to the shared type chart and move helper.
if "from champions.constants import TYPE_CHART_DATA\n" not in engine:
    raise SystemExit("Phase 3: constants import was not found in meta_engine.py")
if "from champions.meta_utils import fetch_move_type\n" not in engine:
    engine = engine.replace(
        "from champions.constants import TYPE_CHART_DATA\n",
        "from champions.constants import TYPE_CHART_DATA\nfrom champions.meta_utils import fetch_move_type\n",
        1,
    )

# Avoid duplicate extraction if this script is ever retried.
if "def get_meta_relevant_checks(" not in engine:
    marker = "\n\ndef create_move_profile(name: str, raw_move_data: dict) -> MoveProfile:\n"
    if marker not in engine:
        raise SystemExit("Phase 3: create_move_profile marker was not found")
    engine = engine.replace(marker, "\n\n" + function + marker, 1)

APP.write_text(app, encoding="utf-8")
ENGINE.write_text(engine, encoding="utf-8")

print("Phase 3 extraction complete.")
