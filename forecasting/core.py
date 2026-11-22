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
    for label, values in [('Actual sales', actual), ('Predictions', predicted)]:
        if (not pd.api.types.is_numeric_dtype(values)
                or pd.api.types.is_bool_dtype(values)
                or pd.api.types.is_complex_dtype(values)):
            raise ValueError(f'{label} must be real numeric values')
        if not np.isfinite(values).all() or (values < 0).any():
            raise ValueError(f'{label} must be finite and non-negative')
    # Convert integer and unsigned columns before subtraction to prevent wraparound.
    actual = actual.to_numpy(dtype=np.float64)
    predicted = predicted.to_numpy(dtype=np.float64)
    with np.errstate(over='ignore', invalid='ignore', divide='ignore'):
        denom = np.sum(actual)
        error = predicted - actual
        absolute_error = np.abs(error)
        absolute_sum = np.sum(absolute_error)
        signed_sum = np.sum(error)
        mae = np.mean(absolute_error)
    if not np.isfinite(denom):
        raise ValueError('Actual sales total exceeds supported numerical range')
    if denom == 0:
        raise ValueError('WAPE denominator is zero')
    if not all(np.isfinite(x) for x in (absolute_sum, signed_sum, mae)):
        raise ValueError('Forecast errors exceed supported numerical range')
    with np.errstate(over='ignore', invalid='ignore', divide='ignore'):
        wape, bias = absolute_sum / denom, signed_sum / denom
    if not np.isfinite(wape) or not np.isfinite(bias):
        raise ValueError('Forecast metrics exceed supported numerical range')
    return {'n': len(data), 'mae': float(mae),
            'wape': float(wape), 'bias': float(bias)}
