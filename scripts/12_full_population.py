"""全量门店商品分析：全量验证是探索性结果，测试集此前已查看。"""
from pathlib import Path
import duckdb
import pandas as pd
from common import check_data, output_dir

folder = output_dir()
train_path = check_data()
eval_path = train_path.parent / 'eval.parquet'
target = folder / 'powerbi_full'
target.mkdir(parents=True, exist_ok=True)
db = duckdb.connect()
db.execute('SET threads=4')
db.execute("SET memory_limit='2GB'")
db.execute('SET temp_directory = ?', [str(target / 'duckdb_tmp')])
db.read_parquet(str(train_path)).create_view('raw_train')
db.read_parquet(str(eval_path)).create_view('raw_test')
db.execute('CREATE VIEW history AS SELECT *, CAST(dt AS DATE) AS day FROM raw_train')
db.execute('CREATE VIEW test_data AS SELECT *, CAST(dt AS DATE) AS day FROM raw_test')

# 校验时间粒度：缺日期时不能将前七行当成前七天。
db.execute('''CREATE TEMP TABLE daily AS
    SELECT store_id, product_id, day, sale_amount, stock_hour6_22_cnt, 'history' AS source FROM history
    UNION ALL
    SELECT store_id, product_id, day, sale_amount, stock_hour6_22_cnt, 'test' AS source FROM test_data''')
duplicates = db.execute('''SELECT COUNT(*) FROM (SELECT store_id, product_id, day
    FROM daily GROUP BY 1,2,3 HAVING COUNT(*) > 1)''').fetchone()[0]
gaps = db.execute('''SELECT COUNT(*) FROM (SELECT day - lag(day) OVER
    (PARTITION BY store_id, product_id ORDER BY day) AS gap FROM daily) WHERE gap <> 1''').fetchone()[0]
if duplicates or gaps:
    raise ValueError(f'时间序列有重复键 {duplicates} 组、日期缺口 {gaps} 处。')
counts = db.execute('''SELECT COUNT(DISTINCT (store_id, product_id)), COUNT(DISTINCT store_id), COUNT(*)
    FROM daily''').fetchone()

# 系数只用内部训练期；随后按天更新，测试日只使用此前已知销量。
db.execute('''CREATE TEMP TABLE weekday_factor AS
    SELECT dayofweek(day) AS weekday, AVG(sale_amount) / (SELECT AVG(sale_amount) FROM daily WHERE day < DATE '2024-06-12') AS factor
    FROM daily WHERE day < DATE '2024-06-12' GROUP BY 1''')
db.execute('''CREATE TEMP TABLE scored AS
    WITH rolling AS (
      SELECT *, AVG(sale_amount) OVER (PARTITION BY store_id, product_id ORDER BY day
          ROWS BETWEEN 7 PRECEDING AND 1 PRECEDING) AS avg7,
          COUNT(sale_amount) OVER (PARTITION BY store_id, product_id ORDER BY day
          ROWS BETWEEN 7 PRECEDING AND 1 PRECEDING) AS history_n
      FROM daily
    ), prediction AS (
      SELECT r.*, f.factor, CASE WHEN source = 'test' THEN 'test' ELSE 'validation' END AS split
      FROM rolling r JOIN weekday_factor f ON dayofweek(r.day) = f.weekday
      WHERE r.day >= DATE '2024-06-12'
    )
    SELECT store_id, product_id, day, split, stock_hour6_22_cnt, sale_amount,
           avg7, avg7 * factor AS adjusted
    FROM prediction WHERE history_n = 7''')
expected = db.execute("SELECT COUNT(*) FROM daily WHERE day >= DATE '2024-06-12'").fetchone()[0]
scored = db.execute('SELECT COUNT(*) FROM scored').fetchone()[0]
if expected != scored:
    raise ValueError(f'存在无法预测的记录：预期 {expected}，实际 {scored}')

# 不把两个模型的销量加在一起；按模型分别计算误差总和及分母。
db.execute('''CREATE TEMP VIEW long_scores AS
    SELECT store_id, product_id, day, split, stock_hour6_22_cnt, sale_amount, '7-day mean' AS model, avg7 AS prediction FROM scored
    UNION ALL SELECT store_id, product_id, day, split, stock_hour6_22_cnt, sale_amount, '7-day mean + weekday', adjusted FROM scored''')
summary = db.execute('''SELECT split, model, COUNT(*) AS records,
    COUNT(DISTINCT store_id) AS stores, COUNT(DISTINCT (store_id,product_id)) AS series,
    AVG(ABS(prediction-sale_amount)) AS mae,
    SUM(ABS(prediction-sale_amount))/NULLIF(SUM(ABS(sale_amount)),0) AS wape,
    SUM(prediction-sale_amount)/NULLIF(SUM(ABS(sale_amount)),0) AS bias
    FROM long_scores GROUP BY 1,2 ORDER BY 1,2''').df()
summary.to_csv(target/'full_metrics.csv', index=False, encoding='utf-8-sig')
daily = db.execute('''SELECT day, split, store_id, model, CASE WHEN stock_hour6_22_cnt > 0 THEN 1 ELSE 0 END AS stockout_key, COUNT(*) AS records,
    SUM(sale_amount) AS observed_sales, SUM(prediction) AS predicted_sales,
    SUM(ABS(prediction-sale_amount)) AS absolute_error,
    SUM(prediction-sale_amount) AS signed_error,
    SUM(CASE WHEN stock_hour6_22_cnt > 0 THEN 1 ELSE 0 END) AS stockout_records,
    SUM(stock_hour6_22_cnt) AS stockout_hours
    FROM long_scores GROUP BY 1,2,3,4,5 ORDER BY 1,2,3,4,5''').df()
daily.to_csv(target/'full_store_day_model.csv', index=False, encoding='utf-8-sig', date_format='%Y-%m-%d')
print(f'全量：{counts[1]} 门店，{counts[0]} 序列，{counts[2]:,} 行；验证与测试 {scored:,} 行')
print(summary.to_string(index=False))
print('输出：', target)
print('注意：官方测试集此前已看过，扩展到全量后的测试结果仅作为探索性结果。')
