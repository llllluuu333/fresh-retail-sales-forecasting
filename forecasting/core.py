"""Fit weekday factors, generate daily forecasts, and calculate metrics."""
import numpy as np
import pandas as pd

KEYS = ['store_id', 'product_id']


def prepare(frame):
    required = set(KEYS + ['dt', 'sale_amount', 'split'])
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f'Missing columns: {sorted(missing)}')
    data = frame.copy()
    data['dt'] = pd.to_datetime(data['dt'], errors='raise')
    data['sale_amount'] = pd.to_numeric(data['sale_amount'], errors='raise')
    if data[KEYS + ['dt', 'sale_amount', 'split']].isna().any().any():
        raise ValueError('Required values cannot be null')
    if not np.isfinite(data['sale_amount']).all() or (data['sale_amount'] < 0).any():
        raise ValueError('Sales must be finite and non-negative')
    if not data['split'].isin(['training', 'validation']).all():
        raise ValueError('Split must be training or validation')
    data = data.sort_values(KEYS + ['dt']).reset_index(drop=True)
    if data.duplicated(KEYS + ['dt']).any():
        raise ValueError('Duplicate store-product-date keys')
    gaps = data.groupby(KEYS)['dt'].diff().dropna()
    if not gaps.eq(pd.Timedelta(days=1)).all():
        raise ValueError('Each series must have consecutive daily observations')
    if not (data['split'] == 'training').any() or not (data['split'] == 'validation').any():
        raise ValueError('Both training and validation rows are required')
    if data.loc[data['split'] == 'training', 'dt'].max() >= data.loc[data['split'] == 'validation', 'dt'].min():
        raise ValueError('Training dates must precede validation dates')
    return data


def fit_weekday_factors(data):
    train = data.loc[data['split'] == 'training'].copy()
    overall = train['sale_amount'].mean()
    if not np.isfinite(overall) or overall <= 0:
        raise ValueError('Training mean must be positive')
    factors = train.groupby(train['dt'].dt.day_of_week)['sale_amount'].mean() / overall
    if set(factors.index) != set(range(7)):
        raise ValueError('Training data must include all weekdays')
    return factors


def predict(data, factors, window=7):
    if window < 1:
        raise ValueError('Window must be positive')
    data = data.copy()
    sales = data.groupby(KEYS)['sale_amount']
    data['baseline'] = sales.transform(lambda x: x.shift(1).rolling(window, min_periods=window).mean())
    data['weekday_factor'] = data['dt'].dt.day_of_week.map(factors)
    data['adjusted'] = data['baseline'] * data['weekday_factor']
    return data


def evaluate(data, method):
    if data.empty or data[['sale_amount', method]].isna().any().any():
        raise ValueError('Evaluation requires nonempty, complete predictions')
    actual, predicted = data['sale_amount'], data[method]
    if not np.isfinite(predicted).all():
        raise ValueError('Predictions must be finite')
    denom = actual.abs().sum()
    if denom == 0:
        raise ValueError('WAPE denominator is zero')
    error = predicted - actual
    return {'n': len(data), 'mae': float(error.abs().mean()),
            'wape': float(error.abs().sum() / denom), 'bias': float(error.sum() / denom)}
