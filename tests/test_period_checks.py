import importlib.util
import unittest
from datetime import date, timedelta

import pandas as pd
from scripts.period_checks import validate_sample_history, validate_sample_test, validate_full_periods

HAS_DUCKDB = importlib.util.find_spec("duckdb") is not None


class SamplePeriodTests(unittest.TestCase):
    def setUp(self):
        dates = pd.date_range("2024-06-26", periods=7)
        self.frame = pd.DataFrame([
            {"store_id": 3, "product_id": product, "dt": day}
            for product in [11, 22] for day in dates
        ])

    def test_complete_expected_period_passes(self):
        validate_sample_test(self.frame, [11, 22], 3)

    def test_wrong_date_is_rejected_even_with_same_row_count(self):
        frame = self.frame.copy()
        frame.loc[0, "dt"] = pd.Timestamp("2024-07-03")
        with self.assertRaisesRegex(ValueError, "official test date"):
            validate_sample_test(frame, [11, 22], 3)

    def test_uneven_series_or_duplicates_are_rejected(self):
        frame = self.frame.copy()
        frame.loc[0, "product_id"] = 22
        with self.assertRaises(ValueError):
            validate_sample_test(frame, [11, 22], 3)
        frame = self.frame.copy()
        frame.loc[0, "dt"] = frame.loc[1, "dt"]
        with self.assertRaises(ValueError):
            validate_sample_test(frame, [11, 22], 3)


class SampleHistoryTests(unittest.TestCase):
    def setUp(self):
        dates = pd.date_range("2024-06-04", "2024-06-25")
        self.frame = pd.DataFrame([
            {"store_id": 3, "product_id": product, "dt": day,
             "split": "training" if day < pd.Timestamp("2024-06-12") else "validation"}
            for product in [11, 22] for day in dates
        ])

    def test_documented_period_passes(self):
        validate_sample_history(self.frame, [11, 22], 3)

    def test_future_training_row_cannot_be_used_for_factors(self):
        frame = self.frame.copy()
        frame.loc[0, "dt"] = pd.Timestamp("2024-07-03")
        with self.assertRaisesRegex(ValueError, "Training must end"):
            validate_sample_history(frame, [11, 22], 3)

    def test_missing_validation_date_rejected(self):
        frame = self.frame.drop(index=8)
        with self.assertRaisesRegex(ValueError, "internal validation date"):
            validate_sample_history(frame, [11, 22], 3)


@unittest.skipUnless(HAS_DUCKDB, "duckdb is needed for full-period SQL checks")
class FullPeriodTests(unittest.TestCase):
    def make_db(self, history, test):
        import duckdb
        db = duckdb.connect()
        db.register("history", pd.DataFrame(history, columns=["store_id", "product_id", "day"]))
        db.register("test_data", pd.DataFrame(test, columns=["store_id", "product_id", "day"]))
        self.addCleanup(db.close)
        return db

    def setUp(self):
        self.history = [(1, product, date(2024, 6, 25)) for product in (1, 2)]
        self.test = [(1, product, date(2024, 6, 26) + timedelta(days=i))
                     for product in (1, 2) for i in range(7)]

    def test_complete_period_passes(self):
        validate_full_periods(self.make_db(self.history, self.test))

    def test_earlier_evaluation_data_cannot_enter_training(self):
        old_history = [(1, 1, date(2024, 6, 25))]
        early = [(1, 1, date(2024, 6, 5) + timedelta(days=i)) for i in range(7)]
        with self.assertRaisesRegex(ValueError, "expected time split"):
            validate_full_periods(self.make_db(old_history, early))

    def test_incomplete_series_rejected_even_when_total_is_unchanged(self):
        changed = self.test.copy()
        changed[0] = changed[7]
        with self.assertRaisesRegex(ValueError, "seven unique dates"):
            validate_full_periods(self.make_db(self.history, changed))

    def test_missing_series_rejected(self):
        with self.assertRaisesRegex(ValueError, "seven unique dates"):
            validate_full_periods(self.make_db(self.history, self.test[7:]))


if __name__ == "__main__":
    unittest.main()
