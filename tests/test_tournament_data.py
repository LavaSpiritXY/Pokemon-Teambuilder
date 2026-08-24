import unittest
from unittest.mock import patch

from champions.constants import CURRENT_REGULATION
from champions.history_data import load_champions_history
from champions.tournament_data import (
    CHAMPIONS_META_DB,
    calculate_tournament_metrics,
    get_tournament_partners,
    import_champions_tournament,
)
import champions.tournament_data as tournament_data_module

print("=== LOADED TOURNAMENT DATA ===")
print("MODULE FILE:", tournament_data_module.__file__)


class TournamentDataTests(unittest.TestCase):
    def setUp(self):
        CHAMPIONS_META_DB.clear()

    def tearDown(self):
        CHAMPIONS_META_DB.clear()

    def test_missing_match_record_keeps_win_rate_unknown(self):
        history = load_champions_history()
        active_regulation = str(
            history.get("active_regulation") or CURRENT_REGULATION
        ).strip().upper()

        import_champions_tournament({
            "regulation": active_regulation,
            "players": [
                {"team": ["Whimsicott", "Farigiraf"], "placing": 1}
            ],
        })

        # Diagnostic checkpoint: determine whether the explicit test import was
        # accepted and stored before calculate_tournament_metrics() can fall
        # back to the generated historical JSON.
        explicit_record = CHAMPIONS_META_DB.get("whimsicott")
        alias_record = tournament_data_module._EXPLICIT_IMPORT_NAMES.get("whimsicott")
        print("=== EXPLICIT IMPORT DIAGNOSTIC ===")
        print("CURRENT_REGULATION:", CURRENT_REGULATION)
        print("HISTORY ACTIVE_REGULATION:", history.get("active_regulation"))
        print("TEST ACTIVE_REGULATION:", active_regulation)
        print("CHAMPIONS_META_DB KEYS:", sorted(CHAMPIONS_META_DB.keys()))
        print("WHIMSICOTT DB RECORD:", explicit_record)
        print("WHIMSICOTT ALIAS RECORD:", alias_record)
        print(
            "SAME OBJECT:",
            explicit_record is alias_record,
        )

        self.assertIsNotNone(
            explicit_record,
            "Diagnostic: the explicit Whimsicott tournament import was not inserted into CHAMPIONS_META_DB."
        )
        self.assertTrue(
            explicit_record.get("_explicit_import"),
            "Diagnostic: Whimsicott exists in CHAMPIONS_META_DB but is not marked as an explicit import."
        )
        self.assertEqual(explicit_record.get("wins"), 0)
        self.assertEqual(explicit_record.get("losses"), 0)
        self.assertEqual(explicit_record.get("match_records"), 0)

        metrics = calculate_tournament_metrics("Whimsicott")
        print("METRICS AFTER EXPLICIT IMPORT:", metrics)

        self.assertIsNone(metrics["win_rate"])
        self.assertFalse(metrics["win_rate_available"])
        self.assertEqual(metrics["top_cut_rate"], 1.0)

    def test_explicit_match_record_is_preserved(self):
        import_champions_tournament({
            "regulation": CURRENT_REGULATION,
            "players": [{
                "team": ["Whimsicott", "Farigiraf"],
                "placing": 9,
                "wins": 3,
                "losses": 1,
            }],
        })

        metrics = calculate_tournament_metrics("Whimsicott")

        self.assertEqual(metrics["win_rate"], 0.75)
        self.assertTrue(metrics["win_rate_available"])
        self.assertEqual(metrics["top_cut_rate"], 0.0)

    def test_wrong_regulation_is_ignored(self):
        import_champions_tournament({
            "regulation": "definitely-not-the-current-regulation",
            "players": [
                {"team": ["Whimsicott"], "placing": 1, "wins": 9}
            ],
        })

        self.assertEqual(CHAMPIONS_META_DB, {})

    def test_partners_are_counted_without_self_pairs(self):
        import_champions_tournament({
            "regulation": CURRENT_REGULATION,
            "players": [{
                "team": ["Whimsicott", "Farigiraf", "Whimsicott"],
                "placing": 4,
            }],
        })

        record = CHAMPIONS_META_DB["whimsicott"]

        self.assertNotIn("whimsicott", record["partners"])
        self.assertEqual(record["partners"]["farigiraf"], 1)

        partners = get_tournament_partners("Whimsicott")
        self.assertEqual(partners[0], ("farigiraf", 1))

    def test_metrics_use_synced_active_regulation(self):
        history_metrics = {
            "overall": {
                "appearances": 100,
                "wins": 50,
                "losses": 50,
                "top_cut_count": 10,
                "win_rate": 0.50,
                "top_cut_rate": 0.10,
            },
            "recent": {
                "usage_weight": 50.0,
                "win_rate": 0.50,
                "top_cut_rate": 0.10,
            },
            "current": {
                "regulation": "M-C",
                "appearances": 20,
                "win_rate": 0.80,
                "top_cut_rate": 0.30,
                "win_rate_available": True,
                "top_cut_rate_available": True,
            },
        }

        with patch(
            "champions.tournament_data.load_champions_history",
            return_value={"active_regulation": "M-C"},
        ), patch(
            "champions.tournament_data.get_history_metrics",
            return_value=history_metrics,
        ):
            metrics = calculate_tournament_metrics("Garchomp")

        self.assertEqual(metrics["current_regulation"], "M-C")
        self.assertEqual(metrics["current_regulation_appearances"], 20)
        self.assertEqual(metrics["current_regulation_win_rate"], 0.80)
        self.assertEqual(metrics["current_regulation_top_cut_rate"], 0.30)


if __name__ == "__main__":
    unittest.main()
