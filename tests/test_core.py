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


    def test_metrics_reject_nonfinite_or_negative_actuals_and_predictions(self):
        invalid_cases = [
            ('sale_amount', float('inf')), ('sale_amount', float('-inf')),
            ('sale_amount', -1.0), ('pred', float('inf')),
            ('pred', float('-inf')), ('pred', -1.0),
            ('sale_amount', float('nan')), ('pred', float('nan')),
        ]
        for column, invalid in invalid_cases:
            with self.subTest(column=column, invalid=invalid):
                rows = pd.DataFrame({'sale_amount': [2., 4.], 'pred': [3., 2.]})
                rows.loc[1, column] = invalid
                with self.assertRaises(ValueError):
                    evaluate(rows, 'pred')

    def test_unsigned_integer_subtraction_does_not_wrap(self):
        rows = pd.DataFrame({'sale_amount': pd.Series([4], dtype='uint64'),
                             'pred': pd.Series([2], dtype='uint64')})
        metrics = evaluate(rows, 'pred')
        self.assertAlmostEqual(metrics['wape'], 0.5)
        self.assertAlmostEqual(metrics['bias'], -0.5)

    def test_metrics_reject_overflow(self):
        rows = pd.DataFrame({'sale_amount': [1e308, 1e308],
                             'pred': [1e308, 1e308]})
        with self.assertRaisesRegex(ValueError, 'numerical range'):
            evaluate(rows, 'pred')
        rows = pd.DataFrame({'sale_amount': [1.0, 1.0],
                             'pred': [1e308, 1e308]})
        with self.assertRaisesRegex(ValueError, 'numerical range'):
            evaluate(rows, 'pred')

    def test_metrics_reject_boolean_and_complex_values(self):
        for values in ([True, False], [1+1j, 2+0j]):
            with self.subTest(values=values), self.assertRaises(ValueError):
                evaluate(pd.DataFrame({'sale_amount': values, 'pred': [1., 2.]}), 'pred')

    def test_metrics_reject_nonnumeric_input(self):
        with self.assertRaisesRegex(ValueError, 'must be real numeric'):
            evaluate(pd.DataFrame({'sale_amount': ['2', '4'], 'pred': [3., 2.]}), 'pred')
        with self.assertRaisesRegex(ValueError, 'must be real numeric'):
            evaluate(pd.DataFrame({'sale_amount': [2., 4.], 'pred': ['3', '2']}), 'pred')


if __name__ == '__main__':
    unittest.main()
