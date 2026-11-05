"""Export a star schema for Power BI; keep observed sales at their original grain."""
from pathlib import Path
import json
import pandas as pd
from common import output_dir


def export(folder):
    folder = Path(folder)
    sample = pd.read_csv(folder / '02_sample.csv', parse_dates=['dt'])
    validation = pd.read_csv(folder / '08_weekday_predictions.csv', parse_dates=['dt'])
    test = pd.read_csv(folder / '10_test_predictions.csv', parse_dates=['dt'])
    test['split'] = 'test'
    columns = ['store_id', 'product_id', 'dt', 'sale_amount', 'stock_hour6_22_cnt', 'split']
    sales = pd.concat([sample[columns], test[columns]], ignore_index=True)
    forecasts = pd.concat([validation, test], ignore_index=True)
    for frame in (sales, forecasts):
        frame['series_key'] = frame['store_id'].astype(str) + '_' + frame['product_id'].astype(str)
        frame['stockout_key'] = frame['stock_hour6_22_cnt'].gt(0).astype(int)
    sales['records'] = 1
    sales['stockout_records'] = sales['stockout_key']
    if sales.duplicated(['series_key', 'dt']).any():
        raise ValueError('Observed sales keys must be unique')
    long = forecasts.melt(
        id_vars=['series_key', 'dt', 'split', 'stockout_key', 'sale_amount'],
        value_vars=['mean_7', 'mean_7_weekday'], var_name='model_key', value_name='prediction')
    if long[['prediction', 'sale_amount']].isna().any().any():
        raise ValueError('Forecasts must be complete')
    if long.duplicated(['series_key', 'dt', 'model_key']).any():
        raise ValueError('Forecast keys must be unique')
    long['error'] = long['prediction'] - long['sale_amount']
    long['abs_error'] = long['error'].abs()
    products = sales[['series_key', 'store_id', 'product_id']].drop_duplicates()
    products['product_label'] = 'Store ' + products['store_id'].astype(str) + ' / Product ' + products['product_id'].astype(str)
    dates = pd.DataFrame({'dt': pd.date_range(sales['dt'].min(), sales['dt'].max())})
    dates['weekday'] = dates['dt'].dt.day_of_week
    dates['weekday_name'] = dates['dt'].dt.day_name()
    dates['month'] = dates['dt'].dt.strftime('%Y-%m')
    frames = {
        'FactSales': sales[['series_key', 'dt', 'split', 'stockout_key', 'sale_amount', 'stock_hour6_22_cnt', 'records', 'stockout_records']],
        'FactForecast': long[['series_key', 'dt', 'split', 'stockout_key', 'model_key', 'sale_amount', 'prediction', 'error', 'abs_error']],
        'DimProduct': products, 'DimDate': dates,
        'DimModel': pd.DataFrame({'model_key': ['mean_7', 'mean_7_weekday'], 'model_name': ['7-day mean', '7-day mean + weekday']}),
        'DimSplit': pd.DataFrame({'split': ['training', 'validation', 'test']}),
        'DimStockout': pd.DataFrame({'stockout_key': [0, 1], 'stockout_label': ['No daytime stockout', 'Daytime stockout']}),
    }
    target = folder / 'powerbi'
    target.mkdir(parents=True, exist_ok=True)
    for name, frame in frames.items():
        frame.to_csv(target / f'{name}.csv', index=False, encoding='utf-8-sig', date_format='%Y-%m-%d')
    # Reconcile all DAX denominators against Python before report consumption.
    checks = []
    for (split, model), group in long.groupby(['split', 'model_key']):
        observed = sales.loc[sales['split'] == split, 'sale_amount'].sum()
        if abs(group['sale_amount'].sum() - observed) > 1e-8:
            raise ValueError('Forecast actuals do not reconcile to observed sales')
        checks.append({'split': split, 'model': model, 'n': len(group),
                       'WAPE': float(group['abs_error'].sum() / observed)})
    (target / 'reconciliation.json').write_text(json.dumps(checks, indent=2), encoding='utf-8')
    print('Power BI tables:', {k: len(v) for k, v in frames.items()})
    print('Data folder:', target.resolve())
    return frames


if __name__ == '__main__':
    export(output_dir())
