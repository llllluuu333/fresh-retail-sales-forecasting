"""第 1 步：检查观察单位、重复键、缺失值和缺货比例。"""

import duckdb

from common import check_data, output_dir


con = duckdb.connect()
con.read_parquet(str(check_data())).create_view("sales")

# 一行应对应一个“门店 × 商品 × 日期”。先检查规模与日期。
rows, first_day, last_day, days, series = con.execute(
    """SELECT COUNT(*), MIN(dt), MAX(dt), COUNT(DISTINCT dt),
              COUNT(DISTINCT (store_id, product_id))
       FROM sales"""
).fetchone()

# 若同一门店、商品、日期出现两行，后续的时间序列计算会有歧义。
duplicate_keys = con.execute(
    """SELECT COUNT(*) FROM (
         SELECT store_id, product_id, dt
         FROM sales GROUP BY 1, 2, 3 HAVING COUNT(*) > 1
       )"""
).fetchone()[0]

# NULL 是缺失；销量为 0 是观察到的零销量，两者不能混用。
null_sales, zero_sales, negative_sales, stockout_days, stockout_hours = con.execute(
    """SELECT
         COUNT(*) FILTER (WHERE sale_amount IS NULL),
         COUNT(*) FILTER (WHERE sale_amount = 0),
         COUNT(*) FILTER (WHERE sale_amount < 0),
         COUNT(*) FILTER (WHERE stock_hour6_22_cnt > 0),
         SUM(stock_hour6_22_cnt)
       FROM sales"""
).fetchone()

summary = f"""# 第 1 步：数据质量检查

- 行数：{rows:,}
- 日期：{first_day} 至 {last_day}，共 {days} 天
- 门店商品序列：{series:,}
- 门店 × 商品 × 日期重复键组：{duplicate_keys}
- 销量 NULL：{null_sales}；零销量：{zero_sales:,}（{zero_sales / rows:.1%}）；负销量：{negative_sales}
- 至少缺货 1 小时的记录：{stockout_days:,}（{stockout_days / rows:.1%}）
- 白天缺货小时占比：{stockout_hours / (rows * 16):.1%}（每行按 16 小时计算）

注意：缺货是“销量被截断”的问题，不等同于普通缺失值。
"""
destination = output_dir() / "01_quality_summary.md"
destination.write_text(summary, encoding="utf-8")
print(summary)
print("保存：", destination)
