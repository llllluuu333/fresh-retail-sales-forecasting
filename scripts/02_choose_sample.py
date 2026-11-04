"""第 2 步：只用训练期选门店和商品，避免用验证期结果来挑样本。"""

import duckdb
import pandas as pd

from common import check_data, output_dir


con = duckdb.connect()
con.read_parquet(str(check_data())).create_view("sales")

# 最后 14 天作为内部验证；官方 eval.parquet 暂时不打开。
last_day = con.execute("SELECT MAX(dt) FROM sales").fetchone()[0]
validation_start = (pd.Timestamp(last_day) - pd.Timedelta(days=13)).date().isoformat()

# 在验证期开始前，寻找商品数最多的门店。
store_id, product_count = con.execute(
    """SELECT store_id, COUNT(DISTINCT product_id) AS n_products
       FROM sales WHERE dt < ?
       GROUP BY store_id HAVING n_products >= 20
       ORDER BY n_products DESC, SUM(sale_amount) DESC, store_id
       LIMIT 1""",
    [validation_start],
).fetchone()

# 再根据训练期累计销量，选这个门店的 20 种商品。
products = con.execute(
    """SELECT product_id FROM sales
       WHERE store_id = ? AND dt < ?
       GROUP BY product_id HAVING COUNT(*) >= 70
       ORDER BY SUM(sale_amount) DESC, product_id
       LIMIT 20""",
    [store_id, validation_start],
).fetchall()
product_ids = [row[0] for row in products]
assert len(product_ids) == 20

# 问号占位符把参数与 SQL 分开，不拼接用户提供的数据值。
placeholders = ",".join("?" for _ in product_ids)
frame = con.execute(
    f"""SELECT dt, city_id, store_id, product_id, sale_amount,
               stock_hour6_22_cnt, discount, holiday_flag, activity_flag,
               precpt, avg_temperature, avg_humidity, avg_wind_level
        FROM sales WHERE store_id = ? AND product_id IN ({placeholders})
        ORDER BY product_id, dt""",
    [store_id, *product_ids],
).df()
frame["is_stockout"] = frame["stock_hour6_22_cnt"] > 0
frame["split"] = frame["dt"].ge(validation_start).map(
    {True: "validation", False: "training"}
)

destination = output_dir() / "02_sample.csv"
frame.to_csv(destination, index=False, encoding="utf-8-sig")
print(f"验证从 {validation_start} 开始；门店 {store_id} 在训练期有 {product_count} 种商品")
print(f"选出 20 种商品，导出 {len(frame):,} 行：{destination}")

# 思考：如果用全部 90 天销量挑商品，验证结果会出现什么偏差？
