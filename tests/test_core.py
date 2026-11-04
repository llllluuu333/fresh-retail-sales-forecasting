import unittest
import pandas as pd
from forecasting.core import prepare, fit_weekday_factors, predict, evaluate


def sample():
    dates = pd.date_range('2024-01-01', periods=14)
    return pd.DataFrame({'store_id': 1, 'product_id': 10, 'dt': dates,
                         'sale_amount': [1.0] * 14,
                         'split': ['training'] * 7 + ['validation'] * 7})


class ForecastTests(unittest.TestCase):
    def test_future_sales_do_not_change_factors_or_same_day_forecast(self):
        original = prepare(sample())
        changed = sample()
        changed.loc[7, 'sale_amount'] = 100.0
        changed = prepare(changed)
        f1, f2 = fit_weekday_factors(original), fit_weekday_factors(changed)
        pd.testing.assert_series_equal(f1, f2)
        self.assertEqual(predict(original, f1).loc[7, 'adjusted'],
                         predict(changed, f2).loc[7, 'adjusted'])
        self.assertNotEqual(predict(original, f1).loc[8, 'adjusted'],
                            predict(changed, f2).loc[8, 'adjusted'])

    def test_duplicate_and_date_gap_are_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            prepare(pd.concat([sample(), sample().iloc[[0]]]))
        with self.assertRaisesRegex(ValueError, 'consecutive'):
            prepare(sample().drop(index=4))

    def test_metrics_and_zero_denominator(self):
        rows = pd.DataFrame({'sale_amount': [2., 4.], 'pred': [3., 2.]})
        metrics = evaluate(rows, 'pred')
        self.assertAlmostEqual(metrics['mae'], 1.5)
        self.assertAlmostEqual(metrics['wape'], 0.5)
        self.assertAlmostEqual(metrics['bias'], -1 / 6)
        with self.assertRaisesRegex(ValueError, 'denominator'):
            evaluate(pd.DataFrame({'sale_amount': [0.], 'pred': [1.]}), 'pred')


if __name__ == '__main__':
    unittest.main()
