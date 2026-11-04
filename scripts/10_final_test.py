"""最终测试：固定星期系数，评估每日更新的一日超前预测。"""
import duckdb
import pandas as pd
from common import check_data, output_dir

folder = output_dir()
sample = pd.read_csv(folder / '02_sample.csv', parse_dates=['dt'])
store = int(sample['store_id'].iloc[0])
ids = sorted(sample['product_id'].unique().tolist())
if sample['store_id'].nunique() != 1 or len(ids) != 20:
    raise ValueError('样本应包含一个门店和 20 个商品。')
test_path = check_data().parent / 'eval.parquet'
con = duckdb.connect()
con.register('chosen', pd.DataFrame({'product_id': ids}))
test = con.execute('''SELECT e.store_id, e.product_id, e.dt, e.sale_amount,
    e.stock_hour6_22_cnt FROM read_parquet(?) e JOIN chosen c USING (product_id)
    WHERE e.store_id = ? ORDER BY e.product_id, e.dt''', [str(test_path), store]).df()
test['dt'] = pd.to_datetime(test['dt'])
history = sample[['store_id', 'product_id', 'dt', 'sale_amount']].copy()
history['period'] = 'train'
test['period'] = 'test'
if len(test) != 140 or test.duplicated(['store_id', 'product_id', 'dt']).any():
    raise ValueError('测试集不满足每个商品 7 条且键唯一。')
combined = pd.concat([history, test], ignore_index=True).sort_values(['product_id', 'dt'])
if combined.duplicated(['store_id', 'product_id', 'dt']).any():
    raise ValueError('训练和测试数据存在重复键。')
if not combined.groupby('product_id')['dt'].diff().dropna().eq(pd.Timedelta(days=1)).all():
    raise ValueError('日期不连续，不能把 7 行当作 7 天。')

# 固定此前内部训练期的星期系数，不用测试集拟合。
fit = sample.loc[sample['split'] == 'training'].copy()
fit['weekday'] = fit['dt'].dt.day_of_week
overall = fit['sale_amount'].mean()
if overall <= 0:
    raise ValueError('训练期平均销量必须大于 0。')
factors = fit.groupby('weekday')['sale_amount'].mean() / overall
if len(factors) != 7:
    raise ValueError('训练期未覆盖全部星期。')
combined['factor'] = combined['dt'].dt.day_of_week.map(factors)
sales = combined.groupby('product_id')['sale_amount']
combined['mean_7'] = sales.transform(lambda x: x.shift(1).rolling(7, min_periods=7).mean())
combined['mean_7_weekday'] = combined['mean_7'] * combined['factor']
final = combined.loc[combined['period'] == 'test'].copy()
methods = ['mean_7', 'mean_7_weekday']
if final[methods + ['sale_amount']].isna().any().any():
    raise ValueError('测试预测或实际销量缺失。')
results = []
for method in methods:
    error = final[method] - final['sale_amount']
    denom = final['sale_amount'].abs().sum()
    if denom == 0:
        raise ValueError('测试集销量总和为 0。')
    results.append({'method': method, 'n': len(final), 'MAE': error.abs().mean(),
                    'WAPE': error.abs().sum() / denom, 'bias': error.sum() / denom})
results = pd.DataFrame(results)
final.to_csv(folder / '10_test_predictions.csv', index=False, encoding='utf-8-sig')
results.to_csv(folder / '10_test_metrics.csv', index=False, encoding='utf-8-sig')
print('测试日期:', final['dt'].min().date(), '至', final['dt'].max().date())
print(results.to_string(index=False, formatters={'MAE': '{:.3f}'.format,
    'WAPE': '{:.1%}'.format, 'bias': '{:.1%}'.format}))
