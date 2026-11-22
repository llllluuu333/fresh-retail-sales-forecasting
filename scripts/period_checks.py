"""Validate the fixed historical evaluation period without changing source data."""
from datetime import date
import pandas as pd

TEST_START = date(2024, 6, 26)
TEST_END = date(2024, 7, 2)
HISTORY_END = date(2024, 6, 25)


def validate_sample_history(sample, product_ids, store_id):
    """Require the documented training cutoff and complete validation window."""
    if sample.empty or sample["store_id"].isna().any() or not sample["store_id"].eq(store_id).all():
        raise ValueError("History rows must belong to the selected store")
    dates = pd.to_datetime(sample["dt"], errors="raise")
    if dates.isna().any() or not sample["split"].isin(["training", "validation"]).all():
        raise ValueError("History requires valid dates and documented split labels")
    training = dates[sample["split"].eq("training")]
    validation = sample.loc[sample["split"].eq("validation")]
    if training.empty or training.max() > pd.Timestamp("2024-06-11"):
        raise ValueError("Training must end no later than 2024-06-11")
    expected_dates = pd.date_range("2024-06-12", "2024-06-25", freq="D")
    expected = {(product, day) for product in product_ids for day in expected_dates}
    observed = list(zip(validation["product_id"], pd.to_datetime(validation["dt"])))
    if len(observed) != len(expected) or set(observed) != expected:
        raise ValueError("Each selected product must have every internal validation date")


def validate_sample_test(test, product_ids, store_id):
    """Require exactly one row for each selected product and official test date."""
    expected_dates = pd.date_range(TEST_START, TEST_END, freq="D")
    expected = {(product, day) for product in product_ids for day in expected_dates}
    if test["store_id"].isna().any() or not test["store_id"].eq(store_id).all():
        raise ValueError("Test rows must belong to the selected store")
    observed = list(zip(test["product_id"], pd.to_datetime(test["dt"])))
    if len(observed) != len(expected) or set(observed) != expected:
        raise ValueError("Each selected product must have one row for every official test date")


def validate_full_periods(db):
    """Check the dates and per-series completeness in history and test_data views."""
    history_end = db.execute("SELECT MAX(day) FROM history").fetchone()[0]
    test_start, test_end, test_rows = db.execute(
        "SELECT MIN(day), MAX(day), COUNT(*) FROM test_data").fetchone()
    if history_end != HISTORY_END or test_start != TEST_START or test_end != TEST_END or not test_rows:
        raise ValueError("History and official test dates do not match the expected time split")
    bad_series = db.execute("""
        SELECT COUNT(*) FROM (
          SELECT store_id, product_id FROM test_data
          GROUP BY store_id, product_id
          HAVING COUNT(*) <> 7 OR COUNT(DISTINCT day) <> 7
             OR MIN(day) <> DATE '2024-06-26' OR MAX(day) <> DATE '2024-07-02'
        )
    """).fetchone()[0]
    missing = db.execute("""
        SELECT COUNT(*) FROM (
          (SELECT DISTINCT store_id, product_id FROM history
           EXCEPT SELECT DISTINCT store_id, product_id FROM test_data)
          UNION ALL
          (SELECT DISTINCT store_id, product_id FROM test_data
           EXCEPT SELECT DISTINCT store_id, product_id FROM history)
        )
    """).fetchone()[0]
    if bad_series or missing:
        raise ValueError("Official test must contain seven unique dates for each historical store-product series")
